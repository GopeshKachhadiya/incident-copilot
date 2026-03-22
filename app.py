import time
import datetime
import os
import streamlit as st
from streamlit_folium import st_folium

from agents.orchestrator     import Orchestrator
from utils.feed_simulator    import FeedSimulator
from map_engine.map_builder  import build_map
from yolo.csv_merger         import load_incident_log, append_to_csv
from config                  import FEED_INTERVAL, MAP_CENTER_LAT, MAP_CENTER_LNG

st.set_page_config(
    page_title="Incident Co-Pilot | Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    :root {
        --bg-color: #0d1117;
        --card-bg: #161b22;
        --border-color: #30363d;
        --text-main: #c9d1d9;
        --text-dim: #8b949e;
        --accent-color: #58a6ff;
        --danger-color: #f85149;
        --warning-color: #d29922;
        --success-color: #3fb950;
    }

    .stApp { background-color: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; }

    .header-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background-color: var(--card-bg); border-bottom: 1px solid var(--border-color); margin-bottom: 20px; }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .logo-text { font-weight: 700; font-size: 1.2rem; letter-spacing: 1px; text-transform: uppercase; color: white; display: flex; align-items: center; gap: 10px; }
    .shield-icon { color: #58a6ff; font-size: 1.4rem; }
    .badge-critical { background-color: #440000; color: #ff4444; border: 1px solid #ff4444; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; }
    .incident-id { font-family: 'JetBrains Mono', monospace; color: var(--text-dim); font-size: 0.85rem; }
    .header-right { display: flex; align-items: center; gap: 20px; font-size: 0.85rem; color: var(--text-dim); }

    .dashboard-panel { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; height: 100%; min-height: 200px; display: flex; flex-direction: column; }
    .panel-title { font-size: 0.75rem; font-weight: 600; color: var(--text-dim); text-transform: uppercase; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
    .info-card { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px; margin-bottom: 10px; }
    .info-card-header { font-size: 0.8rem; font-weight: 600; margin-bottom: 5px; }
    .info-card-val { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: var(--accent-color); }
    .panel-scroll-content { flex-grow: 1; overflow-y: auto; font-size: 0.8rem; color: var(--text-main); line-height: 1.4; }

    .chat-bubble { background: #1f2937; border-radius: 8px; padding: 12px; margin-bottom: 10px; font-size: 0.85rem; }
    .chat-ai { border-left: 3px solid var(--accent-color); }
    .chat-user { border-right: 3px solid var(--text-dim); text-align: right; }

    .timeline-item { border-left: 2px solid var(--border-color); padding-left: 15px; padding-bottom: 15px; position: relative; }
    .timeline-time { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-dim); }
    .timeline-desc { font-size: 0.8rem; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def _init_session():
    if "orchestrator" not in st.session_state:
        orch = Orchestrator()
        orch.start()
        st.session_state.orchestrator = orch
    if "manual_active_point" not in st.session_state: st.session_state.manual_active_point = None
    if "manual_accident"     not in st.session_state: st.session_state.manual_accident = None
    if "manual_start"        not in st.session_state: st.session_state.manual_start = None
    if "manual_end"          not in st.session_state: st.session_state.manual_end = None
    if "last_clicked"        not in st.session_state: st.session_state.last_clicked = None

_init_session()
orch: Orchestrator = st.session_state.orchestrator
results  = orch.get_results()
incident = results.get("incident")
is_active = incident and incident.get("accident_detected", False)

with st.sidebar:
    st.title("🕹️ CONTROL PANEL")
    st.subheader("Manual Incident Setup")
    st.caption("Select type, then click location on Map.")
    c1, c2, c3 = st.columns(3)
    if c1.button("💥 Accident"): st.session_state.manual_active_point = "accident"
    if c2.button("🏁 A Start"): st.session_state.manual_active_point = "start"
    if c3.button("🏁 B End"):   st.session_state.manual_active_point = "end"

    if st.session_state.manual_active_point:
        st.info(f"Setting: {st.session_state.manual_active_point.upper()}")

    st.divider()
    mode = st.radio("Select Analysis Mode", ["Accident Detection", "Vehicle Density Check"])
    st.file_uploader(f"Upload for {mode}", type=['jpg','png','mp4'])

    if st.button("🚨 TRIGGER CUSTOM INCIDENT", type="primary", use_container_width=True):
        lat = st.session_state.manual_accident['lat'] if st.session_state.manual_accident else MAP_CENTER_LAT
        lng = st.session_state.manual_accident['lng'] if st.session_state.manual_accident else MAP_CENTER_LNG
        custom = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "accident_detected": True, "severity": "high", "road_name": "Custom Point",
            "location_lat": lat, "location_lng": lng, "accident_class": "manual_report", "camera_id": "MANUAL-01"
        }
        append_to_csv(custom)
        orch.trigger_now(custom)
        st.rerun()

    if st.button("🗑️ CLEAR CUSTOM POINTS", use_container_width=True):
        st.session_state.manual_accident = None
        st.session_state.manual_start    = None
        st.session_state.manual_end      = None
        st.rerun()

status_badge = '<span class="badge-critical">CRITICAL</span>' if is_active else ''
inc_id       = incident.get("camera_id", "LIVE SCAN") if is_active else "SCANNING..."
current_time = datetime.datetime.now().strftime("%H:%M:%S")

st.markdown(f"""
<div class="header-bar">
    <div class="header-left">
        <div class="logo-text">
            <span class="shield-icon">🛡️</span> INCIDENT CO-PILOT
        </div>
        {status_badge}
        <div class="incident-id">{inc_id}</div>
    </div>
    <div class="header-right">
        <div>FEEDS LIVE</div>
        <div>🕒 {current_time}</div>
    </div>
</div>
""", unsafe_allow_html=True)

m_col, r_col = st.columns([2.2, 1])

with m_col:
    st.markdown("<div class='panel-title'>LIVE MAP VIEW</div>", unsafe_allow_html=True)
    m = build_map(
        incident=incident,
        diversion_result=results.get("diversion"),
        signal_result=results.get("signal"),
        manual_points={
            "accident": st.session_state.manual_accident,
            "start":    st.session_state.manual_start,
            "end":      st.session_state.manual_end,
        }
    )
    map_data = st_folium(m, width=None, height=480, use_container_width=True)
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        if st.session_state.last_clicked != clicked:
            st.session_state.last_clicked = clicked
            if st.session_state.manual_active_point:
                st.session_state[f"manual_{st.session_state.manual_active_point}"] = clicked
                st.session_state.manual_active_point = None
                st.rerun()

    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        if st.button("🚨 Trigger Demo Incident", type="primary", use_container_width=True):
            demo = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "accident_detected": True, "severity": "high", "road_name": "S1 Circle", "camera_id": "CAM-GNR-01"}
            append_to_csv(demo)
            orch.trigger_now(demo)
            st.rerun()
    with btn2:
        if st.button("🔄 Refresh Map", use_container_width=True): st.rerun()
    with btn3:
        auto = st.checkbox("Auto-refresh")

with r_col:
    tab_t, tab_c = st.tabs(["TIMELINE", "AI CHAT"])
    with tab_t:
        if not is_active: st.info("Monitoring Gandhinagar Network...")
        else:
            st.markdown(f'<div class="timeline-item"><div class="timeline-time">{incident.get("timestamp")}</div><div class="timeline-desc"><b>Accident Identified</b> at {incident.get("road_name")}</div></div>', unsafe_allow_html=True)
    with tab_c:
        chat_history = orch.chat_agent.get_history()
        for turn in chat_history:
            cls = "chat-user" if turn["role"] == "officer" else "chat-bubble chat-ai"
            st.markdown(f'<div class="{cls}">{turn["content"]}</div>', unsafe_allow_html=True)
        q = st.chat_input("Ask Co-Pilot")
        if q:
            orch.chat_agent.ask(q, incident or {})
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns(4)

with p1:
    sig = results.get("signal")
    if sig and sig.get("status") not in ("no_incident", None):
        incident_road = sig.get("incident_road") or (incident or {}).get("road_name", "Unknown Road")
        nearby_int    = sig.get("intersections", [])
        nearby_roads  = sig.get("nearby_roads", [])
        rec_raw       = sig.get("recommendation") or ""

        # Parse LLM bullet points into individual signal items
        signal_items = []
        for line in rec_raw.split("\n"):
            line = line.strip().lstrip("•-* ")
            if ":" in line and len(line) > 10:
                parts = line.split(":", 1)
                name   = parts[0].strip()
                detail = parts[1].strip() if len(parts) > 1 else ""
                if name and len(name) < 80:
                    # Parse action / duration / reason if separated by —
                    segments = detail.split("—")
                    action   = segments[0].strip() if len(segments) > 0 else detail
                    duration = segments[1].strip() if len(segments) > 1 else ""
                    signal_items.append({"name": name, "action": action, "duration": duration})

        # Guarantee at least 2 items using nearby_intersections from geo resolver
        fallback_actions = [
            ("Extend green phase by 45s on approach from incident side", "+45s"),
            ("Reduce cycle to 60s to prevent queue spillback",           "Cycle 60s"),
            ("Activate diversion signal mode (flashing yellow)",         "Flash ⚠"),
            ("Hold red on incident-side approach",                       "Hold 90s"),
        ]
        if len(signal_items) < 2:
            signal_items = []
            sources = nearby_int if nearby_int else [f"{incident_road} & Junction", f"Nearby Cross Road"]
            for i, inter in enumerate(sources[:4]):
                name = inter.split("(~")[0].strip()
                act, dur = fallback_actions[i % len(fallback_actions)]
                signal_items.append({"name": name, "action": act, "duration": dur})

        # Build HTML cards (no raw LLM text injected into HTML)
        cards_html = ""
        for item in signal_items[:4]:
            cards_html += (
                f"<div style='background:rgba(255,255,255,0.03);border:1px solid #30363d;"
                f"border-radius:6px;padding:8px 10px;margin-bottom:6px;'>"
                f"<div style='font-size:0.72rem;font-weight:600;color:#58a6ff;margin-bottom:3px;'>"
                f"🚦 {item['name']}</div>"
                f"<div style='font-size:0.7rem;color:#c9d1d9;'>{item['action']}</div>"
            )
            if item["duration"]:
                cards_html += (
                    f"<div style='display:inline-block;background:#1c3a2a;color:#3fb950;"
                    f"border-radius:3px;padding:1px 6px;font-size:0.65rem;margin-top:3px;'>"
                    f"{item['duration']}</div>"
                )
            cards_html += "</div>"

        # Road chips
        chips_html = ""
        if nearby_roads:
            chips = "".join(
                f"<span style='display:inline-block;background:#1f2937;border:1px solid #30363d;"
                f"border-radius:4px;padding:1px 6px;margin:2px;font-size:0.65rem;color:#8b949e'>{r}</span>"
                for r in nearby_roads[:4]
            )
            chips_html = (
                f"<div style='margin:6px 0 4px;'>"
                f"<span style='font-size:0.62rem;color:#6b7280;text-transform:uppercase;'>Nearby Affected:</span>"
                f"<div style='margin-top:3px;'>{chips}</div></div>"
            )

        st.markdown(
            f"<div class='dashboard-panel'>"
            f"<div class='panel-title'>⚡ SIGNAL RE-TIMING</div>"
            f"<div style='font-size:0.68rem;color:#6b7280;margin-bottom:8px;text-transform:uppercase;'>Incident Road</div>"
            f"<div style='font-size:0.8rem;color:#58a6ff;font-weight:600;margin-bottom:10px;"
            f"font-family:monospace;padding:4px 8px;background:#0d1117;border-radius:4px;border-left:3px solid #58a6ff;'>"
            f"{incident_road}</div>"
            f"{chips_html}"
            f"<div style='overflow-y:auto;max-height:160px;'>{cards_html}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div class='dashboard-panel'><div class='panel-title'>⚡ SIGNAL RE-TIMING</div>"
            "<div style='color:#8b949e;font-size:0.8rem'>No adjustments needed.</div></div>",
            unsafe_allow_html=True
        )

with p2:
    div = results.get("diversion")
    if div and div.get("status") not in ("no_incident", None) and div.get("routes"):
        routes_html = ""
        for i, r in enumerate(div.get("routes", [])[:3]):
            label = "PRIMARY" if i == 0 else f"ALT {i}"
            routes_html += f"""<div class='info-card'>
              <div class='info-card-header'>{label}: {r.get('name','Route')}</div>
              <span class='info-card-val'>+{r.get('duration_min',0)} min</span>
              &nbsp;&nbsp;<span style='color:#d29922;font-size:0.75rem'>{r.get('distance_km','')} km</span>
            </div>"""
        html = f"<div class='dashboard-panel'><div class='panel-title'>🚀 DIVERSION ROUTES</div>{routes_html}</div>"
    else:
        html = "<div class='dashboard-panel'><div class='panel-title'>🚀 DIVERSION ROUTES</div><div style='color:#8b949e;font-size:0.8rem'>All routes clear.</div></div>"
    st.markdown(html, unsafe_allow_html=True)

with p3:
    alt = results.get("alerts")
    if alt and alt.get("status") not in ("no_incident", None):
        vms    = (alt.get("vms")    or "").replace("\n", "<br>")
        radio  = (alt.get("radio")  or "").replace("\n", "<br>")
        social = (alt.get("social") or "").replace("\n", "<br>")
        inner  = ""
        if vms:    inner += f"<div class='info-card'><div class='info-card-header'>📺 VMS Board</div><div style='font-size:0.75rem;'>{vms}</div></div>"
        if radio:  inner += f"<div class='info-card'><div class='info-card-header'>📻 Radio Alert</div><div style='font-size:0.75rem;'>{radio}</div></div>"
        if social: inner += f"<div class='info-card'><div class='info-card-header'>📱 Social Media</div><div style='font-size:0.75rem;'>{social}</div></div>"
        html = f"<div class='dashboard-panel'><div class='panel-title'>📢 PUBLIC ALERTS</div><div style='overflow-y:auto;max-height:200px;'>{inner}</div></div>"
    else:
        html = "<div class='dashboard-panel'><div class='panel-title'>📢 PUBLIC ALERTS</div><div style='color:#8b949e;font-size:0.8rem'>No active alerts.</div></div>"
    st.markdown(html, unsafe_allow_html=True)

with p4:
    disp = results.get("dispatch")
    if disp and disp.get("status") == "success":
        sent     = "<br>".join(disp.get("emails_sent", []))
        errs     = disp.get("errors", [])
        err_html = f"<div style='color:#f85149;font-size:0.72rem;margin-top:6px'>{'<br>'.join(errs)}</div>" if errs else ""
        html = f"""<div class='dashboard-panel'>
          <div class='panel-title'>🚑 EMERGENCY DISPATCH</div>
          <div class='info-card'>
            <div class='info-card-header'>Services Notified</div>
            <div style='color:#3fb950;font-size:0.8rem;font-weight:600;'>✅ {sent if sent else 'Dispatched'}</div>
          </div>{err_html}
        </div>"""
    elif disp and disp.get("status") == "failed":
        html = f"<div class='dashboard-panel'><div class='panel-title'>🚑 EMERGENCY DISPATCH</div><div style='color:#f85149;font-size:0.8rem'>❌ {disp.get('message','Failed')}</div></div>"
    else:
        html = "<div class='dashboard-panel'><div class='panel-title'>🚑 EMERGENCY DISPATCH</div><div style='color:#8b949e;font-size:0.8rem'>Standby — awaiting incident.</div></div>"
    st.markdown(html, unsafe_allow_html=True)

if auto:
    time.sleep(FEED_INTERVAL)
    st.rerun()
