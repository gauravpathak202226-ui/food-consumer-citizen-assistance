
import io
import re
import hashlib
from datetime import date

import streamlit as st
import speech_recognition as sr
from gtts import gTTS
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

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
        return r.recognize_google(data, language="hi-IN" if st.session_state.lang=="hi" else "en-IN")
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        st.error(f"Voice recognition error: {e}")
        return ""

def speak(text):
    try:
        b=io.BytesIO()
        gTTS(text=text, lang="hi" if st.session_state.lang=="hi" else "en").write_to_fp(b)
        b.seek(0)
        st.audio(b, format="audio/mp3")
    except Exception:
        pass

def pdf_file():
    b=io.BytesIO()
    doc=SimpleDocTemplate(b,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
    styles=getSampleStyleSheet()
    head=ParagraphStyle("head",parent=styles["Title"],alignment=TA_CENTER,fontSize=15)
    story=[Paragraph("FOOD & CONSUMER PROTECTION DEPARTMENT",head),Spacer(1,8),
           Paragraph(title(st.session_state.flow),head),Spacer(1,15)]
    rows=[]
    for key,hi,en,typ in st.session_state.questions:
        label=hi if st.session_state.lang=="hi" else en
        rows.append([Paragraph("<b>"+label+"</b>",styles["BodyText"]),
                     Paragraph(str(st.session_state.answers.get(key,"")),styles["BodyText"])])
    table=Table(rows,colWidths=[170,330])
    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.grey),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),7),
        ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),
        ("BOTTOMPADDING",(0,0),(-1,-1),7),
    ]))
    story += [table,Spacer(1,18)]
    request=("उपरोक्त विषय में आवश्यक जांच कर नियमानुसार कार्रवाई करने का अनुरोध है।"
             if st.session_state.lang=="hi"
             else "I request the concerned authority to examine the matter and take necessary action as per applicable rules.")
    story += [Paragraph("<b>Request / अनुरोध</b>",styles["Heading3"]),
              Paragraph(request,styles["BodyText"]),Spacer(1,55),
              Paragraph("स्थान / Place: __________________________",styles["BodyText"]),
              Spacer(1,30),
              Paragraph("आवेदक के हस्ताक्षर / अंगूठे का निशान<br/>Applicant Signature / Thumb Impression",styles["BodyText"])]
    doc.build(story)
    b.seek(0)
    return b

for k,v in {
    "lang":"hi","stage":"home","flow":None,"questions":[],"q_index":0,
    "answers":{},"problem":"","voice_text":"","voice_hash":""
}.items():
    if k not in st.session_state: st.session_state[k]=v

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
    st.markdown('<div class="warn">⚠️ Public prototype: use dummy data while testing. Do not enter real Aadhaar or other sensitive personal data.</div>',unsafe_allow_html=True)

    a,b=st.columns(2)
    with a:
        if st.button(L("speak")): st.session_state.stage="voice_problem"; st.rerun()
        if st.button(L("guided")):
            st.session_state.flow="consumer_complaint"; st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0; st.session_state.answers={}; st.session_state.stage="question"; st.rerun()
    with b:
        if st.button(L("type")): st.session_state.stage="type_problem"; st.rerun()
        if st.button(L("write")): st.session_state.stage="type_problem"; st.rerun()

    st.subheader("उदाहरण / Examples")
    st.write("“मुझे इस महीने राशन नहीं मिला।”")
    st.write("“मुझे कम चावल मिला।”")
    st.write("“मुझे नया राशन कार्ड बनवाना है।”")
    st.write("“दुकानदार ने ज्यादा पैसे लिए।”")

elif st.session_state.stage=="voice_problem":
    st.header(L("speak"))
    audio=st.audio_input("🎤 माइक्रोफोन दबाकर बोलें / Press microphone and speak",sample_rate=16000)
    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if h!=st.session_state.voice_hash:
            st.session_state.voice_hash=h
            st.session_state.voice_text=transcribe(audio)
    if st.session_state.voice_text:
        st.markdown(f'<div class="confirm"><b>आपने कहा / You said:</b><br>{st.session_state.voice_text}</div>',unsafe_allow_html=True)
        if st.button("🔊 सुनें / Hear"):
            speak(st.session_state.voice_text)
        if st.button(L("confirm"),type="primary"):
            st.session_state.problem=st.session_state.voice_text
            st.session_state.flow=detect_flow(st.session_state.problem)
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0; st.session_state.answers={}; st.session_state.stage="question"; st.rerun()
    if st.button(L("back")): st.session_state.stage="home"; st.rerun()

elif st.session_state.stage=="type_problem":
    st.header(L("write"))
    problem=st.text_area("अपनी समस्या बताएं / Tell us your problem",value=st.session_state.problem,height=140)
    audio=st.audio_input("🎤 या बोलें / Or speak",sample_rate=16000)
    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if h!=st.session_state.voice_hash:
            st.session_state.voice_hash=h
            t=transcribe(audio)
            if t: problem=t
    if st.button("आगे बढ़ें / Continue",type="primary"):
        if problem.strip():
            st.session_state.problem=problem.strip()
            st.session_state.flow=detect_flow(problem)
            st.session_state.questions=questions(st.session_state.flow)
            st.session_state.q_index=0; st.session_state.answers={}; st.session_state.stage="question"; st.rerun()
        else:
            st.warning("कृपया समस्या बताएं। / Please tell us the problem.")
    if st.button(L("back")): st.session_state.stage="home"; st.rerun()

