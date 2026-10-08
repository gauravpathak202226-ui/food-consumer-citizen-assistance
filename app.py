import base64
import html
import hashlib
import io
import random
import re
from urllib.parse import quote
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components
import speech_recognition as sr
from gtts import gTTS
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
# Keep the reference hero images embedded so Streamlit Cloud never fails because
# a JPG is missing from the GitHub deployment. The remaining header assets are
# loaded from the repository as before.
LOGO = img_data(asset_path("bihar_gov_logo.png"))
CM = img_data(asset_path("cm_samrat.png"))
MINISTER = img_data(asset_path("minister_ashok.png"))
FOOTER_REF = img_data(asset_path("footer_reference.jpg"))
MOBILE_HERO_FULL = img_data(asset_path("jansevak_ui_hero.jpg"))

# Clean reference hero images (no embedded login card).
# They are embedded so the deployed app does not depend on hero filenames being present.
HERO_UI = img_data(asset_path("jansevak_ui_hero.jpg"))
HERO_DESKTOP_BYTES = base64.b64decode(HERO_UI) if HERO_UI else b""


# Devanagari PDF fonts
# ------------------------------------------------------------
FONT_REG = asset_path("fonts/NotoSansDevanagari-Regular.ttf")
FONT_BOLD = asset_path("fonts/NotoSansDevanagari-Bold.ttf")

