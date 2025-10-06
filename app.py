import streamlit as st
from pathlib import Path
from PIL import Image
import io
import sqlite3 as _sqlite3
import streamlit.components.v1 as components
import random
# reportlab is optional — not all environments have it installed
HAVE_REPORTLAB = True
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except Exception:
    HAVE_REPORTLAB = False
import json
import datetime
import os
import sqlite3

# Page config
st.set_page_config(page_title="For Lina 💖", page_icon="❤️", layout="centered")

# Styles
RED_BG = "#ffedf0"
ACCENT = "#d81b60"  # deep pink/red

st.markdown(f"""<style>
body {{background: linear-gradient(180deg, #fff 0%, {RED_BG} 100%); font-family: 'Helvetica Neue', Arial, sans-serif;}}
.main {{background: transparent;}}
.stApp {{padding-top: 10px;}}
.header-wrap {{text-align:center; padding:18px 8px; background: linear-gradient(90deg, rgba(216,27,96,0.06), rgba(216,27,96,0.02)); border-radius:12px; margin-bottom:18px}}
h1 {{color: {ACCENT}; font-family: 'Georgia', serif; font-size:44px; margin:0}}
h3 {{margin-top:4px}}
.love-text {{font-size:18px; color:#7a102a; line-height:1.6}}
.btn-red {{background:{ACCENT}; color:white; padding:10px 18px; border-radius:12px; border:none}}
.btn-red:hover {{opacity:0.95}}
.message-bubble {{background:#fff0f3; color:#2b2b2b; border-radius:12px; padding:12px; margin:10px 0; max-width:78%;}}
.message-bubble .meta {{color:#6a6a6a; font-size:12px}}
.message-left {{margin-right:auto; text-align:left}}
.message-right {{margin-left:auto; text-align:right; background: linear-gradient(180deg,#ffd9e6,#ffb3d1);}}
.heart-decor {{font-size:22px; color:#d81b60; margin:0 6px}}
.timestamp {{font-size:11px; color:#8a6a6a;}}
.download-btn {{background:#c2185b; color:white}}
/* layout */
.container {{max-width:900px; margin:0 auto;}}
.message-row {{display:flex; flex-direction:column; gap:6px}}
.avatar {{display:inline-block; width:20px; height:20px; margin-right:8px}}
.message-bubble .body {{margin-top:8px; color:#2b2b2b}}
/* richer visual touches */
.stApp {{background-image: radial-gradient(rgba(216,27,96,0.03) 1px, transparent 1px); background-size: 20px 20px;}}
.message-bubble {{box-shadow: 0 6px 18px rgba(20,10,20,0.06);}}
.message-right {{align-self:flex-end; background: linear-gradient(180deg,#ffd9e6,#ffb3d1);}}
.message-left {{align-self:flex-start; background: linear-gradient(180deg,#fff,#fff6f8);}}
.meta-row {{display:flex; align-items:center; gap:8px;}}
.meta-name {{font-weight:600; color:#6a1330}}
.meta-time {{font-size:11px; color:#8a6a6a}}
/* responsive tweaks */
@media (max-width: 768px) {{
    .message-bubble {{max-width:92%;}}
}}
</style>
""", unsafe_allow_html=True)