elif st.session_state.stage=="question":
    q=st.session_state.questions[st.session_state.q_index]
    key,hi,en,typ=q
    qtext=hi if st.session_state.lang=="hi" else en
    st.progress(st.session_state.q_index/max(len(st.session_state.questions),1))
    st.caption(f"Step {st.session_state.q_index+1} / {len(st.session_state.questions)}")
    st.header(qtext)
    if st.button("🔊 सवाल सुनें / Hear question"): speak(qtext)

    current=st.session_state.answers.get(key,"")
    if typ=="number":
        answer=str(st.number_input("उत्तर / Answer",min_value=1,max_value=100,value=int(current or 1),key=f"n_{key}_{st.session_state.q_index}"))
    else:
        input_type="password" if typ=="aadhaar" else "tel" if typ=="mobile" else "default"
        answer=st.text_input("उत्तर / Answer",value=current,type=input_type,key=f"a_{key}_{st.session_state.q_index}")
    audio=st.audio_input("🎤 बोलकर उत्तर दें / Answer by voice",sample_rate=16000,key=f"audio_{key}_{st.session_state.q_index}")
    if audio:
        h=hashlib.sha256(audio.getvalue()).hexdigest()
        if st.session_state.get(f"h_{key}_{st.session_state.q_index}")!=h:
            st.session_state[f"h_{key}_{st.session_state.q_index}"]=h
            t=transcribe(audio)
            if t: st.session_state[f"voice_{key}_{st.session_state.q_index}"]=t
    voice=st.session_state.get(f"voice_{key}_{st.session_state.q_index}","")
    if voice:
        st.info("🎤 "+voice)
        if st.button("इस उत्तर को रखें / Use this answer"):
            answer=voice
            st.session_state.answers[key]=voice
            st.rerun()

    a,b=st.columns(2)
    with a:
        if st.button(L("back")):
            if st.session_state.q_index==0: st.session_state.stage="home"
            else: st.session_state.q_index-=1
            st.rerun()
    with b:
        if st.button(L("confirm"),type="primary"):
            answer=str(answer).strip()
            valid=True
            if not answer: st.warning("कृपया उत्तर दें। / Please provide an answer."); valid=False
            if typ=="mobile" and answer and not re.fullmatch(r"\d{10}",answer): st.error("10 अंकों का मोबाइल नंबर दें।"); valid=False
            if typ=="aadhaar" and answer and not re.fullmatch(r"\d{12}",answer.replace(" ","")): st.error("12 अंकों का आधार नंबर दें।"); valid=False
            if valid:
                st.session_state.answers[key]=answer
                st.session_state.pending=(key,answer,st.session_state.q_index)
                st.session_state.stage="confirm"; st.rerun()

elif st.session_state.stage=="confirm":
    key,answer,i=st.session_state.pending
    q=st.session_state.questions[i]
    qtext=q[1] if st.session_state.lang=="hi" else q[2]
    st.header("कृपया पुष्टि करें / Please confirm")
    st.write("**"+qtext+"**")
    st.markdown(f'<div class="confirm"><h3>{answer}</h3></div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    with a:
        if st.button("✏️ बदलें / Change"): st.session_state.stage="question"; st.rerun()
    with b:
        if st.button("✅ हाँ, सही है / Yes, correct",type="primary"):
            st.session_state.q_index+=1
            st.session_state.stage="review" if st.session_state.q_index>=len(st.session_state.questions) else "question"
            st.rerun()

elif st.session_state.stage=="review":
    st.header("🔎 अंतिम जांच / Final review")
    st.subheader(title(st.session_state.flow))
    for q in st.session_state.questions:
        key,hi,en,typ=q
        label=hi if st.session_state.lang=="hi" else en
        st.write(f"**{label}:** {st.session_state.answers.get(key,'')}")
    if st.button("✏️ जानकारी बदलें / Edit"):
        st.session_state.q_index=0; st.session_state.stage="question"; st.rerun()
    if st.button("✅ पुष्टि करें और आवेदन बनाएं / Generate application",type="primary"):
        st.session_state.stage="application"; st.rerun()

elif st.session_state.stage=="application":
    st.header("📄 "+title(st.session_state.flow))
    st.success("आपका आवेदन तैयार है। / Your application is ready.")
    st.write("**दिनांक / Date:** "+date.today().strftime("%d-%m-%Y"))
    for q in st.session_state.questions:
        key,hi,en,typ=q
        label=hi if st.session_state.lang=="hi" else en
        st.write(f"**{label}:** {st.session_state.answers.get(key,'')}")
    st.markdown("---")
    st.write("उपरोक्त विषय में आवश्यक जांच कर नियमानुसार कार्रवाई करने का अनुरोध है।" if st.session_state.lang=="hi"
             else "I request the concerned authority to examine the matter and take necessary action as per applicable rules.")
    pdf=pdf_file()
    st.download_button(L("download"),data=pdf,file_name="citizen_application.pdf",mime="application/pdf",use_container_width=True)
    if st.button(L("new"),type="primary"):
        st.session_state.clear()
        st.rerun()
