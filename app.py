import base64
import html
import hashlib
import io
import random
import re
from datetime import datetime

import streamlit as st
import speech_recognition as sr
from gtts import gTTS
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ============================================================
# JANSEVAK BIHAR
# Citizen Assistance & Service Facilitation System
# ============================================================

st.set_page_config(
    page_title="जनसेवक बिहार — नागरिक सहायता एवं सेवा प्रणाली",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = __file__.rsplit("/", 1)[0]


def asset_path(name):
    return f"{BASE}/{name}"


def img_data(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


def svg_data(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def safe(value):
    return html.escape(str(value or ""))


# ------------------------------------------------------------
# Assets
# ------------------------------------------------------------
LOGO = img_data(asset_path("bihar_gov_logo.png"))
CM = img_data(asset_path("cm_samrat.png"))
MINISTER = img_data(asset_path("minister_ashok.png"))
HERO_DESKTOP = img_data(asset_path("jansevak_hero.jpg"))
HERO_MOBILE = img_data(asset_path("jansevak_hero.jpg"))
MAN = svg_data(asset_path("bihari_man.svg"))
WOMAN = svg_data(asset_path("bihari_woman.svg"))


# ------------------------------------------------------------
# Devanagari PDF fonts
# ------------------------------------------------------------
FONT_REG = asset_path("fonts/NotoSansDevanagari-Regular.ttf")
FONT_BOLD = asset_path("fonts/NotoSansDevanagari-Bold.ttf")

try:
    pdfmetrics.registerFont(TTFont("NotoDeva", FONT_REG))
    pdfmetrics.registerFont(TTFont("NotoDevaBold", FONT_BOLD))
    PDF_FONT = "NotoDeva"
    PDF_BOLD = "NotoDevaBold"
except Exception:
    PDF_FONT = "Helvetica"
    PDF_BOLD = "Helvetica-Bold"


# ------------------------------------------------------------
# CSS — responsive desktop + mobile
# ------------------------------------------------------------
st.markdown(
    """
<style>
:root{
    --blue:#0d4f9e;
    --blue2:#1764bd;
    --navy:#113a70;
    --gold:#e4ad22;
    --green:#258b45;
    --orange:#f28b16;
    --purple:#6d2dd6;
    --red:#d83a4b;
    --ink:#17345f;
    --muted:#667085;
    --line:#dce4ef;
    --soft:#f5f8fc;
}

html, body, [class*="css"] {
    font-family: "Noto Sans Devanagari", "Noto Sans", Arial, sans-serif;
}

.block-container{
    max-width: 1280px !important;
    padding: 0.55rem 0.8rem 2rem !important;
}

#MainMenu, footer {visibility:hidden;}
header[data-testid="stHeader"] {background:transparent;}
[data-testid="stToolbar"] {display:none;}

.gov-header{
    width:100%;
    display:grid;
    grid-template-columns:minmax(0,1fr) auto;
    align-items:center;
    gap:18px;
    padding:12px 16px;
    background:#fff;
    border:1px solid #e2e8f0;
    border-radius:18px;
    box-shadow:0 5px 18px rgba(17,58,112,.08);
}

.gov-identity{
    display:flex;
    align-items:center;
    gap:14px;
    min-width:0;
}

.gov-logo{
    width:82px;
    height:82px;
    object-fit:contain;
    flex:0 0 82px;
}

.gov-hi{
    color:#153c73;
    font-size:30px;
    font-weight:800;
    line-height:1.15;
    white-space:nowrap;
}

.gov-dept{
    color:#153c73;
    font-size:21px;
    font-weight:700;
    line-height:1.3;
    margin-top:3px;
}

.gov-en{
    color:#697386;
    font-size:15px;
    letter-spacing:.25px;
    margin-top:2px;
}

.leader-area{
    display:flex;
    align-items:stretch;
    gap:10px;
}

.leader-card{
    width:235px;
    min-height:88px;
    display:flex;
    align-items:center;
    gap:10px;
    padding:8px 10px;
    background:#fbfcfe;
    border:1px solid #dbe4ef;
    border-radius:17px;
    box-sizing:border-box;
}

.leader-photo{
    width:64px;
    height:64px;
    object-fit:cover;
    object-position:center top;
    border-radius:12px;
    border:2px solid #e8edf5;
    background:#fff;
    flex:0 0 64px;
}

.leader-name{
    color:#153c73;
    font-size:16px;
    font-weight:800;
    line-height:1.2;
}

.leader-role{
    color:#687386;
    font-size:12.5px;
    line-height:1.25;
    margin-top:4px;
}

.hero-shell{
    margin-top:12px;
    width:100%;
    overflow:hidden;
    border-radius:18px;
    border:1px solid #dce5ef;
    box-shadow:0 7px 20px rgba(17,58,112,.10);
    background:#fff;
}

.hero-img-desktop{
    display:block;
    width:100%;
    height:auto;
    object-fit:contain;
}

.hero-img-mobile{display:none;}

.login-card{
    width:min(690px, 100%);
    margin: 14px auto 0;
    position:relative;
    z-index:5;
    background:rgba(255,255,255,.98);
    border:1px solid #d8e2ef;
    border-radius:25px;
    box-shadow:0 14px 38px rgba(17,58,112,.18);
    padding:22px 25px 24px;
}

.welcome-title{
    text-align:center;
    color:#103f7b;
    font-size:30px;
    font-weight:800;
    line-height:1.25;
    margin:0 0 5px;
}

.welcome-text{
    text-align:center;
    color:#42526a;
    font-size:16px;
    line-height:1.55;
    max-width:590px;
    margin:0 auto 16px;
}

.login-tabs{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:4px;
    padding:5px;
    background:#f0f3f8;
    border-radius:17px;
    margin-bottom:15px;
}

.tab-active{
    background:#0d5aa8;
    color:#fff;
    text-align:center;
    border-radius:13px;
    padding:12px 8px;
    font-weight:800;
    font-size:17px;
}

.tab-inactive{
    color:#46546a;
    text-align:center;
    border-radius:13px;
    padding:12px 8px;
    font-weight:700;
    font-size:17px;
}

.service-grid{
    width:min(1050px,100%);
    margin:22px auto 0;
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
}

.service-item{
    background:#fff;
    border:1px solid #dce5ef;
    border-radius:16px;
    min-height:72px;
    display:flex;
    align-items:center;
    gap:11px;
    padding:10px 13px;
    box-shadow:0 4px 12px rgba(17,58,112,.06);
}

.service-icon{
    width:44px;
    height:44px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#fff;
    font-size:21px;
    flex:0 0 44px;
}

.service-text{
    color:#173f78;
    font-weight:800;
    font-size:15px;
    line-height:1.25;
}

.blue{background:#1670d2;}
.green{background:#2b9b49;}
.orange{background:#f28b16;}
.purple{background:#6b31d4;}
.red{background:#d94157;}
.teal{background:#1a9e9b;}

.gov-footer{
    margin-top:28px;
    border-radius:18px;
    overflow:hidden;
    background:linear-gradient(180deg,#0b4d91,#063c76);
    color:#fff;
    padding:20px 18px 16px;
    text-align:center;
    border-top:5px solid #e9b92b;
}

.footer-title{
    font-size:27px;
    font-weight:800;
    margin-bottom:3px;
}

.footer-sub{
    font-size:13px;
    opacity:.9;
}

.stButton>button{
    min-height:48px !important;
    border-radius:13px !important;
    font-weight:800 !important;
    border:1px solid #d9e2ed !important;
}

.primary-action button{
    background:#0d5aa8 !important;
    color:#fff !important;
    border:none !important;
}

.small-note{
    text-align:center;
    color:#748094;
    font-size:12px;
    margin-top:9px;
}

.demo-box{
    background:#fff8e8;
    border:1px solid #efd18a;
    color:#6f5200;
    border-radius:12px;
    padding:9px 12px;
    font-size:12px;
    margin-top:9px;
}

.confirm{
    background:#f2f7ff;
    border:1px solid #a9c8ee;
    border-radius:14px;
    padding:15px;
    margin:10px 0;
}

.voice-answer{
    background:#eef9f0;
    border:1px solid #a5d1aa;
    border-radius:14px;
    padding:14px;
    margin:8px 0;
}

.application-paper{
    background:#fff;
    border:1px solid #dce3ec;
    border-radius:16px;
    padding:22px;
    box-shadow:0 8px 25px rgba(17,58,112,.08);
}

@media (max-width: 900px){
    .block-container{
        padding:0.35rem 0.45rem 1.4rem !important;
    }

    .gov-header{
        grid-template-columns:1fr;
        gap:10px;
        padding:10px;
        border-radius:15px;
    }

    .gov-identity{
        align-items:center;
        justify-content:flex-start;
    }

    .gov-logo{
        width:68px;
        height:68px;
        flex-basis:68px;
    }

    .gov-hi{font-size:23px;}
    .gov-dept{font-size:16px;}
    .gov-en{font-size:11px;}

    .leader-area{
        width:100%;
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:7px;
    }

    .leader-card{
        width:100%;
        min-height:78px;
        padding:6px 7px;
        border-radius:14px;
        gap:7px;
    }

    .leader-photo{
        width:55px;
        height:55px;
        flex-basis:55px;
        border-radius:10px;
    }

    .leader-name{font-size:13px;}
    .leader-role{font-size:10px;}

    .hero-shell{
        margin-top:8px;
        border-radius:13px;
        box-shadow:0 5px 16px rgba(17,58,112,.10);
    }

    .hero-img-desktop{display:none;}
    .hero-img-mobile{
        display:block;
        width:100%;
        height:auto;
    }

    .login-card{
        margin:12px auto 0;
        width:100%;
        padding:17px 12px 18px;
        border-radius:22px;
    }

    .welcome-title{font-size:25px;}
    .welcome-text{font-size:14px;line-height:1.5;margin-bottom:12px;}

    .tab-active,.tab-inactive{
        font-size:14px;
        padding:11px 5px;
    }

    .service-grid{
        grid-template-columns:1fr 1fr;
        gap:8px;
        margin-top:16px;
    }

    .service-item{
        min-height:64px;
        padding:8px 8px;
        gap:7px;
        border-radius:13px;
    }

    .service-icon{
        width:36px;
        height:36px;
        flex-basis:36px;
        font-size:17px;
    }

    .service-text{font-size:12px;}
    .footer-title{font-size:22px;}
}

@media (max-width: 430px){
    .gov-identity{gap:9px;}
    .gov-logo{width:58px;height:58px;flex-basis:58px;}
    .gov-hi{font-size:20px;}
    .gov-dept{font-size:14px;}
    .gov-en{font-size:9.5px;}

    .leader-card{min-height:72px;}
    .leader-photo{width:48px;height:48px;flex-basis:48px;}
    .leader-name{font-size:11.5px;}
    .leader-role{font-size:8.8px;}

    .login-card{
        padding:15px 9px 16px;
        border-radius:20px;
    }

    .welcome-title{font-size:23px;}
    .welcome-text{font-size:13px;}

    .service-text{font-size:11px;}
}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Text and flows
# ------------------------------------------------------------
TEXT = {
    "hi": {
        "dept": "खाद्य एवं उपभोक्ता संरक्षण विभाग",
        "title": "नागरिक सहायता एवं सेवा प्रणाली",
        "welcome": "नमस्कार! 🙏",
        "welcome_text": "बिहार सरकार के खाद्य एवं उपभोक्ता संरक्षण विभाग की नागरिक सहायता प्रणाली में आपका स्वागत है।",
        "citizen": "👤 नागरिक लॉगिन",
        "officer": "♙ अधिकारी लॉगिन",
        "mobile": "📱 मोबाइल नंबर दर्ज करें / Registered mobile number",
        "mobile_placeholder": "10 अंकों का मोबाइल नंबर",
        "send_otp": "✉️ OTP भेजें",
        "otp": "🔐 OTP दर्ज करें",
        "otp_placeholder": "6 अंकों का OTP",
        "login": "लॉगिन करें  →",
        "new_card": "नया राशन कार्ड",
        "less": "राशन कम मिला",
        "not_received": "राशन प्राप्त नहीं हुआ",
        "correction": "कार्ड सुधार / सदस्य जोड़ें",
        "food_complaint": "खाद्य शिकायत",
        "consumer": "उपभोक्ता शिकायत",
        "info": "जानकारी प्राप्त करें",
        "status": "आवेदन की स्थिति देखें",
        "speak": "🎤 बोलकर बताएं",
        "type": "⌨️ टाइप करके बताएं",
        "guided": "👆 मुझसे सवाल पूछें",
        "write": "📝 मेरे लिए आवेदन लिखें",
        "confirm": "सही है, आगे बढ़ें",
        "back": "← वापस",
        "new": "नया आवेदन",
        "download": "📄 PDF डाउनलोड करें",
    },
    "en": {
        "dept": "Food & Consumer Protection Department",
        "title": "Citizen Assistance & Service Facilitation System",
        "welcome": "Namaskar! 🙏",
        "welcome_text": "Welcome to the Bihar Government Food & Consumer Protection Department Citizen Assistance System.",
        "citizen": "👤 Citizen Login",
        "officer": "♙ Officer Login",
        "mobile": "📱 Registered mobile number",
        "mobile_placeholder": "10-digit mobile number",
        "send_otp": "✉️ Send OTP",
        "otp": "🔐 Enter OTP",
        "otp_placeholder": "6-digit OTP",
        "login": "Login  →",
        "new_card": "New Ration Card",
        "less": "Less Ration",
        "not_received": "Ration Not Received",
        "correction": "Card Correction / Add Member",
        "food_complaint": "Food Complaint",
        "consumer": "Consumer Complaint",
        "info": "Get Information",
        "status": "Check Application Status",
        "speak": "🎤 Speak",
        "type": "⌨️ Type",
        "guided": "👆 Ask me questions",
        "write": "📝 Write an application",
        "confirm": "Confirm & Continue",
        "back": "← Back",
        "new": "New application",
        "download": "📄 Download PDF",
    },
}


def L(k):
    return TEXT[st.session_state.lang][k]


COMMON = [
    ("name", "पूरा नाम", "Full name", "text"),
    ("father", "पिता / पति का नाम", "Father / Husband name", "text"),
    ("mobile", "मोबाइल नंबर", "Mobile number", "mobile"),
    ("address", "पूरा पता", "Complete address", "text"),
]

FLOWS = {
    "ration_card": {
        "hi": "नया राशन कार्ड आवेदन",
        "en": "New Ration Card Application",
        "keywords": ["राशन कार्ड", "नया राशन", "ration card", "new ration"],
        "questions": [
            ("family", "परिवार में कितने सदस्य हैं?", "How many members are in your family?", "number"),
            ("aadhaar", "आधार नंबर बताएं।", "Please provide your Aadhaar number.", "aadhaar"),
            ("reason", "नया राशन कार्ड क्यों बनवाना चाहते हैं?", "Why do you want a new ration card?", "text"),
        ],
    },
    "ration_not_received": {
        "hi": "राशन नहीं मिलने की शिकायत",
        "en": "Complaint: Ration Not Received",
        "keywords": ["राशन नहीं मिला", "राशन नही मिला", "अनाज नहीं मिला", "pds", "ration not received"],
        "questions": [
            ("ration_no", "राशन कार्ड नंबर बताएं।", "Please tell me your ration card number.", "text"),
            ("month", "किस महीने का राशन नहीं मिला?", "For which month did you not receive ration?", "text"),
            ("dealer", "उचित मूल्य दुकान / दुकानदार का नाम बताएं।", "Tell me the fair price shop / dealer name.", "text"),
        ],
    },
    "less_ration": {
        "hi": "कम राशन मिलने की शिकायत",
        "en": "Complaint: Less Ration Received",
        "keywords": ["कम राशन", "कम अनाज", "कम गेहूं", "कम चावल", "less ration", "less grain"],
        "questions": [
            ("ration_no", "राशन कार्ड नंबर बताएं।", "Please tell me your ration card number.", "text"),
            ("expected", "आपको कितना राशन मिलना चाहिए था?", "How much ration should you have received?", "text"),
            ("received", "आपको वास्तव में कितना राशन मिला?", "How much ration did you actually receive?", "text"),
            ("dealer", "दुकानदार का नाम बताएं।", "Tell me the dealer's name.", "text"),
        ],
    },
    "ration_correction": {
        "hi": "राशन कार्ड सुधार / समस्या",
        "en": "Ration Card Correction / Problem",
        "keywords": ["राशन कार्ड में समस्या", "राशन कार्ड सुधार", "राशन कार्ड गलत", "correction", "ration card problem"],
        "questions": [
            ("ration_no", "राशन कार्ड नंबर बताएं।", "Please tell me your ration card number.", "text"),
            ("problem", "राशन कार्ड में क्या समस्या है?", "What is the problem with the ration card?", "text"),
        ],
    },
    "consumer_complaint": {
        "hi": "उपभोक्ता / खाद्य संबंधी शिकायत",
        "en": "Consumer / Food Related Complaint",
        "keywords": ["शिकायत", "मिलावट", "मिलावटी", "ज्यादा पैसे", "overcharging", "consumer complaint", "adulteration"],
        "questions": [
            ("shop", "दुकान / प्रतिष्ठान का नाम बताएं।", "Tell me the shop / establishment name.", "text"),
            ("problem", "समस्या विस्तार से बताएं।", "Explain the problem.", "text"),
        ],
    },
}


def detect_flow(text):
    s = (text or "").lower()
    for key, f in FLOWS.items():
        if any(k.lower() in s for k in f["keywords"]):
            return key
    return "consumer_complaint"


def title(flow):
    return FLOWS[flow]["hi"] if st.session_state.lang == "hi" else FLOWS[flow]["en"]


def questions(flow):
    return COMMON + FLOWS[flow]["questions"]


def transcribe(audio):
    if audio is None:
        return ""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio.getvalue())) as source:
            data = recognizer.record(source)
        return recognizer.recognize_google(
            data,
            language="hi-IN" if st.session_state.lang == "hi" else "en-IN",
        )
    except Exception:
        return ""


def speak(text):
    try:
        b = io.BytesIO()
        gTTS(
            text=text,
            lang="hi" if st.session_state.lang == "hi" else "en",
        ).write_to_fp(b)
        b.seek(0)
        st.audio(b, format="audio/mp3")
    except Exception:
        pass


def make_request_id():
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return random.choice(letters) + random.choice(letters) + f"{random.randint(0,9999):04d}"


def formal_subject(flow):
    subjects = {
        "ration_card": "नया राशन कार्ड निर्गत किए जाने के संबंध में।",
        "ration_not_received": "राशन प्राप्त नहीं होने के संबंध में शिकायत।",
        "less_ration": "निर्धारित मात्रा से कम राशन प्राप्त होने के संबंध में शिकायत।",
        "ration_correction": "राशन कार्ड में सुधार / संशोधन के संबंध में।",
        "consumer_complaint": "खाद्य / उपभोक्ता संबंधी शिकायत के संबंध में।",
    }
    return subjects.get(flow, "शिकायत के संबंध में।")


def make_sms(request_id):
    return (
        f"आपका अनुरोध क्रमांक {request_id} है। आपकी समस्या के समाधान हेतु हमारी टीम "
        "इस पर कार्य कर रही है और इसे यथाशीघ्र निस्तारित करने का प्रयास किया जा रहा है। "
        "- खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार"
    )


def pdf_file():
    b = io.BytesIO()
    doc = SimpleDocTemplate(
        b,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    head = ParagraphStyle(
        "GovHead",
        parent=styles["Title"],
        fontName=PDF_BOLD,
        fontSize=15,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#153c73"),
    )
    normal = ParagraphStyle(
        "GovNormal",
        parent=styles["BodyText"],
        fontName=PDF_FONT,
        fontSize=10.5,
        leading=17,
    )
    bold = ParagraphStyle(
        "GovBold",
        parent=normal,
        fontName=PDF_BOLD,
    )
    center = ParagraphStyle(
        "GovCenter",
        parent=normal,
        alignment=TA_CENTER,
    )

    s = st.session_state
    dt = datetime.now().strftime("%d-%m-%Y")
    tm = datetime.now().strftime("%H:%M:%S")

    story = [
        Paragraph("बिहार सरकार", head),
        Paragraph("खाद्य एवं उपभोक्ता संरक्षण विभाग", head),
        Spacer(1, 6),
        Paragraph("नागरिक सहायता एवं सेवा प्रणाली", center),
        Spacer(1, 15),
        Paragraph("<b>अनुरोध क्रमांक:</b> " + safe(s.request_id), normal),
        Paragraph("<b>दिनांक:</b> " + dt + "    <b>समय:</b> " + tm + " (IST)", normal),
        Spacer(1, 12),
        Paragraph("सेवा में,", normal),
        Paragraph("प्रखंड आपूर्ति पदाधिकारी / संबंधित सक्षम पदाधिकारी", normal),
        Paragraph("संबंधित प्रखंड/कार्यालय: ______________________________", normal),
        Spacer(1, 10),
        Paragraph("<b>विषय:</b> " + safe(formal_subject(s.flow)), normal),
        Spacer(1, 8),
        Paragraph("महोदय/महोदया,", normal),
    ]

    name = s.answers.get("name", "")
    family = s.answers.get("family", "")
    reason = s.answers.get("reason", "")
    problem = s.answers.get("problem", s.problem)

    body = (
        f"सविनय निवेदन है कि मैं {safe(name)} हूँ"
        + (f" एवं मेरे परिवार में कुल {safe(family)} सदस्य हैं।" if family else "।")
        + (f" {safe(reason)}" if reason else "")
        + (f" मेरी समस्या का विवरण: {safe(problem)}" if problem else "")
        + " अतः अनुरोध है कि उपलब्ध विवरण/संलग्न दस्तावेजों के आधार पर नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।"
    )
    story += [Paragraph(body, normal), Spacer(1, 12)]

    attachments = [
        "आधार कार्ड की छायाप्रति (जहाँ नियमानुसार आवश्यक हो)",
        "निवास प्रमाण पत्र की छायाप्रति",
        "राशन कार्ड की छायाप्रति, यदि उपलब्ध हो",
        "समस्या से संबंधित प्रमाण / रसीद / पर्ची, यदि उपलब्ध हो",
        "पासपोर्ट साइज फोटो, जहाँ आवश्यक हो",
    ]

    story.append(Paragraph("<b>संलग्नक:</b>", normal))
    for i, item in enumerate(attachments, 1):
        story.append(Paragraph(f"{i}. {safe(item)}", normal))

    story += [
        Spacer(1, 22),
        Paragraph("भवदीय,", normal),
        Spacer(1, 18),
        Paragraph("हस्ताक्षर / अंगूठे का निशान: __________________________", normal),
        Paragraph("नाम: " + safe(name), normal),
        Paragraph("मोबाइल नंबर: " + safe(s.answers.get("mobile", "")), normal),
        Paragraph("पता: " + safe(s.answers.get("address", "")), normal),
        Paragraph("स्थान: ____________________    दिनांक: " + dt, normal),
    ]

    doc.build(story)
    b.seek(0)
    return b


# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
defaults = {
    "lang": "hi",
    "stage": "home",
    "logged_in": False,
    "otp_sent": False,
    "demo_otp": "123456",
    "mobile_login": "",
    "flow": None,
    "questions": [],
    "q_index": 0,
    "answers": {},
    "problem": "",
    "voice_text": "",
    "voice_hash": "",
    "request_id": "",
    "pending": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
leader1 = f"""
<div class="leader-card">
  <img class="leader-photo" src="data:image/png;base64,{CM}">
  <div>
    <div class="leader-name">श्री सम्राट चौधरी</div>
    <div class="leader-role">माननीय मुख्यमंत्री, बिहार</div>
  </div>
</div>
"""

leader2 = f"""
<div class="leader-card">
  <img class="leader-photo" src="data:image/png;base64,{MINISTER}">
  <div>
    <div class="leader-name">श्री अशोक चौधरी</div>
    <div class="leader-role">माननीय मंत्री, खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
  </div>
</div>
"""

st.markdown(
    f"""
<div class="gov-header">
  <div class="gov-identity">
    <img class="gov-logo" src="data:image/png;base64,{LOGO}">
    <div>
      <div class="gov-hi">बिहार सरकार</div>
      <div class="gov-dept">खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
      <div class="gov-en">FOOD &amp; CONSUMER PROTECTION DEPARTMENT</div>
    </div>
  </div>
  <div class="leader-area">
    {leader1}
    {leader2}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Home / Login page
# ------------------------------------------------------------
if st.session_state.stage == "home":
    # Hero is intentionally separate from the login card.
    # This prevents the login panel from covering the faces or the
    # "बढ़ता बिहार, बदलता बिहार" message on mobile.
    # Use Streamlit's native image renderer for the hero.
    # This avoids mobile Safari/WebKit failing to render a large
    # base64 data-URI inside st.markdown, which can show a broken-image
    # icon even though the local JPG exists in the repository.
    st.image(asset_path("jansevak_hero.jpg"), width="stretch")

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="welcome-title">{L("welcome")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="welcome-text">{L("welcome_text")}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
<div class="login-tabs">
  <div class="tab-active">{L("citizen")}</div>
  <div class="tab-inactive">{L("officer")}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    mobile = st.text_input(
        L("mobile"),
        value=st.session_state.mobile_login,
        placeholder=L("mobile_placeholder"),
        max_chars=10,
        key="login_mobile_input",
    )
    st.session_state.mobile_login = mobile

    if not st.session_state.otp_sent:
        if st.button(L("send_otp"), type="primary", use_container_width=True):
            if not re.fullmatch(r"\d{10}", mobile.strip()):
                st.error("कृपया 10 अंकों का मोबाइल नंबर दर्ज करें।")
            else:
                st.session_state.otp_sent = True
                st.session_state.demo_otp = "123456"
                st.rerun()
    else:
        otp = st.text_input(
            L("otp"),
            placeholder=L("otp_placeholder"),
            max_chars=6,
            type="password",
            key="login_otp_input",
        )

        st.markdown(
            '<div class="demo-box">Demo mode: परीक्षण के लिए OTP <b>123456</b> है। '
            'Production में SMS gateway / DLT template जोड़ा जा सकता है.</div>',
            unsafe_allow_html=True,
        )

        if st.button(L("login"), type="primary", use_container_width=True):
            if otp.strip() != st.session_state.demo_otp:
                st.error("OTP सही नहीं है। Demo OTP: 123456")
            else:
                st.session_state.logged_in = True
                st.session_state.stage = "dashboard"
                st.rerun()

    st.markdown(
        '<div class="small-note">सुरक्षित डेमो • वास्तविक आधार/संवेदनशील जानकारी परीक्षण में दर्ज न करें।</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Services are deliberately below the login card.
    services = [
        ("green", "🧾", L("new_card"), "ration_card"),
        ("orange", "📦", L("less"), "less_ration"),
        ("blue", "🛒", L("not_received"), "ration_not_received"),
        ("purple", "🪪", L("correction"), "ration_correction"),
    ]

    cols = st.columns(4)
    for col, (color, icon, label, flow_key) in zip(cols, services):
        with col:
            st.markdown(
                f"""
<div class="service-item">
  <div class="service-icon {color}">{icon}</div>
  <div class="service-text">{safe(label)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown(
        """
<div class="gov-footer">
  <div class="footer-title">सरकार आपके द्वार</div>
  <div class="footer-sub">सुगम सेवा • सशक्त नागरिक • समृद्ध बिहार</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Dashboard after login
# ------------------------------------------------------------
elif st.session_state.stage == "dashboard":
    st.markdown(f"## {L('welcome')}")
    st.write("कृपया नीचे अपनी सेवा चुनें / Please choose a service.")

    service_buttons = [
        ("🟢", L("new_card"), "ration_card"),
        ("🟠", L("less"), "less_ration"),
        ("🔵", L("not_received"), "ration_not_received"),
        ("🟣", L("correction"), "ration_correction"),
        ("🔴", L("food_complaint"), "consumer_complaint"),
        ("🟦", L("consumer"), "consumer_complaint"),
    ]

    cols = st.columns(3)
    for i, (icon, label, flow_key) in enumerate(service_buttons):
        with cols[i % 3]:
            if st.button(f"{icon} {label}", use_container_width=True):
                st.session_state.flow = flow_key
                st.session_state.questions = questions(flow_key)
                st.session_state.q_index = 0
                st.session_state.answers = {}
                st.session_state.problem = ""
                st.session_state.stage = "question"
                st.rerun()

    a, b = st.columns(2)
    with a:
        if st.button(L("speak"), use_container_width=True):
            st.session_state.stage = "voice_problem"
            st.rerun()
    with b:
        if st.button(L("type"), use_container_width=True):
            st.session_state.stage = "type_problem"
            st.rerun()

    if st.button(L("new"), use_container_width=True):
        st.session_state.stage = "home"
        st.session_state.logged_in = False
        st.session_state.otp_sent = False
        st.rerun()


# ------------------------------------------------------------
# Voice problem
# ------------------------------------------------------------
elif st.session_state.stage == "voice_problem":
    st.header(L("speak"))

    audio = st.audio_input(
        "🎤 माइक्रोफोन दबाकर बोलें / Press microphone and speak",
        sample_rate=16000,
    )

    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if h != st.session_state.voice_hash:
            st.session_state.voice_hash = h
            st.session_state.voice_text = transcribe(audio)

    if st.session_state.voice_text:
        st.markdown(
            f'<div class="confirm"><b>आपने कहा / You said:</b><br>{safe(st.session_state.voice_text)}</div>',
            unsafe_allow_html=True,
        )

        if st.button("🔊 सुनें / Hear"):
            speak(st.session_state.voice_text)

        if st.button(L("confirm"), type="primary"):
            st.session_state.problem = st.session_state.voice_text
            st.session_state.flow = detect_flow(st.session_state.problem)
            st.session_state.questions = questions(st.session_state.flow)
            st.session_state.q_index = 0
            st.session_state.answers = {}
            st.session_state.stage = "question"
            st.rerun()

    if st.button(L("back")):
        st.session_state.stage = "dashboard"
        st.rerun()


# ------------------------------------------------------------
# Typed problem
# ------------------------------------------------------------
elif st.session_state.stage == "type_problem":
    st.header(L("write"))

    problem = st.text_area(
        "अपनी समस्या बताएं / Tell us your problem",
        value=st.session_state.problem,
        height=130,
    )

    audio = st.audio_input(
        "🎤 या बोलें / Or speak",
        sample_rate=16000,
    )

    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if h != st.session_state.voice_hash:
            st.session_state.voice_hash = h
            t = transcribe(audio)
            if t:
                problem = t

    if st.button("आगे बढ़ें / Continue", type="primary", use_container_width=True):
        if problem.strip():
            st.session_state.problem = problem.strip()
            st.session_state.flow = detect_flow(problem)
            st.session_state.questions = questions(st.session_state.flow)
            st.session_state.q_index = 0
            st.session_state.answers = {}
            st.session_state.stage = "question"
            st.rerun()
        else:
            st.warning("कृपया समस्या बताएं। / Please tell us the problem.")

    if st.button(L("back")):
        st.session_state.stage = "dashboard"
        st.rerun()


# ------------------------------------------------------------
# Guided question
# ------------------------------------------------------------
elif st.session_state.stage == "question":
    q = st.session_state.questions[st.session_state.q_index]
    key, hi, en, typ = q
    qtext = hi if st.session_state.lang == "hi" else en

    total = len(st.session_state.questions)
    current_step = st.session_state.q_index + 1
    st.progress(current_step / max(total, 1))
    st.caption(f"Step {current_step} / {total}")
    st.header(qtext)

    if st.button("🔊 सवाल सुनें / Hear question"):
        speak(qtext)

    current = st.session_state.answers.get(key, "")

    if typ == "number":
        answer = str(
            st.number_input(
                "उत्तर / Answer",
                min_value=1,
                max_value=100,
                value=int(current or 1),
                key=f"n_{key}_{st.session_state.q_index}",
            )
        )
    else:
        answer = st.text_input(
            "उत्तर / Answer",
            value=current,
            key=f"a_{key}_{st.session_state.q_index}",
        )

    audio = st.audio_input(
        "🎤 बोलकर उत्तर दें / Answer by voice",
        sample_rate=16000,
        key=f"audio_{key}_{st.session_state.q_index}",
    )

    voice_key = f"voice_{key}_{st.session_state.q_index}"
    hash_key = f"h_{key}_{st.session_state.q_index}"

    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if st.session_state.get(hash_key) != h:
            st.session_state[hash_key] = h
            t = transcribe(audio)
            if t:
                st.session_state[voice_key] = t

    voice = st.session_state.get(voice_key, "").strip()

    if voice:
        st.markdown(
            f'<div class="voice-answer"><b>🎤 आपने कहा / You said:</b><br>{safe(voice)}</div>',
            unsafe_allow_html=True,
        )
        a1, a2 = st.columns(2)
        with a1:
            if st.button("✅ हाँ, सही है / Yes, correct", type="primary"):
                st.session_state.answers[key] = voice
                st.session_state.pending = (key, voice, st.session_state.q_index)
                st.session_state.stage = "confirm"
                st.rerun()
        with a2:
            if st.button("🔄 दोबारा बोलें / Speak again"):
                st.session_state.pop(voice_key, None)
                st.session_state.pop(hash_key, None)
                st.rerun()

    a, b = st.columns(2)

    with a:
        if st.button(L("back")):
            if st.session_state.q_index == 0:
                st.session_state.stage = "dashboard"
            else:
                st.session_state.q_index -= 1
            st.rerun()

    with b:
        if st.button(L("confirm"), type="primary"):
            answer = str(answer).strip()
            valid = bool(answer)

            if not valid:
                st.warning("कृपया उत्तर दें। / Please provide an answer.")

            if typ == "mobile" and answer and not re.fullmatch(r"\d{10}", answer):
                st.error("10 अंकों का मोबाइल नंबर दें।")
                valid = False

            if typ == "aadhaar" and answer and not re.fullmatch(r"\d{12}", answer.replace(" ", "")):
                st.error("12 अंकों का आधार नंबर दें।")
                valid = False

            if valid:
                st.session_state.answers[key] = answer
                st.session_state.pending = (key, answer, st.session_state.q_index)
                st.session_state.stage = "confirm"
                st.rerun()


# ------------------------------------------------------------
# Per-answer confirmation
# ------------------------------------------------------------
elif st.session_state.stage == "confirm":
    key, answer, i = st.session_state.pending
    q = st.session_state.questions[i]
    qtext = q[1] if st.session_state.lang == "hi" else q[2]

    st.header("कृपया पुष्टि करें / Please confirm")
    st.write(f"**{qtext}**")
    st.markdown(
        f'<div class="confirm"><h3>{safe(answer)}</h3></div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2)

    with a:
        if st.button("✏️ बदलें / Change"):
            st.session_state.stage = "question"
            st.rerun()

    with b:
        if st.button("✅ हाँ, सही है / Yes, correct", type="primary"):
            st.session_state.q_index += 1
            st.session_state.stage = (
                "review"
                if st.session_state.q_index >= len(st.session_state.questions)
                else "question"
            )
            st.rerun()


# ------------------------------------------------------------
# Final review
# ------------------------------------------------------------
elif st.session_state.stage == "review":
    st.header("🔎 अंतिम जांच / Final review")
    st.subheader(title(st.session_state.flow))

    for q in st.session_state.questions:
        key, hi, en, typ = q
        label = hi if st.session_state.lang == "hi" else en
        st.write(f"**{label}:** {st.session_state.answers.get(key, '')}")

    if st.button("✏️ जानकारी बदलें / Edit"):
        st.session_state.q_index = 0
        st.session_state.stage = "question"
        st.rerun()

    if st.button(
        "✅ पुष्टि करें और आवेदन बनाएं / Generate application",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.request_id = make_request_id()
        st.session_state.stage = "application"
        st.rerun()


# ------------------------------------------------------------
# Application
# ------------------------------------------------------------
elif st.session_state.stage == "application":
    now = datetime.now()
    st.header("📄 " + title(st.session_state.flow))

    st.success("आपका आवेदन तैयार है। / Your application is ready.")

    st.markdown(
        f"""
<div class="application-paper">
<b>अनुरोध क्रमांक / Request ID:</b> {safe(st.session_state.request_id)}<br>
<b>दिनांक / Date:</b> {now.strftime("%d-%m-%Y")}<br>
<b>समय / Time:</b> {now.strftime("%H:%M:%S")} (IST)
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### SMS acknowledgement / SMS सूचना")
    st.info(make_sms(st.session_state.request_id))

    pdf = pdf_file()

    st.download_button(
        L("download"),
        data=pdf,
        file_name=f"Jansevak_Bihar_{st.session_state.request_id}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    if st.button("🖨️ आवेदन प्रिंट करें / Print Application", use_container_width=True):
        st.markdown(
            """
<script>
window.print();
</script>
""",
            unsafe_allow_html=True,
        )

    if st.button(L("new"), type="primary", use_container_width=True):
        st.session_state.clear()
        st.rerun()
