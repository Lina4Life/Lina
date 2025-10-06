import streamlit as st
from pathlib import Path
from PIL import Image
import io
import sqlite3
import sqlite3 as _sqlite3
import streamlit.components.v1 as components
import random
import os
import json
import datetime
import base64
import hashlib
import hmac

# set Streamlit page title and icon
try:
    st.set_page_config(page_title="For my Wife <3 <3 <3", page_icon="❤️")
except Exception:
    pass

# Ensure the browser can find the manifest and theme color for PWA install flows
try:
        components.html("""
        <script>
        (function(){
            try{
                if(!document.querySelector('link[rel="manifest"]')){
                    const l = document.createElement('link'); l.rel='manifest'; l.href='/static/manifest.json'; document.head.appendChild(l);
                }
                if(!document.querySelector('meta[name="theme-color"]')){
                    const m = document.createElement('meta'); m.name='theme-color'; m.content='#b30f3d'; document.head.appendChild(m);
                }
            }catch(e){console.error(e)}
        })();
        </script>
        """, height=0)
except Exception:
        pass

# reportlab is optional — not all environments have it installed
HAVE_REPORTLAB = True
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except Exception:
    HAVE_REPORTLAB = False


# Users storage helpers
USERS_FILE = Path('users.json')

def load_users():
    try:
        if USERS_FILE.exists():
            return json.loads(USERS_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def save_users(users_dict: dict):
    try:
        USERS_FILE.write_text(json.dumps(users_dict, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception:
        return False


def init_users_if_missing():
    # create a simple users.json with two accounts if it does not exist
    if not USERS_FILE.exists():
        defaults = {"Youssef": "youssef123", "Lina": "lina123"}
        save_users(defaults)


init_users_if_missing()
users = load_users()

# Simple forced-login: if not authenticated, show a login screen and stop further rendering
if 'auth_user' not in st.session_state:
    st.session_state['auth_user'] = None

if not st.session_state.get('auth_user'):
    st.markdown("<div style='text-align:center; margin-top:16px'>", unsafe_allow_html=True)
    st.markdown("<h2>Login required</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Use a form for login to ensure single submission behavior
    with st.form('login_form'):
        if users:
            username = st.selectbox('Username', list(users.keys()), key='login_user')
        else:
            username = st.text_input('Username', key='login_user')
        password = st.text_input('Password', type='password', key='login_pwd')
        submitted = st.form_submit_button('Login')

    def verify_password(password: str, stored: str) -> bool:
        try:
            if not isinstance(stored, str):
                return False
            if not stored.startswith('pbkdf2$'):
                return False
            parts = stored.split('$')
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = base64.b64decode(parts[2])
            dk = base64.b64decode(parts[3])
            test = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
            return hmac.compare_digest(test, dk)
        except Exception:
            return False

    if submitted:
        stored = users.get(username) if users else None
        ok = False
        if stored:
            if isinstance(stored, str) and stored.startswith('pbkdf2$'):
                ok = verify_password(password, stored)
            else:
                ok = (stored == password)
        if ok:
            st.session_state['auth_user'] = username
            st.success(f'Logged in as {username}')
            try:
                st.experimental_rerun()
            except Exception:
                pass
        else:
            st.error('Invalid username or password')

    # Prevent rest of the app from rendering until logged in
    if not st.session_state.get('auth_user'):
        st.stop()

# Provide a persistent logout control in the sidebar
with st.sidebar:
    if st.button('Logout'):
        st.session_state['auth_user'] = None
        try:
            st.experimental_rerun()
        except Exception:
            pass

# Top tabs (Play, Journal, Map removed)
tab = st.tabs(["Home", "Messages", "Songs", "Call", "Letters", "Countdowns", "Notifications", "Feeling"])

# Messages storage
MESSAGES_FILE = Path("messages.json")
# Storage backend: 'file' (default) or 'sqlite'
STORAGE = os.getenv('MESSAGE_STORAGE', 'file').lower()
DB_FILE = Path("messages.db")


def init_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            recipient TEXT,
            text TEXT,
            time TEXT,
            read INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def load_messages():
    if STORAGE == 'sqlite':
        if not DB_FILE.exists():
            return []
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, sender as 'from', recipient as 'to', text, time, read FROM messages ORDER BY id ASC")
        rows = c.fetchall()
        msgs = []
        for r in rows:
            msgs.append({'from': r['from'], 'to': r['to'], 'text': r['text'], 'time': r['time'], 'read': bool(r['read'])})
        conn.close()
        return msgs

    # default: file
    if MESSAGES_FILE.exists():
        try:
            return json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []


def add_message(msg):
    if STORAGE == 'sqlite':
        init_db()
        conn = sqlite3.connect(str(DB_FILE))
        c = conn.cursor()
        c.execute("INSERT INTO messages (sender, recipient, text, time, read) VALUES (?, ?, ?, ?, ?)",
                  (msg.get('from'), msg.get('to'), msg.get('text'), msg.get('time'), int(bool(msg.get('read')))))
        conn.commit()
        conn.close()
        return

    # file backend: read-modify-write
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    msgs.append(msg)
    try:
        MESSAGES_FILE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def mark_all_read(recipient=None):
    # Mark all messages as read for the given recipient (defaults to current auth user)
    recipient = recipient or st.session_state.get('auth_user')
    if not recipient:
        return
    if STORAGE == 'sqlite':
        if not DB_FILE.exists():
            return
        conn = sqlite3.connect(str(DB_FILE))
        c = conn.cursor()
        c.execute("UPDATE messages SET read = 1 WHERE recipient = ? AND read = 0", (recipient,))
        conn.commit()
        conn.close()
        return

    # file
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    changed = False
    for m in msgs:
        if m.get('to') == recipient and not m.get('read'):
            m['read'] = True
            changed = True
    if changed:
        try:
            MESSAGES_FILE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass


def save_messages_file(msgs):
    try:
        MESSAGES_FILE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def find_message_index_by_time(msgs, time_str):
    for idx, m in enumerate(msgs):
        if m.get('time') == time_str:
            return idx
    return None


def edit_message_by_time(time_str, new_text):
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    idx = find_message_index_by_time(msgs, time_str)
    if idx is None:
        return False
    msgs[idx]['text'] = new_text
    save_messages_file(msgs)
    st.session_state.messages = load_messages()
    return True


def delete_message_by_time(time_str):
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    idx = find_message_index_by_time(msgs, time_str)
    if idx is None:
        return False
    msgs.pop(idx)
    save_messages_file(msgs)
    st.session_state.messages = load_messages()
    return True


def add_reaction_by_time(time_str, emoji, by):
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    idx = find_message_index_by_time(msgs, time_str)
    if idx is None:
        return False
    msg = msgs[idx]
    reactions = msg.get('reactions', [])
    reactions.append({'by': by, 'emoji': emoji, 'time': datetime.datetime.utcnow().isoformat()})
    msgs[idx]['reactions'] = reactions
    save_messages_file(msgs)
    st.session_state.messages = load_messages()
    return True


def add_reply(parent_time, reply_msg):
    # file backend only (keeps simple)
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    idx = find_message_index_by_time(msgs, parent_time)
    if idx is None:
        return False
    parent = msgs[idx]
    parent.setdefault('replies', [])
    parent['replies'].append(reply_msg)
    save_messages_file(msgs)
    # update session state copy
    for m in st.session_state.messages:
        if m.get('time') == parent_time:
            m.setdefault('replies', [])
            m['replies'].append(reply_msg)
            break
    return True


def add_reaction(parent_time, emoji, who):
    msgs = []
    if MESSAGES_FILE.exists():
        try:
            msgs = json.loads(MESSAGES_FILE.read_text(encoding='utf-8'))
        except Exception:
            msgs = []
    idx = find_message_index_by_time(msgs, parent_time)
    if idx is None:
        return False
    parent = msgs[idx]
    reacts = parent.setdefault('reactions', {})
    reacts[emoji] = reacts.get(emoji, 0) + 1
    save_messages_file(msgs)
    # update session state copy
    for m in st.session_state.messages:
        if m.get('time') == parent_time:
            m.setdefault('reactions', {})
            m['reactions'][emoji] = m['reactions'].get(emoji, 0) + 1
            break
    return True


def notify_webhook(entry):
    url = os.getenv('WEBHOOK_URL')
    if not url:
        return
    try:
        import json as _json
        from urllib import request as _request
        req = _request.Request(url, data=_json.dumps(entry).encode('utf-8'), headers={'Content-Type': 'application/json'})
        _request.urlopen(req, timeout=2)
    except Exception:
        pass


# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = load_messages()
if 'unread' not in st.session_state:
    current_user = st.session_state.get('auth_user')
    st.session_state.unread = sum(1 for m in st.session_state.messages if (m.get('to') == current_user and not m.get('read', False))) if current_user else 0
if 'ttt_board' not in st.session_state:
    st.session_state.ttt_board = [""] * 9
    st.session_state.ttt_turn = 'X'
    st.session_state.ttt_winner = None

# --------------------------
# Home tab
# --------------------------
with tab[0]:


    # Left: image if available
    assets = [p for p in Path('.').glob('*') if p.suffix.lower() in ['.png', '.jpg', '.jpeg']]
    selected_image = None
    if assets:
        for p in assets:
            if 'lina' in p.name.lower() or 'cutie' in p.name.lower() or 'good' in p.name.lower() or 'rose' in p.name.lower():
                selected_image = p
                break
        if not selected_image:
            selected_image = assets[0]

    col1, col2 = st.columns([1, 2])
    with col1:
        if selected_image:
            try:
                img = Image.open(selected_image)
                st.image(img, width='stretch', caption=selected_image.name)
            except Exception:
                st.write(":heart: image preview not available")
        else:
            st.markdown("<div style='text-align:center; font-size:48px;'>❤️</div>", unsafe_allow_html=True)

    with col2:
        # render the love-text HTML safely (avoid raw tags showing up as text)
        st.markdown("<div class='love-text'>", unsafe_allow_html=True)
        st.write("Lina, every moment with you feels like a warm sunrise. Your smile lights up my day and your laugh is my favorite song.")
        st.write("I made this little page to remind you how much you're loved — today and always.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Poems carousel (reads from poems/ folder) — show a random poem on first load
    POEMS_DIR = Path('poems')
    poems = []
    if POEMS_DIR.exists():
        for p in sorted(POEMS_DIR.iterdir()):
            if p.suffix.lower() in ['.txt', '.md']:
                try:
                    poems.append({'type':'text', 'path':p, 'title':p.stem, 'body': p.read_text(encoding='utf-8')})
                except Exception:
                    continue
            elif p.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                poems.append({'type':'image', 'path':p, 'title':p.stem})

    if poems:
        # initialize index
        if 'poem_index' not in st.session_state:
            st.session_state.poem_index = random.randrange(len(poems))

        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:8px'>Today\'s poem</h3>", unsafe_allow_html=True)

        cols = st.columns([1,3,1])
        with cols[0]:
            if st.button('Prev'):
                st.session_state.poem_index = (st.session_state.poem_index - 1) % len(poems)
        with cols[2]:
            if st.button('Next'):
                st.session_state.poem_index = (st.session_state.poem_index + 1) % len(poems)

        # select box to jump
        titles = [f"{i+1}. {p['title']}" for i,p in enumerate(poems)]
        pick = st.selectbox('Pick a poem', titles, index=st.session_state.poem_index, key='poem_pick')
        # sync index if changed via selectbox
        if pick and pick != titles[st.session_state.poem_index]:
            try:
                st.session_state.poem_index = titles.index(pick)
            except Exception:
                pass

        cur = poems[st.session_state.poem_index]
        st.markdown(f"**{cur.get('title','Poem')}**")
        if cur['type'] == 'text':
            st.write(cur.get('body',''))
        else:
            try:
                st.image(str(cur['path']), use_column_width=True)
            except Exception:
                st.write('[image]')


    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.button('Show balloons 🎈'):
        st.balloons()
        st.success("I hope this made you smile my love ❤️❤️❤️")

    st.markdown('---')

    # Printable love note — hidden inside an expander to avoid occupying top of the page
    with st.expander('Printable love note'):
        st.markdown("<h2 style='text-align:center;'>Printable love note</h2>", unsafe_allow_html=True)
        custom_message = st.text_area('Customize the note for Lina', value="Lina, you are my sunshine. I love you.")
        sender_name = st.text_input("Sender name", value="From, your love")

        if HAVE_REPORTLAB:
            def create_pdf(message: str, sender: str) -> bytes:
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # Draw a soft red border
                c.setStrokeColorRGB(0.85, 0.18, 0.35)
                c.setLineWidth(4)
                margin = 15 * mm
                c.rect(margin, margin, width - 2*margin, height - 2*margin)

                # Title
                c.setFont('Helvetica-Bold', 28)
                c.setFillColorRGB(0.82, 0.11, 0.35)
                c.drawCentredString(width/2, height - 50*mm, 'For Lina')

                # Message
                textobject = c.beginText()
                textobject.setTextOrigin(30*mm, height - 80*mm)
                textobject.setFont('Times-Roman', 14)
                textobject.setFillColorRGB(0.3, 0, 0.05)
                for line in message.split('\n'):
                    textobject.textLine(line)
                c.drawText(textobject)

                # Sender
                c.setFont('Times-Italic', 12)
                c.drawRightString(width - 30*mm, 30*mm, sender)

                c.showPage()
                c.save()
                buffer.seek(0)
                return buffer.read()

            if st.button('Generate & download PDF'):
                pdf_bytes = create_pdf(custom_message, sender_name)
                st.download_button('Download love note (PDF)', data=pdf_bytes, file_name='For_Lina_note.pdf', mime='application/pdf')
        else:
            st.warning(
                "PDF generation requires the `reportlab` package. You can install it in your virtual environment:\n"
                "& \".venv\\Scripts\\Activate.ps1\"; pip install reportlab  (PowerShell)\n\n"
                "If you prefer not to install it, you can download the note as plain text instead."
            )
            if st.button('Download note as .txt'):
                txt_bytes = custom_message.encode('utf-8')
                st.download_button('Download text note', data=txt_bytes, file_name='For_Lina_note.txt', mime='text/plain')

# Play tab removed per user request

# --------------------------
# Messages tab (refactored)
# --------------------------
with tab[1]:
    st.markdown("<h2 style='text-align:center;'>Messages <span class='heart-decor'>💌</span></h2>", unsafe_allow_html=True)

    current_user = st.session_state.get('auth_user')
    st.write(f"Sending as **{current_user}**")

    # UX options
    # Composer is fixed at bottom for easier typing below the chat
    composer_pos = 'Bottom'

    # ensure composer state
    st.session_state.setdefault('composer_text', '')

    # helper: save uploaded image + create thumbnail
    def save_image_and_thumb(uploaded_file):
        MEDIA_DIR = Path('message_media')
        MEDIA_DIR.mkdir(exist_ok=True)
        try:
            data = uploaded_file.read()
            ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            safe_name = f"{ts}_{uploaded_file.name}"
            dest = MEDIA_DIR / safe_name
            dest.write_bytes(data)
            # create thumbnail
            try:
                img = Image.open(io.BytesIO(data))
                img.thumbnail((480, 480))
                thumb_buf = io.BytesIO()
                img.save(thumb_buf, format='PNG')
                thumb_name = f"thumb_{safe_name}.png"
                (MEDIA_DIR / thumb_name).write_bytes(thumb_buf.getvalue())
            except Exception:
                thumb_name = None
            return {'file': safe_name, 'thumb': thumb_name}
        except Exception:
            return None

    # composer renderer (can be shown top or bottom)
    def render_composer():
        emojis = ['❤️','😘','😊','😍','🎶','😭','👍']
        cols = st.columns(len(emojis))
        for i, e in enumerate(emojis):
            if cols[i].button(e, key=f'emoji_{i}'):
                st.session_state['composer_text'] = st.session_state.get('composer_text', '') + e
        # Composer UI below emojis (outside the emoji button loop)
        st.write('Attach image(s) (optional)')
        with st.form(f'composer_form_{composer_pos}'):
            img_upload = st.file_uploader('', type=['png','jpg','jpeg','gif'], accept_multiple_files=True, key=f'msg_images_{composer_pos}')
            msg_text = st.text_area('Message', height=120, key='composer_text')

            # Voice input: inject a small Web Speech API control (browser must support it)
            try:
                js_html = """
                <div style='margin-top:8px; margin-bottom:8px; text-align:left;'>
                  <button id='start_rec' style='padding:8px;border-radius:8px;'>Start voice</button>
                  <button id='stop_rec' style='padding:8px;border-radius:8px;margin-left:6px;'>Stop</button>
                  <label style='margin-left:12px; font-size:13px; color:#6a1330;'>Transcription will appear in the message box.</label>
                  <script>
                    (function(){
                      const start = document.getElementById('start_rec');
                      const stop = document.getElementById('stop_rec');
                      let recognition = null;
                      if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
                        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                        recognition = new SR();
                        recognition.lang = 'en-US';
                        recognition.interimResults = true;
                        recognition.continuous = true;
                        recognition.onresult = function(e){
                          let interim = '';
                          let final = '';
                          for(let i=e.resultIndex;i<e.results.length;i++){
                            if(e.results[i].isFinal) final += e.results[i][0].transcript;
                            else interim += e.results[i][0].transcript;
                          }
                          // find textarea by placeholder or name
                          const ta = Array.from(document.querySelectorAll('textarea')).find(t=>t.placeholder && t.placeholder.toLowerCase().includes('message')) || document.querySelector('textarea');
                          if(ta){
                            ta.value = (ta.value||'') + final + interim;
                            ta.dispatchEvent(new Event('input', {bubbles:true}));
                          }
                        };
                      } else {
                        start.disabled = true; stop.disabled = true;
                        const p = document.createElement('span'); p.innerText=' (Voice not supported in this browser)'; p.style.color='#a00'; start.parentNode.appendChild(p);
                      }
                      start.addEventListener('click', ()=>{ if(recognition) recognition.start(); start.disabled=true; stop.disabled=false; });
                      stop.addEventListener('click', ()=>{ if(recognition) recognition.stop(); start.disabled=false; stop.disabled=true; });
                    })();
                  </script>
                </div>
                """
                components.html(js_html, height=90)
            except Exception:
                pass

            submitted = st.form_submit_button('Send')

        if submitted and (msg_text.strip() or (img_upload and len(img_upload) > 0)):
            recipient = 'Lina' if current_user == 'Youssef' else 'Youssef'
            entry = {
                'from': current_user,
                'to': recipient,
                'text': msg_text.strip(),
                'time': datetime.datetime.utcnow().isoformat(),
                'read': False,
                'images': []
            }
            if img_upload:
                for f in img_upload:
                    saved = save_image_and_thumb(f)
                    if saved:
                        entry['images'].append(saved)

            st.session_state.messages.append(entry)
            add_message(entry)
            # Try to notify push server so subscribed devices receive a background notification
            try:
                def send_push_trigger(recipient, message_text):
                    import requests
                    try:
                        requests.post('http://localhost:5001/push', json={'message': f'New message for {recipient}: {message_text}'}, timeout=2)
                    except Exception:
                        pass
                try:
                    # fire-and-forget
                    send_push_trigger(entry.get('to'), entry.get('text'))
                except Exception:
                    pass
            except Exception:
                pass
            # recompute unread
            st.session_state.unread = sum(1 for m in st.session_state.messages if (m.get('to') == current_user and not m.get('read', False)))
            st.session_state['clear_composer'] = True
            try:
                st.session_state[f'msg_images_{composer_pos}'] = None
            except Exception:
                pass
            st.success('Message sent')
            # auto-refresh to show message at once (best-effort)
            try:
                st.experimental_rerun()
            except Exception:
                pass

    # After rendering messages, auto-scroll the container so newest messages are visible
    try:
        if composer_pos == 'Bottom':
            components.html("""
            <script>
            const el = document.querySelector('[data-testid="stMarkdownContainer"] div');
            // try to find our message container by style marker
            const msg = document.querySelector('div[style*="max-height:520px"]');
            if(msg){ msg.scrollTop = msg.scrollHeight; }
            </script>
            """, height=0)
        else:
            components.html("""
            <script>
            const msg = document.querySelector('div[style*="max-height:520px"]');
            if(msg){ msg.scrollTop = 0; }
            </script>
            """, height=0)
    except Exception:
        pass

    # Render composer at top if selected
    if composer_pos == 'Top':
        render_composer()

    st.markdown('---')

    # Messages container
    # Chat styling (dark theme) — matches the screenshot with left/right bubbles, avatars and timestamps
    chat_css = """
    <style>
    .chat-container{max-height:520px; overflow:auto; padding:12px; border-radius:12px; background:#0b0c0e; color:#fff;}
    .message-row{display:flex; margin-bottom:12px; align-items:flex-start;}
    .message-left{justify-content:flex-start;}
    .message-right{justify-content:flex-end;}
    .message-bubble{max-width:68%; padding:10px 14px; border-radius:14px; background:#16181b; color:#fff; box-shadow: 0 4px 12px rgba(0,0,0,0.4);}
    .message-bubble.message-right{background:linear-gradient(135deg,#6a0120,#b30f3d); border-radius:14px 14px 4px 14px;}
    .meta-row{display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:14px; color:#ffd6dd;}
    .avatar{font-size:16px; margin-right:6px;}
    .meta-name{font-weight:700;}
    .meta-time{font-size:12px; color:#f0d7db; opacity:0.9; margin-left:6px;}
    .body{white-space:pre-wrap; font-size:15px; color:#fff;}
    img.chat-thumb{max-width:100%; border-radius:10px; margin-top:8px; box-shadow:0 6px 18px rgba(0,0,0,0.3);}
    </style>
    """
    st.markdown(chat_css + "<div class='chat-container'>", unsafe_allow_html=True)

    # If the URL contains msg_time & action=menu, show a small message action UI (Edit/Delete/React)
    params = st.experimental_get_query_params()
    selected_msg_time = params.get('msg_time', [None])[0]
    selected_action = params.get('action', [None])[0]
    if selected_msg_time and selected_action == 'menu':
        # show actions container
        with st.container():
            st.markdown('### Message actions')
            st.write(f'Message time: {selected_msg_time}')
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                if st.button('Edit', key=f'edit_btn_{selected_msg_time}'):
                    # show edit box
                    idx = find_message_index_by_time(st.session_state.messages, selected_msg_time)
                    orig = ''
                    if idx is not None:
                        orig = st.session_state.messages[idx].get('text','')
                    new_text = st.text_area('Edit message', value=orig, key=f'edit_area_{selected_msg_time}')
                    if st.button('Save', key=f'save_{selected_msg_time}'):
                        if edit_message_by_time(selected_msg_time, new_text):
                            st.success('Message edited')
                            st.experimental_set_query_params()
                            st.experimental_rerun()
            with col2:
                if st.button('Delete', key=f'del_btn_{selected_msg_time}'):
                    if delete_message_by_time(selected_msg_time):
                        st.success('Message deleted')
                        st.experimental_set_query_params()
                        st.experimental_rerun()
            with col3:
                st.markdown('React:')
                emojis = ['❤️','😍','😊','😢','😠','👍']
                for e in emojis:
                    if st.button(e, key=f'react_{selected_msg_time}_{e}'):
                        if add_reaction_by_time(selected_msg_time, e, st.session_state.get('auth_user')):
                            st.success('Reacted')
                            st.experimental_set_query_params()
                            st.experimental_rerun()

    if st.session_state.get('unread'):
        st.info(f"{current_user} has {st.session_state.get('unread')} unread message(s)")

    msgs = st.session_state.messages[:]  # copy
    # Decide order: newest-first if composer at top (so new messages are visible without scrolling)
    if composer_pos == 'Top':
        msgs = list(reversed(msgs))

    for m in msgs:
        sender_name = m.get('from', '')
        is_me = (sender_name == current_user)
        try:
            ts = datetime.datetime.fromisoformat(m.get('time'))
            ts_str = ts.strftime('%b %d %H:%M')
        except Exception:
            ts_str = m.get('time', '')

        avatar = '💖' if sender_name.lower().startswith('l') else '💌'
        container_class = 'message-row message-right' if is_me else 'message-row message-left'
        bubble_class = 'message-bubble message-right' if is_me else 'message-bubble'

        # Build the message bubble HTML
        # Assign an id based on timestamp so JS can refer to it (timestamps should be unique enough here)
        msg_time_id = m.get('time', '')
        safe_id = msg_time_id.replace(':','_').replace('.','_') if msg_time_id else f"msg_{random.randint(1000,9999)}"
        html = f"""
        <div id="{safe_id}" class="{container_class}">
          <div class="{bubble_class}">
            <div class='meta-row'><span class='avatar'>{avatar}</span><span class='meta-name'>{sender_name}</span><span class='meta-time'>{ts_str}</span></div>
            <div class='body'>{m.get('text','')}</div>
            <div class='msg-actions' style='float:right; margin-top:6px; font-size:18px; cursor:pointer;' data-msgtime="{msg_time_id}">⋯</div>
        """

        # Inline images into the bubble when available
        imgs = m.get('images', []) or []
        for im in imgs:
            try:
                if isinstance(im, str):
                    p = Path('message_media') / im
                    thumb = Path('message_media') / f"thumb_{im}.png"
                else:
                    p = Path('message_media') / im.get('file')
                    thumb = Path('message_media') / (im.get('thumb') or f"thumb_{im.get('file')}.png")

                src = None
                if thumb.exists():
                    src = thumb.as_posix()
                elif p.exists():
                    src = p.as_posix()

                if src:
                    # Use file URL so browser can load the local image
                    html += f"<img class='chat-thumb' src='file://{src}' />"
            except Exception:
                # ignore any image rendering issues
                continue

        html += "</div></div>"
        st.markdown(html, unsafe_allow_html=True)
        # render reactions under message (if any)
        reacts = m.get('reactions', []) or []
        if reacts:
            react_html = "<div style='margin-top:6px; font-size:16px; display:flex; gap:8px;'>"
            for r in reacts:
                react_html += f"<div title='by {r.get('by')}' style='padding:4px 8px; background:rgba(255,255,255,0.06); border-radius:12px;'>{r.get('emoji')}</div>"
            react_html += "</div>"
            st.markdown(react_html, unsafe_allow_html=True)
        # images were inlined into the bubble above; no separate st.image fallback here

    st.markdown('</div>', unsafe_allow_html=True)

    # Client JS: wire the per-message '⋯' element, right-click, and long-press to open the action UI
    try:
        components.html("""
        <script>
        (function(){
            function openMenuFor(msgtime){
                try{
                    const params = new URLSearchParams(window.location.search);
                    params.set('msg_time', msgtime);
                    params.set('action', 'menu');
                    // set and reload to let Streamlit read params and render the action UI
                    window.location.search = params.toString();
                }catch(e){console.error(e)}
            }

            // Click on the three-dots button
            document.querySelectorAll('.msg-actions').forEach(function(el){
                el.addEventListener('click', function(ev){
                    ev.stopPropagation();
                    const t = el.getAttribute('data-msgtime');
                    if(t) openMenuFor(t);
                });
            });

            // Right-click on a message row (desktop)
            document.querySelectorAll('.message-row').forEach(function(row){
                row.addEventListener('contextmenu', function(ev){
                    ev.preventDefault();
                    // try to find data-msgtime inside
                    const btn = row.querySelector('.msg-actions');
                    const t = btn ? btn.getAttribute('data-msgtime') : null;
                    if(t) openMenuFor(t);
                });
            });

            // Long-press for touch devices
            let touchTimer = null;
            document.querySelectorAll('.message-row').forEach(function(row){
                row.addEventListener('touchstart', function(ev){
                    if(touchTimer) clearTimeout(touchTimer);
                    touchTimer = setTimeout(function(){
                        const btn = row.querySelector('.msg-actions');
                        const t = btn ? btn.getAttribute('data-msgtime') : null;
                        if(t) openMenuFor(t);
                    }, 600);
                });
                ['touchend','touchcancel','touchmove'].forEach(function(evName){
                    row.addEventListener(evName, function(){ if(touchTimer) { clearTimeout(touchTimer); touchTimer = null; } });
                });
            });
        })();
        </script>
        """, height=0)
    except Exception:
        pass

    if composer_pos == 'Bottom':
        st.markdown('---')
        render_composer()

    # Auto-refresh toggle (client-side) to pick up messages sent from the other user
    auto_refresh = st.checkbox('Auto-refresh chat (every 8s)', value=True, help='When enabled the page will reload every few seconds to show new messages from the other side')
    try:
        auto_flag = 'true' if auto_refresh else 'false'
        js = """
        <script>
        (function() {{
            // Floating composer: try to find the Send button and pin its container to bottom
            function pinComposer(){{
                const buttons = Array.from(document.querySelectorAll('button'));
                const sendBtn = buttons.find(b => b.innerText && b.innerText.trim().toLowerCase() === 'send');
                if(!sendBtn) return;
                let el = sendBtn.closest('[data-testid]') || sendBtn.parentElement;
                if(!el) el = sendBtn.parentElement;
                el.style.position = 'fixed';
                el.style.left = '8px';
                el.style.right = '8px';
                el.style.bottom = '8px';
                el.style.zIndex = '9999';
                el.style.background = 'rgba(255,255,255,0.96)';
                el.style.padding = '8px';
                el.style.borderRadius = '10px';
                el.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
            }}
            // attempt pin a few times (Streamlit renders asynchronously)
            for(let i=0;i<8;i++) setTimeout(pinComposer, i*500);

            // Auto refresh when enabled
            const auto = %s;
            if(auto){
                setInterval(()=>{
                    // don't reload if user is typing
                    const active = document.activeElement;
                    if(active && (active.tagName==='INPUT' || active.tagName==='TEXTAREA')) return;
                    window.location.reload();
                }, 8000);
            }
        })();
        </script>
        """ % (auto_flag)
        components.html(js, height=0)
    except Exception:
        pass

    # Mark read button
    if st.button('Mark all as read'):
        changed = False
        for m in st.session_state.messages:
            if m.get('to') == current_user and not m.get('read'):
                m['read'] = True
                changed = True
        if changed:
            mark_all_read(current_user)
            st.session_state.unread = 0
            st.success('Marked as read')


# --------------------------
# Songs tab
# --------------------------
SONGS_DIR = Path('songs')
SONGS_DIR.mkdir(exist_ok=True)
SONGS_DB = Path('songs.db')

def init_songs_db():
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    # create table with cover_filename column (safe for new DBs)
    c.execute(
        '''CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            orig_name TEXT,
            uploader TEXT,
            time TEXT,
            cover_filename TEXT
        )'''
    )
    # ensure legacy DBs get the new column
    try:
        c.execute("PRAGMA table_info(songs)")
        cols = [r[1] for r in c.fetchall()]
        if 'cover_filename' not in cols:
            try:
                c.execute('ALTER TABLE songs ADD COLUMN cover_filename TEXT')
            except Exception:
                pass
    except Exception:
        pass
    conn.commit()
    conn.close()

def add_song_record(filename, orig_name, uploader, cover_filename=None):
    """Insert or replace a song record. cover_filename is optional and stored in the DB."""
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    try:
        c.execute(
            'INSERT OR REPLACE INTO songs (filename, orig_name, uploader, time, cover_filename) VALUES (?, ?, ?, ?, ?)',
            (filename, orig_name, uploader, datetime.datetime.utcnow().isoformat(), cover_filename)
        )
        conn.commit()
    except Exception:
        pass
    conn.close()

def list_songs():
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    c.execute('SELECT filename, orig_name, uploader, time, cover_filename FROM songs ORDER BY time DESC')
    rows = c.fetchall()
    conn.close()
    return [{'filename': r[0], 'orig_name': r[1], 'uploader': r[2], 'time': r[3], 'cover_filename': r[4]} for r in rows]

def delete_song_record(filename):
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    # fetch cover filename so caller can remove the cover file too
    try:
        c.execute('SELECT cover_filename FROM songs WHERE filename = ?', (filename,))
        row = c.fetchone()
        cover = row[0] if row else None
    except Exception:
        cover = None
    try:
        c.execute('DELETE FROM songs WHERE filename = ?', (filename,))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return cover


def migrate_songs_to_db():
    """Scan the songs directory and add any files that aren't recorded in the DB.
    Tries to associate cover_ files with their audio/video by filename inclusion.
    """
    init_songs_db()
    existing = set(r['filename'] for r in list_songs())
    # map audio filename -> cover filename (if cover contains the audio filename)
    cover_map = {}
    try:
        for p in SONGS_DIR.iterdir():
            if not p.is_file():
                continue
            if p.name.startswith('cover_'):
                # try to find an audio/video filename inside the cover filename
                for q in SONGS_DIR.iterdir():
                    if not q.is_file() or q.name.startswith('cover_'):
                        continue
                    if q.name in p.name:
                        cover_map[q.name] = p.name
                        break
    except Exception:
        pass

    # Add any media files not yet in DB
    try:
        for p in SONGS_DIR.iterdir():
            if not p.is_file():
                continue
            if p.name.startswith('cover_'):
                continue
            if p.name in existing:
                continue
            # determine a reasonable orig_name by stripping a leading timestamp if present
            parts = p.name.split('_', 1)
            orig = parts[1] if len(parts) > 1 else p.name
            uploader = 'migrated'
            cover = cover_map.get(p.name)
            add_song_record(p.name, orig, uploader, cover)
    except Exception:
        pass

with tab[2]:
    st.markdown("<h2 style='text-align:center;'>Songs</h2>", unsafe_allow_html=True)
    st.write("Upload voice recordings or short video recordings (mp3, wav, m4a, ogg, mp4) and play them here.")

    uploader_name = st.session_state.get('auth_user')
    st.write(f"Uploading as **{uploader_name}**")
    uploaded = st.file_uploader('Upload recording(s)', type=['mp3', 'wav', 'm4a', 'ogg', 'mp4'], accept_multiple_files=True)
    cover_upload = st.file_uploader('Optional cover image (PNG/JPG)', type=['png','jpg','jpeg'], accept_multiple_files=False, key='cover_upload')
    if uploaded:
        for f in uploaded:
            try:
                data = f.read()
                ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                safe_name = f"{ts}_{f.name}"
                dest = SONGS_DIR / safe_name
                dest.write_bytes(data)
                # save optional cover if provided
                cover_name = None
                if cover_upload:
                    try:
                        cdata = cover_upload.read()
                        cover_name = f"cover_{ts}_{cover_upload.name}"
                        (SONGS_DIR / cover_name).write_bytes(cdata)
                    except Exception:
                        cover_name = None
                add_song_record(safe_name, f.name, uploader_name, cover_name)
                st.success(f"Uploaded {f.name}")
            except Exception as e:
                st.error(f"Failed to save {f.name}: {e}")

    st.markdown('---')

    # Migrate any files sitting in the songs/ folder into the DB (one-time safe op)
    try:
        migrate_songs_to_db()
    except Exception:
        pass

    # List available songs (from DB)
    items = list_songs()
    if not items:
        st.info('No songs uploaded yet — use the uploader above to add recordings.')
    else:
        for i, info in enumerate(items):
            card_cols = st.columns([1,4,1])
            cover_path = None
            # try to find a cover image in songs dir matching pattern
            for candidate in SONGS_DIR.iterdir():
                if candidate.name.startswith(f"cover_") and info.get('filename') in candidate.name:
                    cover_path = candidate
                    break
            with card_cols[1]:
                st.markdown(f"**{info.get('orig_name')}** — uploaded by *{info.get('uploader')}* on {info.get('time')}")
                if cover_path and cover_path.exists():
                    try:
                        st.image(str(cover_path), use_column_width=True)
                    except Exception:
                        pass
                audio_path = SONGS_DIR / info.get('filename')
                if audio_path.exists():
                    try:
                        suffix = audio_path.suffix.lower()
                        if suffix in ['.mp4', '.webm', '.mov']:
                            st.video(str(audio_path))
                        else:
                            st.audio(str(audio_path))
                    except Exception:
                        st.write('Unable to play this file in the browser.')
                else:
                    st.write('File missing on disk')
            with card_cols[2]:
                if st.button(f'Delete_{i}'):
                    try:
                        if audio_path.exists():
                            audio_path.unlink()
                    except Exception:
                        pass
                    cover_fname = delete_song_record(info.get('filename'))
                    # try to remove associated cover file as well
                    if cover_fname:
                        try:
                            cover_path = SONGS_DIR / cover_fname
                            if cover_path.exists():
                                cover_path.unlink()
                        except Exception:
                            pass
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass

    st.markdown('---')

    st.markdown('---')

# Call tab (simple embedded Jitsi)
with tab[3]:
    st.markdown("<h2 style='text-align:center;'>Call & Screen Share</h2>", unsafe_allow_html=True)
    st.write("Start a private Jitsi Meet room to call Lina and share your screen. Screen sharing works in modern browsers.")
    # room name generator
    default_room = f'lina_call_{datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")}'
    room = st.text_input('Room name (share this with Lina)', value=default_room, key='call_room')
    start_muted = st.checkbox('Start with audio muted', value=False)
    if st.button('Open call in embedded room') and room:
        room_safe = room.replace(' ', '_')
        jitsi_url = f"https://meet.jit.si/{room_safe}#config.startWithAudioMuted={str(start_muted).lower()}"
        st.markdown("<div style='text-align:center; margin-bottom:8px;'>If screen sharing is required, desktop Chrome/Edge/Firefox work best.</div>", unsafe_allow_html=True)
        components.html(f'''<iframe src="{jitsi_url}" allow="camera; microphone; fullscreen; display-capture; autoplay" style="width:100%; height:600px; border:0; border-radius:12px;"></iframe>''', height=620)
    else:
        st.info('Enter a room name and press the button to open the embedded call. You can also share the room name and join from another device.')

    st.markdown('---')

# End

# Journal removed per user request

# Map removed per user request

# --------------------------
# Love Letters Archive
# --------------------------
LETTERS_META = Path('letters.json')

def load_letters():
    if LETTERS_META.exists():
        try:
            return json.loads(LETTERS_META.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_letters(items):
    try:
        LETTERS_META.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[4]:
    st.markdown("<h2 style='text-align:center;'>Love Letters Archive</h2>", unsafe_allow_html=True)
    st.write('Write letters and choose when they unlock (daily, weekly, specific date).')
    letter_text = st.text_area('Letter text')
    unlock = st.selectbox('Unlock schedule', ['immediate','daily','weekly','on date'])
    unlock_date = None
    if unlock == 'on date':
        unlock_date = st.date_input('Unlock date')
    if st.button('Add letter'):
        items = load_letters()
        items.append({'text': letter_text, 'schedule': unlock, 'date': str(unlock_date) if unlock_date else None, 'time': datetime.datetime.utcnow().isoformat()})
        save_letters(items)
        st.success('Letter saved')
    st.markdown('---')
    # Show available letters based on schedule (simple logic)
    items = load_letters()
    now = datetime.datetime.utcnow()
    for it in items:
        show = False
        if it.get('schedule') == 'immediate':
            show = True
        elif it.get('schedule') == 'daily':
            show = True
        elif it.get('schedule') == 'weekly':
            show = True
        elif it.get('schedule') == 'on date' and it.get('date'):
            try:
                d = datetime.date.fromisoformat(it.get('date'))
                if d <= now.date():
                    show = True
            except Exception:
                pass
        if show:
            st.markdown(f"**Letter:** {it.get('time')}")
            st.write(it.get('text',''))
            st.markdown('---')

# --------------------------
# Countdowns
# --------------------------
COUNT_META = Path('countdowns.json')

def load_counts():
    if COUNT_META.exists():
        try:
            return json.loads(COUNT_META.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_counts(items):
    try:
        COUNT_META.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[5]:
    st.markdown("<h2 style='text-align:center;'>Countdowns</h2>", unsafe_allow_html=True)
    name = st.text_input('Event name')
    date = st.date_input('Date')
    if st.button('Add countdown'):
        items = load_counts()
        items.append({'name': name, 'date': str(date)})
        save_counts(items)
        st.success('Countdown added')
    st.markdown('---')
    items = load_counts()
    # Render list with delete buttons
    if not items:
        st.info('No countdowns yet.')
    else:
        for idx, it in enumerate(items):
            try:
                d = datetime.date.fromisoformat(it.get('date'))
                delta = d - datetime.date.today()
                st.write(f"{it.get('name')}: {delta.days} days")
            except Exception:
                st.write(it)
            # provide a delete button per countdown
            if st.button(f'Delete_{idx}', key=f'delete_count_{idx}'):
                try:
                    items.pop(idx)
                    save_counts(items)
                    st.success('Countdown removed')
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
                except Exception:
                    st.error('Could not remove countdown')

# Hidden Messages section removed per user request. The app no longer contains the treasure-hunt feature.

# Personalized Horoscope removed per user request.

# --------------------------
# Notifications tab
# --------------------------
NOTIF_FILE = Path('notifications.json')

# Mad Meter storage
MAD_FILE = Path('mad_meter.json')

def load_mad():
    if MAD_FILE.exists():
        try:
            return json.loads(MAD_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_mad(entries):
    try:
        MAD_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

# (previous `private` helpers were removed when converting the tab to Notifications)
def load_notifications():
    if NOTIF_FILE.exists():
        try:
            return json.loads(NOTIF_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_notifications(d):
    try:
        NOTIF_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


with tab[6]:
    st.markdown("<h2 style='text-align:center;'>Notifications</h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'>Allow browser notifications so your partner receives alerts when you message them (works while the page is open). For full push support when the app is closed you'd need a push service (server + VAPID) — see notes below.</div>", unsafe_allow_html=True)
    prefs = load_notifications()
    user_pref = prefs.get(st.session_state.get('auth_user'), {})

    st.markdown('### Browser permission')
    st.markdown('Click the button below to request the browser permission to display notifications. After granting permission, click *Save preference* to persist the setting on this device.')
    try:
        components.html("""
        <script>
        function askNotificationPermission(){
            if(!('Notification' in window)){
                alert('This browser does not support notifications');
                return;
            }
            Notification.requestPermission().then(function(result){
                alert('Permission: ' + result + '\nNow click Save preference to persist this on the server.');
            });
        }
        </script>
        <button onclick="askNotificationPermission()">Request browser permission</button>
        """, height=80)
    except Exception:
        pass

    if st.button('Save preference (I granted permission)'):
        prefs.setdefault(st.session_state.get('auth_user'), {})['enabled'] = True
        save_notifications(prefs)
        st.success('Saved preference')

    if st.button('Disable notifications'):
        prefs.setdefault(st.session_state.get('auth_user'), {})['enabled'] = False
        save_notifications(prefs)
        st.success('Notifications disabled')

    if st.button('Test notification (show now)'):
        # trigger a small client notification (only appears if permission already granted)
        try:
            components.html("""
            <script>
            if('Notification' in window && Notification.permission === 'granted'){
                new Notification('Test from Lina app', { body: 'If you see this, notifications work in this browser.' });
            } else {
                alert('Notification permission not yet granted in this browser. Use the Request permission button first.');
            }
            </script>
            """, height=60)
        except Exception:
            pass

    st.markdown('---')
    st.markdown('### Web Push (service worker)')
    st.markdown('Register a service worker and subscribe to push notifications (requires a running push server at http://localhost:5001).')
    try:
        components.html("""
        <script>
        async function registerAndSubscribe(){
            if(!('serviceWorker' in navigator)){
                alert('Service workers not supported in this browser'); return;
            }
            try{
                const reg = await navigator.serviceWorker.register('/static/sw.js');
                console.log('SW registered', reg);
            }catch(e){ console.error('SW register failed', e); alert('Service worker registration failed'); return; }

            // fetch VAPID public key
            let pub = null;
            try{
                const r = await fetch('http://localhost:5001/vapid_public');
                pub = await r.text();
            }catch(e){ console.error(e); alert('Could not fetch VAPID key from push server'); return; }

            function urlBase64ToUint8Array(base64String) {
                const padding = '='.repeat((4 - base64String.length % 4) % 4);
                const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
                const rawData = window.atob(base64);
                const outputArray = new Uint8Array(rawData.length);
                for (let i = 0; i < rawData.length; ++i) {
                    outputArray[i] = rawData.charCodeAt(i);
                }
                return outputArray;
            }

            try{
                const reg = await navigator.serviceWorker.ready;
                const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(pub) });
                // send subscription to push server
                await fetch('http://localhost:5001/subscribe', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(sub)});
                alert('Subscribed to push (saved to push server)');
            }catch(e){ console.error(e); alert('Push subscription failed: ' + e); }
        }
        </script>
        <button onclick="registerAndSubscribe()">Register Service Worker & Subscribe</button>
        """, height=120)
    except Exception:
        pass

        # Add an Install to Home Screen button (PWA) using beforeinstallprompt
        try:
                components.html('''
                <script>
                let deferredPrompt;
                window.addEventListener('beforeinstallprompt', (e) => {
                    e.preventDefault();
                    deferredPrompt = e;
                    const btn = document.getElementById('pwa_install_btn');
                    if(btn) btn.style.display = 'inline-block';
                });
                async function promptInstall(){
                    if(!deferredPrompt) { alert('PWA install not available'); return; }
                    deferredPrompt.prompt();
                    const choice = await deferredPrompt.userChoice;
                    if(choice.outcome === 'accepted') alert('Thanks for installing!');
                    deferredPrompt = null;
                }
                </script>
                <button id='pwa_install_btn' style='display:none;' onclick='promptInstall()'>Install app to Home Screen</button>
                ''', height=90)
        except Exception:
                pass



# --------------------------
# Mad Meter tab
# --------------------------
with tab[7]:
    st.markdown("<h2 style='text-align:center;'> How do you feel today? </h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#7a1128;'>Share how you're feeling and what would help — this helps communicate needs calmly.</div>", unsafe_allow_html=True)

    # mood slider: 0 (very mad/red) -> 50 (neutral/yellow) -> 100 (happy/green)
    mood = st.slider('How are you feeling right now?', min_value=0, max_value=100, value=50, help='0 = very mad (red), 50 = neutral, 100 = happy')
    # map to color and label
    if mood <= 20:
        mood_label = 'Very Mad'
        mood_color = 'red'
    elif mood <= 45:
        mood_label = 'Upset'
        mood_color = 'orange'
    elif mood <= 60:
        mood_label = 'Neutral'
        mood_color = 'gold'
    elif mood <= 85:
        mood_label = 'Okay/Content'
        mood_color = 'lightgreen'
    else:
        mood_label = 'Happy'
        mood_color = 'green'

    st.markdown(f"**Mood:** <span style='color:{mood_color}; font-weight:600;'>{mood_label} ({mood})</span>", unsafe_allow_html=True)

    reason = st.text_area('Why do you feel this way?', placeholder='Describe briefly what happened or how you feel')
    help_actions = st.text_area('What can your partner do to make you feel better?', placeholder='E.g. give me a hug, listen, apologize, give space, do chores, plan a date...')
    # Quick suggestion chips
    st.markdown('**Quick suggestions**: (click to append)')
    cols = st.columns(4)
    suggestions = ['Listen without interrupting', 'A sincere apology', 'Hug/me time', 'Help with chores', 'Plan a date', 'Give me space', 'Bring flowers', 'Write a note']
    for i, s in enumerate(suggestions):
        if cols[i % 4].button(s, key=f'sugg_{i}'):
            # append suggestion to help_actions
            cur = st.session_state.get('mad_help', help_actions or '')
            st.session_state['mad_help'] = (cur + '\n' + s).strip()

    # prefer session value if user clicked quick suggestions
    help_actions = st.session_state.get('mad_help', help_actions)

    if st.button('Save mood entry'):
        entries = load_mad()
        entry = {
            'user': st.session_state.get('auth_user'),
            'mood': mood,
            'label': mood_label,
            'reason': reason,
            'help_suggested': help_actions,
            'time': datetime.datetime.utcnow().isoformat()
        }
        entries.append(entry)
        save_mad(entries)
        st.success('Saved your mood')
        try:
            st.experimental_rerun()
        except Exception:
            pass

    st.markdown('---')
    st.markdown('### Recent Mad Meter entries')
    history = load_mad()
    if not history:
        st.info('No entries yet — be the first to share how you feel')
    else:
        for e in reversed(history[-20:]):
            who = e.get('user') or 'Unknown'
            ts = e.get('time', '')
            try:
                tsf = datetime.datetime.fromisoformat(ts).strftime('%b %d %H:%M')
            except Exception:
                tsf = ts
            color = 'green' if e.get('mood', 50) > 80 else ('red' if e.get('mood',50) < 30 else 'orange')
            st.markdown(f"- **{who}** ({tsf}) — <span style='color:{color}; font-weight:600'>{e.get('label')} ({e.get('mood')})</span><br>Reason: {e.get('reason')}<br>What helps: {e.get('help_suggested')}", unsafe_allow_html=True)

# End
