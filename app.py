Wir knacken das jetzt. Wenn die rote Meldung "Verbindung zum Google Sheet nicht möglich" kommt, dann blockt Google den Zugriff ab.

Damit wir nicht länger im Dunkeln tappen, habe ich den Code jetzt so umgebaut, dass er uns den exakten Fehler anzeigt, den Google ausgibt (z.B. "403 Forbidden" oder "404 Not Found").

Schritt 1: Prüfe deine requirements.txt (Ganz wichtig!)

Geh auf GitHub in die Datei requirements.txt. Dort müssen diese Zeilen stehen:

code
Text
download
content_copy
expand_less
streamlit
pandas
qrcode
pillow
st-gsheets-connection
Schritt 2: Der neue "Diagnose-Code" für app.py

Dieser Code zeigt uns jetzt genau, was schief läuft. Ersetze alles in app.py durch diesen Block:

code
Python
download
content_copy
expand_less
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import qrcode
from io import BytesIO
from datetime import datetime
import re

st.set_page_config(page_title="Trust Graph", page_icon="🔐")

# --- VERBINDUNG MIT DIAGNOSE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Mitglieder", ttl=0)
    df = df.dropna(how='all')
except Exception as e:
    st.error("❌ Verbindung fehlgeschlagen!")
    st.warning("Hier ist der technische Fehler für den Support (mich):")
    st.code(str(e)) # Das zeigt uns den echten Grund
    st.info("Checkliste:\n1. Ist das Sheet für 'Jeden mit Link' als 'Bearbeiter' freigegeben?\n2. Heißt der Reiter unten 'Mitglieder'?\n3. Steht die URL korrekt in den Secrets?")
    st.stop()

# --- AB HIER LÄUFT DIE APP WENN DIE VERBINDUNG STEHT ---
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
                            st.success("Erfolg! Link:")
                            st.code(f"https://vanselow-network.streamlit.app/?invite={new_slug}")
        else: st.error("Link ungültig.")
    else: st.info("Zutritt nur mit Einladung.")

with tab2:
    if st.sidebar.text_input("Admin-Passwort", type="password") == "gary123":
        st.dataframe(df)
Schritt 3: Die Secrets (Der "Workspace-Fix")

Da du einen Firmen-Account nutzt, probieren wir jetzt eine URL-Variante, die Google weniger oft blockiert.

Geh in Streamlit auf Settings -> Secrets.

Ersetze den Link durch diesen (das ist die Basis-URL ohne das "sharing"-Gedöns):

code
Toml
download
content_copy
expand_less
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/1B5xOILihJE6C9syNcEGu3eGps608_Z0nx3tK2uD_btQ/"

Speichern.

Schritt 4: App neu starten (Hard Reboot)

Geh in das Dashboard (share.streamlit.io), klicke auf die drei Punkte deiner App und wähle "Reboot App".

Wenn danach wieder eine Fehlermeldung kommt, schick mir bitte einen Screenshot davon. In dem schwarzen Kasten (st.code) wird dann endlich die echte Ursache stehen (z.B. "Client Error 403").

Go! Ich warte.
