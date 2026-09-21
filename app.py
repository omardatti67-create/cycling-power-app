import streamlit as st

st.set_page_config(page_title="Power Meter - Cadence Grade Stability", layout="wide")

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

st.title("🚴 Power Meter Live")

st.sidebar.header("⚙️ Parametri Bici & Atleta")
peso_atleta = st.sidebar.number_input("Peso Ciclista (kg)", value=75.0)
peso_bici = st.sidebar.number_input("Peso Bici (kg)", value=11.0)
peso_totale = peso_atleta + peso_bici
cda = st.sidebar.slider("Aerodinamica (CdA)", 0.25, 0.45, 0.35)

st.sidebar.header("🧪 Modalità Test (Simulazione Divano)")
test_mode = st.sidebar.checkbox("Attiva Simulazione Manuale")
sim_speed = st.sidebar.slider("Simula Velocità (km/h)", 0.0, 50.0, 25.0) if test_mode else 0.0
sim_grade = st.sidebar.slider("Simula Pendenza (%)", -10.0, 20.0, 5.0) if test_mode else 0.0

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
        
        <div style="background: linear-gradient(145deg, #1e222a, #14171d); border: 2px solid #00E676; padding: 15px; border-radius: 12px; margin-top: 15px; text-align: center; box-shadow: 0 4px 12px rgba(0,230,118,0.15);">
            <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #00E676; font-weight: bold;">⚡ WATT STIMATI SUI PEDALI</div>
            <div id="wattVal" style="font-size: 56px; font-weight: 800; line-height: 1.1; margin: 8px 0; color: #FFFFFF;">0 W</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; text-align: center;">
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Velocità</div>
                <div id="speedVal" style="font-size: 22px; font-weight: bold; margin-top: 4px; color: #4CAF50;">0.0 km/h</div>
            </div>
            <div style="background-color: #1e222a; padding: 10px; border-radius: 8px; border: 1px solid #262730;">
                <div style="font-size: 11px; color: #888; text-transform: uppercase;">Pendenza Stabile</div>
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
    const isTestMode = {str(test_mode).lower()};
    const simSpeedVal = {sim_speed};
    const simGradeVal = {sim_grade};
    
    let lastLat = null, lastLon = null, lastAlt = null, lastTime = null;
    let smoothSpeed = 0, stableGrade = 0, smoothWatt = 0;
    let windSpeedKmh = 0, windDirDeg = 0, bikeHeadingDeg = 0;

    function calcolaWatt(vKmh, gradePct, effWindKmh) {{
        if (vKmh < 2.0) return 0;
        
        const g = 9.81, rho = 1.225, eta = 0.95, crr = 0.004;
        const vMs = vKmh / 3.6;
        const vAria = Math.max(0, vMs + (effWindKmh / 3.6));
        const theta = Math.atan(gradePct / 100.0);

        const pGravita = pesoTotale * g * Math.sin(theta) * vMs;
        const pAria = 0.5 * rho * cda * Math.pow(vAria, 2) * vMs;
        const pRotolamento = crr * pesoTotale * g * Math.cos(theta) * vMs;

        return Math.max(0, Math.round((pGravita + pAria + pRotolamento) / eta));
    }}

    if (isTestMode) {{
        document.getElementById('speedVal').innerText = simSpeedVal.toFixed(1) + " km/h";
        document.getElementById('gradeVal').innerText = simGradeVal.toFixed(1) + " %";
        let w = calcolaWatt(simSpeedVal, simGradeVal, 0);
        document.getElementById('wattVal').innerText = w + " W";
    }}

    document.getElementById('startSensors').addEventListener('click', () => {{
        if ("geolocation" in navigator && !isTestMode) {{
            navigator.geolocation.watchPosition((pos) => {{
                let now = Date.now();
                let rawSpd = pos.coords.speed ? (pos.coords.speed * 3.6) : 0;

                // Deadband per azzerare la velocità sotto i 2.0 km/h
                if (rawSpd < 2.0) {{
                    smoothSpeed = 0;
                    stableGrade = 0;
                }} else {{
                    smoothSpeed = (smoothSpeed * 0.7) + (rawSpd * 0.3);
                }}

                document.getElementById('speedVal').innerText = smoothSpeed.toFixed(1) + " km/h";

                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const alt = pos.coords.altitude;

                // ALGORITMO PENDENZA STABILE (FINANDRA DI DISTANZA MINIMA 15m)
                if (smoothSpeed >= 2.0 && alt !== null && lastLat !== null && lastTime !== null) {{
                    let dt = (now - lastTime) / 1000.0;
                    let dist = getDistance(lastLat, lastLon, lat, lon);

                    // Calcola la pendenza solo se sono stati percorsi almeno 15 metri effettivi
                    if (dist >= 15.0 && dt >= 2.0) {{
                        let rawGrade = ((alt - lastAlt) / dist) * 100;
                        
                        // Ignora letture assurde
                        if (rawGrade <= 22.0 && rawGrade >= -18.0) {{
                            // Smussamento ultra-progressivo (Max variazione limitata)
                            let targetGrade = (stableGrade * 0.8) + (rawGrade * 0.2);
                            
                            // Limita il cambio massimo di pendenza a 0.5% per secondo per eliminare gli sbalzi
                            let maxChange = 0.5 * dt;
                            if (Math.abs(targetGrade - stableGrade) > maxChange) {{
                                stableGrade += (targetGrade > stableGrade ? maxChange : -maxChange);
                            }} else {{
                                stableGrade = targetGrade;
                            }}
                        }}
                        lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now;
                    }}
                }} else if (smoothSpeed < 2.0) {{
                    stableGrade = 0;
                    if (alt !== null) {{ lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now; }}
                }} else if (alt !== null) {{
                    lastLat = lat; lastLon = lon; lastAlt = alt; lastTime = now;
                }}

                document.getElementById('gradeVal').innerText = stableGrade.toFixed(1) + " %";

                let targetWatt = calcolaWatt(smoothSpeed, stableGrade, 0);
                smoothWatt = Math.round((smoothWatt * 0.8) + (targetWatt * 0.2));

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