try:
    if not Path(FONT_REG).exists() or not Path(FONT_BOLD).exists():
        raise FileNotFoundError("Bundled Devanagari PDF fonts are missing")
    if not Path(FONT_REG).exists() or not Path(FONT_BOLD).exists():
        raise RuntimeError("Devanagari PDF fonts are missing from the deployment. Please upload the fonts folder.")
    pdfmetrics.registerFont(TTFont("NotoDeva", FONT_REG))
    pdfmetrics.registerFont(TTFont("NotoDevaBold", FONT_BOLD))
    pdfmetrics.registerFontFamily("NotoDeva", normal="NotoDeva", bold="NotoDevaBold", italic="NotoDeva", boldItalic="NotoDevaBold")
    pdfmetrics.registerFont(TTFont("LatinSans", asset_path("fonts/DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("LatinSansBold", asset_path("fonts/DejaVuSans-Bold.ttf")))
    PDF_FONT = "NotoDeva"
    PDF_BOLD = "NotoDevaBold"
except Exception:
    PDF_FONT = "Helvetica"
    PDF_BOLD = "Helvetica-Bold"
    try:
        pdfmetrics.registerFont(TTFont("LatinSans", asset_path("fonts/DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("LatinSansBold", asset_path("fonts/DejaVuSans-Bold.ttf")))
    except Exception:
        pass


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

.application-preview{
    background:#fff;
    border:1px solid #d5dce7;
    border-radius:14px;
    padding:34px 34px 40px;
    margin:18px 0 22px;
    box-shadow:0 10px 28px rgba(17,58,112,.09);
    color:#202733;
    font-family:"Noto Sans Devanagari", "Noto Sans", Arial, sans-serif;
    line-height:1.72;
}
.application-preview .gov-doc-head{
    text-align:center;
    color:#153c73;
    border-top:4px solid #153c73;
    padding-top:10px;
    margin-bottom:18px;
}
.application-preview .gov-doc-head .h1{font-size:25px;font-weight:800;line-height:1.25}
.application-preview .gov-doc-head .h2{font-size:20px;font-weight:700;line-height:1.3}
.application-preview .gov-doc-head .h3{font-size:16px;font-weight:700;line-height:1.3}
.application-preview .doc-meta{
    background:#f8fafc;border:1px solid #d3dce8;border-radius:12px;padding:14px 16px;margin-bottom:22px;
}
.application-preview .doc-meta-row{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.application-preview .doc-subject{font-weight:800;margin:18px 0 14px}
.application-preview .doc-attach{margin-top:18px}
.application-preview .doc-sign{text-align:right;margin-top:30px;line-height:1.9}
.application-preview .doc-footer{border-top:3px solid #c09527;margin-top:28px;padding-top:8px;text-align:center;color:#153c73;font-size:13px}
.application-preview-image{width:min(100%, 820px);margin:18px auto 22px;background:#fff;border:1px solid #d5dce7;border-radius:14px;box-shadow:0 10px 28px rgba(17,58,112,.09);overflow:hidden}
.application-preview-image img{display:block;width:100%;height:auto}
.application-actions{margin-top:4px;margin-bottom:22px}
@media(max-width:600px){
    .application-preview{padding:20px 16px 28px;border-radius:12px;font-size:14px;line-height:1.62}
    .application-preview .gov-doc-head .h1{font-size:21px}
    .application-preview .gov-doc-head .h2{font-size:16px}
    .application-preview .gov-doc-head .h3{font-size:14px}
    .application-preview .doc-meta{padding:12px;margin-bottom:16px}
    .application-preview .doc-meta-row{display:block}
    .application-preview .doc-meta-row > div{margin-bottom:5px}
    .application-preview .doc-sign{text-align:right;font-size:13px}
}

@media (max-width: 600px){
    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"]{
        width:100% !important;
        max-width:100% !important;
        overflow-x:hidden !important;
    }
    .block-container{
        width:100% !important;
        max-width:100vw !important;
        box-sizing:border-box !important;
        padding:4px 7px 22px !important;
        margin:0 !important;
    }
    .gov-header, .hero-shell, .login-card, .service-grid, .gov-footer{
        max-width:100% !important;
        box-sizing:border-box !important;
    }
    .gov-header{
        margin:0 !important;
        padding:8px !important;
        border-radius:14px !important;
        gap:8px !important;
    }
    .gov-identity{width:100%; min-width:0; gap:8px !important;}
    .gov-logo{width:54px !important; height:54px !important; flex:0 0 54px !important;}
    .gov-hi{font-size:20px !important; white-space:normal !important;}
    .gov-dept{font-size:13px !important; line-height:1.2 !important;}
    .gov-en{font-size:8.5px !important; white-space:normal !important; line-height:1.2 !important;}
    .leader-area{width:100% !important; grid-template-columns:1fr 1fr !important; gap:6px !important;}
    .leader-card{min-width:0 !important; min-height:68px !important; padding:5px !important; gap:5px !important; border-radius:12px !important;}
    .leader-photo{width:44px !important; height:44px !important; flex:0 0 44px !important;}
    .leader-name{font-size:11px !important; line-height:1.15 !important;}
    .leader-role{font-size:8px !important; line-height:1.15 !important;}
    .hero-shell{margin-top:6px !important; border-radius:11px !important;}
    [data-testid="stImage"]{width:100% !important; max-width:100% !important; margin:0 !important; padding:0 !important;}
    [data-testid="stImage"] img{width:100% !important; max-width:100% !important; height:auto !important; display:block !important;}
    .login-card{margin:8px 0 0 !important; width:100% !important; padding:12px 9px 13px !important; border-radius:17px !important;}
    .welcome-title{font-size:21px !important; margin-bottom:3px !important;}
    .welcome-text{font-size:11.5px !important; line-height:1.4 !important; margin-bottom:8px !important;}
    .login-tabs{margin-bottom:9px !important; padding:3px !important; border-radius:12px !important;}
    .tab-active,.tab-inactive{font-size:12px !important; padding:8px 3px !important; border-radius:9px !important;}
    .service-grid{grid-template-columns:1fr 1fr !important; gap:6px !important; margin-top:10px !important;}
    .service-item{min-width:0 !important; min-height:56px !important; padding:6px !important; gap:5px !important; border-radius:11px !important;}
    .service-icon{width:31px !important; height:31px !important; flex:0 0 31px !important; font-size:14px !important;}
    .service-text{font-size:10px !important; line-height:1.15 !important;}
    .gov-footer{margin-top:12px !important; padding:13px 9px 11px !important; border-radius:12px !important;}
    .footer-title{font-size:19px !important;}
    .footer-sub{font-size:10px !important;}
    input, textarea, select, button{max-width:100% !important; box-sizing:border-box !important;}
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
    .gov-hi{font-size:19px;}
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

/* ============================================================
   JANSEVAK BIHAR — REFERENCE RESPONSIVE COMPOSITION
   Desktop: wide hero + centered functional login + 4+4 shortcuts
   Mobile: iPhone-first hero + overlapping login + 2x2 shortcuts
   ============================================================ */
.jv-actions{display:flex;align-items:center;gap:7px;justify-content:flex-end}
.jv-pill{display:inline-flex;align-items:center;gap:5px;border:1px solid #dbe4ef;background:#fff;color:#173f78;border-radius:18px;padding:6px 10px;font-size:12px;font-weight:800;white-space:nowrap}
.jv-menu{font-size:22px;color:#0d4f9e;font-weight:900;line-height:1;padding:4px 7px}
.desktop-only{display:flex}

.st-key-home_canvas{
    position:relative !important;
    width:100% !important;
    min-height:690px !important;
    margin:10px 0 0 !important;
    overflow:visible !important;
}
.st-key-desktop_hero,.st-key-mobile_hero{width:100% !important;margin:0 !important}
.st-key-mobile_hero{display:none !important}
.st-key-desktop_hero [data-testid="stImage"],
.st-key-mobile_hero [data-testid="stImage"]{width:100% !important;margin:0 !important;padding:0 !important}
.st-key-desktop_hero img,.st-key-mobile_hero img{
    display:block !important;width:100% !important;max-width:100% !important;height:auto !important;
}

.st-key-login_panel{
    position:absolute !important;z-index:20 !important;top:390px !important;left:50% !important;
    transform:translateX(-50%) !important;width:min(47%,560px) !important;box-sizing:border-box !important;
    background:rgba(255,255,255,.985) !important;border:1px solid #d9e3ef !important;
    border-radius:22px !important;box-shadow:0 12px 30px rgba(14,54,105,.20) !important;
    padding:18px 22px 16px !important;
}
.st-key-left_services,.st-key-right_services{
    position:absolute !important;z-index:15 !important;top:500px !important;width:24% !important;
}
.st-key-left_services{left:2% !important}.st-key-right_services{right:2% !important}
.st-key-left_services .stButton,.st-key-right_services .stButton{margin:0 0 7px !important}
.st-key-left_services .stButton>button,.st-key-right_services .stButton>button{
    width:100% !important;min-height:58px !important;padding:7px 10px !important;
    border-radius:13px !important;background:#fff !important;border:1px solid #dce4ee !important;
    color:#173f78 !important;box-shadow:0 3px 9px rgba(17,58,112,.10) !important;
    font-size:15px !important;font-weight:800 !important;white-space:normal !important;line-height:1.15 !important;
}
.st-key-login_panel .welcome-title{font-size:28px !important;margin:0 0 2px !important}
.st-key-login_panel .welcome-text{font-size:14px !important;line-height:1.35 !important;margin:0 auto 9px !important}
.st-key-login_panel .login-tabs{margin-bottom:8px !important}
.st-key-login_panel [data-testid="stTextInput"]{margin-bottom:4px !important}
.st-key-login_panel [data-testid="stTextInput"] label{display:none !important}
.st-key-login_panel [data-testid="stTextInput"] input{
    min-height:43px !important;border-radius:11px !important;border:1px solid #dbe4ef !important;font-size:14px !important;
}
.st-key-login_panel .stButton>button{
    min-height:43px !important;border-radius:11px !important;font-size:14px !important;
}
.jv-or{display:flex;align-items:center;gap:8px;color:#738096;font-size:12px;margin:4px 0}
.jv-or:before,.jv-or:after{content:"";height:1px;background:#dbe4ef;flex:1}
.jv-google{display:flex;align-items:center;justify-content:center;gap:8px;border:1px solid #dbe4ef;border-radius:11px;background:#fff;color:#173f78;font-weight:800;padding:9px 8px;font-size:14px}
.st-key-home_footer{width:100% !important;margin-top:-12px !important;position:relative !important;z-index:30 !important}
.st-key-home_footer .gov-footer{margin-top:0 !important}
.footer-reference{
    width:100%;
    overflow:hidden;
    border-radius:0 0 18px 18px;
    background:#0a4688;
    line-height:0;
    box-shadow:0 8px 22px rgba(17,58,112,.12);
}
.footer-reference img{
    display:block;
    width:100%;
    height:auto;
    max-height:180px;
    object-fit:cover;
    object-position:center;
}
.mobile-hero-full{
    display:block;
    width:100%;
    max-width:100%;
    height:auto;
    border-radius:10px 10px 0 0;
    object-fit:contain;
}

@media (min-width:769px){
    .gov-header{
        display:grid !important;grid-template-columns:minmax(320px,1fr) auto auto !important;
        align-items:center !important;gap:10px !important;padding:8px 10px !important;border-radius:12px !important;
    }
    .gov-logo{width:70px !important;height:70px !important;flex-basis:70px !important}
    .gov-hi{font-size:25px !important}.gov-dept{font-size:17px !important}.gov-en{font-size:11px !important}
    .leader-area{gap:6px !important}.leader-card{width:215px !important;min-height:72px !important;padding:6px 8px !important}
    .leader-photo{width:55px !important;height:55px !important;flex-basis:55px !important}
    .leader-name{font-size:14px !important}.leader-role{font-size:10px !important}
}
@media (max-width:768px){
    .block-container{padding:0 6px 16px !important;max-width:100vw !important;width:100% !important}
    .gov-header{
        display:grid !important;grid-template-columns:1fr !important;gap:5px !important;padding:7px !important;
        margin:0 !important;border-radius:12px !important;box-shadow:0 3px 10px rgba(17,58,112,.06) !important;
    }
    .gov-identity{display:grid !important;grid-template-columns:52px 1fr auto !important;gap:7px !important;align-items:center !important}
    .gov-logo{width:52px !important;height:52px !important;flex-basis:52px !important}
    .gov-hi{font-size:19px !important;white-space:nowrap !important}
    .gov-dept{font-size:12.5px !important;line-height:1.15 !important}.gov-en{font-size:8.5px !important;line-height:1.1 !important}
    .jv-actions{display:flex !important;flex-direction:column !important;gap:2px !important}
    .jv-pill{font-size:9px !important;padding:4px 7px !important}.jv-menu{font-size:21px !important;padding:1px 5px !important}
    .leader-area{display:grid !important;grid-template-columns:1fr 1fr !important;gap:5px !important;width:100% !important}
    .leader-card{width:100% !important;min-height:62px !important;padding:4px !important;border-radius:10px !important;gap:4px !important}
    .leader-photo{width:42px !important;height:42px !important;flex-basis:42px !important;border-radius:8px !important}
    .leader-name{font-size:10.5px !important}.leader-role{font-size:7.6px !important;line-height:1.1 !important}
    .st-key-home_canvas{min-height:0 !important;margin-top:5px !important}
    .st-key-desktop_hero{display:none !important}.st-key-mobile_hero{display:block !important}
    .st-key-mobile_hero img{width:100% !important;height:auto !important;border-radius:10px 10px 0 0 !important}
    .mobile-hero-full{width:100% !important;height:auto !important;border-radius:10px 10px 0 0 !important}
    .footer-reference{border-radius:0 0 11px 11px !important;box-shadow:0 5px 15px rgba(17,58,112,.10) !important}
    .footer-reference img{max-height:none !important;width:100% !important;height:auto !important;object-fit:cover !important}
    .st-key-login_panel{
        position:relative !important;top:auto !important;left:auto !important;transform:none !important;
        width:calc(100% - 18px) !important;margin:16px auto 0 !important;padding:12px 9px 12px !important;
        border-radius:17px !important;box-shadow:0 9px 22px rgba(17,58,112,.20) !important;
    }
    .st-key-login_panel .welcome-title{font-size:20px !important}
    .st-key-login_panel .welcome-text{font-size:10.5px !important;line-height:1.32 !important;margin-bottom:7px !important}
    .st-key-login_panel .login-tabs{padding:2px !important;margin-bottom:6px !important;border-radius:10px !important}
    .st-key-login_panel .tab-active,.st-key-login_panel .tab-inactive{font-size:11px !important;padding:7px 3px !important;border-radius:8px !important}
    .st-key-login_panel [data-testid="stTextInput"] input{min-height:39px !important;font-size:12px !important;padding:7px 9px !important}
    .st-key-login_panel .stButton>button{min-height:39px !important;font-size:12px !important;padding:5px 7px !important}
    .st-key-login_panel .stHorizontalBlock{gap:5px !important}.jv-google{font-size:12px !important;padding:7px !important}.jv-or{font-size:10px !important;margin:2px 0}
    .st-key-left_services{
        position:relative !important;top:auto !important;left:auto !important;width:100% !important;margin:8px 0 0 !important;
        display:grid !important;grid-template-columns:1fr 1fr !important;gap:6px !important;
    }
    .st-key-left_services .stButton{margin:0 !important}
    .st-key-left_services .stButton>button{min-height:52px !important;height:52px !important;padding:5px 6px !important;border-radius:11px !important;font-size:10px !important;line-height:1.05 !important}
    .st-key-right_services{display:none !important}.st-key-home_footer{margin-top:7px !important}
    .st-key-home_footer .gov-footer{padding:10px 7px 9px !important;border-radius:10px !important;border-top-width:3px !important}
    .st-key-home_footer .footer-title{font-size:18px !important}.st-key-home_footer .footer-sub{font-size:9px !important}

/* Logged-in service dashboard: always 2-column grid (1,2 / 3,4 / 5,6) */
.st-key-dashboard_services{
    width:100% !important;
    max-width:980px !important;
    margin:16px auto 0 !important;
}
.st-key-dashboard_services .stHorizontalBlock{
    gap:14px !important;
}
.st-key-dashboard_services .stButton{
    margin:0 0 12px !important;
}
.st-key-dashboard_services .stButton>button{
    min-height:72px !important;
    height:auto !important;
    padding:12px 14px !important;
    border-radius:16px !important;
    background:#fff !important;
    color:#173f78 !important;
    border:1px solid #dce5ef !important;
    box-shadow:0 4px 12px rgba(17,58,112,.07) !important;
    font-size:18px !important;
    font-weight:800 !important;
    white-space:normal !important;
    line-height:1.25 !important;
}
.st-key-dashboard_services .stButton>button:hover{
    border-color:#1764bd !important;
    color:#0d4f9e !important;
}
.st-key-dashboard_footer{
    width:100% !important;
    max-width:980px !important;
    margin:14px auto 0 !important;
}
.st-key-dashboard_footer .gov-footer{
    margin-top:0 !important;
}
@media (max-width:600px){
    .st-key-dashboard_services{margin-top:10px !important;}
    .st-key-dashboard_services .stHorizontalBlock{gap:6px !important;}
    .st-key-dashboard_services .stButton{margin:0 0 7px !important;}
    .st-key-dashboard_services .stButton>button{
        min-height:58px !important;
        padding:7px 5px !important;
        border-radius:12px !important;
        font-size:12px !important;
        line-height:1.15 !important;
    }
    .st-key-dashboard_footer .gov-footer{padding:11px 8px 10px !important;border-radius:11px !important;}
    .st-key-dashboard_footer .footer-title{font-size:18px !important;}
    .st-key-dashboard_footer .footer-sub{font-size:9px !important;}
}
    .desktop-only{display:none !important}
}

/* ============================================================
   V21 DESKTOP FIXES
   - Keep both people visible on the hero: login is below the hero.
   - Use a dedicated A4 print document instead of printing the Streamlit page.
   ============================================================ */
@media (min-width:769px){
    .st-key-home_canvas{min-height:0 !important;margin:10px 0 0 !important;overflow:visible !important;}
    .st-key-desktop_hero{display:block !important;position:relative !important;width:100% !important;margin:0 !important;}
    .st-key-desktop_hero [data-testid="stImage"]{width:100% !important;max-width:100% !important;margin:0 auto !important;padding:0 !important;}
    .st-key-desktop_hero img{width:100% !important;max-width:100% !important;height:auto !important;display:block !important;object-fit:contain !important;}
    /* Desktop: force the login card to the true centre of the viewport. */
    .st-key-login_panel{
        position:relative !important;z-index:20 !important;top:auto !important;
        left:50% !important;transform:translateX(-50%) !important;
        width:min(620px,92%) !important;margin:18px 0 0 !important;
        box-sizing:border-box !important;padding:18px 22px 18px !important;
    }
    .st-key-home_footer{margin-top:18px !important;position:relative !important;z-index:5 !important;}
    [data-testid="stAudioInput"]{width:100% !important;max-width:900px !important;margin:8px auto 14px !important;}
    .application-preview{width:min(900px,100%) !important;margin:18px auto 24px !important;box-sizing:border-box !important;}
}

/* Dedicated A4 print document */
.jv-print-page{width:210mm;min-height:297mm;box-sizing:border-box;margin:0 auto;padding:12mm 15mm 10mm;background:#fff;color:#202733;font-family:'JVPrintDeva',sans-serif;font-size:10.2pt;line-height:1.38;display:flex;flex-direction:column;}
.jv-print-page .doc-head{text-align:center;color:#153c73;border-top:1.5pt solid #153c73;padding-top:4mm;}
.jv-print-page .doc-h1{font-size:17pt;font-weight:700;line-height:1.2}.jv-print-page .doc-h2{font-size:12.5pt;font-weight:700;line-height:1.2}.jv-print-page .doc-h3{font-size:10pt;font-weight:700;line-height:1.2}
.jv-print-page .doc-meta{margin-top:4mm;padding:3.2mm 4mm;background:#f8fafc;border:.6pt solid #d3dce8;border-radius:2.5mm}.jv-print-page .doc-meta-row{display:flex;justify-content:space-between;gap:8mm}.jv-print-page .doc-section{margin-top:4.2mm}.jv-print-page .doc-subject{font-weight:700;margin-top:4mm}.jv-print-page .doc-attach{margin-top:4mm}.jv-print-page ol{margin:1.5mm 0 0 6mm;padding-left:5mm}.jv-print-page li{margin:.8mm 0}.jv-print-page .doc-sign{text-align:right;margin-top:6mm;line-height:1.55}.jv-print-page .doc-footer{margin-top:auto;padding-top:2.5mm;border-top:1.2pt solid #c09527;text-align:center;color:#153c73;font-size:7.5pt}
.jv-print-button-wrap{text-align:center;padding:7px}.jv-print-button{font-family:Arial,'Noto Sans Devanagari',sans-serif;font-size:15px;font-weight:700;color:#17345f;background:#fff;border:1px solid #d6dfeb;border-radius:12px;padding:10px 18px;cursor:pointer}
@media print{html,body{margin:0!important;padding:0!important;background:#fff!important}.jv-print-button-wrap{display:none!important}.jv-print-page{margin:0!important;box-shadow:none!important}@page{size:A4;margin:0}}

/* Native print mode: the iframe print button asks the top-level Streamlit page
   to print only the already-reviewed application preview. */
@media print {
  body.jv-native-print * { visibility:hidden !important; }
  body.jv-native-print .application-preview,
  body.jv-native-print .application-preview * { visibility:visible !important; }
  body.jv-native-print .application-preview {
      position:absolute !important; left:0 !important; top:0 !important;
      width:100% !important; margin:0 !important; padding:24px !important;
      border:0 !important; box-shadow:none !important; background:#fff !important;
  }
  @page { size:A4; margin:0; }
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
        "mobile": "📱 मोबाइल नंबर दर्ज करें / Register mobile number",
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
        "confirm": "आगे बढ़ें →",
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
        "mobile": "📱 Register mobile number",
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


def render_page_footer():
    """Render the same citizen-facing footer on every non-login page."""
    st.markdown(
        f'<div class="footer-reference page-footer-reference"><img src="data:image/jpeg;base64,{FOOTER_REF}" alt="सरकार आपके द्वार" /></div>',
        unsafe_allow_html=True,
    )


def render_nav(left_label="✏️ अगर आप बदलना चाहते हैं", right_label="आगे बढ़ें →",
               left_action=None, right_action=None, left_key="nav_left", right_key="nav_right"):
    """Keep edit/change on the left and continue on the right on every workflow page."""
    left, right = st.columns(2, gap="small")
    with left:
        if st.button(left_label, key=left_key, use_container_width=True):
            if left_action:
                left_action()
            st.rerun()
    with right:
        if st.button(right_label, key=right_key, type="primary", use_container_width=True):
            if right_action:
                right_action()
            st.rerun()


@st.cache_data(show_spinner=False)
def welcome_audio_bytes():
    """Generate the Hindi citizen welcome message once for the session."""
    try:
        b = io.BytesIO()
        gTTS(
            text="नमस्कार! आपका स्वागत है। आप किस प्रकार की सहायता प्राप्त करना चाहते हैं?",
            lang="hi",
            slow=False,
        ).write_to_fp(b)
        b.seek(0)
        return b.getvalue()
    except Exception:
        return b""


def transcribe(audio):
    if audio is None:
        return ""
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 250
        recognizer.dynamic_energy_threshold = True
        with sr.AudioFile(io.BytesIO(audio.getvalue())) as source:
            data = recognizer.record(source)
        return recognizer.recognize_google(
            data,
            language="hi-IN" if st.session_state.lang == "hi" else "en-IN",
        )
    except sr.UnknownValueError:
        st.warning("आवाज़ स्पष्ट रूप से समझ नहीं आई। कृपया दोबारा बोलें।")
    except sr.RequestError:
        st.error("वाणी पहचान सेवा से संपर्क नहीं हो पाया। कृपया इंटरनेट कनेक्शन जाँचें और दोबारा बोलें।")
    except Exception as exc:
        st.error(f"माइक्रोफोन रिकॉर्डिंग संसाधित नहीं हो सकी। कृपया दोबारा प्रयास करें। ({type(exc).__name__})")
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


IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)


def application_now():
    """Return the fixed IST timestamp captured when the application was generated."""
    value = st.session_state.get("application_created_at", "")
    if value:
        try:
            return datetime.fromisoformat(value).astimezone(IST)
        except Exception:
            pass
    return now_ist()


def make_request_id():
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return random.choice(letters) + random.choice(letters) + f"{random.randint(0,9999):04d}"


def formal_subject(flow):
    subjects = {
        "ration_card": "नया राशन कार्ड निर्गत किए जाने के संबंध में।",
        "ration_not_received": "राशन प्राप्त नहीं होने के संबंध में शिकायत।",
        "less_ration": "निर्धारित मात्रा से कम राशन प्राप्त होने के संबंध में शिकायत।",
        "ration_correction": "राशन कार्ड में आवश्यक सुधार / संशोधन के संबंध में।",
        "consumer_complaint": "खाद्य एवं उपभोक्ता संरक्षण से संबंधित शिकायत के संबंध में।",
    }
    return subjects.get(flow, "शिकायत के संबंध में।")


def make_sms(request_id):
    return (
        f"आपका अनुरोध क्रमांक {request_id} है। आपकी समस्या के समाधान हेतु हमारी टीम "
        "इस पर कार्य कर रही है और इसे यथाशीघ्र निस्तारित करने का प्रयास किया जा रहा है। "
        "- खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार"
    )


# PDF generation uses explicit font tags for mixed Hindi/Latin text to avoid ReportLab font-family mapping errors on Streamlit Cloud.
def _is_devanagari(ch):
    code = ord(ch)
    return 0x0900 <= code <= 0x097F or ch in "।॥"


def _segments(text):
    """Split text into Devanagari and Latin/number runs for reliable PDF rendering."""
    text = str(text or "")
    if not text:
        return []
    out = []
    current = text[0]
    current_kind = "deva" if _is_devanagari(text[0]) else "latin"
    for ch in text[1:]:
        kind = "deva" if _is_devanagari(ch) else "latin"
        if kind == current_kind:
            current += ch
        else:
            out.append((current_kind, current))
            current = ch
            current_kind = kind
    out.append((current_kind, current))
    return out


def _mixed_width(draw, text, deva_font, latin_font):
    width = 0
    for kind, part in _segments(text):
        font = deva_font if kind == "deva" else latin_font
        box = draw.textbbox((0, 0), part, font=font)
        width += box[2] - box[0]
    return width


def _draw_mixed(draw, xy, text, deva_font, latin_font, fill):
    x, y = xy
    for kind, part in _segments(text):
        font = deva_font if kind == "deva" else latin_font
        draw.text((x, y), part, font=font, fill=fill)
        box = draw.textbbox((0, 0), part, font=font)
        x += box[2] - box[0]
    return x


def _wrap_text(draw, text, deva_font, latin_font, max_width):
    """Wrap mixed Hindi/English text by rendered pixel width."""
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if _mixed_width(draw, candidate, deva_font, latin_font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = word
        else:
            chunk = ""
            for ch in word:
                test = chunk + ch
                if _mixed_width(draw, test, deva_font, latin_font) <= max_width:
                    chunk = test
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(draw, text, x, y, deva_font, latin_font, fill, max_width, line_gap=12):
    lines = _wrap_text(draw, text, deva_font, latin_font, max_width)
    deva_box = draw.textbbox((0, 0), "अ", font=deva_font)
    latin_box = draw.textbbox((0, 0), "Ag", font=latin_font)
    line_h = max(deva_box[3] - deva_box[1], latin_box[3] - latin_box[1]) + line_gap
    for line in lines:
        _draw_mixed(draw, (x, y), line, deva_font, latin_font, fill)
        y += line_h
    return y


def application_texts():
    """Return one authoritative, corrected Hindi application text model.

    The same wording is used for the on-screen preview, PDF and print document
    so the citizen sees exactly the application that will be downloaded/printed.
    """
    s = st.session_state
    name = str(s.answers.get("name", "") or "")
    family = str(s.answers.get("family", "") or "")
    reason = str(s.answers.get("reason", "") or "")
    problem = str(s.answers.get("problem", s.problem) or "")
    mobile = str(s.answers.get("mobile", "") or "")
    address = str(s.answers.get("address", "") or "")
    subject = formal_subject(s.flow)

    if s.flow == "ration_card":
        body = f"सविनय निवेदन है कि मैं {name} हूँ"
        if family:
            body += f" तथा मेरे परिवार में कुल {family} सदस्य हैं।"
        else:
            body += "।"
        if reason:
            body += f" नया राशन कार्ड बनवाने का कारण: {reason}।"
        body += " अतः अनुरोध है कि उपलब्ध विवरण एवं संलग्न दस्तावेजों के आधार पर नियमानुसार आवश्यक कार्रवाई करते हुए मेरा नया राशन कार्ड निर्गत करने की कृपा की जाए।"
    else:
        body = f"सविनय निवेदन है कि मैं {name} हूँ।"
        if problem:
            body += f" मेरी समस्या का विवरण इस प्रकार है: {problem}।"
        if reason:
            body += f" संबंधित विवरण: {reason}।"
        body += " अतः अनुरोध है कि उपलब्ध विवरण एवं संलग्न दस्तावेजों के आधार पर नियमानुसार आवश्यक कार्रवाई करने की कृपा की जाए।"

    attachments = [
        "आधार कार्ड की छायाप्रति (जहाँ नियमानुसार आवश्यक हो)",
        "निवास प्रमाण-पत्र की छायाप्रति",
        "परिवार के सदस्यों का विवरण / परिवार रजिस्टर, यदि उपलब्ध हो",
        "पूर्व राशन कार्ड की छायाप्रति, यदि उपलब्ध हो",
        "पासपोर्ट आकार का फोटो, जहाँ आवश्यक हो",
    ]
    return {
        "name": name, "family": family, "reason": reason, "problem": problem,
        "mobile": mobile, "address": address, "subject": subject,
        "body": body, "attachments": attachments,
    }


def application_preview_html():
    d = application_texts()
    s = st.session_state
    # Embed the exact bundled Devanagari fonts in the preview so iPhone/Safari
    # and Streamlit Cloud never fall back to a different or incomplete font.
    font_regular_b64 = base64.b64encode(Path(FONT_REG).read_bytes()).decode("ascii")
    font_bold_b64 = base64.b64encode(Path(FONT_BOLD).read_bytes()).decode("ascii")
    now = application_now()
    dt = now.strftime("%d-%m-%Y")
    tm = now.strftime("%H:%M:%S")
    esc = lambda v: html.escape(str(v or ""))
    items = "".join(f"<li>{esc(x)}</li>" for x in d["attachments"])
    return f"""
<style>
@font-face{{font-family:'JVDeva';src:url(data:font/ttf;base64,{font_regular_b64}) format('truetype');font-weight:400;font-style:normal;font-display:block}}
@font-face{{font-family:'JVDeva';src:url(data:font/ttf;base64,{font_bold_b64}) format('truetype');font-weight:700 900;font-style:normal;font-display:block}}
.application-preview{{font-family:'JVDeva','Noto Sans Devanagari',sans-serif !important;}}
.application-preview b,.application-preview strong{{font-family:'JVDeva','Noto Sans Devanagari',sans-serif !important;font-weight:700;}}
</style>
<div class='application-preview'>
  <div class='gov-doc-head'>
    <div class='h1'>बिहार सरकार</div>
    <div class='h2'>खाद्य एवं उपभोक्ता संरक्षण विभाग</div>
    <div class='h3'>नागरिक सहायता एवं सेवा प्रणाली</div>
  </div>
  <div class='doc-meta'>
    <div><b>अनुरोध क्रमांक:</b> {esc(s.request_id)}</div>
    <div class='doc-meta-row'>
      <div><b>दिनांक:</b> {esc(dt)}</div>
      <div><b>समय:</b> {esc(tm)} (भारतीय मानक समय)</div>
    </div>
  </div>
  <div>सेवा में,</div>
  <div>प्रखंड आपूर्ति पदाधिकारी / संबंधित सक्षम पदाधिकारी</div>
  <div>संबंधित प्रखंड / कार्यालय: ____________________________________</div>
  <div class='doc-subject'><b>विषय : </b>{esc(d["subject"])}</div>
  <div>महोदय/महोदया,</div>
  <p>{esc(d["body"])}</p>
  <div class='doc-attach'><b>संलग्नक:</b>
    <ol>{items}</ol>
  </div>
  <div class='doc-sign'>
    भवदीय,<br><br>
    हस्ताक्षर / अंगूठे का निशान: __________________________<br>
    नाम: {esc(d["name"])}<br>
    मोबाइल नंबर: {esc(d["mobile"])}<br>
    पता: {esc(d["address"])}<br>
    स्थान: ____________________<br>
    दिनांक: {esc(dt)}
  </div>
  <div class='doc-footer'>जनसेवक बिहार • सुगम सेवा • सशक्त नागरिक • समृद्ध बिहार</div>
</div>
"""



def application_print_html():
    d = application_texts()
    s = st.session_state
    font_regular_b64 = base64.b64encode(Path(FONT_REG).read_bytes()).decode("ascii")
    font_bold_b64 = base64.b64encode(Path(FONT_BOLD).read_bytes()).decode("ascii")
    now = application_now()
    dt = now.strftime("%d-%m-%Y")
    tm = now.strftime("%H:%M:%S")
    esc = lambda v: html.escape(str(v or "")).replace("\n", "<br/>")
    items = "".join(f"<li>{esc(x)}</li>" for x in d["attachments"])
    return f"""<!doctype html>
<html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
@font-face{{font-family:'JVPrintDeva';src:url(data:font/ttf;base64,{font_regular_b64}) format('truetype');font-weight:400;font-style:normal;font-display:block}}
@font-face{{font-family:'JVPrintDeva';src:url(data:font/ttf;base64,{font_bold_b64}) format('truetype');font-weight:700 900;font-style:normal;font-display:block}}
*{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:#eef2f7}}
.jv-print-button-wrap{{text-align:center;padding:7px}}.jv-print-button{{font-family:Arial,'JVPrintDeva',sans-serif;font-size:15px;font-weight:700;color:#17345f;background:#fff;border:1px solid #d6dfeb;border-radius:12px;padding:10px 18px;cursor:pointer}}
.jv-print-page{{width:210mm;min-height:297mm;box-sizing:border-box;margin:0 auto;padding:12mm 15mm 10mm;background:#fff;color:#202733;font-family:'JVPrintDeva',sans-serif;font-size:10.2pt;line-height:1.38;display:flex;flex-direction:column}}
.doc-head{{text-align:center;color:#153c73;border-top:1.5pt solid #153c73;padding-top:4mm}}.doc-h1{{font-size:17pt;font-weight:700;line-height:1.2}}.doc-h2{{font-size:12.5pt;font-weight:700;line-height:1.2}}.doc-h3{{font-size:10pt;font-weight:700;line-height:1.2}}
.doc-meta{{margin-top:4mm;padding:3.2mm 4mm;background:#f8fafc;border:0.6pt solid #d3dce8;border-radius:2.5mm}}.doc-meta-row{{display:flex;justify-content:space-between;gap:8mm}}.doc-section{{margin-top:4.2mm}}.doc-subject{{font-weight:700;margin-top:4mm}}.doc-attach{{margin-top:4mm}}ol{{margin:1.5mm 0 0 6mm;padding-left:5mm}}li{{margin:.8mm 0}}.doc-sign{{text-align:right;margin-top:6mm;line-height:1.55}}.doc-footer{{margin-top:auto;padding-top:2.5mm;border-top:1.2pt solid #c09527;text-align:center;color:#153c73;font-size:7.5pt}}
@media print{{html,body{{background:#fff!important}}.jv-print-button-wrap{{display:none!important}}.jv-print-page{{margin:0!important;box-shadow:none!important}}@page{{size:A4;margin:0}}}}
</style></head><body>
<div class="jv-print-button-wrap"><button class="jv-print-button" onclick="window.print()">🖨️ आवेदन प्रिंट करें</button></div>
<div class="jv-print-page">
<div class="doc-head"><div class="doc-h1">बिहार सरकार</div><div class="doc-h2">खाद्य एवं उपभोक्ता संरक्षण विभाग</div><div class="doc-h3">नागरिक सहायता एवं सेवा प्रणाली</div></div>
<div class="doc-meta"><div><b>अनुरोध क्रमांक: {esc(s.request_id)}</b></div><div class="doc-meta-row"><div><b>दिनांक: {esc(dt)}</b></div><div><b>समय: {esc(tm)} (भारतीय मानक समय)</b></div></div></div>
<div class="doc-section">सेवा में,</div><div>प्रखंड आपूर्ति पदाधिकारी / संबंधित सक्षम पदाधिकारी</div><div>संबंधित प्रखंड / कार्यालय: ____________________________________</div>
<div class="doc-subject">विषय : {esc(d["subject"])}</div><div class="doc-section">महोदय/महोदया,</div><div>{esc(d["body"])}</div>
<div class="doc-attach"><b>संलग्नक:</b><ol>{items}</ol></div>
<div class="doc-sign">भवदीय,<br><br>हस्ताक्षर / अंगूठे का निशान: __________________________<br>नाम: {esc(d["name"])}<br>मोबाइल नंबर: {esc(d["mobile"])}<br>पता: {esc(d["address"])}<br>स्थान: ____________________<br>दिनांक: {esc(dt)}</div>
<div class="doc-footer">जनसेवक बिहार  •  सुगम सेवा  •  सशक्त नागरिक  •  समृद्ध बिहार</div></div></body></html>"""


def pdf_file(page_png=None):
    """Create a real text-based A4 PDF from the same authoritative application data.

    Devanagari is rendered directly with Noto Sans Devanagari by ReportLab,
    avoiding Pillow/RAQM differences between local and Streamlit Cloud.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )

    pdf_bytes = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_bytes,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=14*mm,
        bottomMargin=18*mm,
        title=f"Jansevak Bihar {st.session_state.request_id}",
        author="खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार",
    )

    # Noto Sans Devanagari contains both Devanagari and Latin characters,
    # so a single font is used throughout the document for consistent shaping.
    pdfmetrics.registerFont(TTFont("NotoDeva", FONT_REG))
    pdfmetrics.registerFont(TTFont("NotoDevaBold", FONT_BOLD))

    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "JVBase", parent=styles["Normal"], fontName="NotoDeva",
        fontSize=10.5, leading=15.5, textColor=colors.HexColor("#232730"),
        spaceAfter=4,
    )
    small = ParagraphStyle("JVSmall", parent=base, fontSize=9.2, leading=13.2)
    head = ParagraphStyle(
        "JVHead", parent=base, fontName="NotoDevaBold", fontSize=16,
        leading=19, alignment=TA_CENTER, textColor=colors.HexColor("#153c73"),
        spaceAfter=1,
    )
    subhead = ParagraphStyle(
        "JVSubHead", parent=head, fontSize=11.5, leading=14,
    )
    meta = ParagraphStyle(
        "JVMeta", parent=base, fontSize=9.4, leading=13.5,
    )
    subject = ParagraphStyle(
        "JVSubject", parent=base, fontName="NotoDevaBold", fontSize=10.8,
        leading=15.8, spaceBefore=8, spaceAfter=7,
    )
    sign = ParagraphStyle(
        "JVSign", parent=base, alignment=TA_RIGHT, leading=15.2,
    )
    footer = ParagraphStyle(
        "JVFooter", parent=base, fontSize=8.2, leading=10,
        alignment=TA_CENTER, textColor=colors.HexColor("#153c73"),
    )

    s = st.session_state
    d = application_texts()
    now = application_now()
    dt = now.strftime("%d-%m-%Y")
    tm = now.strftime("%H:%M:%S")

    def esc(v):
        return html.escape(str(v or "")).replace("\n", "<br/>")

    story = []
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#153c73"), spaceAfter=7))
    story.append(Paragraph("बिहार सरकार", head))
    story.append(Paragraph("खाद्य एवं उपभोक्ता संरक्षण विभाग", subhead))
    story.append(Paragraph("नागरिक सहायता एवं सेवा प्रणाली", ParagraphStyle(
        "JVH3", parent=subhead, fontSize=9.8, leading=12,
    )))
    story.append(Spacer(1, 7))

    meta_data = [
        [Paragraph(f"<b>अनुरोध क्रमांक: {esc(s.request_id)}</b>", meta),
         Paragraph(f"<b>दिनांक: {esc(dt)}</b>", meta)],
        [Paragraph(f"समय: {esc(tm)} (भारतीय मानक समय)", meta), Paragraph("", meta)],
    ]
    mt = Table(meta_data, colWidths=[(A4[0]-36*mm)/2]*2)
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f9fbfe")),
        ("BOX", (0,0), (-1,-1), 0.8, colors.HexColor("#d2dae6")),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e1e6ee")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(mt)
    story.append(Spacer(1, 12))

    story.append(Paragraph("सेवा में,", base))
    story.append(Paragraph("प्रखंड आपूर्ति पदाधिकारी / संबंधित सक्षम पदाधिकारी", base))
    story.append(Paragraph("संबंधित प्रखंड / कार्यालय: ________________________________", base))
    story.append(Paragraph(f"विषय : {esc(d['subject'])}", subject))
    story.append(Paragraph("महोदय/महोदया,", base))
    story.append(Paragraph(esc(d["body"]), base))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>संलग्नक:</b>", base))
    attach_rows = []
    for i, item in enumerate(d["attachments"], 1):
        attach_rows.append(Paragraph(f"{i}. {esc(item)}", base))
    story.extend(attach_rows)
    story.append(Spacer(1, 14))

    sign_text = (
        "भवदीय,<br/><br/>"
        "हस्ताक्षर / अंगूठे का निशान: __________________________<br/>"
        f"नाम: {esc(d['name'])}<br/>"
        f"मोबाइल नंबर: {esc(d['mobile'])}<br/>"
        f"पता: {esc(d['address'])}<br/>"
        "स्थान: ____________________<br/>"
        f"दिनांक: {esc(dt)}"
    )
    story.append(Paragraph(sign_text, sign))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#c09527"), spaceAfter=5))
    story.append(Paragraph("जनसेवक बिहार  •  सुगम सेवा  •  सशक्त नागरिक  •  समृद्ध बिहार", footer))

    doc.build(story)
    pdf_bytes.seek(0)
    return pdf_bytes


# ------------------------------------------------------------
# Final-review helper
# ------------------------------------------------------------
def go_to_question_for_edit(question_index, speak_again=False):
    """Return to a specific answer without showing a separate confirmation page."""
    st.session_state.q_index = int(question_index)
    st.session_state.question_edit_mode = not speak_again
    if speak_again:
        key = st.session_state.questions[int(question_index)][0]
        st.session_state[f"voice_{key}_{int(question_index)}"] = ""
        st.session_state.pop(f"h_{key}_{int(question_index)}", None)
        st.session_state.voice_round = int(st.session_state.get("voice_round", 0)) + 1
    st.session_state.stage = "question"


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
    "voice_edit_mode": False,
    "voice_round": 0,
    "request_id": "",
    "application_created_at": "",
    "pending": None,
    "question_edit_mode": False,
    "problem_edit_mode": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

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
    <div class="jv-actions">
      <span class="jv-pill">🌐 हिंदी⌄</span>
      <span class="jv-menu">☰</span>
    </div>
  </div>
  <div class="leader-area">{leader1}{leader2}</div>
  <div class="jv-actions desktop-only">
    <span class="jv-pill">📞 हेल्पलाइन<br><b>1800-3456-194</b></span>
  </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Home / Login page — responsive composition
# ------------------------------------------------------------
if st.session_state.stage == "home":

    def start_service(flow_key):
        st.session_state.flow = flow_key
        st.session_state.questions = questions(flow_key)
        st.session_state.q_index = 0
        st.session_state.answers = {}
        st.session_state.problem = ""
        st.session_state.stage = "dashboard"
        st.rerun()

    with st.container(key="home_canvas"):
        with st.container(key="desktop_hero"):
            st.image(io.BytesIO(HERO_DESKTOP_BYTES), width="stretch")

        with st.container(key="mobile_hero"):
            st.markdown(
                f'<img class="mobile-hero-full" src="data:image/jpeg;base64,{MOBILE_HERO_FULL}" alt="जनसेवक बिहार" />',
                unsafe_allow_html=True,
            )

        with st.container(key="login_panel"):
            st.markdown(f'<div class="welcome-title">{L("welcome")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="welcome-text">{L("welcome_text")}</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="login-tabs">
                  <div class="tab-active">👤 {L("citizen")}</div>
                  <div class="tab-inactive">♙ {L("officer")}</div>
                </div>
                """, unsafe_allow_html=True)

            mobile = st.text_input(
                "mobile",
                value=st.session_state.mobile_login,
                placeholder="📱 मोबाइल नंबर दर्ज करें / Register mobile number",
                max_chars=10,
                key="login_mobile_input",
                label_visibility="collapsed",
            )
            st.session_state.mobile_login = mobile

            otp_col, send_col = st.columns([3.2, 1.0], gap="small")
            with otp_col:
                otp = st.text_input(
                    "otp", placeholder="🔐 OTP दर्ज करें", max_chars=6,
                    type="password", key="login_otp_input", label_visibility="collapsed",
                )
            with send_col:
                if st.button("OTP भेजें", key="send_otp_home", use_container_width=True):
                    if not re.fullmatch(r"\d{10}", mobile.strip()):
                        st.error("कृपया 10 अंकों का मोबाइल नंबर दर्ज करें।")
                    else:
                        st.session_state.otp_sent = True
                        st.session_state.demo_otp = "123456"
                        st.toast("Demo OTP भेजा गया: 123456")

            if st.button("लॉगिन करें  →", key="login_home", type="primary", use_container_width=True):
                if not re.fullmatch(r"\d{10}", mobile.strip()):
                    st.error("कृपया 10 अंकों का मोबाइल नंबर दर्ज करें।")
                elif otp.strip() != st.session_state.demo_otp:
                    st.error("OTP सही नहीं है। Demo OTP: 123456")
                else:
                    st.session_state.logged_in = True
                    st.session_state.stage = "dashboard"
                    st.rerun()

            st.markdown('<div class="jv-or"><span>या</span></div>', unsafe_allow_html=True)
            if st.button("🇬  Google से लॉगिन करें", key="google_demo", use_container_width=True):
                st.info("Google Login demo mode में है।")
            st.markdown(
                '<div class="small-note">सुरक्षित डेमो • परीक्षण में वास्तविक आधार/संवेदनशील जानकारी दर्ज न करें।</div>',
                unsafe_allow_html=True,
            )

    with st.container(key="home_footer"):
        st.markdown(
            f'<div class="footer-reference"><img src="data:image/jpeg;base64,{FOOTER_REF}" alt="सरकार आपके द्वार" /></div>',
            unsafe_allow_html=True,
        )

# ------------------------------------------------------------
# Dashboard after login
# ------------------------------------------------------------
elif st.session_state.stage == "dashboard":
    st.markdown(f"## {L('welcome')}")
    st.write("कृपया नीचे अपनी सेवा चुनें / Please choose a service.")

    # Citizen welcome message in Hindi. The user taps play to hear the female-style
    # Google Hindi TTS greeting; autoplay is intentionally avoided because mobile
    # browsers commonly block automatic audio playback.
    welcome_audio = welcome_audio_bytes()
    if welcome_audio:
        st.markdown("**🔊 नागरिक स्वागत संदेश / Citizen Welcome Message**")
        st.audio(welcome_audio, format="audio/mp3")

    # Fixed six-service order requested by the user:
    # 1,2 side-by-side; 3,4 directly below; 5,6 directly below.
    service_buttons = [
        ("🟢", L("new_card"), "ration_card"),
        ("🟣", L("correction"), "ration_correction"),
        ("🟠", L("less"), "less_ration"),
        ("🔴", L("food_complaint"), "consumer_complaint"),
        ("🔵", L("not_received"), "ration_not_received"),
        ("🟦", L("consumer"), "consumer_complaint"),
    ]

    with st.container(key="dashboard_services"):
        # Two columns are deliberately kept for every viewport so the layout
        # remains 1-2 / 3-4 / 5-6 on phones, tablets and desktop screens.
        for row in range(3):
            left_item = service_buttons[row * 2]
            right_item = service_buttons[row * 2 + 1]
            cols = st.columns(2, gap="small", wrap=False)
            for col, (icon, label, flow_key) in zip(cols, (left_item, right_item)):
                with col:
                    if st.button(f"{icon} {label}", key=f"dash_service_{row}_{flow_key}", use_container_width=True):
                        st.session_state.flow = flow_key
                        st.session_state.questions = questions(flow_key)
                        st.session_state.q_index = 0
                        st.session_state.answers = {}
                        st.session_state.problem = ""
                        st.session_state.stage = "question"
                        st.rerun()

    a, b = st.columns(2, gap="small")
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

    with st.container(key="dashboard_footer"):
        st.markdown(
            f'<div class="footer-reference"><img src="data:image/jpeg;base64,{FOOTER_REF}" alt="सरकार आपके द्वार" /></div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Voice problem
# ------------------------------------------------------------
elif st.session_state.stage == "voice_problem":
    st.header(L("speak"))
    st.write("अपनी समस्या बताएं। आप चाहें तो इसे दोबारा बोल सकते हैं या लिखकर सुधार सकते हैं।")

    audio = st.audio_input(
        "🎤 माइक्रोफोन दबाकर बोलें / Press microphone and speak",
        sample_rate=16000,
        key=f"voice_problem_audio_{st.session_state.get('voice_round', 0)}",
    )
    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if h != st.session_state.voice_hash:
            st.session_state.voice_hash = h
            text = transcribe(audio)
            if text:
                st.session_state.voice_text = text
                st.session_state.problem = text
                st.session_state.voice_edit_mode = False
                st.rerun()

    voice_text = str(st.session_state.get("voice_text", "") or "").strip()
    if voice_text:
        st.markdown(
            f'<div class="voice-answer"><b>🎤 आपने कहा / You said:</b><br>{safe(voice_text)}</div>',
            unsafe_allow_html=True,
        )

    a1, a2 = st.columns(2, gap="small")
    with a1:
        if st.button("🔄 दोबारा बोलें / Speak again", key="voice_problem_repeat", use_container_width=True):
            st.session_state.voice_text = ""
            st.session_state.problem = ""
            st.session_state.voice_hash = ""
            st.session_state.voice_edit_mode = False
            st.session_state.voice_round = int(st.session_state.get("voice_round", 0)) + 1
            st.rerun()
    with a2:
        if st.button("✏️ जानकारी बदलें / Edit", key="voice_problem_edit", use_container_width=True):
            st.session_state.voice_edit_mode = True
            st.rerun()

    if st.session_state.get("voice_edit_mode", False):
        edited = st.text_area(
            "✏️ अपनी समस्या सुधारें / Edit your problem",
            value=st.session_state.get("problem", "") or voice_text,
            height=130,
            key="voice_problem_editor",
        )
        st.session_state.problem = edited
        st.session_state.voice_text = edited

    left, right = st.columns(2, gap="small")
    with left:
        if st.button("✏️ अगर आप बदलना चाहते हैं", key="voice_problem_back", use_container_width=True):
            st.session_state.stage = "dashboard"
            st.rerun()
    with right:
        next_label = "पुष्टि करें एवं आगे बढ़ें →" if st.session_state.get("voice_edit_mode", False) else "आगे बढ़ें →"
        if st.button(next_label, key="voice_problem_continue", type="primary", use_container_width=True):
            value = str(st.session_state.get("problem", "") or st.session_state.get("voice_text", "")).strip()
            if value:
                st.session_state.problem = value
                st.session_state.flow = detect_flow(value)
                st.session_state.questions = questions(st.session_state.flow)
                st.session_state.q_index = 0
                st.session_state.answers = {}
                st.session_state.voice_edit_mode = False
                st.session_state.stage = "question"
                st.rerun()
            else:
                st.warning("कृपया अपनी समस्या बताएं।")
    render_page_footer()


# ------------------------------------------------------------
# Typed problem
# ------------------------------------------------------------
elif st.session_state.stage == "type_problem":
    st.header(L("write"))

    edit_mode = bool(st.session_state.get("problem_edit_mode", False))
    problem_value = str(st.session_state.get("problem", "") or "")

    problem = st.text_area(
        "अपनी समस्या बताएं / Tell us your problem",
        value=problem_value,
        height=130,
        disabled=not edit_mode and bool(problem_value),
        key="problem_text_area",
    )

    audio = st.audio_input(
        "🎤 या बोलकर बताएं / Or speak",
        sample_rate=16000,
        key=f"problem_audio_{st.session_state.get('voice_round', 0)}",
    )
    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if h != st.session_state.voice_hash:
            st.session_state.voice_hash = h
            t = transcribe(audio)
            if t:
                st.session_state.problem = t
                st.session_state.voice_text = t
                st.session_state.problem_edit_mode = False
                st.rerun()

    if st.session_state.problem:
        st.markdown(
            f'<div class="voice-answer"><b>🎤 आपने कहा / You said:</b><br>{safe(st.session_state.problem)}</div>',
            unsafe_allow_html=True,
        )

    a1, a2 = st.columns(2, gap="small")
    with a1:
        if st.button("🔄 दोबारा बोलें / Speak again", key="problem_speak_again", use_container_width=True):
            st.session_state.problem = ""
            st.session_state.voice_text = ""
            st.session_state.voice_hash = ""
            st.session_state.problem_edit_mode = False
            st.session_state.voice_round = int(st.session_state.get("voice_round", 0)) + 1
            st.rerun()
    with a2:
        if st.button("✏️ जानकारी बदलें / Edit", key="problem_edit", use_container_width=True):
            st.session_state.problem_edit_mode = True
            st.rerun()

    # Keep the manually edited text in session state when the field is active.
    if edit_mode:
        st.session_state.problem = problem

    left, right = st.columns(2, gap="small")
    with left:
        if st.button("✏️ अगर आप बदलना चाहते हैं", key="type_nav_edit", use_container_width=True):
            st.session_state.problem_edit_mode = True
            st.rerun()
    with right:
        next_label = "पुष्टि करें एवं आगे बढ़ें →" if st.session_state.get("problem_edit_mode", False) else "आगे बढ़ें →"
        if st.button(next_label, key="type_nav_continue", type="primary", use_container_width=True):
            value = str(st.session_state.get("problem", "") or problem).strip()
            if value:
                st.session_state.problem = value
                st.session_state.flow = detect_flow(value)
                st.session_state.questions = questions(st.session_state.flow)
                st.session_state.q_index = 0
                st.session_state.answers = {}
                st.session_state.problem_edit_mode = False
                st.session_state.stage = "question"
                st.rerun()
            else:
                st.warning("कृपया अपनी समस्या बताएं।")

    render_page_footer()


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
    st.caption(f"चरण {current_step} / {total}  •  Step {current_step} / {total}")
    st.header(qtext)

    if st.button("🔊 सवाल सुनें / Hear question", key=f"hear_q_{key}_{st.session_state.q_index}"):
        speak(qtext)

    voice_key = f"voice_{key}_{st.session_state.q_index}"
    hash_key = f"h_{key}_{st.session_state.q_index}"
    edit_key = f"edit_{key}_{st.session_state.q_index}"
    voice_round = int(st.session_state.get("voice_round", 0))

    # The voice recorder is always available. Pressing "Speak again" below
    # clears the previous transcript and increments the recorder key.
    audio = st.audio_input(
        "🎤 बोलकर उत्तर दें / Answer by voice",
        sample_rate=16000,
        key=f"audio_{key}_{st.session_state.q_index}_{voice_round}",
    )
    if audio:
        h = hashlib.sha256(audio.getvalue()).hexdigest()
        if st.session_state.get(hash_key) != h:
            st.session_state[hash_key] = h
            t = transcribe(audio)
            if t:
                st.session_state[voice_key] = t
                # A fresh voice answer is accepted without asking the citizen
                # another confirmation question.
                st.session_state.question_edit_mode = False
                st.rerun()

    voice = str(st.session_state.get(voice_key, "") or "").strip()
    existing = str(st.session_state.answers.get(key, "") or "").strip()
    current_answer = voice or existing

    if voice:
        st.markdown(
            f'<div class="voice-answer"><b>🎤 आपने कहा / You said:</b><br>{safe(voice)}</div>',
            unsafe_allow_html=True,
        )

    # Every information page has a Speak Again control. It does not ask for
    # confirmation; it simply clears the previous voice answer and opens a new
    # recorder on the same page.
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button(
            "🔄 दोबारा बोलें / Speak again",
            key=f"repeat_voice_{key}_{st.session_state.q_index}",
            use_container_width=True,
        ):
            st.session_state[voice_key] = ""
            st.session_state.pop(hash_key, None)
            st.session_state.question_edit_mode = False
            st.session_state.voice_round = voice_round + 1
            st.rerun()
    with b2:
        if st.button(
            "✏️ जानकारी बदलें / Edit",
            key=f"edit_answer_{key}_{st.session_state.q_index}",
            use_container_width=True,
        ):
            st.session_state.question_edit_mode = True
            st.rerun()

    # Manual editing is explicitly separated from the normal path. If the
    # citizen does not press Edit, the current answer is saved directly.
    if st.session_state.get("question_edit_mode", False):
        if typ == "number":
            try:
                default_number = int(re.sub(r"\D", "", current_answer) or "1")
            except Exception:
                default_number = 1
            answer = str(st.number_input(
                "✏️ उत्तर बदलें / Edit answer",
                min_value=1,
                max_value=100,
                value=max(1, min(default_number, 100)),
                key=f"edit_num_{key}_{st.session_state.q_index}",
            ))
        else:
            answer = st.text_input(
                "✏️ उत्तर बदलें / Edit answer",
                value=current_answer,
                key=f"edit_text_{key}_{st.session_state.q_index}",
            )
    else:
        # Normal display remains editable for typed answers, while voice
        # recognition is shown clearly as the current answer.
        if typ == "number":
            try:
                default_number = int(re.sub(r"\D", "", current_answer) or "1")
            except Exception:
                default_number = 1
            answer = str(st.number_input(
                "उत्तर / Answer",
                min_value=1,
                max_value=100,
                value=max(1, min(default_number, 100)),
                key=f"answer_num_{key}_{st.session_state.q_index}",
            ))
        else:
            answer = st.text_input(
                "उत्तर / Answer",
                value=current_answer,
                key=f"answer_text_{key}_{st.session_state.q_index}",
            )

    def save_and_continue(value):
        value = str(value or "").strip()
        if not value:
            st.warning("कृपया उत्तर दर्ज करें।")
            return False

        # Normalize Hindi digits and common spacing/hyphenation returned by
        # speech recognition for mobile/Aadhaar numbers.
        digit_map = str.maketrans("०१२३४५६७८९", "0123456789")
        normalized = value.translate(digit_map)
        normalized = re.sub(r"[\s\-]", "", normalized)

        if typ == "mobile":
            if not re.fullmatch(r"\d{10}", normalized):
                st.error("कृपया 10 अंकों का मोबाइल नंबर दर्ज करें।")
                return False
            value = normalized
        elif typ == "aadhaar":
            if not re.fullmatch(r"\d{12}", normalized):
                st.error("कृपया 12 अंकों का आधार नंबर दर्ज करें।")
                return False
            value = normalized

        st.session_state.answers[key] = value
        st.session_state[voice_key] = "" if st.session_state.get("question_edit_mode", False) else st.session_state.get(voice_key, "")
        st.session_state.question_edit_mode = False
        st.session_state.q_index += 1
        if st.session_state.q_index >= len(st.session_state.questions):
            st.session_state.stage = "review"
        else:
            st.session_state.stage = "question"
        return True

    # The navigation is deliberately simple: left = edit, right = continue.
    # No separate "Is this correct?" page is shown.
    left, right = st.columns(2, gap="small")
    with left:
        left_label = "✏️ जानकारी बदलें / Edit" if not st.session_state.get("question_edit_mode", False) else "↩️ बदलाव रद्द करें / Cancel"
        if st.button(
            left_label,
            key=f"question_edit_{key}_{st.session_state.q_index}",
            use_container_width=True,
        ):
            st.session_state.question_edit_mode = not st.session_state.get("question_edit_mode", False)
            st.rerun()
    with right:
        next_label = "पुष्टि करें एवं आगे बढ़ें →" if st.session_state.get("question_edit_mode", False) else "आगे बढ़ें →"
        if st.button(
            next_label,
            key=f"question_continue_{key}_{st.session_state.q_index}",
            type="primary",
            use_container_width=True,
        ):
            if save_and_continue(answer):
                st.rerun()

    render_page_footer()


# ------------------------------------------------------------
# Final review
# ------------------------------------------------------------
elif st.session_state.stage == "review":
    st.header("🔎 अंतिम जाँच / Final review")
    st.subheader(title(st.session_state.flow))
    st.write("नीचे दी गई जानकारी अंतिम आवेदन में शामिल की जाएगी। यदि कोई बदलाव आवश्यक हो, तो संबंधित बटन दबाएँ।")

    for idx, q in enumerate(st.session_state.questions):
        key, hi, en, typ = q
        label = hi if st.session_state.lang == "hi" else en
        value = st.session_state.answers.get(key, "")
        with st.container(border=True):
            st.markdown(f"**{label}:** {safe(value)}")
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("✏️ जानकारी बदलें / Edit", key=f"review_edit_{idx}", use_container_width=True):
                    go_to_question_for_edit(idx, speak_again=False)
                    st.rerun()
            with c2:
                if st.button("🔄 दोबारा बोलें / Speak again", key=f"review_speak_{idx}", use_container_width=True):
                    go_to_question_for_edit(idx, speak_again=True)
                    st.rerun()

    left, right = st.columns(2, gap="small")
    with left:
        if st.button("✏️ जानकारी बदलें / Edit", key="review_edit_first", use_container_width=True):
            go_to_question_for_edit(0, speak_again=False)
            st.rerun()
    with right:
        if st.button("आगे बढ़ें → आवेदन तैयार करें", key="review_continue", type="primary", use_container_width=True):
            st.session_state.request_id = make_request_id()
            st.session_state.application_created_at = now_ist().isoformat()
            st.session_state.stage = "application"
            st.rerun()

    render_page_footer()


# ------------------------------------------------------------
# Application
# ------------------------------------------------------------
elif st.session_state.stage == "application":
    st.header("📄 " + title(st.session_state.flow))
    st.success("आपका आवेदन तैयार है। / Your application is ready.")

    # The visible application and the downloaded PDF both use the same
    # authoritative application_texts() data model. The visible preview is
    # real browser text (not a rasterized Pillow image), preventing Hindi
    # shaping/spelling differences on Streamlit Cloud.
    st.markdown(application_preview_html(), unsafe_allow_html=True)

    # The PDF is generated directly from the same authoritative text model
    # using Noto Sans Devanagari in ReportLab.
    pdf = pdf_file()

    print_doc = application_print_html()

    col1, col2 = st.columns(2, gap="small")
    with col1:
        st.download_button("📄 PDF डाउनलोड करें", data=pdf,
                           file_name=f"Jansevak_Bihar_{st.session_state.request_id}.pdf",
                           mime="application/pdf", use_container_width=True)
    with col2:
        components.html(print_doc, height=70, scrolling=False)

    st.markdown("### SMS acknowledgement / SMS सूचना")
    st.info(make_sms(st.session_state.request_id))
    st.info("प्रिंट के लिए A4 आकार चुनें। डाउनलोड किया गया PDF इसी आवेदन के हिंदी प्रारूप में है।")

    left, right = st.columns(2, gap="small")
    with left:
        if st.button("✏️ अगर आप बदलना चाहते हैं", key="application_edit", use_container_width=True):
            st.session_state.stage = "review"
            st.rerun()
    with right:
        if st.button("आगे बढ़ें → नया आवेदन", key="application_new", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_page_footer()

