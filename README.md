# जनसेवक बिहार — Citizen Assistance & Service Facilitation System

A mobile-friendly and web-friendly Streamlit prototype for the Bihar Food & Consumer Protection Department concept.

## What is included

- Bihar Government logo on the login and service screens
- Responsive mobile/desktop UI
- Citizen login prototype with OTP flow (demo OTP: `123456`)
- Registered mobile number carried into the application workflow
- Hindi/English toggle
- Voice input and speech recognition
- Guided service flows for ration-card and consumer/food complaints
- Confirmation after each answer
- Formal A4 citizen application
- 6-character request ID: exactly 2 uppercase letters + 4 digits, e.g. `AB4827`
- Date and time (IST) captured when the application is generated
- PDF generation with bundled Devanagari fonts
- Print application button
- SMS acknowledgement integration through MSG91 Flow API
- Demo SMS mode when MSG91 credentials are not configured
- Basic in-session application status screen
- Footer: `सरकार आपके द्वार`

## Important prototype note

This is a demonstration/prototype. Do not enter real Aadhaar numbers or other sensitive citizen data in a public test deployment. A production system should use a secure backend, database, real OTP authentication, role-based access, audit logs, encryption, document storage, and official department integrations.

## Run locally

Use Python 3.12 or another Python version supported by your Streamlit deployment.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown by Streamlit in Chrome/Safari on the laptop or phone.

## Demo login

1. Enter any valid 10-digit Indian mobile number beginning with 6-9.
2. Tap `OTP भेजें`.
3. Enter demo OTP `123456`.
4. Continue to the citizen dashboard.

The mobile number is retained as the registered mobile for the prototype and is carried into the application.

## Real SMS setup

The code uses the MSG91 Flow API. Create an approved DLT SMS template containing a variable for the request ID. The app sends `VAR1` as the request ID.

In Streamlit Community Cloud, put the following in the app's Secrets settings, not in GitHub:

```toml
MSG91_AUTH_KEY = "YOUR_MSG91_AUTH_KEY"
MSG91_TEMPLATE_ID = "YOUR_APPROVED_DLT_TEMPLATE_ID"
```

The intended Hindi acknowledgement is:

`आपका अनुरोध क्रमांक {{VAR1}} है। आपकी समस्या के समाधान हेतु हमारी टीम इस पर कार्य कर रही है और इसे यथाशीघ्र निस्तारित करने का प्रयास किया जा रहा है। - खाद्य एवं उपभोक्ता संरक्षण विभाग, बिहार सरकार`

Without these secrets, the app runs in demo SMS mode and shows the exact message that would be sent, without sending a real SMS.

## Request ID

The prototype generates an ID in the format `AA9999`, such as `BJ7514`.

Because this prototype does not use a central database, global uniqueness is not mathematically guaranteed. Production must reserve/check IDs centrally before assignment.

## Streamlit Community Cloud

Deploy `app.py` from the repository root. Community Cloud reads the repository, installs `requirements.txt`, and runs the app. When the GitHub repository is updated, the deployed app is updated automatically.
