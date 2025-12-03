import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# --- Konfiguration ---
st.set_page_config(page_title="Social Media Agentur Tool", page_icon="🚀", layout="wide")

# --- Google Sheets Verbindung ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Hilfsfunktionen ---
def get_data():
    try:
        # Wir laden die Daten und zwingen alles zu Text (vermeidet Zahlen-Fehler)
        df_customers = conn.read(worksheet="Customers", usecols=[0,1,2,3], ttl=0)
        df_customers = df_customers.astype(str)
        df_posts = conn.read(worksheet="Posts", usecols=[0,1,2,3,4,5], ttl=0)
    except:
        st.error("Fehler beim Laden der Datenbank.")
        st.stop()
    return df_customers, df_posts

def save_post(customer_id, caption, image_url, date_str):
    df_customers, df_posts = get_data()
    
    # Neue ID berechnen
    if df_posts.empty: new_id = 1
    else: new_id = pd.to_numeric(df_posts['id']).max() + 1
        
    new_entry = pd.DataFrame([{
        "id": new_id,
        "customer_id": int(customer_id),
        "caption": caption,
        "media_name": image_url, # Hier speichern wir jetzt den Link zum Bild
        "status": "Ready",       # Signalwort für Make.com
        "date": date_str
    }])
    
    updated_df = pd.concat([df_posts, new_entry], ignore_index=True)
    conn.update(worksheet="Posts", data=updated_df)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=100)
    st.title("Agentur Cockpit")
    st.info("Backend: Google Sheets & Make.com")

# --- Daten laden ---
df_customers, df_posts = get_data()

# --- HAUPTBEREICH (Nur Admin, da Kunden nicht mehr technisch verbinden müssen) ---
st.title("👨‍💻 Content Planung")

tab1, tab2 = st.tabs(["Neuer Post", "Übersicht"])

with tab1:
    if df_customers.empty:
        st.warning("Keine Kunden in der Datenbank.")
    else:
        # Kunde wählen
        selected_comp = st.selectbox("Kunde auswählen", df_customers['company_name'].unique())
        c_row = df_customers[df_customers['company_name'] == selected_comp].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Inhalt")
            caption = st.text_area("Post Text (Caption)")
            # WICHTIG: Make.com braucht einen Link zum Bild.
            # Für den Anfang nutzen wir externe Links (z.B. Google Drive Link, Dropbox Link, Website)
            image_url = st.text_input("Link zum Bild/Video (URL)")
            
            post_date = st.date_input("Wann soll gepostet werden?")
            post_time = st.time_input("Uhrzeit")
            
            if st.button("An Make.com übergeben 🚀", type="primary"):
                if caption and image_url:
                    full_date = f"{post_date} {post_time}"
                    save_post(c_row['id'], caption, image_url, full_date)
                    st.success("Gespeichert! Der Roboter übernimmt ab hier.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Bitte Text und Bild-Link angeben.")

        with col2:
            st.info("Vorschau")
            if image_url:
                try:
                    st.image(image_url)
                except:
                    st.warning("Bild konnte nicht geladen werden (Link prüfen)")
            
            if caption:
                st.write(f"**{selected_comp}:** {caption}")

with tab2:
    st.subheader("Warteschlange für den Roboter")
    # Wir zeigen eine schönere Tabelle
    if not df_posts.empty:
        # Join mit Kundennamen für bessere Übersicht
        # (Einfacher Merge Logik für die Anzeige)
        df_customers['id'] = pd.to_numeric(df_customers['id'])
        df_posts['customer_id'] = pd.to_numeric(df_posts['customer_id'])
        
        merged = pd.merge(df_posts, df_customers[['id', 'company_name']], left_on='customer_id', right_on='id')
        st.dataframe(merged[['company_name', 'date', 'status', 'caption', 'media_name']], use_container_width=True)
    else:
        st.info("Nichts geplant.")
