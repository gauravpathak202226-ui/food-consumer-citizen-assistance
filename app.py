import io
import re
import hashlib
import base64
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
import uuid
import random
import string
import os
import requests

import streamlit as st
import streamlit.components.v1 as components
import speech_recognition as sr
from gtts import gTTS
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
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
        "sms_success":"📱 आपके पंजीकृत मोबाइल नंबर पर अनुरोध की सूचना भेज दी गई है।",
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

WELCOME_HI = "नमस्कार- मैं खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार की ओर से आपकी सेवा में उपस्थित हूँ। कृपया मुझे अपनी समस्या बताएं।"
WELCOME_EN = "Namaskar. I am here to assist you on behalf of the Food & Consumer Protection Department, Government of Bihar. Please tell me your problem."

IST = ZoneInfo("Asia/Kolkata")

def application_timestamp():
    return datetime.now(IST)

def ensure_application_metadata():
    """Create one stable request ID and timestamp for the current application."""
    if not st.session_state.get("application_id"):
        now = application_timestamp()
        # Compact 6-character request ID: 2 letters + 4 digits, e.g. AB4827.
        # For production, reserve/check IDs in a central database to guarantee
        # uniqueness across all applications.
        letters = "".join(random.SystemRandom().choice(string.ascii_uppercase) for _ in range(2))
        digits = f"{random.SystemRandom().randint(0, 9999):04d}"
        st.session_state.application_id = f"{letters}{digits}"
        st.session_state.application_datetime = now.strftime("%d-%m-%Y %H:%M:%S")
    return st.session_state.application_id, st.session_state.application_datetime

def application_sms_text(application_id):
    return (
        f"आपका अनुरोध क्रमांक {application_id} है। "
        "आपकी समस्या के समाधान हेतु हमारी टीम इस पर कार्य कर रही है "
        "और इसे यथाशीघ्र निस्तारित करने का प्रयास किया जा रहा है। "
        "- खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार"
    )

def send_application_sms(mobile, application_id):
    """Send the registered-mobile notification through MSG91 Flow API.

    Required Streamlit secrets:
      MSG91_AUTH_KEY, MSG91_TEMPLATE_ID
    Optional: MSG91_SENDER_ID if the approved flow expects it.
    The Hindi message must be configured as an approved DLT template with a
    variable named VAR1 containing the request/application ID.
    """
    mobile = re.sub(r"\D", "", str(mobile or ""))
    if not re.fullmatch(r"[6-9]\d{9}", mobile):
        return False, "मोबाइल नंबर मान्य नहीं है।"

    try:
        authkey = st.secrets.get("MSG91_AUTH_KEY", "")
        template_id = st.secrets.get("MSG91_TEMPLATE_ID", "")
    except Exception:
        authkey = os.getenv("MSG91_AUTH_KEY", "")
        template_id = os.getenv("MSG91_TEMPLATE_ID", "")
    if not authkey or not template_id:
        # Demo mode: lets you test the complete workflow without exposing
        # credentials or sending a real SMS. Configure Streamlit secrets for SMS.
        return True, "DEMO_SMS_NOT_SENT"

    recipient = {"mobiles": "91" + mobile, "VAR1": application_id}

    payload = {
        "template_id": template_id,
        "short_url": "0",
        "recipients": [recipient],
    }
    try:
        response = requests.post(
            "https://control.msg91.com/api/v5/flow",
            headers={
                "accept": "application/json",
                "authkey": authkey,
                "content-type": "application/json",
            },
            json=payload,
            timeout=12,
        )
        data = response.json() if response.content else {}
        if response.ok and str(data.get("type", "")).lower() == "success":
            return True, str(data.get("message", "sent"))
        return False, str(data.get("message", f"HTTP {response.status_code}"))
    except Exception as exc:
        return False, str(exc)

def notify_registered_mobile():
    """Send exactly one notification for the current application generation."""
    if st.session_state.get("sms_status") is not None:
        return st.session_state.sms_status, st.session_state.get("sms_detail", "")
    mobile = st.session_state.answers.get("mobile", "")
    app_id = st.session_state.application_id
    ok, detail = send_application_sms(mobile, app_id)
    st.session_state.sms_status = "sent" if ok else "not_sent"
    st.session_state.sms_detail = detail
    return st.session_state.sms_status, detail

