import streamlit as st

st.set_page_config(page_title="Power Meter - Auto Wind & GPS", layout="wide")

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

st.title("🚴 Power Meter Live (Vento & GPS Auto)")

st.sidebar.header("⚙️ Parametri Bici & Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=75.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=11.0)
peso_totale = peso_atleta + peso_bici
cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.35)

cadence_url = st.sidebar.text_input("Link Cadence Live:", value="https://livetracker.getcadence.app/BVsKx7593UzZ0X")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 Mappa Cadence Live")
    if cadence_url:
        st.components.v1.iframe(cadence_url, height=520, scrolling=True)

with col2:
    st.subheader("⚡ Watt con Vento e GPS in Tempo Reale")
    
    st.components.v1.html(f"""
    <div style="font-family: system-ui, sans-serif; background-color: #0e1117; color: white; padding: 15px; border-radius: 10px;">
        <button id="startSensors" style="background-color: #FF4B4B; color: white; padding: 12px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%;">
            🚀 ATTIVA SENSORI (GPS + VENTO AUTO)
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
            <div style="background-color: #262730; padding: 10px; border-radius: 8px;">
                <small>Vento Meteo Live</small>
                <h3 id="windVal" style="margin: 5px 0; color: #00BCD4;">-- km/h</h3>
            </div>
            <div style="background-color: #262730; padding: 10px; border-radius: 8px;">
                <small>Vento Effettivo Bici</small>
                <h3 id="effWindVal" style="margin: 5px 0; color: #E91E63;">0.0 km/h</h3>
            </div>
        </div>

        <div style="background-color: #1e222a; border: 2px solid #FF4B4B; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center;">
            <span style="font-size: 14px; text-transform: uppercase; color: #aaa;">⚡ WATT STIMATI SUI PEDALI</span>
            <h1 id="wattVal" style="font-size: 48px; margin: 5px 0; color: #FFFFFF;">0 W</h1>
        </div>
    </div>

    <script>
    const pesoTotale = {peso_totale};
    const cda = {cda};
    
    let lastLat = null, lastLon = null, lastAlt = null;
    let currentSpeed = 0, currentGrade = 0;
    let windSpeedKmh = 0, windDirDeg = 0, bikeHeadingDeg = 0;

    // OTTIENI VENTO REALE DA API METEO
    async function fetchWindData(lat, lon) {{
        try {{
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${{lat}}&longitude=${{lon}}&current_weather=true`;
            const res = await fetch(url);
            const data = await res.json();
            if (data.current_weather) {{
                windSpeedKmh = data.current_weather.windspeed;
                windDirDeg = data.current_weather.winddirection;
                document.getElementById('windVal').innerText = windSpeedKmh.toFixed(1) + " km/h";
            }}
        }} catch(e) {{ console.log("Errore Meteo API:", e); }}
    }}

    function calcolaWatt(vKmh, gradePct, effWindKmh) {{
        if (vKmh <= 0.8) return 0;
        
        const g = 9.81, rho = 1.225, eta = 0.95, crr = 0.004;
        const vMs = vKmh / 3.6;
        const vAria = Math.max(0, vMs + (effWindKmh / 3.6));
        const theta = Math.atan(gradePct / 100.0);

        const pGravita = pesoTotale * g * Math.sin(theta) * vMs;
        const pAria = 0.5 * rho * cda * Math.pow(vAria, 2) * vMs;
        const pRotolamento = crr * pesoTotale * g * Math.cos(theta) * vMs;

        return Math.max(0, Math.round((pGravita + pAria + pRotolamento) / eta));
    }}

    document.getElementById('startSensors').addEventListener('click', () => {{
        if ("geolocation" in navigator) {{
            navigator.geolocation.watchPosition((pos) => {{
                let spd = pos.coords.speed ? (pos.coords.speed * 3.6) : 0;
                currentSpeed = spd < 0.5 ? 0 : spd;
                document.getElementById('speedVal').innerText = currentSpeed.toFixed(1) + " km/h";

                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;

                // Chiama API vento ogni volta che ci si sposta
                if (!lastLat || getDistance(lastLat, lastLon, lat, lon) > 500) {{
                    fetchWindData(lat, lon);
                }}

                // Direzione GPS della bici
                if (pos.coords.heading !== null && !isNaN(pos.coords.heading)) {{
                    bikeHeadingDeg = pos.coords.heading;
                }}

                // Calcolo Vento Effettivo (Contro o A favore)
                let angleRad = (windDirDeg - bikeHeadingDeg) * (Math.PI / 180);
                let effWind = windSpeedKmh * Math.cos(angleRad);
                document.getElementById('effWindVal').innerText = (effWind > 0 ? "+" : "") + effWind.toFixed(1) + " km/h";

                // Pendenza
                if (pos.coords.altitude !== null && lastLat !== null) {{
                    let dist = getDistance(lastLat, lastLon, lat, lon);
                    let altDiff = pos.coords.altitude - lastAlt;
                    if (dist > 2.5) {{
                        currentGrade = Math.min(30, Math.max(-25, (altDiff / dist) * 100));
                        document.getElementById('gradeVal').innerText = currentGrade.toFixed(1) + " %";
                        lastLat = lat; lastLon = lon; lastAlt = pos.coords.altitude;
                    }}
                }} else if (pos.coords.altitude !== null) {{
                    lastLat = lat; lastLon = lon; lastAlt = pos.coords.altitude;
                }}

                // Calcolo Watt Finale
                const watt = calcolaWatt(currentSpeed, currentGrade, effWind);
                document.getElementById('wattVal').innerText = watt + " W";

            }}, (err) => alert("GPS: " + err.message), {{ enableHighAccuracy: true }});
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
    """, height=420)
