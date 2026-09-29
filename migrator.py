import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine

st.set_page_config(page_title="Migracja SQM HUB", layout="centered")
st.title("Migracja SQM HUB do Supabase 🚀")

# Gotowy link do nowej bazy
DB_URL = "postgresql+psycopg2://postgres.twmuwhgjtxmwvaihmgnr:7dJfrLGb3Wuilvyl@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

if st.button("Rozpocznij przenoszenie danych do SQL", type="primary", use_container_width=True):
    engine = create_engine(DB_URL)
    
    # Połączenie ze starym Google Sheets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    gc = gspread.authorize(creds)
    sh = gc.open("NOWY PODZIAŁ OBOWIĄZKÓW") 

    arkusze = [
        'DB_Eventy', 'Zlecenia', 'Zlecenia Poboczne', 'DB_Sloty', 
        'DB_Subrenty', 'DB_Yestech', 'DB_Katalog_Firm', 'Miejsca', 
        'Zleceniobiorcy', 'Projekty', 'System_Ustawienia', 'DB_Empties', 
        'DB_Rampy', 'DB_Event_Etapy', 'DB_Eventy ARCHIWUM', 
        'Zlecenia Poboczne ARCHIWUM', 'Raport_Ksiegowy'
    ]

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, arkusz in enumerate(arkusze):
        status_text.text(f"Kopiowanie arkusza: {arkusz}...")
        try:
            worksheet = sh.worksheet(arkusz)
            raw_data = worksheet.get_all_values()
            
            if raw_data and len(raw_data) > 0:
                headers = raw_data[0]
                # Oczyszczanie nagłówków
                headers = [f"Brak_Nazwy_{idx}" if str(h).strip() == "" else str(h).strip() for idx, h in enumerate(headers)]
                seen = set()
                for idx, h in enumerate(headers):
                    if h in seen:
                        headers[idx] = f"{h}_duplikat_{idx}"
                    seen.add(headers[idx])
                    
                df = pd.DataFrame(raw_data[1:], columns=headers)
                
                # Formatowanie pod SQL (małe litery, bez spacji)
                nazwa_tabeli = arkusz.lower().replace(" ", "_").replace("/", "_")
                df.to_sql(nazwa_tabeli, engine, if_exists='replace', index=False)
                st.write(f"✅ Przeniesiono tabelę: **{nazwa_tabeli}** ({len(df)} rekordów)")
            else:
                st.write(f"⚠️ Pusty arkusz **{arkusz}** - zignorowano.")
        except Exception as e:
            st.error(f"❌ Błąd dla {arkusz}: {e}")
        
        progress_bar.progress((i + 1) / len(arkusze))
        
    status_text.success("🎉 MIGRACJA ZAKOŃCZONA SUKCESEM! Baza PostgreSQL jest gotowa.")
    st.balloons()
