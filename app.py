import streamlit as st
from pathlib import Path
from PIL import Image
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
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

# Top tabs
tab = st.tabs(["Home", "Play", "Messages", "Songs", "Journal", "Map", "Letters", "Countdowns", "Private"])

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


def mark_all_read():
    if STORAGE == 'sqlite':
        if not DB_FILE.exists():
            return
        conn = sqlite3.connect(str(DB_FILE))
        c = conn.cursor()
        c.execute("UPDATE messages SET read = 1 WHERE recipient = ? AND read = 0", ('You',))
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
        if m.get('to') == 'You' and not m.get('read'):
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
    st.session_state.unread = sum(1 for m in st.session_state.messages if (m.get('to') == 'You' and not m.get('read', False)))
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

# --------------------------
# Play tab: mini-games + ideas
# --------------------------
with tab[1]:
    st.markdown("<h2 style='text-align:center;'>Play together</h2>", unsafe_allow_html=True)
    st.write("Choose a mini-game to play together:")

    game = st.selectbox("Mini-game", ["Tic-Tac-Toe", "Rock-Paper-Scissors", "Guess a Number (co-op)"])

    # Tic-Tac-Toe
    if game == "Tic-Tac-Toe":
        st.write("Two-player Tic-Tac-Toe. Click a cell to place X/O.")
        board = st.session_state.ttt_board
        winner = st.session_state.ttt_winner

        cols = st.columns(3)
        for i in range(3):
            for j in range(3):
                idx = i*3 + j
                label = board[idx] if board[idx] else ""
                if cols[j].button(label or " ", key=f"cell_{idx}") and not winner:
                    if not board[idx]:
                        board[idx] = st.session_state.ttt_turn
                        # toggle
                        st.session_state.ttt_turn = 'O' if st.session_state.ttt_turn == 'X' else 'X'
                        # check winner
                        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
                        for a,b,c in wins:
                            if board[a] and board[a] == board[b] == board[c]:
                                st.session_state.ttt_winner = board[a]
                                break
                        if all(board) and not st.session_state.ttt_winner:
                            st.session_state.ttt_winner = 'Draw'
        if st.session_state.ttt_winner:
            if st.session_state.ttt_winner == 'Draw':
                st.info("It's a draw!")
            else:
                st.success(f"{st.session_state.ttt_winner} wins!")
            if st.button('Reset Tic-Tac-Toe'):
                st.session_state.ttt_board = [""]*9
                st.session_state.ttt_turn = 'X'
                st.session_state.ttt_winner = None

    # Rock-Paper-Scissors (two-player on same screen)
    if game == "Rock-Paper-Scissors":
        st.write("Two-player RPS: Player 1 picks, then Player 2 picks.")
        if 'rps_p1' not in st.session_state:
            st.session_state.rps_p1 = None
            st.session_state.rps_p2 = None
        p1 = st.selectbox("Player 1 pick", ["", "Rock", "Paper", "Scissors"], key='p1')
        if st.button('Lock Player 1 pick'):
            st.session_state.rps_p1 = p1
        if st.session_state.rps_p1:
            st.write(f"Player 1 locked: {st.session_state.rps_p1}")
            p2 = st.selectbox("Player 2 pick", ["", "Rock", "Paper", "Scissors"], key='p2')
            if st.button('Lock Player 2 pick'):
                st.session_state.rps_p2 = p2
            if st.session_state.rps_p2:
                p1v = st.session_state.rps_p1
                p2v = st.session_state.rps_p2
                outcome = None
                if p1v == p2v:
                    outcome = 'Draw'
                elif (p1v, p2v) in [('Rock','Scissors'), ('Scissors','Paper'), ('Paper','Rock')]:
                    outcome = 'Player 1 wins'
                else:
                    outcome = 'Player 2 wins'
                st.success(outcome)
                if st.button('Reset RPS'):
                    st.session_state.rps_p1 = None
                    st.session_state.rps_p2 = None

    # Guess a Number (co-op)
    if game == "Guess a Number (co-op)":
        st.write("One sets a secret number (1-50) and the other guesses with hints")
        if 'secret' not in st.session_state:
            st.session_state.secret = None
        if st.session_state.secret is None:
            secret = st.number_input('Set secret number (Player A) — keep it private', min_value=1, max_value=50, step=1, key='secret_set')
            if st.button('Set Secret'):
                st.session_state.secret = int(secret)
                st.success('Secret set — now Player B can guess')
        else:
            guess = st.number_input('Guess the number (Player B)', min_value=1, max_value=50, step=1, key='guess')
            if st.button('Submit Guess'):
                if guess == st.session_state.secret:
                    st.success('Correct!')
                    st.session_state.secret = None
                elif guess < st.session_state.secret:
                    st.info('Higher')
                else:
                    st.info('Lower')

    st.markdown('---')
    st.write('More mini-game ideas:')
    st.write('- Memory matching card game (turn-based)')
    st.write('- Collaborative drawing (one draws a line each turn)')
    st.write('- Two-player trivia (take turns asking questions)')
    st.write('- Word ladder / 20 questions')

