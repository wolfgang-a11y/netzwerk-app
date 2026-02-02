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
    return conn.read(worksheet="Mitglieder", ttl="0")

def save_data(df):
    conn.update(worksheet="Mitglieder", data=df)

# --- LOGIK ---
def add_member(name, email, phone, inviter_id):
    df = get_data()
    
    if email in df['email'].values or str(phone) in df['phone'].astype(str).values:
        return False, "E-Mail oder Telefon bereits registriert.", None

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
        "invited": inviter_id,
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
    df = get_data()
    if invite_slug:
        inviter_row = df[df['slug'] == invite_slug]
        
        if not inviter_row.empty:
            inviter = inviter_row.iloc[0]
            st.markdown(f"<div class='inviter-box'><p style='color:#888;'>PERSÖNLICHE EINLADUNG VON</p><h2>{inviter['name']}</h2></div>", unsafe_allow_html=True)
            
            with st.form("join"):
                name = st.text_input("Vor- & Nachname")
                email = st.text_input("E-Mail Adresse")
                phone = st.text_input("Handynummer")
                if st.form_submit_button("EINLADUNG ANNEHMEN"):
                    if name and email and phone:
                        success, res_slug, res_name = add_member(name, email, phone, inviter['id'])
                        if success:
                            st.success(f"Willkommen, {res_name}!")
                            my_link = f"https://vanselow-network.streamlit.app/?invite={res_slug}"
                            st.code(my_link)
                            qr = qrcode.make(my_link)
                            buf = BytesIO()
                            qr.save(buf, format="PNG")
                            st.image(buf.getvalue(), width=200)
                            st.balloons()
                        else:
                            st.error(res_slug)
        else:
            st.error("Dieser Einladungslink ist ungültig.")
    else:
        st.title("🔐 Geschlossenes System")
        with st.expander("Link vergessen?"):
            mail_check = st.text_input("E-Mail Adresse:")
            if st.button("Link suchen"):
                user = df[df['email'] == mail_check]
                if not user.empty:
                    st.code(f"https://vanselow-network.streamlit.app/?invite={user.iloc[0]['slug']}")
                else:
                    st.error("Nicht gefunden.")

with tab2:
    pw = st.sidebar.text_input("Admin Passwort", type="password")
    if pw == "gary123":
        df = get_data()
        st.subheader("Mitglieder")
        st.dataframe(df)
        
        st.divider()
        member_to_edit = st.selectbox("Mitglied wählen", df['name'].tolist())
        new_name_val = st.text_input("Neuer Name")
        if st.button("Aktualisieren"):
            df.loc[df['name'] == member_to_edit, 'name'] = new_name_val
            save_data(df)
            st.success("Aktualisiert!")
            st.rerun()
