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
.card {{background: #fff; border-radius: 16px; padding: 22px; box-shadow: 0 12px 30px rgba(216,27,96,0.08);}}
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
.card {{border: 1px solid rgba(200,20,70,0.06)}}
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
tab = st.tabs(["Home", "Play", "Messages"])

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
    # Main card
    st.markdown("<div class='card'>", unsafe_allow_html=True)

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
        st.markdown("<div class='love-text'>")
        st.write("Lina, every moment with you feels like a warm sunrise. Your smile lights up my day and your laugh is my favorite song.")
        st.write("I made this little page to remind you how much you're loved — today and always.")
        st.markdown("</div>")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.button('Show balloons 🎈'):
        st.balloons()
        st.success("I hope this made you smile, Lina! ❤️")

    st.markdown("---")

    # Printable love note
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

    msg_text = st.text_area('Message', height=100)
    if st.button('Send') and msg_text.strip():
        entry = {
            'from': sender,
            'to': recipient,
            'text': msg_text.strip(),
            'time': datetime.datetime.utcnow().isoformat(),
            'read': False
        }
        st.session_state.messages.append(entry)
        add_message(entry)
        if entry['to'] == 'Youssef':
            st.session_state.unread += 1
        st.success('Message sent')

    st.markdown('---')

    # Show unread count
    if st.session_state.unread:
        st.info(f'Youssef has {st.session_state.unread} unread message(s)')

        # List messages (render as chat bubbles)
        msgs = list(reversed(st.session_state.messages))  # newest first
        for i, m in enumerate(msgs):
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

# End
