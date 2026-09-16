import streamlit as st
import math

st.set_page_config(page_title="Cycling Power Meter", layout="wide")

PASSWORD_SEGRETA = "LaTuaPassword123"

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

# --- FUNZIONE CALCOLO WATT ---
def calcola_watt(v_kmh, pendenza_pct, vento_kmh, peso_tot_kg, cda=0.32, crr=0.004):
    if v_kmh <= 0:
        return 0.0
    g, rho, eta = 9.81, 1.225, 0.95
    v_ms = v_kmh / 3.6
    v_aria = max(0, v_ms + (vento_kmh / 3.6))
    theta = math.atan(pendenza_pct / 100.0)

    p_gravita = peso_tot_kg * g * math.sin(theta) * v_ms
    p_aria = 0.5 * rho * cda * (v_aria ** 2) * v_ms
    p_rotolamento = crr * peso_tot_kg * g * math.cos(theta) * v_ms

    return max(0.0, (p_gravita + p_aria + p_rotolamento) / eta)

# --- INTERFACCIA APP ---
st.title("🚴 Power Dashboard Live")

# Sidebar
st.sidebar.header("⚙️ Configurazione Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=75.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=11.0)
peso_totale = peso_atleta + peso_bici
cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.35)

cadence_url = st.sidebar.text_input("Link Cadence Live:", value="https://livetracker.getcadence.app/BVsKx7593UzZ0X")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📡 Mappa & Dati Cadence Live")
    if cadence_url:
        st.components.v1.iframe(cadence_url, height=550, scrolling=True)

with col_right:
    st.subheader("⚡ Calcolatore Watt Istantanei")
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        v_kmh = st.number_input("Velocità Attuale (km/h)", value=25.0, step=0.5)
        pendenza = st.number_input("Pendenza Attuale (%)", value=3.0, step=0.5)
    with col_in2:
        vento_kmh = st.number_input("Vento (km/h) [+ contro / - a favore]", value=0.0, step=1.0)
        bpm = st.number_input("Frequenza Cardiaca (BPM)", value=145, step=1)

    watt = calcola_watt(v_kmh, pendenza, vento_kmh, peso_totale, cda)
    
    st.markdown("---")
    st.metric(label="⚡ WATT STIMATI SUI PEDALI", value=f"{int(watt)} W")
    
    # Integrazione Sensore Cardio Bluetooth (Web-Bluetooth)
    st.markdown("### ❤️ Connetti Fascia Cardio Bluetooth (Opzionale)")
    st.components.v1.html("""
        <button id="connectBle" style="background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
            🔗 Collega Fascia Cardio Bluetooth
        </button>
        <h3 style="color: white; margin-top: 10px;">BPM Live: <span id="bpmValue">--</span></h3>

        <script>
        document.getElementById('connectBle').addEventListener('click', async () => {
            try {
                const device = await navigator.bluetooth.requestDevice({
                    filters: [{ services: ['heart_rate'] }]
                });
                const server = await device.gatt.connect();
                const service = await server.getPrimaryService('heart_rate');
                const characteristic = await service.getCharacteristic('heart_rate_measurement');
                await characteristic.startNotifications();
                characteristic.addEventListener('characteristicvaluechanged', (e) => {
                    const value = e.target.value;
                    const bpm = value.getUint8(1);
                    document.getElementById('bpmValue').innerText = bpm + " BPM";
                });
            } catch (error) {
                alert("Errore di connessione Bluetooth: " + error);
            }
        });
        </script>
    """, height=130)
