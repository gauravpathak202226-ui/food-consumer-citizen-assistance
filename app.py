import io
import re
import hashlib
from pathlib import Path
from datetime import date

import streamlit as st
import streamlit.components.v1 as components
import speech_recognition as sr
from gtts import gTTS
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape

st.set_page_config(
    page_title="Food & Consumer Citizen Assistance",
    page_icon="🍚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container {max-width:850px;padding:1rem 1rem 4rem}
h1 {font-size:2rem!important}
.big-title {font-size:2.1rem;font-weight:800;text-align:center}
.big-help {font-size:1.2rem;line-height:1.6;text-align:center}
.stButton>button {min-height:58px;font-size:1.08rem;border-radius:14px;width:100%;font-weight:700}
.confirm {background:#f1f7ff;border:1px solid #8bb8e8;border-radius:12px;padding:16px;margin:12px 0}
.warn {background:#fff8e6;border:1px solid #e4b64a;border-radius:12px;padding:12px;margin:12px 0}
.voice-answer {background:#eef8ee;border:1px solid #8bc48b;border-radius:12px;padding:16px;margin:8px 0}
</style>
""", unsafe_allow_html=True)

TEXT = {
    "hi": {
        "dept":"खाद्य एवं उपभोक्ता संरक्षण विभाग",
        "title":"नागरिक सहायता एवं आवेदन प्रणाली",
        "intro":"आप बोलकर या टाइप करके अपनी समस्या बता सकते हैं। आवेदन का नाम जानना जरूरी नहीं है।",
        "speak":"🎤 बोलकर बताएं",
        "type":"⌨️ टाइप करके बताएं",
        "guided":"👆 मुझसे सवाल पूछें",
        "write":"📝 मेरे लिए आवेदन लिखें",
        "confirm":"सही है, आगे बढ़ें",
        "back":"← वापस",
        "new":"नया आवेदन",
        "download":"📄 PDF डाउनलोड करें",
    },
    "en": {
        "dept":"Food & Consumer Protection Department",
        "title":"Citizen Assistance & Application System",
        "intro":"Speak or type your problem. You do not need to know the application name.",
        "speak":"🎤 Speak",
        "type":"⌨️ Type your problem",
        "guided":"👆 Ask me questions",
        "write":"📝 Write an application for me",
        "confirm":"Confirm & Continue",
        "back":"← Back",
        "new":"New application",
        "download":"📄 Download PDF",
    }
}

def L(k):
    return TEXT[st.session_state.lang][k]

COMMON = [
    ("name","पूरा नाम","Full name","text"),
    ("father","पिता / पति का नाम","Father / Husband name","text"),
    ("mobile","मोबाइल नंबर","Mobile number","mobile"),
    ("address","पूरा पता","Complete address","text"),
]

FLOWS = {
    "ration_card": {
        "hi":"नया राशन कार्ड आवेदन","en":"New Ration Card Application",
        "keywords":["राशन कार्ड","नया राशन","ration card","new ration"],
        "questions":[
            ("family","परिवार में कितने सदस्य हैं?","How many members are in your family?","number"),
            ("aadhaar","आधार नंबर बताएं।","Please provide your Aadhaar number.","aadhaar"),
            ("reason","नया राशन कार्ड क्यों बनवाना चाहते हैं?","Why do you want a new ration card?","text"),
        ],
    },
    "ration_not_received": {
        "hi":"राशन नहीं मिलने की शिकायत","en":"Complaint: Ration Not Received",
        "keywords":["राशन नहीं मिला","राशन नही मिला","अनाज नहीं मिला","pds","ration not received"],
        "questions":[
            ("ration_no","राशन कार्ड नंबर बताएं।","Please tell me your ration card number.","text"),
            ("month","किस महीने का राशन नहीं मिला?","For which month did you not receive ration?","text"),
            ("dealer","उचित मूल्य दुकान / दुकानदार का नाम बताएं।","Tell me the fair price shop / dealer name.","text"),
        ],
    },
    "less_ration": {
        "hi":"कम राशन मिलने की शिकायत","en":"Complaint: Less Ration Received",
        "keywords":["कम राशन","कम अनाज","कम गेहूं","कम चावल","less ration","less grain"],
        "questions":[
            ("ration_no","राशन कार्ड नंबर बताएं।","Please tell me your ration card number.","text"),
            ("expected","आपको कितना राशन मिलना चाहिए था?","How much ration should you have received?","text"),
            ("received","आपको वास्तव में कितना राशन मिला?","How much ration did you actually receive?","text"),
            ("dealer","दुकानदार का नाम बताएं।","Tell me the dealer's name.","text"),
        ],
    },
    "ration_correction": {
        "hi":"राशन कार्ड सुधार / समस्या","en":"Ration Card Correction / Problem",
        "keywords":["राशन कार्ड में समस्या","राशन कार्ड सुधार","राशन कार्ड गलत","correction","ration card problem"],
        "questions":[
            ("ration_no","राशन कार्ड नंबर बताएं।","Please tell me your ration card number.","text"),
            ("problem","राशन कार्ड में क्या समस्या है?","What is the problem with the ration card?","text"),
        ],
    },
    "consumer_complaint": {
        "hi":"उपभोक्ता / खाद्य संबंधी शिकायत","en":"Consumer / Food Related Complaint",
        "keywords":["शिकायत","मिलावट","मिलावटी","ज्यादा पैसे","overcharging","consumer complaint","adulteration"],
        "questions":[
            ("shop","दुकान / प्रतिष्ठान का नाम बताएं।","Tell me the shop / establishment name.","text"),
            ("problem","समस्या विस्तार से बताएं।","Explain the problem.","text"),
        ],
    },
}

def detect_flow(text):
    s=(text or "").lower()
    for key, f in FLOWS.items():
        if any(k.lower() in s for k in f["keywords"]):
            return key
    return "consumer_complaint"

def title(flow):
    return FLOWS[flow]["hi"] if st.session_state.lang=="hi" else FLOWS[flow]["en"]

def questions(flow):
    return COMMON + FLOWS[flow]["questions"]

def transcribe(audio):
    if audio is None:
        return ""
    try:
        r=sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio.getvalue())) as source:
            data=r.record(source)
        return r.recognize_google(
            data,
            language="hi-IN" if st.session_state.lang=="hi" else "en-IN"
        )
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        st.error(f"Voice recognition error: {e}")
        return ""

def speak(text):
    try:
        b=io.BytesIO()
        gTTS(
            text=text,
            lang="hi" if st.session_state.lang=="hi" else "en"
        ).write_to_fp(b)
        b.seek(0)
        st.audio(b, format="audio/mp3")
    except Exception:
        pass

def _register_pdf_fonts():
    """Register a Unicode Devanagari font bundled with the app."""
    font_dir = Path(__file__).resolve().parent / "fonts"
    regular = font_dir / "NotoSansDevanagari-Regular.ttf"
    bold = font_dir / "NotoSansDevanagari-Bold.ttf"

    if regular.exists():
        if "NotoDevanagari" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("NotoDevanagari", str(regular)))
        if bold.exists() and "NotoDevanagariBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("NotoDevanagariBold", str(bold)))
        return "NotoDevanagari", ("NotoDevanagariBold" if bold.exists() else "NotoDevanagari")

    # Fallback: useful for English-only environments. The bundled font is
    # required for Hindi/Devanagari text to render correctly.
    fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fallback_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if Path(fallback).exists():
        if "AppDejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("AppDejaVu", fallback))
        if Path(fallback_bold).exists() and "AppDejaVuBold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("AppDejaVuBold", fallback_bold))
        return "AppDejaVu", "AppDejaVuBold"

    return "Helvetica", "Helvetica-Bold"


def _pdf_text(value):
    """Escape user-entered text before putting it inside a ReportLab Paragraph."""
    return escape(str(value or ""))



def formal_subject(flow):
    subjects = {
        "ration_card": "विषय: नया राशन कार्ड निर्गत किए जाने के संबंध में।",
        "ration_not_received": "विषय: माह का राशन प्राप्त नहीं होने के संबंध में शिकायत।",
        "less_ration": "विषय: निर्धारित मात्रा से कम राशन प्राप्त होने के संबंध में शिकायत।",
        "ration_correction": "विषय: राशन कार्ड में आवश्यक सुधार किए जाने के संबंध में।",
        "consumer_complaint": "विषय: खाद्य/उपभोक्ता संबंधी शिकायत के संबंध में आवश्यक कार्रवाई हेतु।",
    }
    return subjects.get(flow, "विषय: आवश्यक कार्रवाई हेतु आवेदन।")


def formal_body(flow, a):
    name = a.get("name", "")
    ration_no = a.get("ration_no", "")
    month = a.get("month", "")
    dealer = a.get("dealer", "")
    expected = a.get("expected", "")
    received = a.get("received", "")
    problem = a.get("problem", "")
    reason = a.get("reason", "")
    family = a.get("family", "")
    shop = a.get("shop", "")

    if flow == "less_ration":
        return (
            f"महोदय/महोदया,\u00a0\u00a0\u00a0\u00a0\u00a0सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। "
            f"माह <b>{escape(month)}</b> में उचित मूल्य दुकान/डीलर <b>{escape(dealer)}</b> से "
            f"मुझे निर्धारित मात्रा <b>{escape(expected)}</b> के स्थान पर केवल <b>{escape(received)}</b> राशन प्राप्त हुआ। "
            "अतः अनुरोध है कि मामले की जांच कर निर्धारित मात्रा के अनुसार राशन उपलब्ध कराने तथा नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।"
        )
    if flow == "ration_not_received":
        return (
            f"महोदय/महोदया,\u00a0\u00a0\u00a0\u00a0\u00a0सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। माह <b>{escape(month)}</b> का राशन "
            f"उचित मूल्य दुकान/डीलर <b>{escape(dealer)}</b> से मुझे प्राप्त नहीं हुआ है। "
            "अतः अनुरोध है कि मामले की जांच कर नियमानुसार आवश्यक कार्रवाई करते हुए मुझे पात्र राशन उपलब्ध कराने की कृपा की जाए।"
        )
    if flow == "ration_card":
        return (
            f"महोदय/महोदया,\u00a0\u00a0\u00a0\u00a0\u00a0सविनय निवेदन है कि मैं <b>{escape(name)}</b> "
            f"एवं मेरे परिवार में कुल <b>{escape(family)}</b> सदस्य हैं। नया राशन कार्ड बनवाने का कारण: "
            f"<b>{escape(reason)}</b>। अतः अनुरोध है कि संलग्न दस्तावेजों के आधार पर नियमानुसार मेरा नया राशन कार्ड निर्गत करने की कृपा की जाए।"
        )
    if flow == "ration_correction":
        return (
            f"महोदय/महोदया,\u00a0\u00a0\u00a0\u00a0\u00a0सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। राशन कार्ड में निम्न समस्या/सुधार अपेक्षित है: "
            f"<b>{escape(problem)}</b>। अतः अनुरोध है कि अभिलेखों की जांच कर आवश्यक सुधार नियमानुसार करने की कृपा की जाए।"
        )
    return (
        f"महोदय/महोदया,\u00a0\u00a0\u00a0\u00a0\u00a0सविनय निवेदन है कि मैं <b>{escape(name)}</b> "
        f"<b>{escape(shop)}</b> से संबंधित निम्न समस्या के संबंध में शिकायत प्रस्तुत कर रहा/रही हूँ: "
        f"<b>{escape(problem)}</b>। अतः अनुरोध है कि मामले की जांच कर नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।"
    )


def attachments_for(flow):
    return {
        "ration_card": [
            "आधार कार्ड की छायाप्रति (परिवार के सभी सदस्यों की)",
            "निवास प्रमाण पत्र की छायाप्रति",
            "परिवार के सदस्यों का विवरण/परिवार रजिस्टर, यदि उपलब्ध हो",
            "पासपोर्ट साइज फोटो",
            "पूर्व राशन कार्ड की छायाप्रति, यदि उपलब्ध हो",
        ],
        "ration_not_received": [
            "राशन कार्ड की छायाप्रति",
            "आधार कार्ड की छायाप्रति",
            "ई-पॉस/राशन वितरण रसीद या पर्ची, यदि उपलब्ध हो",
            "उचित मूल्य दुकान से संबंधित उपलब्ध प्रमाण/फोटो, यदि उपलब्ध हो",
        ],
        "less_ration": [
            "पुराने राशन कार्ड की छायाप्रति",
            "आधार कार्ड की छायाप्रति (परिवार के सभी सदस्यों की)",
            "निवास प्रमाण पत्र की छायाप्रति",
            "पासपोर्ट साइज़ फोटो",
            "राशन कम मिलने का प्रमाण (रसीद/फोटो/पर्ची, यदि उपलब्ध हो)",
        ],
        "ration_correction": [
            "राशन कार्ड की छायाप्रति",
            "सही विवरण से संबंधित पहचान/दस्तावेज की छायाप्रति",
            "आधार कार्ड की छायाप्रति",
            "निवास प्रमाण पत्र की छायाप्रति, यदि आवश्यक हो",
        ],
        "consumer_complaint": [
            "खरीद की रसीद/बिल की छायाप्रति, यदि उपलब्ध हो",
            "उत्पाद/सामग्री का फोटो, यदि उपलब्ध हो",
            "शिकायत से संबंधित अन्य प्रमाण/दस्तावेज",
        ],
    }.get(flow, [])


def formal_office(flow):
    return "प्रखंड आपूर्ति पदाधिकारी / संबंधित सक्षम पदाधिकारी"


def printable_application_html():
    """Render a government-style application with a print button."""
    flow = st.session_state.flow
    answers = st.session_state.answers
    lang = st.session_state.lang

    def esc(v):
        return escape(str(v or ""))

    labels = {
        "name": "नाम / Name",
        "father": "पिता / पति का नाम / Father / Husband Name",
        "mobile": "मोबाइल नंबर / Mobile Number",
        "address": "पूरा पता / Complete Address",
    }

    rows = []
    for key, hi, en, typ in st.session_state.questions:
        label = hi if lang == "hi" else en
        rows.append(f"<tr><th>{esc(label)}</th><td>{esc(answers.get(key, ''))}</td></tr>")

    attachment_html = "".join(
        f"<li>{esc(item)}</li>" for item in attachments_for(flow)
    )

    body = formal_body(flow, answers)
    subject = formal_subject(flow)
    office = formal_office(flow)
    today = date.today().strftime('%d-%m-%Y')

    html = f"""
<!doctype html>
<html lang='hi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<style>
    @font-face {{
        font-family: 'NotoDevanagari';
        src: url('https://fonts.gstatic.com/s/notosansdevanagari/v24/TuG7UUFzXI5FBtUq5a8bjKYTZjtRU6SgvjU.woff2');
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#eef1f5; font-family:'NotoDevanagari', Arial, sans-serif; color:#111; }}
    .toolbar {{ position:sticky; top:0; z-index:10; padding:12px; background:#fff; border-bottom:1px solid #d8d8d8; text-align:center; }}
    .print-btn {{ border:0; border-radius:10px; padding:13px 22px; font-size:17px; font-weight:700; background:#0b57d0; color:white; cursor:pointer; }}
    .paper {{ width:210mm; min-height:297mm; margin:18px auto; padding:18mm 17mm; background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.12); }}
    .dept {{ text-align:center; font-weight:800; font-size:20px; margin-bottom:2px; }}
    .dept-en {{ text-align:center; font-size:12px; margin-bottom:22px; font-family:Arial,sans-serif; }}
    .to {{ margin-bottom:15px; line-height:1.7; }}
    .subject {{ font-weight:800; text-decoration:underline; line-height:1.7; margin:12px 0 15px; }}
    table {{ width:100%; border-collapse:collapse; margin:12px 0 20px; font-size:13px; }}
    th,td {{ border:1px solid #888; padding:8px; vertical-align:top; text-align:left; }}
    th {{ width:36%; font-weight:700; background:#fafafa; }}
    .body {{ font-size:14px; line-height:1.9; text-align:justify; }}
    .attach-title {{ font-weight:800; margin-top:18px; }}
    ol {{ margin-top:7px; line-height:1.8; font-size:13px; }}
    .closing {{ margin-top:25px; line-height:2; }}
    .signature {{ margin-top:25px; line-height:2.0; }}
    .footer-note {{ margin-top:18px; font-size:10px; color:#666; text-align:center; }}
    @media (max-width: 800px) {{
      .paper {{ width:100%; min-height:auto; margin:0; padding:18px 14px; box-shadow:none; }}
      .dept {{ font-size:18px; }}
      .body {{ font-size:14px; }}
      table {{ font-size:12px; }}
    }}
    @media print {{
      @page {{ size:A4; margin:0; }}
      body {{ background:#fff; }}
      .toolbar {{ display:none !important; }}
      .paper {{ width:210mm; min-height:297mm; margin:0; padding:16mm 16mm; box-shadow:none; }}
      .footer-note {{ display:none; }}
    }}
</style>
</head>
<body>
<div class='toolbar'>
  <button class='print-btn' onclick='window.print()'>🖨️ आवेदन प्रिंट करें / Print Application</button>
</div>
<div class='paper' id='application'>
  <div class='dept'>खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
  <div class='dept-en'>FOOD &amp; CONSUMER PROTECTION DEPARTMENT</div>

  <div class='to'><b>सेवा में,</b><br>{esc(office)}<br>संबंधित प्रखंड/कार्यालय: ______________________________</div>

  <div class='subject'>{esc(subject)}</div>

  <table>{''.join(rows)}</table>

  <div class='body'><b>महोदय/महोदया,</b><br>{esc(body)}<br><br>
  अतः उपर्युक्त तथ्यों के आलोक में नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।</div>

  <div class='attach-title'>संलग्नक:</div>
  <ol>{attachment_html}</ol>

  <div class='closing'><b>भवदीय,</b></div>
  <div class='signature'>
    हस्ताक्षर / अंगूठे का निशान: ______________________________<br>
    नाम: {esc(answers.get('name',''))}<br>
    मोबाइल नंबर: {esc(answers.get('mobile',''))}<br>
    आधार संख्या: {esc(answers.get('aadhaar','')) or '______________________________'}<br>
    दिनांक: {today}<br>
    स्थान: ______________________________
  </div>
</div>
</body>
</html>
"""
    components.html(html, height=1180, scrolling=True)

def pdf_file():
    regular_font, bold_font = _register_pdf_fonts()

    b = io.BytesIO()
    doc = SimpleDocTemplate(
        b,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    body = ParagraphStyle(
        "app_body",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=10.5,
        leading=15,
        wordWrap="CJK",
    )

    body_bold = ParagraphStyle(
        "app_body_bold",
        parent=body,
        fontName=bold_font,
    )

    head = ParagraphStyle(
        "app_head",
        parent=styles["Title"],
        fontName=bold_font,
        alignment=TA_CENTER,
        fontSize=15,
        leading=20,
    )

    section = ParagraphStyle(
        "app_section",
        parent=body,
        fontName=bold_font,
        fontSize=11.5,
        leading=17,
    )

    flow = st.session_state.flow
    answers = st.session_state.answers
    story = [
        Paragraph("खाद्य एवं उपभोक्ता संरक्षण विभाग", head),
        Spacer(1, 4),
        Paragraph("Food & Consumer Protection Department", body),
        Spacer(1, 16),
        Paragraph("सेवा में,", body),
        Paragraph(_pdf_text(formal_office(flow)), body),
        Paragraph("संबंधित प्रखंड/कार्यालय: ______________________________", body),
        Spacer(1, 14),
        Paragraph(_pdf_text(formal_subject(flow)), body_bold),
        Spacer(1, 10),
    ]

    rows = []
    for key, hi, en, typ in st.session_state.questions:
        label = hi if st.session_state.lang == "hi" else en
        value = st.session_state.answers.get(key, "")
        rows.append([
            Paragraph("<b>" + _pdf_text(label) + "</b>", body),
            Paragraph(_pdf_text(value), body)
        ])

    table = Table(rows, colWidths=[170, 330], repeatRows=0)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("FONTNAME", (0, 0), (-1, -1), regular_font),
    ]))

    story += [table, Spacer(1, 18)]

    story += [
        Paragraph("<b>महोदय/महोदया,</b>", body),
        Spacer(1, 8),
        Paragraph(formal_body(flow, answers), body),
        Spacer(1, 22),
        Paragraph("अतः उपर्युक्त तथ्यों के आलोक में नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।", body),
        Spacer(1, 22),
        Paragraph("<b>संलग्नक:</b>", section),
    ]

    for idx, item in enumerate(attachments_for(flow), 1):
        story.append(Paragraph(f"{idx}. {_pdf_text(item)}", body))

    story += [
        Spacer(1, 28),
        Paragraph("भवदीय,", body),
        Spacer(1, 28),
        Paragraph("हस्ताक्षर / अंगूठे का निशान: ______________________________", body),
        Spacer(1, 10),
        Paragraph(f"नाम: {_pdf_text(answers.get('name',''))}", body),
        Spacer(1, 8),
        Paragraph(f"मोबाइल नंबर: {_pdf_text(answers.get('mobile',''))}", body),
        Spacer(1, 8),
        Paragraph(f"आधार संख्या: {_pdf_text(answers.get('aadhaar','')) or '______________________________'}", body),
        Spacer(1, 8),
        Paragraph(f"दिनांक: {date.today().strftime('%d-%m-%Y')}", body),
        Spacer(1, 8),
        Paragraph("स्थान: ______________________________", body),
    ]

    doc.build(story)
    b.seek(0)
    return b

for k,v in {
    "lang":"hi",
    "stage":"home",
    "flow":None,
    "questions":[],
    "q_index":0,
    "answers":{},
    "problem":"",
    "voice_text":"",
    "voice_hash":""
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

c1,c2=st.columns([4,1])
with c1:
    st.markdown(f"### 🍚 {L('dept')}")
    st.caption(L("title"))
with c2:
    if st.button("English" if st.session_state.lang=="hi" else "हिन्दी"):
        st.session_state.lang="en" if st.session_state.lang=="hi" else "hi"
        st.rerun()

if st.session_state.stage=="home":
    st.markdown(f'<div class="big-title">{L("title")}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="big-help">{L("intro")}</div>',unsafe_allow_html=True)
    st.markdown(
        '<div class="warn">⚠️ Public prototype: use dummy data while testing. '
        'Do not enter real Aadhaar or other sensitive personal data.</div>',
        unsafe_allow_html=True
    )
    a,b=st.columns(2)
    with a:
        if st.button(L("speak")):
            st.session_state.stage="voice_problem"
            st.rerun()
        if st.button(L("guided")):
            st.session_state.flow="consumer_complaint"
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0
            st.session_state.answers={}
            st.session_state.stage="question"
            st.rerun()
    with b:
        if st.button(L("type")):
            st.session_state.stage="type_problem"
            st.rerun()
        if st.button(L("write")):
            st.session_state.stage="type_problem"
            st.rerun()
    st.subheader("उदाहरण / Examples")
    st.write("“मुझे इस महीने राशन नहीं मिला।”")
    st.write("“मुझे कम चावल मिला।”")
    st.write("“मुझे नया राशन कार्ड बनवाना है।”")
    st.write("“दुकानदार ने ज्यादा पैसे लिए।”")

elif st.session_state.stage=="voice_problem":
    st.header(L("speak"))
    audio=st.audio_input(
        "🎤 माइक्रोफोन दबाकर बोलें / Press microphone and speak",
        sample_rate=16000
    )
    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if h!=st.session_state.voice_hash:
            st.session_state.voice_hash=h
            st.session_state.voice_text=transcribe(audio)

    if st.session_state.voice_text:
        st.markdown(
            f'<div class="confirm"><b>आपने कहा / You said:</b><br>'
            f'{st.session_state.voice_text}</div>',
            unsafe_allow_html=True
        )
        if st.button("🔊 सुनें / Hear"):
            speak(st.session_state.voice_text)
        if st.button(L("confirm"),type="primary"):
            st.session_state.problem=st.session_state.voice_text
            st.session_state.flow=detect_flow(st.session_state.problem)
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0
            st.session_state.answers={}
            st.session_state.stage="question"
            st.rerun()

    if st.button(L("back")):
        st.session_state.stage="home"
        st.rerun()

elif st.session_state.stage=="type_problem":
    st.header(L("write"))
    problem=st.text_area(
        "अपनी समस्या बताएं / Tell us your problem",
        value=st.session_state.problem,
        height=140
    )
    audio=st.audio_input(
        "🎤 या बोलें / Or speak",
        sample_rate=16000
    )
    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if h!=st.session_state.voice_hash:
            st.session_state.voice_hash=h
            t=transcribe(audio)
            if t:
                problem=t

    if st.button("आगे बढ़ें / Continue",type="primary"):
        if problem.strip():
            st.session_state.problem=problem.strip()
            st.session_state.flow=detect_flow(problem)
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0
            st.session_state.answers={}
            st.session_state.stage="question"
            st.rerun()
        else:
            st.warning("कृपया समस्या बताएं। / Please tell us the problem.")

    if st.button(L("back")):
        st.session_state.stage="home"
        st.rerun()

elif st.session_state.stage=="question":
    q=st.session_state.questions[st.session_state.q_index]
    key,hi,en,typ=q
    qtext=hi if st.session_state.lang=="hi" else en

    st.progress(
        st.session_state.q_index/max(len(st.session_state.questions),1)
    )
    st.caption(
        f"Step {st.session_state.q_index+1} / {len(st.session_state.questions)}"
    )
    st.header(qtext)

    if st.button("🔊 सवाल सुनें / Hear question"):
        speak(qtext)

    current=st.session_state.answers.get(key,"")

    if typ=="number":
        answer=str(
            st.number_input(
                "उत्तर / Answer",
                min_value=1,
                max_value=100,
                value=int(current or 1),
                key=f"n_{key}_{st.session_state.q_index}"
            )
        )
    else:
        answer=st.text_input(
            "उत्तर / Answer",
            value=current,
            key=f"a_{key}_{st.session_state.q_index}"
        )

    audio=st.audio_input(
        "🎤 बोलकर उत्तर दें / Answer by voice",
        sample_rate=16000,
        key=f"audio_{key}_{st.session_state.q_index}"
    )

    voice_key=f"voice_{key}_{st.session_state.q_index}"
    hash_key=f"h_{key}_{st.session_state.q_index}"

    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if st.session_state.get(hash_key)!=h:
            st.session_state[hash_key]=h
            t=transcribe(audio)
            if t:
                st.session_state[voice_key]=t

    voice=st.session_state.get(voice_key,"").strip()

    # IMPORTANT:
    # The recognized voice answer and its confirmation buttons are shown
    # side-by-side on the SAME SCREEN. No stale text_input value is used.
    if voice:
        left,right=st.columns([3,2],vertical_alignment="center")

        with left:
            st.markdown(
                f'<div class="voice-answer"><b>🎤 आपने कहा / You said:</b><br>'
                f'<span style="font-size:1.15rem">{voice}</span></div>',
                unsafe_allow_html=True
            )

        with right:
            if st.button(
                "✅ हाँ, सही है\nYes, correct",
                type="primary",
                key=f"voice_yes_{key}_{st.session_state.q_index}"
            ):
                st.session_state.answers[key]=voice
                st.session_state.pending=(
                    key,
                    voice,
                    st.session_state.q_index
                )
                st.session_state.stage="confirm"
                st.rerun()

            if st.button(
                "🔄 दोबारा बोलें\nSpeak again",
                key=f"voice_again_{key}_{st.session_state.q_index}"
            ):
                st.session_state.pop(voice_key,None)
                st.session_state.pop(hash_key,None)
                st.rerun()

        st.caption(
            "ऊपर दिखाया गया उत्तर सही होने पर “हाँ, सही है” दबाएं। "
            "गलत होने पर “दोबारा बोलें” दबाएं।"
            if st.session_state.lang=="hi"
            else "If the displayed answer is correct, tap “Yes, correct”. "
                 "If it is wrong, tap “Speak again”."
        )

    a,b=st.columns(2)

    with a:
        if st.button(L("back")):
            if st.session_state.q_index==0:
                st.session_state.stage="home"
            else:
                st.session_state.q_index-=1
            st.rerun()

    with b:
        if st.button(
            L("confirm"),
            type="primary",
            key=f"text_confirm_{key}_{st.session_state.q_index}"
        ):
            answer=str(answer).strip()
            valid=True

            if not answer:
                st.warning(
                    "कृपया उत्तर दें। / Please provide an answer."
                )
                valid=False

            if (
                typ=="mobile"
                and answer
                and not re.fullmatch(r"\d{10}",answer)
            ):
                st.error("10 अंकों का मोबाइल नंबर दें।")
                valid=False

            if (
                typ=="aadhaar"
                and answer
                and not re.fullmatch(r"\d{12}",answer.replace(" ",""))
            ):
                st.error("12 अंकों का आधार नंबर दें।")
                valid=False

            if valid:
                st.session_state.answers[key]=answer
                st.session_state.pending=(
                    key,
                    answer,
                    st.session_state.q_index
                )
                st.session_state.stage="confirm"
                st.rerun()

elif st.session_state.stage=="confirm":
    key,answer,i=st.session_state.pending
    q=st.session_state.questions[i]
    qtext=q[1] if st.session_state.lang=="hi" else q[2]

    st.header("कृपया पुष्टि करें / Please confirm")
    st.write("**"+qtext+"**")
    st.markdown(
        f'<div class="confirm"><h3>{answer}</h3></div>',
        unsafe_allow_html=True
    )

    a,b=st.columns(2)

    with a:
        if st.button("✏️ बदलें / Change"):
            st.session_state.stage="question"
            st.rerun()

    with b:
        if st.button(
            "✅ हाँ, सही है / Yes, correct",
            type="primary"
        ):
            st.session_state.q_index+=1
            st.session_state.stage=(
                "review"
                if st.session_state.q_index>=len(st.session_state.questions)
                else "question"
            )
            st.rerun()

elif st.session_state.stage=="review":
    st.header("🔎 अंतिम जांच / Final review")
    st.subheader(title(st.session_state.flow))

    for q in st.session_state.questions:
        key,hi,en,typ=q
        label=hi if st.session_state.lang=="hi" else en
        st.write(
            f"**{label}:** {st.session_state.answers.get(key,'')}"
        )

    if st.button("✏️ जानकारी बदलें / Edit"):
        st.session_state.q_index=0
        st.session_state.stage="question"
        st.rerun()

    if st.button(
        "✅ पुष्टि करें और आवेदन बनाएं / Generate application",
        type="primary"
    ):
        st.session_state.stage="application"
        st.rerun()

elif st.session_state.stage=="application":
    st.header("📄 औपचारिक आवेदन / Formal Application")
    st.success("आपका सरकारी कार्यालय शैली में आवेदन तैयार है। / Your formal application is ready.")

    printable_application_html()

    pdf=pdf_file()

    st.download_button(
        L("download"),
        data=pdf,
        file_name="citizen_application.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    if st.button(L("new"),type="primary"):
        st.session_state.clear()
        st.rerun()
