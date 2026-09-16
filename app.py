import streamlit as st
import math
import requests
import re
import time
from geopy.distance import geodesic

st.set_page_config(page_title="Cycling Watt Calculator - Live Auto", layout="wide")

PASSWORD_SEGRETA = "LaTuaPassword123"  # Cambia la password

# --- SICUREZZA ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Password d'accesso:", type="password")
    if st.button("Accedi"):
        if pwd == PASSWORD_SEGRETA:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Password errata!")
    st.stop()

# --- MEMORIA SESSIONE PER CALCOLO PENDENZA ---
if "last_lat" not in st.session_state:
    st.session_state.last_lat = None
    st.session_state.last_lon = None
    st.session_state.last_ele = None
    st.session_state.last_time = None
    st.session_state.calculated_grade = 0.0

# --- ESTRAZIONE DATI LIVE DA CADENCE ---
def ottieni_dati_cadence(url):
    """
    Estrae Latitudine, Longitudine, Altitudine, Velocità e BPM dal Live Tracking di Cadence
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=5)
        text = response.text
        
        bpm, v_kmh, lat, lon, ele = None, None, None, None, None
        
        # Regex per estrarre le metriche
        match_hr = re.search(r'("heartRate"|"hr"|"bpm")\s*:\s*(\d+)', text, re.IGNORECASE)
        match_speed = re.search(r'("speed"|"speedKmh")\s*:\s*([\d\.]+)', text, re.IGNORECASE)
        match_lat = re.search(r'("latitude"|"lat")\s*:\s*([\d\.\-]+)', text, re.IGNORECASE)
        match_lon = re.search(r'("longitude"|"lng"|"lon")\s*:\s*([\d\.\-]+)', text, re.IGNORECASE)
        match_ele = re.search(r'("altitude"|"elevation"|"ele")\s*:\s*([\d\.\-]+)', text, re.IGNORECASE)

        if match_hr: bpm = int(match_hr.group(2))
        if match_speed: v_kmh = float(match_speed.group(2))
        if match_lat: lat = float(match_lat.group(2))
        if match_lon: lon = float(match_lon.group(2))
        if match_ele: ele = float(match_ele.group(2))

        # Calcolo Pendenza Istantanea (Grade) basata su Delta Altimetria / Delta Distanza
        if lat and lon and ele and st.session_state.last_lat:
            p1 = (st.session_state.last_lat, st.session_state.last_lon)
            p2 = (lat, lon)
            distanza_m = geodesic(p1, p2).meters
            delta_ele_m = ele - st.session_state.last_ele
            
            if distanza_m > 3.0:  # Calcola solo se ci si è mossi di almeno 3 metri per evitare rumore GPS
                st.session_state.calculated_grade = max(-25.0, min(30.0, (delta_ele_m / distanza_m) * 100))
                st.session_state.last_lat = lat
                st.session_state.last_lon = lon
                st.session_state.last_ele = ele
        elif lat and lon and ele:
            st.session_state.last_lat = lat
            st.session_state.last_lon = lon
            st.session_state.last_ele = ele

        return v_kmh, bpm, st.session_state.calculated_grade
    except Exception:
        return None, None, st.session_state.calculated_grade

# --- CALCOLO POTENZA (FISICA) ---
def calcola_watt(v_kmh, pendenza_pct, vento_kmh, peso_tot_kg, cda=0.32, crr=0.004):
    if v_kmh is None or v_kmh <= 0:
        return 0.0
    g, rho, eta = 9.81, 1.225, 0.95
    v_ms = v_kmh / 3.6
    vento_ms = vento_kmh / 3.6
    v_aria = max(0, v_ms + vento_ms)

    theta = math.atan(pendenza_pct / 100.0)
    p_gravita = peso_tot_kg * g * math.sin(theta) * v_ms
    p_aria = 0.5 * rho * cda * (v_aria ** 2) * v_ms
    p_rotolamento = crr * peso_tot_kg * g * math.cos(theta) * v_ms

    return max(0.0, (p_gravita + p_aria + p_rotolamento) / eta)

# --- DASHBOARD APP ---
st.title("🚴 Power Meter Live - Auto Cadence Tracking")

# Configurazione Sidebar
st.sidebar.header("⚙️ Configurazione Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=70.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=9.0)
peso_totale = peso_atleta + peso_bici

cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.32)
cadence_link = st.sidebar.text_input("Link Cadence Live:", value="https://livetracker.getcadence.app/BVsKx7593UzZ0X")

# Vento (impostabile manualmente o da API meteo)
vento_kmh = st.sidebar.number_input("Vento (km/h) [+ contro / - a favore]", value=0.0, step=1.0)

# Estrazione in tempo reale
v_live, bpm_live, grade_live = ottieni_dati_cadence(cadence_link)

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    val_v = f"{v_live:.1f} km/h" if v_live is not None else "---"
    st.metric("Velocità (GPS)", val_v)

with col2:
    val_grade = f"{grade_live:.1f} %"
    st.metric("Pendenza Calcolata", val_grade)

with col3:
    val_bpm = f"{bpm_live} BPM" if bpm_live is not None else "---"
    st.metric("Frequenza Cardiaca", val_bpm)

with col4:
    if v_live is not None:
        watt = calcola_watt(v_live, grade_live, vento_kmh, peso_totale, cda)
        st.metric("⚡ WATT STIMATI", f"{int(watt)} W")
    else:
        st.metric("⚡ WATT STIMATI", "0 W")

# Aggiornamento automatico della pagina ogni 3 secondi
st.button("🔄 Aggiorna ora")
st.caption("Nota: Muovendoti in bici, l'app aggiorna la pendenza confrontando la variazione di quota ogni pochi metri.")