# Basic header
st.markdown("<div class='header-wrap'>", unsafe_allow_html=True)
st.markdown("<h1>For Lina <span class='heart-decor'>❤️</span></h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#b71c46'>My beautiful cutie pie <span class='heart-decor'>💞</span></h3>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Top tabs (Play, Journal, Map removed)
# Users / Forced login
USERS_FILE = Path('users.json')

def load_users():
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_users(d: dict):
    try:
        USERS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


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
    # Show usernames from users.json so the user can pick one (makes it easy to test)
    if users:
        username = st.selectbox('Username', list(users.keys()), key='login_user')
    else:
        username = st.text_input('Username', key='login_user')
    password = st.text_input('Password', type='password', key='login_pwd')
    if st.button('Login'):
        if users and users.get(username) == password:
            st.session_state['auth_user'] = username
            st.success(f'Logged in as {username}')
            try:
                st.experimental_rerun()
            except Exception:
                # Some Streamlit deployments may not allow rerun; continue gracefully
                pass
        else:
            st.error('Invalid username or password')
    # Prevent rest of the app from rendering until logged in
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
tab = st.tabs(["Home", "Messages", "Songs", "Letters", "Countdowns", "Private"])

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
        st.success("I hope this made you smile, Lina! ❤️")

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
    st.markdown("<div style='text-align:center; color:#7a1128;'>Send messages to each other — messages are stored locally in this folder as <code>messages.json</code></div>", unsafe_allow_html=True)

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

        st.write('Attach image(s) (optional)')
        img_upload = st.file_uploader('', type=['png','jpg','jpeg','gif'], accept_multiple_files=True, key=f'msg_images_{composer_pos}')
        msg_text = st.text_area('Message', height=120, key='composer_text')
        if st.button('Send', key=f'send_btn_{composer_pos}') and (msg_text.strip() or (img_upload and len(img_upload) > 0)):
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
    st.markdown("<div style='max-height:520px; overflow:auto; padding:8px; border-radius:12px; background:linear-gradient(180deg,#fff,#fff6f8)'>", unsafe_allow_html=True)

    if st.session_state.get('unread'):
        st.info(f"{current_user} has {st.session_state.get('unread')} unread message(s)")

    msgs = st.session_state.messages[:]  # copy
    # Decide order: newest-first if composer at top (so new messages are visible without scrolling)
    if composer_pos == 'Top':
        msgs = list(reversed(msgs))

    for m in msgs:
        sender_name = m.get('from', '')
        is_me = (sender_name == current_user)
        side_class = 'message-right' if is_me else 'message-left'
        try:
            ts = datetime.datetime.fromisoformat(m.get('time'))
            ts_str = ts.strftime('%b %d %H:%M')
        except Exception:
            ts_str = m.get('time', '')
        avatar = '💖' if sender_name.lower().startswith('l') else '💌'
        html = f"""
        <div class='message-row'>
          <div class='message-bubble {side_class}'>
            <div class='meta-row'><span class='avatar'>{avatar}</span><span class='meta-name'>{sender_name}</span><span class='meta-time'>&nbsp;{ts_str}</span></div>
            <div class='body'>{m.get('text','')}</div>
          </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        try:
            imgs = m.get('images', []) or []
            for im in imgs:
                # support both old string format and new dict format
                if isinstance(im, str):
                    p = Path('message_media') / im
                    thumb = Path('message_media') / f"thumb_{im}.png"
                else:
                    p = Path('message_media') / im.get('file')
                    thumb = Path('message_media') / (im.get('thumb') or f"thumb_{im.get('file')}.png")
                if thumb.exists():
                    try:
                        st.image(thumb.read_bytes(), width=360)
                    except Exception:
                        try:
                            st.image(p.read_bytes(), width=360)
                        except Exception:
                            pass
                elif p.exists():
                    try:
                        st.image(p.read_bytes(), width=360)
                    except Exception:
                        pass
        except Exception:
            pass

    st.markdown('</div>', unsafe_allow_html=True)

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
    c.execute(
        '''CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            orig_name TEXT,
            uploader TEXT,
            time TEXT
        )'''
    )
    conn.commit()
    conn.close()

def add_song_record(filename, orig_name, uploader):
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    try:
        c.execute('INSERT OR REPLACE INTO songs (filename, orig_name, uploader, time) VALUES (?, ?, ?, ?)',
                  (filename, orig_name, uploader, datetime.datetime.utcnow().isoformat()))
        conn.commit()
    except Exception:
        pass
    conn.close()

def list_songs():
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    c.execute('SELECT filename, orig_name, uploader, time FROM songs ORDER BY time DESC')
    rows = c.fetchall()
    conn.close()
    return [{'filename': r[0], 'orig_name': r[1], 'uploader': r[2], 'time': r[3]} for r in rows]

def delete_song_record(filename):
    init_songs_db()
    conn = _sqlite3.connect(str(SONGS_DB))
    c = conn.cursor()
    c.execute('DELETE FROM songs WHERE filename = ?', (filename,))
    conn.commit()
    conn.close()

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
                add_song_record(safe_name, f.name, uploader_name)
                st.success(f"Uploaded {f.name}")
            except Exception as e:
                st.error(f"Failed to save {f.name}: {e}")

    st.markdown('---')

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
                        st.image(str(cover_path), width=240)
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
                    delete_song_record(info.get('filename'))
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass

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

with tab[3]:
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

with tab[4]:
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
# Private password-protected space
# --------------------------
PRIVATE_META = Path('private.json')

def load_private():
    if PRIVATE_META.exists():
        try:
            return json.loads(PRIVATE_META.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_private(d):
    try:
        PRIVATE_META.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[5]:
    st.markdown("<h2 style='text-align:center;'>Private Space 🔒</h2>", unsafe_allow_html=True)
    # basic password protect (local only)
    pri = load_private()
    if 'password' not in pri:
        if st.text_input('Set a password for the private space', type='password'):
            p = st.session_state.get('text')
            pri['password'] = p
            save_private(pri)
            st.success('Password set')
    else:
        entered = st.text_input('Enter password to unlock', type='password')
        if entered:
            if entered == pri.get('password'):
                st.success('Unlocked private space')
                pm = st.text_area('Write a private note')
                if st.button('Save private note'):
                    pri.setdefault('notes',[]).append({'text': pm, 'time': datetime.datetime.utcnow().isoformat()})
                    save_private(pri)
                    st.success('Saved')
                for n in pri.get('notes',[]):
                    st.markdown(f"- {n.get('time')}: {n.get('text')}")
            else:
                st.error('Incorrect password')

# End
