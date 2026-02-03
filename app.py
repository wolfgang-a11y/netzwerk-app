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
st.set_page_config(page_title="Trust Graph | Profi-Netzwerk", page_icon="🔐", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #D4AF37 !important; color: black !important; font-weight: bold; height: 3.5em; border: none; }
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
    </style>
""", unsafe_allow_html=True)

# --- HELFER-FUNKTIONEN ---
def format_phone(number):
    """Macht aus 0173... automatisch +49173..."""
    clean = re.sub(r'[^0-9+]', '', number) # Nur Zahlen und + behalten
    if clean.startswith('0') and not clean.startswith('00'):
        clean = '+49' + clean[1:]
    elif clean.startswith('00'):
        clean = '+' + clean[2:]
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
                    "name": props["Name"]["title"][0]["text"]["content"] if props.get("Name") and props["Name"]["title"] else "",
                    "email": email_val.lower(),
                    "slug": slug_val
                })
            return pd.DataFrame(members)
        return pd.DataFrame(columns=["name", "email", "slug"])
    except:
        return pd.DataFrame(columns=["name", "email", "slug"])

def add_member_to_notion(full_name, email, phone, inviter_name, slug):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": full_name}}]},
            "Email": {"email": email.lower()},
            "Handy": {"phone_number": phone},
            "Einlader": {"rich_text": [{"text": {"content": inviter_name}}]},
            "Slug": {"rich_text": [{"text": {"content": slug}}]}
        }
    }
    return requests.post(url, headers=headers, json=payload)

# --- APP LOGIK ---
df = get_members_from_notion()
invite_slug = st.query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        if invite_slug.lower() == "gary":
            inviter_name = "Direktion Vanselow"
        else:
            inviter_row = df[df['slug'] == invite_slug.lower()] if not df.empty else pd.DataFrame()
            inviter_name = inviter_row.iloc[0]['name'] if not inviter_row.empty else None

        if inviter_name:
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EINLADUNG VON</p><h2 style='margin:0;'>{inviter_name}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                col1, col2 = st.columns(2)
                with col1:
                    vorname = st.text_input("Vorname")
                with col2:
                    nachname = st.text_input("Nachname")
                
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer", placeholder="0173 1234567")
                
                if st.form_submit_button("JETZT BEITRETEN"):
                    if vorname and nachname and email and phone:
                        full_name = f"{vorname} {nachname}"
                        clean_phone = format_phone(phone)
                        clean_email = email.lower().strip()
                        
                        if not df.empty and clean_email in df['email'].values:
                            st.warning("Bereits registriert!")
                            user_slug = df[df['email'] == clean_email].iloc[0]['slug']
                            link = f"https://vanselow-network.streamlit.app/?invite={user_slug}"
                            st.code(link)
                        else:
                            # Slug generieren (nur Vorname)
                            new_slug = re.sub(r'[^a-zA-Z]', '', vorname).lower()
                            # Falls Slug existiert, Nachname-Anfang anhängen
                            if not df.empty and new_slug in df['slug'].values:
                                new_slug += nachname[0].lower()

                            res = add_member_to_notion(full_name, clean_email, clean_phone, inviter_name, new_slug)
                            
                            if res.status_code == 200:
                                st.success(f"Willkommen, {full_name}!")
                                link = f"https://vanselow-network.streamlit.app/?invite={new_slug}"
                                st.code(link)
                                qr = qrcode.make(link)
                                buf = BytesIO()
                                qr.save(buf, format="PNG")
                                st.image(buf.getvalue(), width=200)
                                st.balloons()
                            else:
                                st.error("Fehler beim Speichern.")
                                st.write(res.text)
                    else:
                        st.warning("Bitte alle Felder ausfüllen.")
        else:
            st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über Einladung möglich.")

with tab2:
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.subheader("Live-Daten aus Notion")
        st.dataframe(df)
