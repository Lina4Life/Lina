import streamlit as st
from pathlib import Path
from PIL import Image
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# Page config
st.set_page_config(page_title="For Lina 💖", page_icon="❤️", layout="centered")

# Styles
RED_BG = "#ffedf0"
ACCENT = "#d81b60"  # deep pink/red

st.markdown(f"""<style>
body {{background: linear-gradient(180deg, #fff 0%, {RED_BG} 100%);}}
.main {{background: transparent;}}
h1 {{color: {ACCENT}; font-family: 'Georgia', serif;}}
h2 {{color: {ACCENT};}}
.card {{background: white; border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(216,27,96,0.08);}}
.love-text {{font-size:20px; color:#8b1a3a; line-height:1.5}}
.btn-red {{background:{ACCENT}; color:white; padding:10px 18px; border-radius:8px;}}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
st.markdown("<h1>For Lina</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#b71c46'>My beautiful cutie pie 💕</h3>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Main card
st.markdown("<div class='card'>", unsafe_allow_html=True)

# Left: image if available
assets = [p for p in Path('.').glob('*') if p.suffix.lower() in ['.png', '.jpg', '.jpeg']]
selected_image = None
if assets:
    # Prefer images that mention "Lina" or look romantic
    for p in assets:
        if 'lina' in p.name.lower() or 'cutie' in p.name.lower() or 'good' in p.name.lower() or 'rose' in p.name.lower():
            selected_image = p
            break
    if not selected_image:
        selected_image = assets[0]

# Layout
col1, col2 = st.columns([1, 2])
with col1:
    if selected_image:
        try:
            img = Image.open(selected_image)
            st.image(img, use_container_width=True, caption=selected_image.name)
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

# Interactive section
st.markdown("<h2 style='text-align:center;'>A tiny surprise</h2>", unsafe_allow_html=True)
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

# Footer with a short poem
poem = """
Roses whisper red, in twilight's hush,
Your name, Lina, blooms within my chest.
Soft as morning light, bold as a blush—
With you, my heart has found its rest.
"""
st.markdown("<div style='margin-top:20px; text-align:center; color:#7a1128;'>" + poem.replace('\n', '<br>') + "</div>", unsafe_allow_html=True)

# Small credits
st.markdown("<div style='text-align:center; margin-top:18px; font-size:12px; color:#a62b45;'>Made with ❤️ just for Lina</div>", unsafe_allow_html=True)
