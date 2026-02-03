import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

st.set_page_config(page_title="Trust Graph", page_icon="🔐")

# --- VERBINDUNG ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Mitglieder", ttl=0)
    df = df.dropna(how='all')
except Exception as e:
    st.error("❌ Verbindung fehlgeschlagen!")
    st.code(str(e))
    st.stop()

# --- APP LOGIK ---
invite_slug = st.query_params.get("invite", None)
tab1, tab2 = st.tabs(["🤝 Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        inviter_row = df[df['slug'].astype(str) == str(invite_slug)]
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.subheader(f"Einladung von {inviter['name']}")
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail")
                phone = st.text_input("Handy")
                if st.form_submit_button("JETZT BEITRETEN"):
                    if name and email and phone:
                        if email in df['email'].astype(str).values:
                            st.error("E-Mail existiert schon.")
                        else:
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            new_member = pd.DataFrame([{"id": str(uuid.uuid4()), "name": name, "email": email, "phone": str(phone), "invited": str(inviter['id']), "slug": new_slug, "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")}])
                            updated_df = pd.concat([df, new_member], ignore_index=True)
                            conn.update(worksheet="Mitglieder", data=updated_df)
                            st.success("Erfolg!")
                            st.code(f"https://vanselow-network.streamlit.app/?invite={new_slug}")
        else: st.error("Link ungültig.")
    else: st.info("Zutritt nur mit Einladung.")

with tab2:
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.dataframe(df)
