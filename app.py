import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
import re
from io import BytesIO
from datetime import datetime

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="The Trust Graph | Exklusiv", page_icon="🔐", layout="centered")

def local_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stButton>button { 
            width: 100%; border-radius: 5px; height: 3em; 
            background-color: #D4AF37; color: black; border: none; font-weight: bold;
        }
        .inviter-box { 
            padding: 20px; border: 1px solid #D4AF37; border-radius: 10px; 
            background-color: #1a1c23; text-align: center; margin-bottom: 25px;
        }
        h1, h2, h3 { color: #D4AF37 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS VERBINDUNG ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Liest die Daten aus dem Sheet
    return conn.read(worksheet="Mitglieder", ttl="0")

def save_data(df):
    # Speichert den gesamten Dataframe zurück ins Sheet
    conn.update(worksheet="Mitglieder", data=df)

# --- LOGIK ---
def add_member(name, email, phone, inviter_id):
    df = get_data()
    
    # Dubletten-Check
    if email in df['email'].values or phone in df['phone'].values:
        return False, "E-Mail oder Telefon bereits registriert.", None

    # Friendly Slug (Link-Name) erstellen
    base_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
    slug = base_slug
    counter = 2
    while slug in df['slug'].values:
        slug = f"{base_slug}{counter}"
        counter += 1
    
    new_id = str(uuid.uuid4())
    new_entry = pd.DataFrame([{
        "id": new_id,
        "name": name,
        "email": email,
        "phone": str(phone),
        "invited_by": inviter_id,
        "slug": slug,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }])
    
    updated_df = pd.concat([df, new_entry], ignore_index=True)
    save_data(updated_df)
    return True, slug, name

# --- UI START ---
local_css()
query_params = st.query_params
invite_slug = query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        df = get_data()
        inviter_row = df[df['slug'] == invite_slug]
        
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.markdown(f"<div class='inviter-box'><p style='color:#888;'>PERSÖNLICHE EINLADUNG VON</p><h2>{inviter['name']}</h2></div>", unsafe_allow_html=True)
            
            st.warning("⏳ Dein exklusiver Zugang ist für 12 Stunden reserviert. Bitte schließe die Anmeldung jetzt ab.")
            
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer")
                if st.form_submit_button("EINLADUNG ANNEHMEN"):
                    if name and email and phone:
                        success, res_slug, res_name = add_member(name, email, phone, inviter['id'])
                        if success:
                            st.success(f"Willkommen im Netzwerk, {res_name}!")
                            my_link = f"https://vanselow-network.streamlit.app/?invite={res_slug}"
                            
                            st.divider()
                            st.subheader("Dein persönlicher Einladungs-Link:")
                            st.info("Kopiere diesen Link oder speichere den QR-Code, um vertrauenswürdige Kontakte einzuladen.")
                            st.code(my_link)
                            
                            qr = qrcode.make(my_link)
                            buf = BytesIO()
                            qr.save(buf, format="PNG")
                            st.image(buf.getvalue(), caption="Dein Einladungs-QR-Code", width=200)
                            st.balloons()
                        else:
                            st.error(res_slug)
                    else:
                        st.error("Bitte alle Felder ausfüllen.")
        else:
            st.error("Dieser Einladungslink ist leider nicht mehr gültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Zutritt nur mit persönlicher Einladung möglich.")
        
        with st.expander("Link vergessen?"):
            mail_check = st.text_input("Gib deine registrierte E-Mail ein:")
            if st.button("Link abrufen"):
                df = get_data()
                user = df[df['email'] == mail_check]
                if not user.empty:
                    st.success(f"Willkommen zurück! Dein Einladungslink lautet:")
                    st.code(f"https://vanselow-network.streamlit.app/?invite={user.iloc[0]['slug']}")
                else:
                    st.error("Diese E-Mail ist nicht im System registriert.")

with tab2:
    pw = st.sidebar.text_input("Admin Passwort", type="password")
    if pw == "gary123":
        df = get_data()
        st.subheader("Netzwerk-Stammbaum")
        st.dataframe(df[["name", "email", "timestamp", "slug"]])
        
        st.divider()
        st.subheader("Mitglied bearbeiten")
        member_to_edit = st.selectbox("Wähle ein Mitglied", df['name'].tolist())
        new_name = st.text_input("Neuer Name (z.B. Direktion Vanselow)")
        if st.button("Namen aktualisieren"):
            df.loc[df['name'] == member_to_edit, 'name'] = new_name
            save_data(df)
            st.success("Name wurde im Google Sheet aktualisiert!")
            st.rerun()
