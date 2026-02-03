import streamlit as st
import pandas as pd
import uuid
import qrcode
import requests
import re
from io import BytesIO
from datetime import datetime

# --- NOTION KONFIGURATION (JETZT MIT DER KORREKTEN ID) ---
NOTION_TOKEN = "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"
DATABASE_ID = "2fc7b7e3c9cd80c095ffeb71649ed94d"

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- SETUP & DESIGN ---
st.set_page_config(page_title="Trust Graph | Notion Live", page_icon="🔐", layout="centered")

st.markdown("""
    <style>
    .stButton>button {width:100%; background-color:#D4AF37 !important; color:black !important; font-weight:bold; height:3em;}
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
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
                members.append({
                    "name": props["Name"]["title"][0]["text"]["content"] if props.get("Name") and props["Name"]["title"] else "",
                    "email": props["Email"]["email"] if props.get("Email") and props["Email"]["email"] else "",
                    "slug": props["Slug"]["rich_text"][0]["text"]["content"] if props.get("Slug") and props["Slug"]["rich_text"] else ""
                })
            return pd.DataFrame(members)
        else:
            return pd.DataFrame(columns=["name", "email", "slug"])
    except:
        return pd.DataFrame(columns=["name", "email", "slug"])

def add_member_to_notion(name, email, phone, inviter_name, slug):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": name}}]},
            "Email": {"email": email},
            "Handy": {"rich_text": [{"text": {"content": phone}}]},
            "Einlader": {"rich_text": [{"text": {"content": inviter_name}}]},
            "Slug": {"rich_text": [{"text": {"content": slug}}]}
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    return response

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
            inviter_row = df[df['slug'] == invite_slug] if not df.empty else pd.DataFrame()
            inviter_name = inviter_row.iloc[0]['name'] if not inviter_row.empty else None

        if inviter_name:
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EINLADUNG VON</p><h2 style='margin:0;'>{inviter_name}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail")
                phone = st.text_input("Handynummer")
                if st.form_submit_button("JETZT BEITRETEN"):
                    if name and email and phone:
                        if not df.empty and email in df['email'].values:
                            st.warning("Bereits registriert!")
                            user_slug = df[df['email'] == email].iloc[0]['slug']
                            link = f"https://vanselow-network.streamlit.app/?invite={user_slug}"
                            st.code(link)
                            st.image(get_qr(link), width=200)
                        else:
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            res = add_member_to_notion(name, email, phone, inviter_name, new_slug)
                            
                            if res.status_code == 200:
                                st.success(f"Willkommen im Netzwerk, {name}!")
                                link = f"https://vanselow-network.streamlit.app/?invite={new_slug}"
                                st.code(link)
                                st.image(get_qr(link), width=200)
                                st.balloons()
                                st.info("Erfolgreich in Notion gespeichert.")
                            else:
                                st.error("Fehler beim Speichern.")
                                st.write("Grund:", res.text)
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
