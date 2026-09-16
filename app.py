import streamlit as st
import math

st.set_page_config(page_title="Power Meter Live - Telefono Sensor Suite", layout="wide")

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

# --- ALGORITMO FISICO WATT ---
def calcola_watt(v_kmh, pendenza_pct, vento_kmh, peso_tot_kg, cda=0.35, crr=0.004):
    if v_kmh <= 0.5: # Soglia di arresto
        return 0.0
    g, rho, eta = 9.81, 1.225, 0.95
    v_ms = v_kmh / 3.6
    v_aria = max(0, v_ms + (vento_kmh / 3.6))
    theta = math.atan(pendenza_pct / 100.0)

    p_gravita = peso_tot_kg * g * math.sin(theta) * v_ms
    p_aria = 0.5 * rho * cda * (v_aria ** 2) * v_ms
    p_rotolamento = crr * peso_tot_kg * g * math.cos(theta) * v_ms

    return max(0.0, (p_gravita + p_aria + p_rotolamento) / eta)

# --- DASHBOARD APP ---
st.title("🚴 Cycling Power Meter - Full Auto")

st.sidebar.header("⚙️ Configurazione Bici & Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=75.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=11.0)
peso_totale = peso_atleta + peso_bici
cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.35)
vento_kmh = st.sidebar.number_input("Vento Stimato (km/h) [+ contro / - a favore]", value=0.0)

cadence_url = st.sidebar.text_input("Link Cadence Live (Per Mappa):", value="https://livetracker.getcadence.app/BVsKx7593UzZ0X")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 Mappa Cadence Live")
    if cadence_url:
        st.components.v1.iframe(cadence_url, height=500, scrolling=True)

with col2:
    st.subheader("⚡ Calcolo Watt Automatico dai Sensori")
    
    # MODULO JAVASCRIPT: GPS + BAROMETRO + BLUETOOTH
    st.components.v1.html("""
    <div style="font-family: sans-serif; background-color: #0e1117; color: white; padding: 15px; border-radius: 10px;">
        <button id="startSensors" style="background-color: #FF4B4B; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%;">
            🚀 ATTIVA SENSORI TELEFONO (GPS + BAROMETRO)
        </button>
        <br/><br/>
        <button id="connectBle" style="background-color: #008CBA; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; width: 100%;">
            ❤️ Collega Fascia Cardio Bluetooth
        </button>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; text-align: center;">
            <div style="background-color: #262730; padding: 10px; border-radius: 5px;">
                <small>Velocità (GPS)</small>
                <h2 id="speedVal" style="margin: 5px 0; color: #4CAF50;">0.0 km/h</h2>
            </div>
            <div style="background-color: #262730; padding: 10px; border-radius: 5px;">
                <small>Pendenza (Barometro)</small>
                <h2 id="gradeVal" style="margin: 5px 0; color: #FF9800;">0.0 %</h2>
            </div>
            <div style="background-color: #262730; padding: 10px; border-radius: 5px;">
                <small>Battito Cardio</small>
                <h2 id="bpmVal" style="margin: 5px 0; color: #E91E63;">-- BPM</h2>
            </div>
            <div style="background-color: #262730; padding: 10px; border-radius: 5px;">
                <small>Pressione Mbar</small>
                <h2 id="pressVal" style="margin: 5px 0; color: #00BCD4;">--</h2>
            </div>
        </div>
    </div>

    <script>
    let lastLat = null, lastLon = null, lastAlt = null, lastTime = null;
    let currentSpeed = 0, currentGrade = 0;

    // ATTIVAZIONE GPS E BAROMETRO
    document.getElementById('startSensors').addEventListener('click', () => {
        // 1. GPS Tracking
        if ("geolocation" in navigator) {
            navigator.geolocation.watchPosition((pos) => {
                const spd = pos.coords.speed ? (pos.coords.speed * 3.6) : 0;
                currentSpeed = spd < 0.5 ? 0 : spd;
                document.getElementById('speedVal').innerText = currentSpeed.toFixed(1) + " km/h";
                
                // Calcolo Fallback pendenza via Altimetria GPS se il barometro manca
                if (pos.coords.altitude && lastLat !== null) {
                    let dist = getDistance(lastLat, lastLon, pos.coords.latitude, pos.coords.longitude);
                    let altDiff = pos.coords.altitude - lastAlt;
                    if (dist > 3) {
                        currentGrade = (altDiff / dist) * 100;
                        document.getElementById('gradeVal').innerText = currentGrade.toFixed(1) + " %";
                    }
                }
                lastLat = pos.coords.latitude;
                lastLon = pos.coords.longitude;
                lastAlt = pos.coords.altitude;
            }, (err) => alert("Errore GPS: " + err.message), { enableHighAccuracy: true });
        }

        // 2. Barometro Atmosferico (Pressione)
        if ('PressureObserver' in window) {
            const sample_interval = 1000;
            const observer = new PressureObserver(records => {
                const lastRecord = records[records.length - 1];
                document.getElementById('pressVal').innerText = lastRecord.pressure.toFixed(1);
            });
            observer.observe({ sampleInterval: sample_interval });
        } else {
            document.getElementById('pressVal').innerText = "GPS Alt";
        }
    });

    // DISTANZA HAVERSINE
    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000;
        const dLat = (lat2-lat1) * Math.PI / 180;
        const dLon = (lon2-lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }

    // FASCIA CARDIO BLUETOOTH
    document.getElementById('connectBle').addEventListener('click', async () => {
        try {
            const device = await navigator.bluetooth.requestDevice({ filters: [{ services: ['heart_rate'] }] });
            const server = await device.gatt.connect();
            const service = await server.getPrimaryService('heart_rate');
            const characteristic = await service.getCharacteristic('heart_rate_measurement');
            await characteristic.startNotifications();
            characteristic.addEventListener('characteristicvaluechanged', (e) => {
                const bpm = e.target.value.getUint8(1);
                document.getElementById('bpmVal').innerText = bpm + " BPM";
            });
        } catch (e) { alert("Bluetooth: " + e); }
    });
    </script>
    """, height=350)

    # Input manuali di override se vuoi testarli a mano
    v_override = st.number_input("Velocità Manuale (Se vuoi Sovrascrivere)", value=0.0, step=0.5)
    p_override = st.number_input("Pendenza Manuale (Se vuoi Sovrascrivere)", value=0.0, step=0.5)

    watt = calcola_watt(v_override, p_override, vento_kmh, peso_totale, cda)
    st.markdown("---")
    st.metric(label="⚡ WATT STIMATI", value=f"{int(watt)} W")