def logo_data_uri():
    logo_path = Path(__file__).resolve().parent / "bihar_gov_logo.png"
    if not logo_path.exists():
        return ""
    try:
        data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return "data:image/png;base64," + data
    except Exception:
        return ""



def asset_data_uri(filename):
    """Return a local image as a data URI for reliable Streamlit rendering."""
    path = Path(__file__).resolve().parent / filename
    if not path.exists():
        return ""
    try:
        suffix = path.suffix.lower()
        mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else ("image/svg+xml" if suffix == ".svg" else "image/png")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""

def welcome_message():
    return WELCOME_HI if st.session_state.lang == "hi" else WELCOME_EN

def play_welcome_audio():
    try:
        b = io.BytesIO()
        gTTS(
            text=WELCOME_HI if st.session_state.lang == "hi" else WELCOME_EN,
            lang="hi" if st.session_state.lang == "hi" else "en"
        ).write_to_fp(b)
        b64 = base64.b64encode(b.getvalue()).decode("ascii")
        components.html(
            f'<audio controls autoplay style="width:100%;height:42px">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mpeg"></audio>',
            height=50,
        )
    except Exception:
        speak(welcome_message())

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
            f"सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। "
            f"माह <b>{escape(month)}</b> में उचित मूल्य दुकान/डीलर <b>{escape(dealer)}</b> से "
            f"मुझे निर्धारित मात्रा <b>{escape(expected)}</b> के स्थान पर केवल <b>{escape(received)}</b> राशन प्राप्त हुआ। "
            "अतः अनुरोध है कि मामले की जांच कर निर्धारित मात्रा के अनुसार राशन उपलब्ध कराने तथा नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।"
        )
    if flow == "ration_not_received":
        return (
            f"सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। माह <b>{escape(month)}</b> का राशन "
            f"उचित मूल्य दुकान/डीलर <b>{escape(dealer)}</b> से मुझे प्राप्त नहीं हुआ है। "
            "अतः अनुरोध है कि मामले की जांच कर नियमानुसार आवश्यक कार्रवाई करते हुए मुझे पात्र राशन उपलब्ध कराने की कृपा की जाए।"
        )
    if flow == "ration_card":
        return (
            f"सविनय निवेदन है कि मैं <b>{escape(name)}</b> "
            f"एवं मेरे परिवार में कुल <b>{escape(family)}</b> सदस्य हैं। नया राशन कार्ड बनवाने का कारण: "
            f"<b>{escape(reason)}</b>। अतः अनुरोध है कि संलग्न दस्तावेजों के आधार पर नियमानुसार मेरा नया राशन कार्ड निर्गत करने की कृपा की जाए।"
        )
    if flow == "ration_correction":
        return (
            f"सविनय निवेदन है कि मैं <b>{escape(name)}</b>, "
            f"राशन कार्ड संख्या <b>{escape(ration_no)}</b> का लाभार्थी हूँ। राशन कार्ड में निम्न समस्या/सुधार अपेक्षित है: "
            f"<b>{escape(problem)}</b>। अतः अनुरोध है कि अभिलेखों की जांच कर आवश्यक सुधार नियमानुसार करने की कृपा की जाए।"
        )
    return (
        f"सविनय निवेदन है कि मैं <b>{escape(name)}</b> "
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
    """Render a formal citizen application in Bihar government letter style.

    The layout follows the visual structure of the attached BIPARD official
    letter (letterhead, addressee, subject, formal body, closing and copies),
    while clearly presenting this document as a citizen application rather
    than an official departmental letter.
    """
    flow = st.session_state.flow
    answers = st.session_state.answers
    app_id, app_dt = ensure_application_metadata()
    today = datetime.strptime(app_dt, '%d-%m-%Y %H:%M:%S').strftime('%d-%m-%Y')
    app_time = datetime.strptime(app_dt, '%d-%m-%Y %H:%M:%S').strftime('%H:%M:%S')

    def esc(v):
        return escape(str(v or ""))

    body = formal_body(flow, answers)
    subject = formal_subject(flow)
    office = formal_office(flow)
    attachment_html = "".join(f"<li>{esc(item)}</li>" for item in attachments_for(flow))
    logo = logo_data_uri()

    html = f"""
<!doctype html>
<html lang='hi'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<style>
@font-face {{
  font-family:'NotoDevanagari';
  src:url('https://fonts.gstatic.com/s/notosansdevanagari/v24/TuG7UUFzXI5FBtUq5a8bjKYTZjtRU6SgvjU.woff2');
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#eef1f5; color:#111; font-family:'NotoDevanagari', Arial, sans-serif; }}
.toolbar {{ position:sticky; top:0; z-index:20; padding:12px; background:#fff; border-bottom:1px solid #d0d0d0; text-align:center; }}
.print-btn {{ border:0; border-radius:10px; padding:13px 24px; font-size:17px; font-weight:700; background:#0b57d0; color:#fff; cursor:pointer; }}
.paper {{ width:210mm; min-height:297mm; margin:18px auto; padding:14mm 18mm 16mm; background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.12); }}
.header {{ text-align:center; border-bottom:1px solid #555; padding-bottom:8px; margin-bottom:16px; }}
.logo {{ width:66px; height:66px; object-fit:contain; margin-bottom:2px; }}
.dept {{ font-weight:800; font-size:20px; line-height:1.35; }}
.gov {{ font-weight:700; font-size:15px; line-height:1.4; }}
.en {{ font-family:Arial,sans-serif; font-size:11px; margin-top:2px; }}
.date {{ text-align:right; margin:7px 0 15px; font-size:13px; }}
.to {{ line-height:1.75; margin-bottom:14px; }}
.subject {{ font-weight:800; text-decoration:underline; line-height:1.75; margin:13px 0 16px; }}
.salutation {{ font-weight:700; margin-bottom:7px; }}
.body {{ font-size:14px; line-height:2.0; text-align:justify; }}
.attach-title {{ font-weight:800; margin-top:22px; margin-bottom:5px; }}
ol {{ margin-top:5px; padding-left:25px; line-height:1.8; font-size:13px; }}
.closing {{ margin-top:24px; line-height:2; }}
.signature {{ margin-top:10px; margin-left:0; line-height:2.0; font-size:13px; }}
.notice {{ margin-top:28px; padding-top:7px; border-top:1px solid #bbb; font-size:9px; color:#666; text-align:center; }}
@media(max-width:800px) {{
 .paper {{ width:100%; min-height:auto; margin:0; padding:18px 15px 25px; box-shadow:none; }}
 .dept {{ font-size:18px; }} .body {{ font-size:14px; }}
}}
@media print {{
 @page {{ size:A4; margin:0; }}
 body {{ background:#fff; }} .toolbar {{ display:none !important; }}
 .paper {{ width:210mm; min-height:297mm; margin:0; padding:14mm 18mm 16mm; box-shadow:none; }}
 .notice {{ display:none; }}
}}
</style>
</head>
<body>
<div class='toolbar'><button class='print-btn' onclick='window.print()'>🖨️ आवेदन प्रिंट करें / Print Application</button></div>
<div class='paper'>
  <div class='header'>
    {f"<img class='logo' src='{logo}' alt='BIPARD logo'>" if logo else ''}
    <div class='dept'>खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
    <div class='gov'>बिहार सरकार</div>
    <div class='en'>FOOD &amp; CONSUMER PROTECTION DEPARTMENT</div>
  </div>

  <div class='date'><b>दिनांक:</b> {today}<br><b>समय:</b> {app_time}<br><b>अनुरोध क्रमांक:</b> {esc(app_id)}</div>

  <div class='to'>
    <b>सेवा में,</b><br>
    {esc(office)}<br>
    संबंधित प्रखंड/कार्यालय: ______________________________
  </div>

  <div class='subject'>{esc(subject)}</div>

  <div class='salutation'>महोदय/महोदया,</div>
  <div class='body'>{body}</div>

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

  <div class='notice'>यह नागरिक द्वारा तैयार आवेदन का प्रारूप है। यह किसी सरकारी कार्यालय द्वारा जारी पत्र/आदेश नहीं है।</div>
</div>
</body>
</html>
"""
    components.html(html, height=1100, scrolling=True)


def pdf_file():
    """Create an A4 formal citizen application with Devanagari support."""
    regular_font, bold_font = _register_pdf_fonts()
    b = io.BytesIO()
    doc = SimpleDocTemplate(
        b, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=42, bottomMargin=42
    )
    styles = getSampleStyleSheet()

    body = ParagraphStyle(
        "app_body", parent=styles["BodyText"], fontName=regular_font,
        fontSize=10.5, leading=17, wordWrap="CJK"
    )
    bold = ParagraphStyle(
        "app_bold", parent=body, fontName=bold_font
    )
    head = ParagraphStyle(
        "app_head", parent=styles["Title"], fontName=bold_font,
        alignment=TA_CENTER, fontSize=15, leading=20
    )
    small = ParagraphStyle(
        "app_small", parent=body, fontSize=8.5, leading=12, alignment=TA_CENTER
    )

    flow = st.session_state.flow
    answers = st.session_state.answers
    app_id, app_dt = ensure_application_metadata()
    app_date = datetime.strptime(app_dt, '%d-%m-%Y %H:%M:%S').strftime('%d-%m-%Y')
    app_time = datetime.strptime(app_dt, '%d-%m-%Y %H:%M:%S').strftime('%H:%M:%S')
    logo_path = Path(__file__).resolve().parent / "bihar_gov_logo.png"
    story = []

    if logo_path.exists():
        logo = RLImage(str(logo_path), width=52, height=52)
        title_block = [
            Paragraph("खाद्य एवं उपभोक्ता संरक्षण विभाग", head),
            Paragraph("बिहार सरकार", bold),
            Paragraph("Food & Consumer Protection Department", body),
        ]
        ht = Table([[logo, title_block]], colWidths=[65, 435])
        ht.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (0,0), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
        story.append(ht)
    else:
        story += [Paragraph("खाद्य एवं उपभोक्ता संरक्षण विभाग", head), Paragraph("बिहार सरकार", bold)]

    story += [
        Spacer(1, 5),
        Paragraph(f"अनुरोध क्रमांक: {_pdf_text(app_id)}", bold),
        Paragraph(f"दिनांक: {app_date}", body),
        Paragraph(f"समय: {app_time}", body),
        Spacer(1, 14),
        Paragraph("सेवा में,", body),
        Paragraph(_pdf_text(formal_office(flow)), body),
        Paragraph("संबंधित प्रखंड/कार्यालय: ______________________________", body),
        Spacer(1, 13),
        Paragraph(_pdf_text(formal_subject(flow)), bold),
        Spacer(1, 14),
        Paragraph("महोदय/महोदया,", bold),
        Spacer(1, 4),
        Paragraph(formal_body(flow, answers), body),
        Spacer(1, 20),
        Paragraph("संलग्नक:", bold),
    ]

    for idx, item in enumerate(attachments_for(flow), 1):
        story.append(Paragraph(f"{idx}. {_pdf_text(item)}", body))

    story += [
        Spacer(1, 25),
        Paragraph("भवदीय,", body),
        Spacer(1, 24),
        Paragraph("हस्ताक्षर / अंगूठे का निशान: ______________________________", body),
        Spacer(1, 8),
        Paragraph(f"नाम: {_pdf_text(answers.get('name',''))}", body),
        Spacer(1, 6),
        Paragraph(f"मोबाइल नंबर: {_pdf_text(answers.get('mobile',''))}", body),
        Spacer(1, 6),
        Paragraph(f"आधार संख्या: {_pdf_text(answers.get('aadhaar','')) or '______________________________'}", body),
        Spacer(1, 6),
        Paragraph(f"दिनांक: {app_date}", body),
        Spacer(1, 6),
        Paragraph("स्थान: ______________________________", body),
        Spacer(1, 15),
        Paragraph("यह नागरिक द्वारा तैयार आवेदन का प्रारूप है। यह किसी सरकारी कार्यालय द्वारा जारी पत्र/आदेश नहीं है।", small),
    ]

    doc.build(story)
    b.seek(0)
    return b

for k,v in {
    "lang":"hi",
    "stage":"login",
    "flow":None,
    "questions":[],
    "q_index":0,
    "answers":{},
    "problem":"",
    "voice_text":"",
    "voice_hash":"",
    "application_id":None,
    "application_datetime":None,
    "sms_status":None,
    "sms_detail":"",
    "registered_mobile":"",
    "login_mobile":"",
    "otp_sent":False,
    "logged_in":False
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

# Official-style Bihar Government / Department header.
# Current office-holder names are based on the Bihar Food & Consumer Protection
# Department's official EPDS portal.
bihar_logo_uri = asset_data_uri("bihar_gov_logo.png")
cm_uri = asset_data_uri("cm_samrat.png")
minister_uri = asset_data_uri("minister_ashok.png")

st.markdown("""
<style>

.login-shell {max-width:760px;margin:8px auto 18px;padding:20px 14px 24px;border-radius:24px;background:linear-gradient(135deg,#f8fbff 0%,#eef5ff 55%,#fffaf0 100%);border:1px solid #d9e4f1;box-shadow:0 8px 30px rgba(16,61,115,.08);}
.login-logo {width:105px;height:105px;object-fit:contain;display:block;margin:0 auto 6px;}
.brand-hi {text-align:center;font-size:2.2rem;font-weight:900;color:#123b73;line-height:1.15;}
.brand-sub {text-align:center;font-size:1rem;font-weight:800;color:#7a4a00;margin-top:4px;}
.tagline {text-align:center;font-size:1.15rem;font-weight:800;color:#174a8b;margin:12px 0 18px;}
.character-row {display:flex;justify-content:center;gap:28px;margin:8px auto 18px;}
.character {width:190px;padding:14px 10px 12px;border-radius:22px;background:rgba(255,255,255,.88);border:1px solid #dfe7f1;text-align:center;}
.character-img {width:140px;height:166px;object-fit:contain;display:block;margin:0 auto 8px;}
.character-emoji {font-size:76px;line-height:1;margin-bottom:8px;}
.character-label {font-weight:800;color:#173f78;}
.login-card {max-width:560px;margin:0 auto;background:#fff;border:1px solid #dbe4ef;border-radius:20px;padding:18px;box-shadow:0 5px 18px rgba(0,0,0,.06);}
.login-title {font-size:1.35rem;font-weight:900;text-align:center;color:#123b73;margin-bottom:12px;}
.login-note {text-align:center;font-size:.85rem;color:#667085;margin-top:10px;}
.footer-bar {margin:28px -1rem -3rem;padding:18px 12px 24px;background:#0d467f;color:#fff;text-align:center;font-size:1.35rem;font-weight:900;border-top:4px solid #e8b923;}
.footer-sub {font-size:.78rem;font-weight:500;margin-top:4px;opacity:.9;}
.dashboard-welcome {background:#fff;border:1px solid #dce5ef;border-radius:18px;padding:16px;margin:10px 0 16px;text-align:center;}
.service-grid {margin-top:12px;}
.demo-badge {display:inline-block;padding:5px 10px;border-radius:999px;background:#fff3cd;color:#7a5b00;font-size:.78rem;font-weight:700;margin:6px 0 12px;}
@media(max-width:650px){.login-shell{padding:16px 10px 20px;border-radius:18px}.brand-hi{font-size:1.8rem}.tagline{font-size:1rem}.character-row{gap:8px}.character{width:46%;padding:10px 5px}.character-img{width:105px;height:125px}.character-emoji{font-size:55px}.login-card{padding:14px}.footer-bar{font-size:1.15rem}}
.gov-hero {border-radius:18px;padding:18px 14px 20px;margin:4px 0 18px;background:linear-gradient(135deg,#f7f9fc 0%,#eef4ff 55%,#fff 100%);border:1px solid #d8e2ef;text-align:center;}
.gov-logo {width:82px;height:82px;object-fit:contain;margin-bottom:6px;}
.gov-name-hi {font-size:1.9rem;font-weight:800;line-height:1.25;color:#123b73;}
.gov-name-en {font-size:1rem;font-weight:700;letter-spacing:.4px;color:#3f4c5c;margin-top:3px;}
.bihar-quote {font-size:1.65rem;font-weight:900;color:#173f78;margin:12px 0 2px;}
.bihar-quote-sub {font-size:.92rem;color:#667085;}
.profile-row {display:flex;gap:14px;justify-content:center;margin:16px 0 10px;}
.profile-card {flex:1;max-width:320px;background:white;border:1px solid #dce3ec;border-radius:16px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);text-align:center;}
.profile-card img {width:120px;height:120px;object-fit:cover;border-radius:12px;border:1px solid #e2e8f0;}
.profile-name {font-size:1.08rem;font-weight:800;color:#174a8b;margin-top:8px;}
.profile-role {font-size:.9rem;font-weight:700;color:#b42318;margin-top:2px;}
@media(max-width:650px){.gov-name-hi{font-size:1.55rem}.bihar-quote{font-size:1.35rem}.profile-row{gap:8px}.profile-card{padding:9px}.profile-card img{width:92px;height:92px}.profile-name{font-size:.95rem}.profile-role{font-size:.78rem}}
</style>
""", unsafe_allow_html=True)


if st.session_state.stage=="login":
    logo_html = f'<img class="login-logo" src="{bihar_logo_uri}" alt="Bihar Government logo">' if bihar_logo_uri else ''
    man_uri = asset_data_uri("bihari_man.svg")
    woman_uri = asset_data_uri("bihari_woman.svg")
    man_html = f'<img class="character-img" src="{man_uri}" alt="Traditional Bihari man welcoming citizen">' if man_uri else '<div class="character-emoji">👨🏻🙏</div>'
    woman_html = f'<img class="character-img" src="{woman_uri}" alt="Traditional Bihari woman welcoming citizen">' if woman_uri else '<div class="character-emoji">👩🏻🙏</div>'
    st.markdown(f"""
    <div class="login-shell">
      {logo_html}
      <div class="brand-hi">जनसेवक बिहार</div>
      <div class="brand-sub">नागरिक सहायता एवं सेवा प्रणाली</div>
      <div class="tagline">“आपकी समस्या, हमारी प्राथमिकता”</div>
      <div class="character-row">
        <div class="character">{man_html}<div class="character-label">बिहारी परिधान में स्वागत</div></div>
        <div class="character">{woman_html}<div class="character-label">बिहारी परिधान में स्वागत</div></div>
      </div>
      <div class="login-card">
        <div class="login-title">नागरिक लॉगिन / Citizen Login</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.info("🔐 डेमो परीक्षण के लिए OTP: 123456  |  वास्तविक प्रणाली में OTP SMS gateway से भेजा जाएगा।")
    mobile = st.text_input("📱 पंजीकृत मोबाइल नंबर / Registered mobile number", max_chars=10, placeholder="10 अंकों का मोबाइल नंबर")
    if st.button("📨 OTP भेजें / Send OTP", use_container_width=True):
        if not re.fullmatch(r"[6-9]\d{9}", mobile.strip()):
            st.error("कृपया 10 अंकों का मान्य मोबाइल नंबर दर्ज करें।")
        else:
            st.session_state.login_mobile = mobile.strip()
            st.session_state.otp_sent = True
            st.success("OTP भेजा गया है। डेमो में OTP 123456 है।")

    if st.session_state.get("otp_sent"):
        otp = st.text_input("🔢 OTP दर्ज करें / Enter OTP", max_chars=6, type="password")
        if st.button("🔓 लॉगिन करें / Login", type="primary", use_container_width=True):
            if otp == "123456":
                st.session_state.logged_in = True
                st.session_state.registered_mobile = st.session_state.login_mobile
                st.session_state.answers["mobile"] = st.session_state.login_mobile
                st.session_state.stage = "dashboard"
                st.session_state.otp_sent = False
                st.rerun()
            else:
                st.error("गलत OTP। डेमो OTP 123456 है।")

    st.markdown("<div class='login-note'>यह एक कार्यशील प्रोटोटाइप है। परीक्षण के दौरान वास्तविक आधार/संवेदनशील जानकारी दर्ज न करें।</div>", unsafe_allow_html=True)

    st.markdown("<div class='footer-bar'>सरकार आपके द्वार<div class='footer-sub'>सुगम सेवा • सशक्त नागरिक • समृद्ध बिहार</div></div>", unsafe_allow_html=True)

elif st.session_state.stage=="dashboard":
    logo_html = f'<img class="gov-logo" src="{bihar_logo_uri}" alt="Bihar Government emblem">' if bihar_logo_uri else ''
    cm_html = f'<img src="{cm_uri}" alt="Shri Samrat Choudhary">' if cm_uri else ''
    minister_html = f'<img src="{minister_uri}" alt="Shri Ashok Chaudhary">' if minister_uri else ''
    st.markdown(f"""
    <div class="gov-hero">
      {logo_html}
      <div class="gov-name-hi">बिहार सरकार</div>
      <div class="gov-name-en">GOVERNMENT OF BIHAR</div>
      <div class="gov-name-hi" style="font-size:1.35rem;margin-top:8px;">खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
      <div class="gov-name-en">FOOD &amp; CONSUMER PROTECTION DEPARTMENT</div>
      <div class="bihar-quote">“बढ़ता बिहार, बदलता बिहार”</div>
      <div class="bihar-quote-sub">नागरिक सहायता एवं आवेदन प्रणाली</div>
      <div class="profile-row">
        <div class="profile-card">{cm_html}<div class="profile-name">श्री सम्राट चौधरी</div><div class="profile-role">माननीय मुख्यमंत्री, बिहार</div></div>
        <div class="profile-card">{minister_html}<div class="profile-name">श्री अशोक चौधरी</div><div class="profile-role">माननीय मंत्री, खाद्य एवं उपभोक्ता संरक्षण विभाग</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
elif st.session_state.stage != "login":
    logo_html = f'<img class="gov-logo" style="width:52px;height:52px;" src="{bihar_logo_uri}" alt="Bihar Government emblem">' if bihar_logo_uri else ''
    st.markdown(f"""<div style='text-align:center;margin:4px 0 12px;'>{logo_html}<div style='font-weight:800;font-size:1.35rem;color:#123b73;'>खाद्य एवं उपभोक्ता संरक्षण विभाग</div><div style='font-weight:700;color:#555;'>बिहार सरकार</div></div>""", unsafe_allow_html=True)

# Language switch is available throughout the authenticated application.
if st.session_state.stage != "login":
    c1,c2=st.columns([5,1])
    with c1:
        st.caption(L("title"))
    with c2:
        if st.button("English" if st.session_state.lang=="hi" else "हिन्दी"):
            st.session_state.lang="en" if st.session_state.lang=="hi" else "hi"
            st.rerun()

if st.session_state.stage=="dashboard":
    st.markdown(f'<div class="confirm"><b>नमस्कार / Namaskar</b><br>{welcome_message()}</div>', unsafe_allow_html=True)
    if not st.session_state.get("welcome_autoplay_done", False):
        play_welcome_audio()
        st.session_state.welcome_autoplay_done = True
    if st.button("🔊 परिचय फिर से सुनें / Hear introduction again"):
        play_welcome_audio()
    st.markdown(f'<div class="big-help">{L("intro")}</div>',unsafe_allow_html=True)
    st.markdown('<div class="warn">⚠️ Public prototype: use dummy data while testing. Do not enter real Aadhaar or other sensitive personal data.</div>', unsafe_allow_html=True)
    a,b=st.columns(2)
    with a:
        if st.button(L("speak")):
            st.session_state.stage="voice_problem"
            st.rerun()
        if st.button(L("guided")):
            st.session_state.flow="consumer_complaint"
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0
            st.session_state.answers={"mobile": st.session_state.get("registered_mobile", "")}
            st.session_state.stage="question"
            st.rerun()
    with b:
        if st.button(L("type")):
            st.session_state.stage="type_problem"
            st.rerun()
        if st.button(L("write")):
            st.session_state.stage="type_problem"
            st.rerun()
    if st.session_state.get("application_id"):
        if st.button("🔎 आवेदन की स्थिति देखें / Track application", use_container_width=True):
            st.session_state.stage="status"
            st.rerun()

    st.subheader("उदाहरण / Examples")
    st.write("“मुझे इस महीने राशन नहीं मिला।”")
    st.write("“मुझे कम चावल मिला।”")
    st.write("“मुझे नया राशन कार्ड बनवाना है।”")
    st.write("“दुकानदार ने ज्यादा पैसे लिए।”")


    st.markdown("<div class='dashboard-welcome'><b>नमस्कार! 🙏 आपका स्वागत है।</b><br>अपनी समस्या बोलकर या लिखकर बताएं। हम चरण-दर-चरण आपकी सहायता करेंगे।</div>", unsafe_allow_html=True)
    if st.button("🔐 लॉगआउट / Logout", use_container_width=True):
        st.session_state.logged_in=False
        st.session_state.stage="login"
        st.rerun()

elif st.session_state.stage=="status":
    st.header("🔎 आवेदन की स्थिति / Application Status")
    app_id = st.session_state.get("application_id")
    app_dt = st.session_state.get("application_datetime")
    if app_id:
        st.markdown(f"<div class='confirm' style='text-align:center'><div style='font-size:.9rem;color:#667085'>अनुरोध क्रमांक</div><div style='font-size:2rem;font-weight:900;letter-spacing:2px;color:#123b73'>{escape(app_id)}</div><div>दिनांक: {escape(str(app_dt).split(' ')[0])} | समय: {escape(str(app_dt).split(' ')[1])} IST</div></div>", unsafe_allow_html=True)
        st.progress(0.65)
        st.markdown("""### 🟢 आवेदन प्राप्त
आपका अनुरोध प्रणाली में दर्ज है।

### 🔵 जांचाधीन
संबंधित टीम द्वारा मामले की जांच की जा रही है।

### ⚪ निस्तारण
अंतिम कार्रवाई के बाद स्थिति यहां अपडेट की जाएगी।""")
    else:
        st.info("अभी कोई आवेदन उपलब्ध नहीं है।")
    if st.button("← डैशबोर्ड पर वापस / Back to dashboard", use_container_width=True):
        st.session_state.stage="dashboard"
        st.rerun()

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
            st.session_state.answers={"mobile": st.session_state.get("registered_mobile", "")}
            st.session_state.stage="question"
            st.rerun()

    if st.button(L("back")):
        st.session_state.stage="dashboard"
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
            st.session_state.answers={"mobile": st.session_state.get("registered_mobile", "")}
            st.session_state.stage="question"
            st.rerun()
        else:
            st.warning("कृपया समस्या बताएं। / Please tell us the problem.")

    if st.button(L("back")):
        st.session_state.stage="dashboard"
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
                st.session_state.stage="dashboard"
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
    app_id, app_dt = ensure_application_metadata()
    sms_status, sms_detail = notify_registered_mobile()

    st.header("📄 औपचारिक आवेदन / Formal Application")
    st.success("आपका सरकारी कार्यालय शैली में आवेदन तैयार है। / Your formal application is ready.")

    st.markdown(f"""
    <div class="confirm" style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#174a8b;">अनुरोध क्रमांक / Request ID</div>
      <div style="font-size:1.55rem;font-weight:900;letter-spacing:.5px;">{app_id}</div>
      <div style="margin-top:8px;"><b>दिनांक:</b> {app_dt.split(' ')[0]}<br><b>समय:</b> {app_dt.split(' ')[1]} (IST)</div>
    </div>
    """, unsafe_allow_html=True)

    if sms_status == "sent" and sms_detail == "DEMO_SMS_NOT_SENT":
        st.info("📱 डेमो मोड: SMS gateway अभी जोड़ा नहीं गया है। नीचे वही संदेश दिखाया गया है जो वास्तविक SMS में जाएगा।")
        st.markdown(f"<div class='confirm'><b>SMS संदेश / SMS message</b><br>{escape(application_sms_text(app_id))}</div>", unsafe_allow_html=True)
    elif sms_status == "sent":
        st.success("📱 आपके पंजीकृत मोबाइल नंबर पर अनुरोध क्रमांक की सूचना भेज दी गई है।")
    elif sms_status == "not_sent":
        st.warning("📱 SMS अभी नहीं भेजा जा सका। कृपया SMS सेवा की सेटिंग जांचें।")
        if st.button("📱 SMS दोबारा भेजें / Resend SMS"):
            st.session_state.sms_status = None
            st.session_state.sms_detail = ""
            st.rerun()

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
        mobile = st.session_state.get("registered_mobile", "")
        lang = st.session_state.get("lang", "hi")
        st.session_state.clear()
        st.session_state.lang = lang
        st.session_state.registered_mobile = mobile
        st.session_state.answers = {"mobile": mobile}
        st.session_state.stage = "dashboard"
        st.rerun()


# Persistent footer for all authenticated screens
if st.session_state.get("stage") not in {"login"}:
    st.markdown("<div class='footer-bar'>सरकार आपके द्वार<div class='footer-sub'>जनसेवक बिहार • नागरिक सहायता एवं सेवा प्रणाली</div></div>", unsafe_allow_html=True)
