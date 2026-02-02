import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

# Design
st.set_page_config(page_title="Trust Graph", page_icon="🔐")
st.markdown("<style>.stButton>button {width:100%; background-color:#D4AF37; color:black; font-weight:bold;}</style>", unsafe_allow_html=True)

# Verbindung
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Mitglieder", ttl=0)
except Exception as e:
    st.error("Verbindung zum Google Sheet fehlgeschlagen. Bitte prüfe die Secrets.")
    st.stop()

# URL Parameter
invite_slug = st.query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Beitritt", "⚙️ Admin"])

with tab1:
    if invite_slug:
        inviter_row = df[df['slug'] == invite_slug]
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.subheader(f"Einladung von {inviter['name']}")
            with st.form("join"):
                name = st.text_input("Name")
                email = st.text_input("E-Mail")
                phone = st.text_input("Handy")
                if st.form_submit_button("Beitreten"):
                    if name and email and phone:
                        if email in df['email'].values:
                            st.error("Bereits registriert.")
                        else:
                            # Neuen Member anlegen
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            new_entry = pd.DataFrame([{"id": str(uuid.uuid4()), "name": name, "email": email, "phone": str(phone), "invited": inviter['id'], "slug": new_slug, "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}])
                            updated_df = pd.concat([df, new_entry], ignore_index=True)
                            conn.update(worksheet="Mitglieder", data=updated_df)
                            st.success("Erfolg!")
                            st.code(f"https://vanselow-network-final.streamlit.app/?invite={new_slug}")
                    else:
                        st.warning("Felder ausfüllen.")
        else:
            st.error("Link ungültig.")
    else:
        st.info("Zutritt nur mit Link.")

with tab2:
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.write(df)