# --------------------------
# Messages tab
# --------------------------
with tab[2]:
    st.markdown("<h2 style='text-align:center;'>Messages <span class='heart-decor'>💌</span></h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#7a1128;'>Send messages to each other — messages are stored locally in this folder as <code>messages.json</code></div>", unsafe_allow_html=True)
    st.markdown('')

    # Sidebar quick controls
    sender = st.selectbox('Send as', ['Youssef', 'Lina'])
    recipient = 'Lina' if sender == 'Youssef' else 'Youssef'

    # If a previous send requested the composer be cleared, do it before creating the widget
    if st.session_state.pop('clear_composer', False):
        # Safe to assign because the widget hasn't been created yet on this run
        st.session_state['composer_text'] = ''

    # Ensure composer state exists so we can reference it
    st.session_state.setdefault('composer_text', '')
    # quick emoji picker
    emojis = ['❤️','😘','😊','😍','🎶','😭','👍']
    cols = st.columns(len(emojis))
    for i, e in enumerate(emojis):
        if cols[i].button(e, key=f'emoji_{i}'):
            # append emoji to composer text
            st.session_state['composer_text'] = st.session_state.get('composer_text', '') + e

    # image attachments
    st.write('Attach image(s) (optional)')
    img_upload = st.file_uploader('', type=['png','jpg','jpeg','gif'], accept_multiple_files=True, key='msg_images')

    msg_text = st.text_area('Message', height=100, key='composer_text')
    if st.button('Send') and (msg_text.strip() or (img_upload and len(img_upload) > 0)):
        entry = {
            'from': sender,
            'to': recipient,
            'text': msg_text.strip(),
            'time': datetime.datetime.utcnow().isoformat(),
            'read': False,
            'images': []
        }

        # save attached images to message_media/
        MEDIA_DIR = Path('message_media')
        MEDIA_DIR.mkdir(exist_ok=True)
        if img_upload:
            for f in img_upload:
                try:
                    data = f.read()
                    ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                    safe_name = f"{ts}_{f.name}"
                    dest = MEDIA_DIR / safe_name
                    dest.write_bytes(data)
                    entry['images'].append(safe_name)
                except Exception:
                    pass

        # append to session and persist
        st.session_state.messages.append(entry)
        add_message(entry)
        if entry['to'] == 'Youssef':
            st.session_state.unread += 1
        # Request the composer to be cleared on the next rerun to avoid modifying a widget-backed key
        st.session_state['clear_composer'] = True
        # clear uploader state where possible
        try:
            st.session_state['msg_images'] = None
        except Exception:
            pass
        st.success('Message sent')

    st.markdown('---')

    # Show unread count and chat zone
    st.markdown("<div style='max-height:360px; overflow:auto; padding:8px; border-radius:12px; background:linear-gradient(180deg,#fff,#fff6f8)'>", unsafe_allow_html=True)
    if st.session_state.unread:
        st.info(f'Youssef has {st.session_state.unread} unread message(s)')

    # List messages (render as chat bubbles) - always visible in chat zone (newest at bottom)
    msgs = st.session_state.messages[:]  # oldest -> newest
    for m in msgs:
        sender_name = m.get('from', '')
        is_me = (sender_name == 'Youssef')
        side_class = 'message-right' if is_me else 'message-left'
        # friendly timestamp
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
        # render any attached images for this message (saved in message_media/)
        try:
            imgs = m.get('images', []) or []
            for im in imgs:
                p = Path('message_media') / im
                if p.exists():
                    st.image(str(p), width=240)
        except Exception:
            pass
    st.markdown("</div>", unsafe_allow_html=True)

    # Mark messages as read button
    if st.button('Mark all as read'):
        changed = False
        for m in st.session_state.messages:
            if m.get('to') == 'Youssef' and not m.get('read'):
                m['read'] = True
                changed = True
        if changed:
            mark_all_read()
            st.session_state.unread = 0
            st.success('Marked as read')

    st.markdown('---')

