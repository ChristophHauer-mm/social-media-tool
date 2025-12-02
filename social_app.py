import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection
from requests_oauthlib import OAuth2Session

# --- Konfiguration ---
st.set_page_config(page_title="Social Media Agentur Tool", page_icon="🚀", layout="wide")

# --- Google Sheets Verbindung ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Facebook Config ---
try:
    FB_CLIENT_ID = st.secrets["oauth"]["client_id"]
    FB_CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
    REDIRECT_URI = st.secrets["oauth"]["redirect_uri"]
except:
    st.error("Fehler: Facebook Secrets fehlen oder sind falsch formatiert!")
    st.stop()

AUTHORIZATION_BASE_URL = 'https://www.facebook.com/dialog/oauth'
TOKEN_URL = 'https://graph.facebook.com/oauth/access_token'

# --- Hilfsfunktionen Datenbank ---
def get_data():
    try:
        df_customers = conn.read(worksheet="Customers", usecols=[0,1,2,3,4,5], ttl=0)
        # Leere Zeilen filtern
        df_customers = df_customers.dropna(how='all')
    except:
        df_customers = pd.DataFrame(columns=["id", "company_name", "username", "password", "ig_token", "fb_token"])
    
    try:
        df_posts = conn.read(worksheet="Posts", usecols=[0,1,2,3,4,5], ttl=0)
        df_posts = df_posts.dropna(how='all')
    except:
        df_posts = pd.DataFrame(columns=["id", "customer_id", "caption", "media_name", "status", "date"])
        
    return df_customers, df_posts

def save_customer(company, user, pw):
    df_customers, df_posts = get_data()
    if not df_customers.empty and user in df_customers['username'].values: return False
    
    # ID berechnen (Nummer sicher gehen)
    if df_customers.empty:
        new_id = 1
    else:
        # Wir konvertieren zu Numeric, um Fehler zu vermeiden
        new_id = pd.to_numeric(df_customers['id']).max() + 1
        
    new_entry = pd.DataFrame([{"id": new_id, "company_name": company, "username": user, "password": pw, "ig_token": "", "fb_token": ""}])
    updated_df = pd.concat([df_customers, new_entry], ignore_index=True)
    conn.update(worksheet="Customers", data=updated_df)
    return True

def save_post(customer_id, caption, media, date_str):
    df_customers, df_posts = get_data()
    
    if df_posts.empty:
        new_id = 1
    else:
        new_id = pd.to_numeric(df_posts['id']).max() + 1
        
    new_entry = pd.DataFrame([{"id": new_id, "customer_id": int(customer_id), "caption": caption, "media_name": media, "status": "Geplant", "date": date_str}])
    updated_df = pd.concat([df_posts, new_entry], ignore_index=True)
    conn.update(worksheet="Posts", data=updated_df)

def update_token(customer_id, token):
    df_customers, df_posts = get_data()
    # Wir suchen die Zeile anhand der ID
    mask = df_customers['id'] == customer_id
    df_customers.loc[mask, 'fb_token'] = token
    df_customers.loc[mask, 'ig_token'] = "Via Facebook verbunden" 
    conn.update(worksheet="Customers", data=df_customers)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=100)
    st.title("Cloud Cockpit")
    user_role = st.radio("Login als:", ["Admin", "Kunde"])
    if st.button("Logout / Reset"):
        st.session_state.clear()
        st.rerun()

# --- Hauptlogik ---
df_customers, df_posts = get_data()

# WICHTIG: Wir wandeln alles in Text um, damit Zahlen-Passwörter (1234) funktionieren
if not df_customers.empty:
    df_customers['username'] = df_customers['username'].astype(str).str.strip()
    df_customers['password'] = df_customers['password'].astype(str).str.strip()
    # str.strip() entfernt auch versehentliche Leerzeichen am Ende

# ==========================================
# ADMIN BEREICH
# ==========================================
if user_role == "Admin":
    st.title("👨‍💻 Agentur Dashboard")
    tab1, tab2 = st.tabs(["Neuer Post", "Kunden"])
    
    with tab1:
        if df_customers.empty: st.warning("Keine Kunden.")
        else:
            selected_comp = st.selectbox("Kunde", df_customers['company_name'].unique())
            c_row = df_customers[df_customers['company_name'] == selected_comp].iloc[0]
            
            uploaded = st.file_uploader("Media")
            cap = st.text_area("Text")
            dat = st.date_input("Datum")
            
            if st.button("Speichern ☁️"):
                if uploaded and cap:
                    save_post(c_row['id'], cap, uploaded.name, str(dat))
                    st.success("Gespeichert!")
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
                else: st.error("Fehler")
        st.dataframe(df_customers)

# ==========================================
# KUNDEN BEREICH
# ==========================================
else:
    if 'cust_id' not in st.session_state: st.session_state.cust_id = None
    
    # --- LOGIN ---
    if st.session_state.cust_id is None:
        st.header("Kunden Login")
        u = st.text_input("User")
        p = st.text_input("Passwort", type="password")
        if st.button("Login"):
            # .strip() entfernt Leerzeichen bei der Eingabe
            u_clean = str(u).strip()
            p_clean = str(p).strip()
            
            user_row = df_customers[(df_customers['username'] == u_clean) & (df_customers['password'] == p_clean)]
            
            if not user_row.empty:
                st.session_state.cust_id = int(user_row.iloc[0]['id'])
                st.rerun()
            else:
                st.error("Benutzername oder Passwort falsch.")
                # Debug-Hilfe (nur für dich, kannst du später löschen):
                # st.write("Ich habe gesucht nach:", u_clean, p_clean)
                # st.write("In der Datenbank steht:", df_customers[['username', 'password']])
                
    # --- DASHBOARD  ---
    else:
        # Hier muss der Code von vorhin für das Dashboard hin (Facebook etc.)
        # Kopiere einfach den unteren Teil ("else: me = ...") aus dem vorherigen Code 
        # oder soll ich dir die ganze Datei nochmal komplett schicken?
        # Um Fehler zu vermeiden, hier der ganze Restblock:
        
        me = df_customers[df_customers['id'] == st.session_state.cust_id].iloc[0]
        st.title(f"Hallo {me['company_name']} 👋")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Verbindung")
            has_token = len(str(me['fb_token'])) > 10
            
            if has_token:
                st.success("✅ Facebook & Instagram verbunden!")
            else:
                st.warning("⚠️ Noch nicht verbunden")
                
                facebook = OAuth2Session(FB_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=["pages_show_list", "pages_read_engagement", "pages_manage_posts"])
                authorization_url, state = facebook.authorization_url(AUTHORIZATION_BASE_URL)
                
                st.link_button("👉 Jetzt mit Facebook verbinden", authorization_url)
                
                try:
                    if "code" in st.query_params:
                        code = st.query_params["code"]
                        token = facebook.fetch_token(TOKEN_URL, client_secret=FB_CLIENT_SECRET, code=code)
                        update_token(me['id'], token['access_token'])
                        st.balloons()
                        st.success("Erfolg!")
                        st.query_params.clear()
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

        with col2:
            st.subheader("Deine Posts")
            my_posts = df_posts[df_posts['customer_id'] == me['id']]
            st.dataframe(my_posts)
