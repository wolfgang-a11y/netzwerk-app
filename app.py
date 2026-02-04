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
st.set_page_config(page_title="Trust Graph | Netzwerk", page_icon="🔐", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #D4AF37 !important; color: black !important; font-weight: bold; height: 3.5em; border: none; }
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
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
                birth_val = props["Birth Date"]["rich_text"][0]["text"]["content"] if "Birth Date" in props and props["Birth Date"].get("rich_text") else ""
                members.append({
                    "Name": props["Name"]["title"][0]["text"]["content"] if props.get("Name") and props["Name"]["title"] else "Unbekannt",
                    "Email": email_val.lower(),
                    "Geburtstag": birth_val,
                    "Code": slug_val
                })
            return pd.DataFrame(members)
        return pd.DataFrame(columns=["Name", "Email", "Geburtstag", "Code"])
    except:
        return pd.DataFrame(columns=["Name", "Email", "Geburtstag", "Code"])

def add_member_to_notion(full_name, email, phone, inviter_name, slug, birth_date_obj):
    url = "https://api.notion.com/v1/pages"
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    # Wir formatieren das Datum hier als deutschen Text
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
        else:
            inviter_row = df[df['Code'] == invite_slug.lower()] if not df.empty else pd.DataFrame()
            inviter_name = inviter_row.iloc[0]['Name'] if not inviter_row.empty else None

        if inviter_name:
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EXKLUSIVE EINLADUNG VON</p><h2 style='margin:0;'>{inviter_name}</h2></div>", unsafe_allow_html=True)
            with st.form("join"):
                col1, col2 = st.columns(2)
                with col1: vorname = st.text_input("Vorname")
                with col2: nachname = st.text_input("Nachname")
                
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer (+49...)")
                
                # Datum-Picker bleibt (bequem für Nutzer), aber wir speichern es als Text
                birth_date_picker = st.date_input("Geburtsdatum", min_value=datetime(1940, 1, 1), max_value=datetime.now())
                
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
                            
                            # Hier wird das Datum-Objekt an die Speicherfunktion übergeben
                            res = add_member_to_notion(full_name, email.lower().strip(), clean_phone, inviter_name, new_slug, birth_date_picker)
                            
                            if res.status_code == 200:
                                st.success(f"Willkommen, {vorname}!")
                                final_link = f"https://vanselow-network.streamlit.app/?invite={new_slug}"
                                st.code(final_link)
                                st.image(get_qr(final_link), width=200)
                                st.balloons()
                            else:
                                st.error("Fehler beim Speichern. Hast du 'Birth Date' in Notion auf Text umgestellt?")
                                st.write("Grund:", res.text)
                    else: st.error("Bitte alles ausfüllen.")
        else: st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über persönlichen Link möglich.")

with tab2:
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.metric("Mitglieder", len(df))
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Liste laden", data=csv, file_name="export.csv")
