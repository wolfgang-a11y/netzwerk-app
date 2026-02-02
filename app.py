import streamlit as st
import pandas as pd
import sqlite3
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
        .main { background-color: #0e1117; }
        .stButton>button { 
            width: 100%; border-radius: 5px; height: 3em; 
            background-color: #D4AF37; color: black; border: none; font-weight: bold;
        }
        .stButton>button:hover { background-color: #C5A028; color: white; }
        .stTextInput>div>div>input { background-color: #1a1c23; color: white; border: 1px solid #333; }
        .inviter-box { 
            padding: 20px; border: 1px solid #D4AF37; border-radius: 10px; 
            background-color: #1a1c23; text-align: center; margin-bottom: 25px;
        }
        h1, h2, h3 { color: #D4AF37 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- DATENBANK FUNKTIONEN ---
DB_NAME = "network_final.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (id TEXT PRIMARY KEY, display_name TEXT, email TEXT UNIQUE, 
                  phone TEXT UNIQUE, invited_by_id TEXT, friendly_slug TEXT UNIQUE, 
                  created_at TIMESTAMP)''')
    
    # Gary Vanselow als Ursprung prüfen/anlegen
    c.execute("SELECT COUNT(*) FROM members WHERE id = 'ROOT_GARY'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)", 
                  ('ROOT_GARY', 'Gary Vanselow', 'gary@vanselow.de', '000', 'NONE', 'Gary', datetime.now()))
    conn.commit()
    conn.close()

def get_member_by_slug(slug):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM members WHERE friendly_slug = ?", conn, params=(slug,))
    conn.close()
    return df.iloc[0] if not df.empty else None

def add_member(name, email, phone, inviter_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Friendly Slug generieren (Vorname + Check)
    base_slug = re.sub(r'[^a-zA-Z]', '', name.split()[0])
    slug = base_slug
    counter = 2
    while True:
        c.execute("SELECT COUNT(*) FROM members WHERE friendly_slug = ?", (slug,))
        if c.fetchone()[0] == 0: break
        slug = f"{base_slug}{counter}"
        counter += 1
    
    new_id = str(uuid.uuid4())
    try:
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)", 
                  (new_id, name, email, phone, inviter_id, slug, datetime.now()))
        conn.commit()
        return True, slug
    except sqlite3.IntegrityError:
        return False, "Diese E-Mail oder Nummer ist bereits registriert."
    finally:
        conn.close()

# --- UI LOGIK ---
local_css()
init_db()

query_params = st.query_params
invite_slug = query_params.get("invite", None)

tab1, tab2 = st.tabs(["🤝 Netzwerk-Beitritt", "⚙️ Verwaltung"])

with tab1:
    if invite_slug:
        inviter = get_member_by_slug(invite_slug)
        if inviter is not None:
            st.markdown(f"""<div class='inviter-box'>
                <p style='margin:0; font-size: 0.9em; color: #888;'>PERSÖNLICHE EINLADUNG VON</p>
                <h2 style='margin:0;'>{inviter['display_name']}</h2>
            </div>""", unsafe_allow_html=True)
            
            st.markdown("### Werde Teil des Netzwerks")
            st.write("Bitte gib deine Daten an, um deinen persönlichen Zugang zu generieren.")
            
            with st.form("join_form"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer")
                submit = st.form_submit_button("JETZT BEITRETEN")
                
                if submit:
                    if name and email and phone:
                        success, result = add_member(name, email, phone, inviter['id'])
                        if success:
                            st.success("Erfolgreich registriert!")
                            # Generiere Link (Ersetze 'deine-app.streamlit.app' später durch deine echte URL)
                            link = f"https://vanselow-network.streamlit.app/?invite={result}"   

                            st.markdown("---")
                            st.subheader("Dein persönlicher Einladungs-Link:")
                            st.code(link)
                            
                            qr = qrcode.make(link)
                            buf = BytesIO()
                            qr.save(buf, format="PNG")
                            st.image(buf.getvalue(), caption="Dein persönlicher QR-Code", width=200)
                            st.balloons()
                        else:
                            st.error(result)
                    else:
                        st.warning("Bitte fülle alle Felder aus.")
        else:
            st.error("Der Einladungslink ist ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        st.info("Der Beitritt ist nur über eine persönliche Einladung eines bestehenden Mitglieds möglich.")

with tab2:
    st.subheader("Admin-Bereich")
    pw = st.text_input("Passwort", type="password")
    if pw == "gary123": # Dein Admin-Passwort
        conn = sqlite3.connect(DB_NAME)
        df_all = pd.read_sql_query("SELECT * FROM members", conn)
        conn.close()
        
        st.markdown("### Mitglieder & Stammbaum")
        
        # Namen bearbeiten
        st.write("---")
        member_to_edit = st.selectbox("Mitglied umbenennen (z.B. Direktion Vanselow)", df_all['display_name'].tolist())
        new_name = st.text_input("Neuer Anzeigename")
        if st.button("Namen aktualisieren"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE members SET display_name = ? WHERE display_name = ?", (new_name, member_to_edit))
            conn.commit()
            conn.close()
            st.success("Aktualisiert!")
            st.rerun()

        st.write("---")
        # Visualisierung wer wen gebracht hat
        for _, row in df_all.iterrows():
            if row['invited_by_id'] != 'NONE':
                inviter_row = df_all[df_all['id'] == row['invited_by_id']]
                inv_name = inviter_row['display_name'].values[0] if not inviter_row.empty else "Unbekannt"
                st.write(f"👤 **{row['display_name']}** ← eingeladen von: {inv_name}")
            else:
                st.write(f"👑 **{row['display_name']}** (Stammbaumhalter)")
