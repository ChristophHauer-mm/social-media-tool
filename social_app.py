import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# --- Konfiguration ---
st.set_page_config(page_title="Social Media Agentur Tool", page_icon="🚀", layout="wide")

# --- Google Sheets Verbindung ---
# Wir holen uns die Verbindung aus den Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Hilfsfunktionen für Google Sheets ---

def get_data():
    # Lädt die Tabelle neu. Wir gehen davon aus, dass Blatt 1 "Customers" und Blatt 2 "Posts" ist.
    # Um es einfach zu halten, nutzen wir hier EINE Tabelle mit Spalten für alles oder filtern.
    # BESSERER WEG FÜR DEN ANFANG: Wir nutzen Worksheets.
    
    # Wir lesen das erste Arbeitsblatt (sollte 'Customers' heißen oder wir nehmen einfach Worksheets[0])
    try:
        df_customers = conn.read(worksheet="Customers", usecols=[0,1,2,3,4,5], ttl=0)
        # ttl=0 bedeutet: Nicht cachen, immer frisch laden!
    except:
        # Falls leer/nicht existent, leeres DF erstellen
        df_customers = pd.DataFrame(columns=["id", "company_name", "username", "password", "ig_token", "fb_token"])
    
    try:
        df_posts = conn.read(worksheet="Posts", usecols=[0,1,2,3,4,5], ttl=0)
    except:
        df_posts = pd.DataFrame(columns=["id", "customer_id", "caption", "media_name", "status", "date"])
        
    return df_customers, df_posts

def save_customer(company, user, pw):
    df_customers, df_posts = get_data()
    
    # Check ob User existiert
    if not df_customers.empty and user in df_customers['username'].values:
        return False
    
    # Neue ID generieren
    new_id = 1 if df_customers.empty else df_customers['id'].max() + 1
    
    new_entry = pd.DataFrame([{
        "id": new_id,
        "company_name": company,
        "username": user,
        "password": pw,
        "ig_token": "",
        "fb_token": ""
    }])
    
    updated_df = pd.concat([df_customers, new_entry], ignore_index=True)
    conn.update(worksheet="Customers", data=updated_df)
    return True

def save_post(customer_id, caption, media, date_str):
    df_customers, df_posts = get_data()
    
    new_id = 1 if df_posts.empty else df_posts['id'].max() + 1
    
    new_entry = pd.DataFrame([{
        "id": new_id,
        "customer_id": int(customer_id),
        "caption": caption,
        "media_name": media,
        "status": "Geplant",
        "date": date_str
    }])
    
    updated_df = pd.concat([df_posts, new_entry], ignore_index=True)
    conn.update(worksheet="Posts", data=updated_df)

def update_token(customer_id, platform, token):
    df_customers, df_posts = get_data()
    
    # Zeile finden und updaten
    mask = df_customers['id'] == customer_id
    if platform == 'ig':
        df_customers.loc[mask, 'ig_token'] = token
    else:
        df_customers.loc[mask, 'fb_token'] = token
        
    conn.update(worksheet="Customers", data=df_customers)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=100)
    st.title("Cloud Cockpit")
    st.caption("Connected to Google Sheets 🟢")
    st.markdown("---")
    user_role = st.radio("Login als:", ["Admin", "Kunde"])

# --- Daten laden ---
try:
    df_customers, df_posts = get_data()
except Exception as e:
    st.error(f"Verbindungsfehler zu Google Sheets! Bitte prüfen: {e}")
    st.stop()

# ==========================================
# ADMIN
# ==========================================
if user_role == "Admin":
    st.title("👨‍💻 Agentur Dashboard (Cloud)")
    
    tab1, tab2 = st.tabs(["Neuer Post", "Kunden"])
    
    with tab1:
        if df_customers.empty:
            st.warning("Noch keine Kunden.")
        else:
            c_list = df_customers['company_name'].unique()
            selected_comp = st.selectbox("Kunde", c_list)
            # ID holen
            c_row = df_customers[df_customers['company_name'] == selected_comp].iloc[0]
            c_id = int(c_row['id'])
            
            uploaded = st.file_uploader("Media")
            cap = st.text_area("Text")
            dat = st.date_input("Datum")
            
            if st.button("Speichern ☁️"):
                if uploaded and cap:
                    save_post(c_id, cap, uploaded.name, str(dat))
                    st.success("In Google Sheet gespeichert!")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        with st.form("new_c"):
            c_name = st.text_input("Firma")
            c_user = st.text_input("User")
            c_pw = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anlegen"):
                if save_customer(c_name, c_user, c_pw):
                    st.success("Kunde angelegt!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Fehler oder User existiert schon.")
        
        st.write("Datenbank Inhalt:")
        st.dataframe(df_customers)

# ==========================================
# KUNDE
# ==========================================
else:
    if 'cust_id' not in st.session_state: st.session_state.cust_id = None
    
    if st.session_state.cust_id is None:
        st.header("Kunden Login")
        u = st.text_input("User")
        p = st.text_input("Passwort", type="password")
        if st.button("Login"):
            # Suche in DF
            user_row = df_customers[(df_customers['username'] == u) & (df_customers['password'] == p)]
            if not user_row.empty:
                st.session_state.cust_id = int(user_row.iloc[0]['id'])
                st.rerun()
            else:
                st.error("Falsch")
    else:
        # Eingeloggt
        me = df_customers[df_customers['id'] == st.session_state.cust_id].iloc[0]
        st.title(f"Hallo {me['company_name']}")
        if st.button("Logout"): 
            st.session_state.cust_id = None
            st.rerun()
            
        st.subheader("Deine Posts (aus Google Sheets)")
        # Filter posts
        my_posts = df_posts[df_posts['customer_id'] == me['id']]
        st.dataframe(my_posts)
