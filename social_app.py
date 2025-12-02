import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import time

# --- Konfiguration & Design ---
st.set_page_config(
    page_title="Social Media Agentur Tool", 
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Datenbank Management (Identisch wie vorher) ---
def init_db():
    conn = sqlite3.connect('agentur_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY, company_name TEXT, username TEXT, password TEXT, ig_token TEXT, fb_token TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY, customer_id INTEGER, caption TEXT, media_name TEXT, status TEXT, date TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- Hilfsfunktionen (Identisch wie vorher) ---
def get_customers():
    return pd.read_sql("SELECT * FROM customers", conn)

def add_customer(company_name, username, password):
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE username = ?", (username,))
    if c.fetchone(): return False
    c.execute("INSERT INTO customers (company_name, username, password, ig_token, fb_token) VALUES (?, ?, ?, '', '')", (company_name, username, password, '', ''))
    conn.commit()
    return True

def check_login(username, password):
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE username = ? AND password = ?", (username, password))
    return c.fetchone()

def save_post(customer_id, caption, media_name, date):
    c = conn.cursor()
    c.execute("INSERT INTO posts (customer_id, caption, media_name, status, date) VALUES (?, ?, ?, 'Geplant', ?)", (int(customer_id), caption, media_name, date))
    conn.commit()

def get_posts(customer_id=None):
    query = "SELECT posts.id, customers.company_name, posts.caption, posts.status, posts.date FROM posts LEFT JOIN customers ON posts.customer_id = customers.id"
    if customer_id: query += f" WHERE posts.customer_id = {customer_id}"
    return pd.read_sql(query, conn)

def update_token(customer_id, platform, token):
    c = conn.cursor()
    col = "ig_token" if platform == "ig" else "fb_token"
    c.execute(f"UPDATE customers SET {col} = ? WHERE id = ?", (token, customer_id))
    conn.commit()

# --- Sidebar: Logo & Navigation ---
with st.sidebar:
    # Hier simulieren wir dein Agentur-Logo mit einem Platzhalter-Bild aus dem Internet
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=100)
    st.title("Agentur Cockpit")
    st.markdown("---")
    user_role = st.radio("Ansicht wählen:", ["Admin (Agentur)", "Kunde (Extern)"])
    st.markdown("---")
    st.caption("© 2024 SocialMaster Tool v1.0")

# ==========================================
# ADMIN ANSICHT
# ==========================================
if user_role == "Admin (Agentur)":
    st.title("👨‍💻 Agentur Dashboard")
    
    # Metriken anzeigen (Sieht professioneller aus)
    m1, m2, m3 = st.columns(3)
    m1.metric("Kunden aktiv", len(get_customers()))
    m2.metric("Posts geplant", len(get_posts()))
    m3.metric("System Status", "Online 🟢")
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["✍️ Neuer Post", "👥 Kunden verwalten", "📊 Übersicht"])
    
    with tab1:
        st.subheader("Content Planung")
        customers = get_customers()
        if customers.empty:
            st.warning("⚠️ Bitte erst Kunden anlegen!")
        else:
            col1, col2 = st.columns([1, 2], gap="large")
            with col1:
                selected_company = st.selectbox("Kunde auswählen", customers['company_name'])
                customer_id = int(customers[customers['company_name'] == selected_company]['id'].values[0])
                
                uploaded_file = st.file_uploader("Media Datei", type=['png', 'jpg', 'mp4'])
                caption = st.text_area("Caption / Text", height=150)
                post_date = st.date_input("Datum")
                
                if st.button("Post einplanen 📅", type="primary", use_container_width=True):
                    if uploaded_file and caption:
                        save_post(customer_id, caption, uploaded_file.name, str(post_date))
                        st.success("Gespeichert!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Daten fehlen.")
            with col2:
                st.info("Vorschau")
                if uploaded_file:
                    st.image(uploaded_file) if uploaded_file.type.startswith('image') else st.info("Video")

    with tab2:
        col_form, col_list = st.columns([1, 2], gap="large")
        with col_form:
            st.subheader("Neuer Kunde")
            with st.form("new_customer"):
                c_company = st.text_input("Firmenname")
                c_user = st.text_input("Benutzername")
                c_pass = st.text_input("Passwort", type="password")
                if st.form_submit_button("Kunde anlegen ✨"):
                    if c_company and c_user and c_pass:
                        if add_customer(c_company, c_user, c_pass):
                            st.success("Erstellt!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("User existiert schon!")
        with col_list:
            st.subheader("Kundenliste")
            st.dataframe(get_customers()[['company_name', 'username']], use_container_width=True)

    with tab3:
        st.dataframe(get_posts(), use_container_width=True)

# ==========================================
# KUNDEN ANSICHT (Login Screen)
# ==========================================
else:
    if 'logged_in_customer_id' not in st.session_state:
        st.session_state.logged_in_customer_id = None

    if st.session_state.logged_in_customer_id is None:
        # Zentriertes Login-Design
        col_spacer1, col_login, col_spacer2 = st.columns([1, 2, 1])
        with col_login:
            st.markdown("<h2 style='text-align: center;'>🔐 Kunden Login</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>Bitte melden Sie sich an.</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Benutzername")
                password = st.text_input("Passwort", type="password")
                submit = st.form_submit_button("Anmelden", use_container_width=True, type="primary")
                
                if submit:
                    user = check_login(username, password)
                    if user:
                        st.session_state.logged_in_customer_id = user[0]
                        st.session_state.logged_in_name = user[1]
                        st.rerun()
                    else:
                        st.error("Daten falsch.")
    else:
        # Eingeloggter Bereich
        customers = get_customers()
        cust_data = customers[customers['id'] == st.session_state.logged_in_customer_id].iloc[0]
        
        col_header, col_logout = st.columns([3, 1])
        col_header.title(f"Moin, {cust_data['company_name']}! 👋")
        col_logout.write("") 
        if col_logout.button("Abmelden"):
            st.session_state.logged_in_customer_id = None
            st.rerun()
            
        st.markdown("---")
        
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.subheader("Ihre Kanäle")
            # Status Cards
            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:10px;">
                <strong>Instagram:</strong> {'✅ Verbunden' if cust_data['ig_token'] else '❌ Getrennt'}
            </div>
            """, unsafe_allow_html=True)
            
            if not cust_data['ig_token']:
                fake_token = st.text_input("Token eingeben (Simuliert)")
                if st.button("Verbinden"):
                    update_token(cust_data['id'], 'ig', fake_token)
                    st.rerun()
            else:
                if st.button("Trennen"): update_token(cust_data['id'], 'ig', ''); st.rerun()

        with col2:
            st.subheader("Aktuelle Posts")
            my_posts = get_posts(int(cust_data['id']))
            st.dataframe(my_posts[['caption', 'date', 'status']], use_container_width=True)
