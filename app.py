import streamlit as st

st.set_page_config(page_title="Power Meter Live", layout="wide")

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

st.title("🚴 Power Meter Live")

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
        st.markdown(
            f"""
            <div style="width: 100%; height: 480px; border-radius: 12px; overflow: hidden; background-color: #0e1117; border: 1px solid #262730;">
                <iframe src="{cadence_url}" width="100%" height="100%" frameborder="0" style="border:0; display:block;" allowfullscreen></iframe>
            </div>
            """,
            unsafe_allow_html=True
        )

with col2:
    st.subheader("⚡ Sensori & Potenza Istantanea")
    
    st.components.v1.html(f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0e1117; color: white; padding: 12px; border-radius: 12px; box-sizing: border-box;">
        
        <button id="startSensors" style="background-color: #FF4B4B; color: white; padding: 14px; border: none; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: bold; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            🚀 ATTIVA SENSORI GPS & METEO
        </button>
        
        <!-- DISPLAY PRINCIPALE WATT -->
        <div style="background: linear-gradient(145deg, #1e222a, #14171d); border: 2px solid #00E676; padding: 15px; border-radius: 12px; margin-top: 15px; text-align: center; box-shadow: 0 4px 12px rgba(0,230,118,0.15);">
            <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #00E676; font-weight: bold;">⚡ WATT STIMATI SUI PEDALI</div>
            <div id="wattVal" style="font-size: 56px; font-weight: 800; line-height: 1.1; margin: 8px 0; color: #FFFFFF; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">0 W</div>
        </div>

        <!-- GRIGLIA TELEMETRIA -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; text-align: center;">
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Velocità</div>
                <div id="speedVal" style="font-size: 22px; font-weight: bold; margin-top: 4px; color: #4CAF50;">0.0 km/h</div>
            </div>
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Pendenza</div>
                <div id="gradeVal" style="font-size: 22px; font-weight: bold; margin-top: 4px; color: #FF9800;">0.0 %</div>
            </div>
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Vento Meteo</div>
                <div id="windVal" style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #00BCD4;">-- km/h</div>
            </div>
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Vento Effettivo</div>
                <div id="effWindVal" style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #E91E63;">0.0 km/h</div>
            </div>
        </div>
        
    </div>

    <script>
    const pesoTotale = {peso_totale};
    const cda = {cda};
    
    let lastLat = null, lastLon = null, lastAlt = null, lastTime = null;
    let smoothSpeed = 0, smoothGrade = 0, smoothWatt = 0;
    let windSpeedKmh = 0, windDirDeg = 0, bikeHeadingDeg = 0;

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
        }} catch(e) {{ console.log("Meteo Err:", e); }}
    }}

    function calcolaWatt(vKmh, gradePct, effWindKmh) {{
        if (vKmh < 1.8) return 0;
        
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
                let now = Date.now();
                let rawSpd = pos.coords.speed ? (pos.coords.speed * 3.6) : 0;

                if (rawSpd < 1.8) {{
                    smoothSpeed = 0;
                }} else {{
                    smoothSpeed = (smoothSpeed * 0.6) + (rawSpd * 0.4);
                }}

                document.getElementById('speedVal').innerText = smoothSpeed.toFixed(1) + " km/h";

                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const alt = pos.coords.altitude;

                if (!lastLat || getDistance(lastLat, lastLon, lat, lon) > 500) {{
                    fetchWindData(lat, lon);
                }}

                if (pos.coords.heading !== null && !isNaN(pos.coords.heading)) {{
                    bikeHeadingDeg = pos.coords.heading;
                }}

                let angleRad = (windDirDeg - bikeHeadingDeg) * (Math.PI / 180);
                let effWind = (smoothSpeed > 0) ? (windSpeedKmh * Math.cos(angleRad)) : 0;
                document.getElementById('effWindVal').innerText = (effWind > 0 ? "+" : "") + effWind.toFixed(1) + " km/h";

                if (smoothSpeed >= 1.8 && alt !== null && lastLat !== null && lastTime !== null) {{
                    let dt = (now - lastTime) / 1000.0;
                    let dist = getDistance(lastLat, lastLon, lat, lon);

                    if (dt >= 1.5 && dist >= 6.0) {{
                        let rawGrade = ((alt - lastAlt) / dist) * 100;
                        if (rawGrade <= 25.0 && rawGrade >= -20.0) {{
                            smoothGrade = (smoothGrade * 0.75) + (rawGrade * 0.25);
                        }}
                        lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now;
                    }}
                }} else if (smoothSpeed < 1.8) {{
                    smoothGrade = 0;
                    if (alt !== null) {{ lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now; }}
                }} else if (alt !== null) {{
                    lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now;
                }}

                document.getElementById('gradeVal').innerText = smoothGrade.toFixed(1) + " %";

                let targetWatt = calcolaWatt(smoothSpeed, smoothGrade, effWind);
                smoothWatt = Math.round((smoothWatt * 0.7) + (targetWatt * 0.3));

                document.getElementById('wattVal').innerText = smoothWatt + " W";

            }}, (err) => alert("GPS Err: " + err.message), {{ enableHighAccuracy: true }});
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
    """, height=440)
