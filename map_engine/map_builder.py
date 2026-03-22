import math
import random
import folium
import streamlit as st
from config import MAP_CENTER_LAT, MAP_CENTER_LNG, MAP_ZOOM
from map_engine.graph_manager import G
import osmnx as ox

SEVERITY_COLOURS = {
    "high":   "#E24B4A",
    "medium": "#EF9F27",
    "low":    "#639922",
    "none":   "#639922",
}


def _congestion_colour(ratio: float) -> str:
    if ratio < 0.05:
        return "#27AE60"
    elif ratio < 0.12:
        return "#F4D03F"
    elif ratio < 0.20:
        return "#E67E22"
    else:
        return "#E24B4A"


@st.cache_data
def get_road_network_geojson(_incident_lat: float = None, _incident_lng: float = None, _density_level: str = "high"):
    try:
        nodes, edges = ox.graph_to_gdfs(G)
        display_edges = edges.copy()

        import numpy as np
        hw_col = display_edges["highway"].astype(str)

        high = np.where(hw_col.str.contains("motorway|trunk"), 0.08,
               np.where(hw_col.str.contains("primary|secondary"), 0.15,
               np.where(hw_col.str.contains("tertiary|residential"), 0.22, 0.10)))
        low = np.where(hw_col.str.contains("motorway|trunk"), 0.0,
              np.where(hw_col.str.contains("primary|secondary"), 0.02,
              np.where(hw_col.str.contains("tertiary|residential"), 0.03, 0.0)))

        np.random.seed(42)
        base = np.random.uniform(low, high)

        if _incident_lat and _incident_lng:
            u_nodes  = display_edges.index.get_level_values(0)
            u_coords = nodes.loc[u_nodes, ["y", "x"]]
            dists = np.sqrt(
                (u_coords["y"].values - _incident_lat)**2 +
                (u_coords["x"].values - _incident_lng)**2
            ) * 111.0
            if _density_level == "low":
                base = np.where(dists < 0.6, 0.0, base)
            else:
                base = np.where(dists < 0.3, base + 0.55,
                       np.where(dists < 0.6, base + 0.25,
                       np.where(dists < 1.0, base + 0.10, base)))
            base = np.clip(base, 0.0, 1.0)

        display_edges["congestion_ratio"] = base
        display_edges["color"] = display_edges["congestion_ratio"].apply(_congestion_colour)

        if "name" in display_edges.columns:
            display_edges["name"] = display_edges["name"].apply(
                lambda x: " / ".join(x) if isinstance(x, list) else (str(x) if str(x) != "nan" else "Unnamed Street")
            )
        else:
            display_edges["name"] = "Unnamed Street"

        display_edges["weight"] = np.where(hw_col.str.contains("primary|motorway|trunk"), 3, 2)

        cols = ["geometry", "name", "color", "weight", "congestion_ratio"]
        available = [c for c in cols if c in display_edges.columns]
        return display_edges[available].to_json()

    except Exception as e:
        print(f"[MapBuilder] Error generating GeoJSON: {e}")
        return None


