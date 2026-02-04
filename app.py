import streamlit as st
import pandas as pd
import uuid
import qrcode
import requests
import re
from io import BytesIO
from datetime import datetime

# --- NOTION KONFIGURATION ---
NOTION_TOKEN = "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"
DATABASE_ID = "2fc7b7e3c9cd809d993feb456d8d8c01"

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- SETUP & DESIGN ---
st.set_page_config(
    page_title="Direktion Vanselow | Netzwerk", 
    page_icon="🔐", 
    layout="centered"
)

# Das Bild, das wir bei GitHub hochgeladen haben (Link zur 'Raw'-Datei)
GARY_IMAGE_URL = "https://raw.githubusercontent.com/wolfgang-a11y/netzwerk-app/main/gary.png"

# Meta-Daten für die "sexy" Vorschau in WhatsApp/Telegram
st.markdown(
    f"""
    <head>
        <meta property="og:title" content="Einladung von Direktion Vanselow" />
        <meta property="og:description" content="Exklusiver Zugang zum geschlossenen Netzwerk." />
        <meta property="og:image" content="{GARY_IMAGE_URL}" />
        <meta property="og:type" content="website" />
    </head>
    """, unsafe_allow_html=True
)

st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #D4AF37 !important; color: black !important; font-weight: bold; height: 3.5em; border: none; border-radius: 8px; }
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {
        padding: 30px; 
        border: 1px solid #D4AF37; 
        border-radius: 15px; 
        background-color: #1a1c23; 
        text-align: center; 
        margin-bottom: 25px;
    }
    .gary-img {
        border-radius: 50%;
        border: 3px solid #D4AF37;
        margin-bottom: 15px;
        object-fit: cover;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELFER-FUNKTIONEN ---
def format_phone(number):
    clean = re.sub(r'[^0-9+]', '', number)
    if clean.startswith('0') and not clean.startswith('00'):
        clean = '+49' + clean[1:]
    return clean

def get_members_from_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            members = []
            for row in data["results"]:
                props = row["properties"]
                email_val = props["Email"]["email"] if "Email" in props and props["Email"]["email"] else ""
                slug_val = props["Slug"]["rich_text"][0]["text"]["content"] if "Slug" in props and props["Slug"].get("rich_text") else ""
                members.append({
                    "Name": props["Name"]["title"][0]["text"]["content"] if props.get("Name") and props["Name"]["title"] else "Unbekannt",
                    "Email": email_val.lower().strip(),
                    "Code": slug_val
                })
            return pd.DataFrame(members)
        return pd.DataFrame(columns=["Name", "Email", "Code"])
    except:
        return pd.DataFrame(columns=["Name", "Email", "Code"])

def add_member_to_notion(full_name, email, phone, inviter_name, slug, birth_date_obj):
    url = "https://api.notion.com/v1/pages"
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    birth_date_str = birth_date_obj.strftime("%d.%m.%Y")
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": full_name}}]},
            "Email": {"email": email},
            "Handy": {"phone_number": phone},
            "Einlader": {"rich_text": [{"text": {"content": inviter_name}}]},
            "Slug": {"rich_text": [{"text": {"content": slug}}]},
            "Datum": {"rich_text": [{"text": {"content": now_str}}]},
            "Birth Date": {"rich_text": [{"text": {"content": birth_date_str}}]}
        }
    }
    return requests.post(url, headers=headers, json=payload)

def get_qr(url):
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# --- APP LOGIK ---
df = get_members_from_notion()
invite_slug = st.query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        if invite_slug.lower() == "gary":
            inviter_name = "Direktion Vanselow"
            show_gary_pic = True
        else:
            inviter_row = df[df['Code'] == invite_slug.lower()] if not df.empty else pd.DataFrame()
            inviter_name = inviter_row.iloc[0]['Name'] if not inviter_row.empty else None
            show_gary_pic = False

        if inviter_name:
            # Edle Einladungs-Box mit Bild (falls Gary einlädt)
            st.markdown("<div class='inviter-box'>", unsafe_allow_html=True)
            if show_gary_pic:
                st.image(GARY_IMAGE_URL, width=120)
            st.markdown(f"<p style='color:#888;margin:0;'>EXKLUSIVE EINLADUNG VON</p><h2 style='margin:0;'>{inviter_name}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                st.write("### Deine Daten")
                col1, col2 = st.columns(2)
                with col1: vorname = st.text_input("Vorname", placeholder="z.B. Max")
                with col2: nachname = st.text_input("Nachname", placeholder="z.B. Mustermann")
                email = st.text_input("E-Mail Adresse", placeholder="name@beispiel.de")
                phone = st.text_input("Handynummer", placeholder="+49 173 1234567")
                birth_date_picker = st.date_input("Geburtsdatum", min_value=datetime(1940, 1, 1), max_value=datetime.now(), format="DD.MM.YYYY")
                
                if st.form_submit_button("JETZT BEITRETEN"):
                    clean_phone = format_phone(phone)
                    if vorname and nachname and email and phone:
                        if len(re.sub(r'[^0-9]', '', clean_phone)) < 10:
                            st.error("Bitte gib eine gültige Handynummer ein.")
                        elif not df.empty and email.lower().strip() in df['Email'].values:
                            st.warning("Bereits registriert!")
                            user_slug = df[df['Email'] == email.lower().strip()].iloc[0]['Code']
                            st.code(f"https://vanselow-network.streamlit.app/?invite={user_slug}")
                        else:
                            full_name = f"{vorname.strip()} {nachname.strip()}"
                            new_slug = re.sub(r'[^a-zA-Z]', '', vorname).lower()
                            res = add_member_to_notion(full_name, email.lower().strip(), clean_phone, inviter_name, new_slug, birth_date_picker)
                            if res.status_code == 200:
                                st.success(f"Willkommen im Team, {vorname}!")
                                final_link = f"https://vanselow-network.streamlit.app/?invite={new_slug}"
                                st.divider()
                                st.write("### Dein Einladungs-Link:")
                                st.code(final_link)
                                st.image(get_qr(final_link), width=200)
                                st.balloons()
                            else:
                                st.error("Fehler beim Speichern.")
                    else: st.error("Bitte alles ausfüllen.")
        else: st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über persönlichen Link möglich.")

with tab2:
    st.title("Admin-Panel")
    if st.sidebar.text_input("Admin-Passwort", type="password") == "gary123":
        st.metric("Mitglieder", len(df))
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Liste als CSV laden", data=csv, file_name="export.csv")
