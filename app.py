import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

# --- KONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1B5xOILihJE6C9syNcEGu3eGps608_Z0nx3tK2uD_btQ/edit?usp=sharing"

st.set_page_config(page_title="Trust Graph", page_icon="🔐", layout="centered")

# Design
st.markdown("""
    <style>
    .stButton>button {width:100%; background-color:#D4AF37; color:black; font-weight:bold; height:3em;}
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
    </style>
""", unsafe_allow_html=True)

# Verbindung direkt über die URL (OHNE SECRETS)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df = df.dropna(how='all')
except Exception as e:
    st.error("Verbindung zum Google Sheet fehlgeschlagen.")
    st.write("Technischer Fehler:", e)
    st.stop()

# --- APP LOGIK ---
invite_slug = st.query_params.get("invite", None)
tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        inviter_row = df[df['slug'].astype(str) == str(invite_slug)]
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EINLADUNG VON</p><h2 style='margin:0;'>{inviter['name']}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail")
                phone = st.text_input("Handynummer")
                if st.form_submit_button("JETZT BEITRETEN"):
                    if name and email and phone:
                        if email in df['email'].astype(str).values:
                            st.error("Bereits registriert.")
                        else:
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            new_member = pd.DataFrame([{
                                "id": str(uuid.uuid4()), "name": name, "email": email, "phone": str(phone),
                                "invited": str(inviter['id']), "slug": new_slug, "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                            }])
                            updated_df = pd.concat([df, new_member], ignore_index=True)
                            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=updated_df)
                            st.success("Erfolg!")
                            st.code(f"https://vanselow-network.streamlit.app/?invite={new_slug}")
                            st.balloons()
        else: st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über persönlichen Link.")

with tab2:
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.dataframe(df)