def build_map(
    incident: dict | None = None,
    diversion_result: dict | None = None,
    signal_result: dict | None = None,
    cameras: list[dict] | None = None,
    manual_points: dict | None = None,
    hide_network: bool = False,
) -> folium.Map:
    def _is_valid(val):
        try:
            return val is not None and math.isfinite(float(val))
        except:
            return False

    inc_dict   = (incident or {})
    det_active = inc_dict.get("accident_detected", False)
    inc_lat    = inc_dict.get("location_lat") if det_active else None
    inc_lng    = inc_dict.get("location_lng") if det_active else None

    if not _is_valid(inc_lat) or not _is_valid(inc_lng):
        inc_lat, inc_lng = None, None

    density = inc_dict.get("density_level", "high")

    m = folium.Map(
        location=[MAP_CENTER_LAT, MAP_CENTER_LNG],
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
        control_scale=True,
    )

    if manual_points:
        if manual_points.get("accident"):
            pt = manual_points["accident"]
            if _is_valid(pt.get("lat")) and _is_valid(pt.get("lng")):
                folium.Marker(
                    location=[pt["lat"], pt["lng"]],
                    tooltip=" Pending Accident Point",
                    icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
                ).add_to(m)
        if manual_points.get("start"):
            pt = manual_points["start"]
            if _is_valid(pt.get("lat")) and _is_valid(pt.get("lng")):
                folium.Marker(
                    location=[pt["lat"], pt["lng"]],
                    tooltip=" Pending Start Route Point",
                    icon=folium.Icon(color="green", icon="play", prefix="fa"),
                ).add_to(m)
        if manual_points.get("end"):
            pt = manual_points["end"]
            if _is_valid(pt.get("lat")) and _is_valid(pt.get("lng")):
                folium.Marker(
                    location=[pt["lat"], pt["lng"]],
                    tooltip=" Pending End Route Point",
                    icon=folium.Icon(color="purple", icon="flag-checkered", prefix="fa"),
                ).add_to(m)

    if not hide_network:
        try:
            geojson_data = get_road_network_geojson(inc_lat, inc_lng, density)
            if geojson_data:
                folium.GeoJson(
                    geojson_data,
                    name="Road Congestion",
                    style_function=lambda x: {
                        "color":   x["properties"].get("color", "#27AE60"),
                        "weight":  x["properties"].get("weight", 2),
                        "opacity": 0.75,
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name", "congestion_ratio"],
                        aliases=["Street:", "Congestion:"],
                        labels=True,
                        style="font-size:12px",
                    ),
                ).add_to(m)
        except Exception as e:
            print(f"[MapBuilder] Error adding road network: {e}")

    if incident and inc_lat is not None and inc_lng is not None:
        severity = incident.get("severity", "medium")
        colour   = SEVERITY_COLOURS.get(severity, "#E24B4A")
        cls      = str(incident.get("accident_class") or "unknown").replace("_", " ").title()

        folium.CircleMarker(
            location=[inc_lat, inc_lng],
            radius=30, color=colour, fill=True,
            fill_color=colour, fill_opacity=0.15, weight=2, opacity=0.5,
        ).add_to(m)

        folium.Marker(
            location=[inc_lat, inc_lng],
            popup=folium.Popup(_incident_popup_html(incident), max_width=290),
            tooltip=f" ACCIDENT: {cls} | {severity.upper()}",
            icon=folium.Icon(
                color="red" if severity == "high" else "orange",
                icon="exclamation-triangle", prefix="fa",
            ),
        ).add_to(m)

        _add_bbox_overlay(m, incident, inc_lat, inc_lng, colour)

    if diversion_result:
        original_route = diversion_result.get("original_route")
        if original_route and original_route.get("coords"):
            coords = [c for c in original_route["coords"] if _is_valid(c[0]) and _is_valid(c[1])]
            if len(coords) >= 2:
                folium.PolyLine(
                    locations=coords, color="#E24B4A", weight=6,
                    opacity=0.9, dash_array="10 6",
                    tooltip=f" {original_route['name']} — BLOCKED",
                ).add_to(m)
                folium.Marker(
                    location=coords[len(coords) // 2],
                    icon=folium.DivIcon(
                        html=(
                            '<div style="background:#E24B4A;color:white;padding:3px 8px;'
                            'border-radius:4px;font-size:11px;font-weight:bold;'
                            'white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.4)">'
                            ' BLOCKED</div>'
                        ),
                        icon_size=(80, 22), icon_anchor=(40, 11),
                    ),
                ).add_to(m)

        alt_colours = ["#27AE60", "#1ABC9C", "#2ECC71"]
        alt_routes  = diversion_result.get("routes", [])

        for i, route in enumerate(alt_routes):
            raw_coords = route.get("coords", [])
            coords     = [c for c in raw_coords if _is_valid(c[0]) and _is_valid(c[1])]
            if len(coords) < 2:
                continue
            is_forced = "Forced" in route.get("name", "")
            alt_col = "#E24B4A" if is_forced else alt_colours[i % len(alt_colours)]

            folium.PolyLine(
                locations=coords, color=alt_col, weight=6, opacity=0.90,
                dash_array="10 6" if is_forced else None,
                tooltip=(
                    f" {route['name']} — {route['distance_km']} km · "
                    f"~{route['duration_min']} min"
                ),
            ).add_to(m)

            folium.CircleMarker(
                location=coords[0], radius=7, color=alt_col,
                fill=True, fill_color=alt_col, fill_opacity=0.95,
                tooltip=f"{route['name']} — Start",
            ).add_to(m)

            folium.Marker(
                location=coords[-1],
                icon=folium.DivIcon(
                    html=(
                        f'<div style="background:{alt_col};color:white;padding:3px 8px;'
                        f'border-radius:4px;font-size:11px;font-weight:bold;'
                        f'white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.4)">'
                        f' {route["name"]}</div>'
                    ),
                    icon_size=(100, 22), icon_anchor=(50, 11),
                ),
            ).add_to(m)

    if signal_result and signal_result.get("status") == "ok" and signal_result.get("intersections"):
        if inc_lat and inc_lng:
            offsets = [
                (0.003, 0.0), (-0.003, 0.0), (0.0, 0.003),
                (0.0, -0.003), (0.002, 0.002), (-0.002, -0.002)
            ]
            for idx, inter_name in enumerate(signal_result["intersections"]):
                if idx >= len(offsets): break
                dlat, dlng = offsets[idx]
                s_lat, s_lng = inc_lat + dlat, inc_lng + dlng
                folium.Marker(
                    location=[s_lat, s_lng],
                    tooltip=f"🚦 {inter_name} (Flow Controlled)",
                    icon=folium.DivIcon(
                        html=(
                            '<div style="background:#2b2b2b;color:#00ffcc;padding:4px 6px;'
                            'border-radius:6px;font-size:10px;font-weight:bold;text-align:center;'
                            'white-space:nowrap;box-shadow:0 2px 5px rgba(0,0,0,0.5);border:1px solid #00ffcc;">'
                            '🚦 Signal<br>Flow Ctrl</div>'
                        ),
                        icon_size=(90, 30), icon_anchor=(45, 15),
                    ),
                ).add_to(m)

    if cameras:
        for cam in cameras:
            folium.Marker(
                location=[cam["lat"], cam["lng"]],
                tooltip=f"📷 {cam.get('id', 'Camera')}",
                icon=folium.Icon(color="blue", icon="video-camera", prefix="fa"),
            ).add_to(m)

    folium.LayerControl().add_to(m)
    _add_legend(m)
    return m


def _incident_popup_html(incident: dict) -> str:
    cls      = str(incident.get("accident_class") or "N/A").replace("_", " ").title()
    severity = incident.get("severity", "N/A").upper()
    lanes    = incident.get("lanes_blocked", "N/A")
    det_conf = f"{float(incident.get('detection_conf', 0)):.0%}"
    cls_conf = f"{float(incident.get('class_conf', 0)):.0%}"
    ts       = incident.get("timestamp", "N/A")
    road     = incident.get("road_name", "N/A")
    cam      = incident.get("camera_id", "N/A")
    colour   = SEVERITY_COLOURS.get(incident.get("severity", "medium"), "#E24B4A")

    return f"""
    <div style="font-family:sans-serif;font-size:13px;min-width:230px">
      <div style="background:{colour};color:white;padding:6px 10px;
                  border-radius:4px 4px 0 0;font-weight:bold;font-size:14px">
         {cls}
      </div>
      <div style="padding:8px 10px;border:1px solid #ddd;border-top:none;border-radius:0 0 4px 4px">
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="color:#888;padding:2px">Severity</td>
              <td style="font-weight:bold;color:{colour}">{severity}</td></tr>
          <tr><td style="color:#888;padding:2px">Road</td><td>{road}</td></tr>
          <tr><td style="color:#888;padding:2px">Lanes blocked</td><td>{lanes}</td></tr>
          <tr><td style="color:#888;padding:2px">Camera</td><td>{cam}</td></tr>
          <tr><td style="color:#888;padding:2px">Detection</td><td>{det_conf} confidence</td></tr>
          <tr><td style="color:#888;padding:2px">Classification</td><td>{cls_conf} confidence</td></tr>
          <tr><td style="color:#888;padding:2px">Time</td><td>{ts}</td></tr>
        </table>
      </div>
    </div>
    """


def _add_bbox_overlay(m, incident, lat, lng, colour):
    x1 = incident.get("bbox_x1")
    if x1 is None:
        return
    offset = 0.0003
    folium.Rectangle(
        bounds=[[lat - offset, lng - offset], [lat + offset, lng + offset]],
        color=colour, weight=2, fill=True, fill_color=colour,
        fill_opacity=0.10, tooltip="Detected accident zone", dash_array="6",
    ).add_to(m)


def _add_legend(m):
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
                background:white;padding:12px 16px;border-radius:10px;
                border:1px solid #ddd;font-family:sans-serif;font-size:12px;
                box-shadow:0 2px 12px rgba(0,0,0,0.18);min-width:190px">
      <b style="font-size:13px"> Map Legend</b><br><br>
      <b style="font-size:11px;color:#888">ROAD CONGESTION</b><br>
      <span style="color:#27AE60;font-size:16px">━</span> Free flow (clear)<br>
      <span style="color:#F4D03F;font-size:16px">━</span> Light congestion<br>
      <span style="color:#E67E22;font-size:16px">━</span> Moderate congestion<br>
      <span style="color:#E24B4A;font-size:16px">━</span> Heavy / blocked<br><br>
      <b style="font-size:11px;color:#888">ROUTES</b><br>
      <span style="color:#E24B4A;font-size:16px">╌</span> Blocked original route<br>
      <span style="color:#27AE60;font-size:16px">━</span> A* alternative route<br><br>
      <b style="font-size:11px;color:#888">MARKERS</b><br>
      <span style="color:#E24B4A">●</span> High severity incident<br>
      <span style="color:#EF9F27">●</span> Medium severity incident<br>
      <span style="color:#0066ff">📷</span> Traffic camera
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
