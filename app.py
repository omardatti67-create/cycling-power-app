import streamlit as st
import math

st.set_page_config(page_title="Cycling Power Meter Live", layout="wide")

PASSWORD_SEGRETA = "123"

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

st.title("🚴 Power Dashboard Live")

st.sidebar.header("⚙️ Parametri Bici & Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=75.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=11.0)
peso_totale = peso_atleta + peso_bici
cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.35)
vento_kmh = st.sidebar.number_input("Vento (km/h) [+ contro / - a favore]", value=0.0)

cadence_url = st.sidebar.text_input("Link Cadence Live:", value="https://livetracker.getcadence.app/BVsKx7593UzZ0X")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 Mappe Cadence Live")
    if cadence_url:
        st.components.v1.iframe(cadence_url, height=520, scrolling=True)

with col2:
    st.subheader("⚡ Calcolo Watt istantaneo dai Sensori")
    
    st.components.v1.html(f"""
    <div style="font-family: system-ui, sans-serif; background-color: #0e1117; color: white; padding: 15px; border-radius: 10px;">
        <button id="startSensors" style="background-color: #FF4B4B; color: white; padding: 12px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%;">
            🚀 ATTIVA SENSORI GPS & PAROMETRO
        </button>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; text-align: center;">
            <div style="background-color: #262730; padding: 10px; border-radius: 8px;">
                <small>Velocità (GPS)</small>
                <h2 id="speedVal" style="margin: 5px 0; color: #4CAF50;">0.0 km/h</h2>
            </div>
            <div style="background-color: #262730; padding: 10px; border-radius: 8px;">
                <small>Pendenza</small>
                <h2 id="gradeVal" style="margin: 5px 0; color: #FF9800;">0.0 %</h2>
            </div>
        </div>

        <div style="background-color: #1e222a; border: 2px solid #FF4B4B; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center;">
            <span style="font-size: 14px; text-transform: uppercase; tracking: 1px; color: #aaa;">⚡ WATT STIMATI SUI PEDALI</span>
            <h1 id="wattVal" style="font-size: 48px; margin: 5px 0; color: #FFFFFF;">0 W</h1>
        </div>
    </div>

    <script>
    const pesoTotale = {peso_totale};
    const cda = {cda};
    const ventoKmh = {vento_kmh};
    
    let lastLat = null, lastLon = null, lastAlt = null;
    let currentSpeed = 0, currentGrade = 0;

    function calcolaWattFisici(vKmh, gradePct) {{
        if (vKmh <= 0.8) return 0;
        
        const g = 9.81, rho = 1.225, eta = 0.95, crr = 0.004;
        const vMs = vKmh / 3.6;
        const vAria = Math.max(0, vMs + (ventoKmh / 3.6));
        const theta = Math.atan(gradePct / 100.0);

        const pGravita = pesoTotale * g * Math.sin(theta) * vMs;
        const pAria = 0.5 * rho * cda * Math.pow(vAria, 2) * vMs;
        const pRotolamento = crr * pesoTotale * g * Math.cos(theta) * vMs;

        const watt = (pGravita + pAria + pRotolamento) / eta;
        return Math.max(0, Math.round(watt));
    }}

    document.getElementById('startSensors').addEventListener('click', () => {{
        if ("geolocation" in navigator) {{
            navigator.geolocation.watchPosition((pos) => {{
                let spd = pos.coords.speed ? (pos.coords.speed * 3.6) : 0;
                currentSpeed = spd < 0.5 ? 0 : spd;
                
                document.getElementById('speedVal').innerText = currentSpeed.toFixed(1) + " km/h";

                if (pos.coords.altitude !== null && lastLat !== null) {{
                    let dist = getDistance(lastLat, lastLon, pos.coords.latitude, pos.coords.longitude);
                    let altDiff = pos.coords.altitude - lastAlt;
                    if (dist > 2.5) {{
                        currentGrade = (altDiff / dist) * 100;
                        if (currentGrade > 30) currentGrade = 30;
                        if (currentGrade < -25) currentGrade = -25;
                        document.getElementById('gradeVal').innerText = currentGrade.toFixed(1) + " %";
                        lastLat = pos.coords.latitude;
                        lastLon = pos.coords.longitude;
                        lastAlt = pos.coords.altitude;
                    }}
                }} else if (pos.coords.altitude !== null) {{
                    lastLat = pos.coords.latitude;
                    lastLon = pos.coords.longitude;
                    lastAlt = pos.coords.altitude;
                }}

                // AGGIORNA I WATT IN TEMPO REALE
                const watt = calcolaWattFisici(currentSpeed, currentGrade);
                document.getElementById('wattVal').innerText = watt + " W";

            }}, (err) => alert("GPS Errore: " + err.message), {{ enableHighAccuracy: true }});
        }}
    }});

    function getDistance(lat1, lon1, lat2, lon2) {{
        const R = 6371000;
        const dLat = (lat2-lat1) * Math.PI / 180;
        const dLon = (lon2-lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }}
    </script>
    """, height=380)