# --------------------------
# Songs tab
# --------------------------
SONGS_DIR = Path('songs')
SONGS_DIR.mkdir(exist_ok=True)
SONGS_META = Path('songs.json')

def load_songs_meta():
    if SONGS_META.exists():
        try:
            return json.loads(SONGS_META.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_songs_meta(meta: dict):
    try:
        SONGS_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[3]:
    st.markdown("<h2 style='text-align:center;'>Songs</h2>", unsafe_allow_html=True)
    st.write("Upload voice recordings or short video recordings (mp3, wav, m4a, ogg, mp4) and play them here.")

    uploader_name = st.selectbox('Upload as', ['Youssef', 'Lina'], key='song_uploader')
    uploaded = st.file_uploader('Upload recording(s)', type=['mp3', 'wav', 'm4a', 'ogg', 'mp4'], accept_multiple_files=True)
    if uploaded:
        meta = load_songs_meta()
        for f in uploaded:
            try:
                data = f.read()
                ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                safe_name = f"{ts}_{f.name}"
                dest = SONGS_DIR / safe_name
                dest.write_bytes(data)
                meta[safe_name] = {
                    'orig_name': f.name,
                    'uploader': uploader_name,
                    'time': datetime.datetime.utcnow().isoformat()
                }
                st.success(f"Uploaded {f.name}")
            except Exception as e:
                st.error(f"Failed to save {f.name}: {e}")
        save_songs_meta(meta)

    st.markdown('---')

    # List available songs
    meta = load_songs_meta()
    if not meta:
        st.info('No songs uploaded yet — use the uploader above to add recordings.')
    else:
        # sort by time desc
        items = sorted(meta.items(), key=lambda kv: kv[1].get('time',''), reverse=True)
        for i, (fname, info) in enumerate(items):
            col1, col2 = st.columns([6,1])
            with col1:
                st.markdown(f"**{info.get('orig_name')}** — uploaded by *{info.get('uploader')}* on {info.get('time')}")
                audio_path = SONGS_DIR / fname
                if audio_path.exists():
                    try:
                        suffix = audio_path.suffix.lower()
                        # Video formats -> use st.video, audio formats -> st.audio
                        if suffix in ['.mp4', '.webm', '.mov']:
                            try:
                                st.video(str(audio_path))
                            except Exception:
                                st.video(audio_path.read_bytes())
                        else:
                            try:
                                st.audio(str(audio_path))
                            except Exception:
                                # fallback to bytes
                                try:
                                    st.audio(audio_path.read_bytes())
                                except Exception:
                                    st.write('Unable to play this file in the browser.')
                    except Exception:
                        st.write('Unable to play this file in the browser.')
                else:
                    st.write('File missing on disk')
            with col2:
                if st.button(f'Delete_{i}'):
                    try:
                        if audio_path.exists():
                            audio_path.unlink()
                    except Exception:
                        pass
                    meta.pop(fname, None)
                    save_songs_meta(meta)
                    st.experimental_rerun()

    st.markdown('---')

# End

# --------------------------
# Digital Love Journal
# --------------------------
JOURNAL_DIR = Path('journal')
JOURNAL_DIR.mkdir(exist_ok=True)
JOURNAL_META = Path('journal.json')

def load_journal():
    if JOURNAL_META.exists():
        try:
            return json.loads(JOURNAL_META.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_journal(items):
    try:
        JOURNAL_META.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[4]:
    st.markdown("<h2 style='text-align:center;'>Digital Love Journal</h2>", unsafe_allow_html=True)
    st.write('Add timeline entries with photos, short videos, and notes.')
    title = st.text_input('Title')
    note = st.text_area('Note')
    media = st.file_uploader('Add photo/video (optional)', type=['png','jpg','jpeg','mp4','mov','webm'], key='journal_media')
    if st.button('Add entry'):
        items = load_journal()
        ts = datetime.datetime.utcnow().isoformat()
        fname = None
        if media:
            safe = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{media.name}"
            (JOURNAL_DIR / safe).write_bytes(media.read())
            fname = str(JOURNAL_DIR / safe)
        items.append({'title': title, 'note': note, 'media': fname, 'time': ts})
        save_journal(items)
        st.success('Entry added')
    st.markdown('---')
    items = load_journal()
    if not items:
        st.info('No journal entries yet.')
    else:
        for it in sorted(items, key=lambda x: x.get('time',''), reverse=True):
            st.markdown(f"**{it.get('title','')}** — {it.get('time')}")
            st.write(it.get('note',''))
            if it.get('media'):
                p = Path(it.get('media'))
                if p.exists():
                    if p.suffix.lower() in ['.mp4','.mov','.webm']:
                        st.video(str(p))
                    else:
                        st.image(str(p))
            st.markdown('---')

# --------------------------
# Virtual Memory Map
# --------------------------
MAP_META = Path('map.json')

def load_map():
    if MAP_META.exists():
        try:
            return json.loads(MAP_META.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_map(items):
    try:
        MAP_META.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

with tab[5]:
    st.markdown("<h2 style='text-align:center;'>Virtual Memory Map</h2>", unsafe_allow_html=True)
    st.write('Pin places you visited together and add a short memory or photo.')
    place = st.text_input('Place name (city, spot)')
    coords = st.text_input('Coordinates (lat,lon) — optional')
    note = st.text_area('Memory / story')
    photo = st.file_uploader('Photo (optional)', type=['png','jpg','jpeg'], key='map_photo')
    if st.button('Add pin'):
        items = load_map()
        fname = None
        if photo:
            safe = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{photo.name}"
            (Path('map_media') / safe).parent.mkdir(exist_ok=True)
            (Path('map_media') / safe).write_bytes(photo.read())
            fname = str(Path('map_media') / safe)
        items.append({'place': place, 'coords': coords, 'note': note, 'photo': fname, 'time': datetime.datetime.utcnow().isoformat()})
        save_map(items)
        st.success('Pin added')
    st.markdown('---')
    items = load_map()
    if not items:
        st.info('No map pins yet.')
    else:
        for it in items:
            st.markdown(f"**{it.get('place')}** — {it.get('time')}")
            st.write(it.get('note',''))
            if it.get('photo') and Path(it.get('photo')).exists():
                st.image(it.get('photo'))
            if it.get('coords'):
                st.write(f"Coordinates: {it.get('coords')}")
            st.markdown('---')

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

with tab[6]:
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

with tab[7]:
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
    for it in items:
        try:
            d = datetime.date.fromisoformat(it.get('date'))
            delta = d - datetime.date.today()
            st.write(f"{it.get('name')}: {delta.days} days")
        except Exception:
            st.write(it)

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

with tab[8]:
    st.markdown("<h2 style='text-align:center;'>Private Space 🔒</h2>", unsafe_allow_html=True)
    st.write('This area can be password-protected for only you two.')
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
