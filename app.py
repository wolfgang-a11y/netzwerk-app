import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

# Design & Setup
st.set_page_config(page_title="Trust Graph", page_icon="🔐", layout="centered")

st.markdown("""
    <style>
    .stButton>button {width:100%; background-color:#D4AF37; color:black; font-weight:bold; height:3em;}
    h1, h2, h3 {color: #D4AF37 !important;}
    .inviter-box {padding:20px; border:1px solid #D4AF37; border-radius:10px; background-color:#1a1c23; text-align:center; margin-bottom:20px;}
    </style>
""", unsafe_allow_html=True)

# Verbindung zum Google Sheet
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Wir lesen das Blatt "Mitglieder"
    df = conn.read(worksheet="Mitglieder", ttl=0)
    # Entferne leere Zeilen
    df = df.dropna(how='all')
except Exception as e:
    st.error("⚠️ Verbindung zum Google Sheet nicht möglich.")
    st.info("Bitte prüfe, ob der Link in den Streamlit-Secrets korrekt (einzeilig!) hinterlegt ist.")
    st.stop()

# URL Parameter auslesen
invite_slug = st.query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        # Suche den Einlader im Sheet
        inviter_row = df[df['slug'].astype(str) == str(invite_slug)]
        
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.markdown(f"<div class='inviter-box'><p style='color:#888;margin:0;'>EINLADUNG VON</p><h2 style='margin:0;'>{inviter['name']}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join_form", clear_on_submit=True):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer")
                submit = st.form_submit_button("JETZT BEITRETEN")
                
                if submit:
                    if name and email and phone:
                        if email in df['email'].astype(str).values:
                            st.error("Diese E-Mail ist bereits registriert.")
                        else:
                            # Neuen Slug (Link-Endung) generieren
                            new_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
                            # Falls Vorname existiert, Zahl anhängen
                            temp_slug = new_slug
                            i = 2
                            while temp_slug in df['slug'].astype(str).values:
                                temp_slug = f"{new_slug}{i}"
                                i += 1
                            
                            new_member = pd.DataFrame([{
                                "id": str(uuid.uuid4()),
                                "name": name,
                                "email": email,
                                "phone": str(phone),
                                "invited": str(inviter['id']),
                                "slug": temp_slug,
                                "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                            }])
                            
                            # Daten ans Sheet senden
                            updated_df = pd.concat([df, new_member], ignore_index=True)
                            conn.update(worksheet="Mitglieder", data=updated_df)
                            
                            st.success(f"Willkommen im Netzwerk, {name}!")
                            final_link = f"https://vanselow-network.streamlit.app/?invite={temp_slug}"
                            st.code(final_link)
                            
                            # QR Code
                            qr = qrcode.make(final_link)
                            buf = BytesIO()
                            qr.save(buf, format="PNG")
                            st.image(buf.getvalue(), width=200)
                            st.balloons()
                    else:
                        st.warning("Bitte alle Felder ausfüllen.")
        else:
            st.error("Dieser Einladungslink ist leider ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Beitritt nur über einen persönlichen Einladungslink möglich.")

with tab2:
    st.subheader("Admin-Bereich")
    if st.sidebar.text_input("Passwort", type="password") == "gary123":
        st.write("### Aktuelle Mitgliederliste")
        st.dataframe(df)
        
        st.divider()
        st.write("### Namen anpassen")
        member_to_rename = st.selectbox("Mitglied wählen", df['name'].tolist())
        new_name_text = st.text_input("Neuer Name / Titel")
        if st.button("Speichern"):
            df.loc[df['name'] == member_to_rename, 'name'] = new_name_text
            conn.update(worksheet="Mitglieder", data=df)
            st.success("Aktualisiert!")
            st.rerun()
