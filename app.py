import streamlit as st
import pandas as pd
import sqlite3
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

# --- SETUP & DESIGN ---
st.set_page_config(page_title="Trust Graph | Exklusiv", page_icon="🔐")

st.markdown("""
    <style>
    .stButton>button {width:100%; background-color:#D4AF37 !important; color:black !important; font-weight:bold; height:3em;}
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
    </style>
""", unsafe_allow_html=True)

# --- LOKALE DATENBANK (SQLITE) ---
def init_db():
    conn = sqlite3.connect('netzwerk.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (id TEXT, name TEXT, email TEXT, phone TEXT, invited TEXT, slug TEXT, timestamp TEXT)''')
    # Gary als Startpunkt anlegen, falls leer
    c.execute("SELECT COUNT(*) FROM members")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)", 
                  ('ROOT_GARY', 'Direktion Vanselow', 'gary@vanselow.de', '0', 'NONE', 'Gary', '02.02.2026'))
    conn.commit()
    return conn

conn = init_db()

def get_df():
    return pd.read_sql_query("SELECT * FROM members", conn)

# --- APP LOGIK ---
invite_slug = st.query_params.get("invite", None)
tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    df = get_df()
    if invite_slug:
        inviter_row = df[df['slug'] == invite_slug]
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EINLADUNG VON</p><h2 style='margin:0;'>{inviter['name']}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail")
                phone = st.text_input("Handy")
                if st.form_submit_button("JETZT BEITRETEN"):
                    if name and email and phone:
                        if email in df['email'].values:
                            st.error("Bereits registriert.")
                        else:
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            # Dubletten-Check für Slug
                            if new_slug in df['slug'].values: new_slug += str(len(df))
                            
                            c = conn.cursor()
                            c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)",
                                      (str(uuid.uuid4()), name, email, phone, inviter['id'], new_slug, datetime.now().strftime("%d.%m.%Y %H:%M")))
                            conn.commit()
                            st.success(f"Willkommen, {name}!")
                            st.code(f"https://vanselow-network.streamlit.app/?invite={new_slug}")
                            st.balloons()
                            st.rerun()
                    else: st.warning("Bitte Felder ausfüllen.")
        else: st.error("Link ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Zutritt nur mit persönlichem Link möglich.")

with tab2:
    st.subheader("Admin-Bereich")
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        df = get_df()
        st.write("### Aktuelle Mitglieder")
        st.dataframe(df)
        
        # Datensicherung
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Mitgliederliste (CSV) exportieren", data=csv, file_name="netzwerk_backup.csv", mime="text/csv")
        st.caption("Tipp: Speichere diese Datei regelmäßig als Backup.")
