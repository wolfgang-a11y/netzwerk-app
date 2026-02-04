import streamlit as st
import pandas as pd
import uuid
import qrcode
import requests
import re
from io import BytesIO
from datetime import datetime

# --- NOTION KONFIGURATION (KORRIGIERTE ID) ---
NOTION_TOKEN = "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"
DATABASE_ID = "2fc7b7e3c9cd80c095ffeb71649ed94d" # ID aus deinem letzten Link!

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- SETUP & DESIGN ---
st.set_page_config(page_title="Trust Graph | Network Control", page_icon="🔐", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #D4AF37 !important; color: black !important; font-weight: bold; height: 3.5em; border: none; }
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
    .stDataFrame {background-color: #1a1c23; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- NOTION FUNKTIONEN ---
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
                phone_val = props["Handy"]["phone_number"] if "Handy" in props and props["Handy"]["phone_number"] else ""
                inviter_val = props["Einlader"]["rich_text"][0]["text"]["content"] if "Einlader" in props and props["Einlader"].get("rich_text") else ""
                slug_val = props["Slug"]["rich_text"][0]["text"]["content"] if "Slug" in props and props["Slug"].get("rich_text") else ""
                
                members.append({
                    "Name": props["Name"]["title"][0]["text"]["content"] if props.get("Name") and props["Name"]["title"] else "Unbekannt",
                    "Email": email_val.lower(),
                    "Handy": phone_val,
                    "Eingeladen von": inviter_val,
                    "Code/Slug": slug_val
                })
            return pd.DataFrame(members)
        return pd.DataFrame(columns=["Name", "Email", "Handy", "Eingeladen von", "Code/Slug"])
    except:
        return pd.DataFrame(columns=["Name", "Email", "Handy", "Eingeladen von", "Code/Slug"])

def add_member_to_notion(full_name, email, phone, inviter_name, slug):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": full_name}}]},
            "Email": {"email": email},
            "Handy": {"phone_number": phone},
            "Einlader": {"rich_text": [{"text": {"content": inviter_name}}]},
            "Slug": {"rich_text": [{"text": {"content": slug}}]}
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
            inviter_row = df[df['Code/Slug'] == invite_slug.lower()] if not df.empty else pd.DataFrame()
            inviter_name = inviter_row.iloc[0]['Name'] if not inviter_row.empty else None

        if inviter_name:
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EXKLUSIVE EINLADUNG VON</p><h2 style='margin:0;'>{inviter_name}</h2></div>", unsafe_allow_html=True)
            with st.form("join"):
                col1, col2 = st.columns(2)
                with col1: vorname = st.text_input("Vorname")
                with col2: nachname = st.text_input("Nachname")
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer (+49...)")
                if st.form_submit_button("JETZT BEITRETEN"):
                    if vorname and nachname and email and phone:
                        full_name = f"{vorname.strip()} {nachname.strip()}"
                        clean_email = email.lower().strip()
                        if not df.empty and clean_email in df['Email'].values:
                            st.warning("Bereits registriert!")
                            user_slug = df[df['Email'] == clean_email].iloc[0]['Code/Slug']
                            st.code(f"https://vanselow-network.streamlit.app/?invite={user_slug}")
                        else:
                            new_slug = re.sub(r'[^a-zA-Z]', '', vorname).lower()
                            res = add_member_to_notion(full_name, clean_email, phone, inviter_name, new_slug)
                            if res.status_code == 200:
                                st.success(f"Willkommen, {vorname}!")
                                final_link = f"https://vanselow-network.streamlit.app/?invite={new_slug}"
                                st.code(final_link)
                                st.image(get_qr(final_link), width=200)
                                st.balloons()
                            else:
                                st.error("Fehler beim Speichern.")
                                st.write(res.text)
                    else: st.error("Bitte alles ausfüllen.")
        else: st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über persönlichen Link möglich.")

with tab2:
    st.title("Admin-Control-Panel")
    if st.sidebar.text_input("Admin-Passwort", type="password") == "gary123":
        if not df.empty:
            st.metric("Gesamtmitglieder", len(df))
            
            # Suchfunktion für Gary
            search = st.text_input("🔍 Mitglied suchen (Name oder E-Mail)")
            if search:
                filtered_df = df[df['Name'].str.contains(search, case=False) | df['Email'].str.contains(search, case=False)]
            else:
                filtered_df = df
            
            st.write("### Mitgliederübersicht")
            st.dataframe(filtered_df, use_container_width=True)
            
            # CSV Download für Excel
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Liste als CSV für Excel laden", data=csv, file_name="netzwerk_export.csv")
        else:
            st.info("Noch keine Mitglieder in der Datenbank.")
