from llm.hf_client import call_llm
from utils.geo_resolver import resolve_incident_roads


def _build_prompt(incident: dict, geo_info: dict) -> str:
    road     = geo_info.get("incident_road") or incident.get("road_name", "Unknown Road")
    lat      = incident.get("location_lat", "N/A")
    lng      = incident.get("location_lng", "N/A")
    acc_type = str(incident.get("accident_class") or "accident").replace("_", " ").title()
    severity = incident.get("severity", "medium").upper()
    lanes    = incident.get("lanes_blocked", 1)
    speed    = incident.get("speed_zone_kmph", 60)
    ts       = incident.get("timestamp", "N/A")

    nearby_intersections = geo_info.get("nearby_intersections", [])
    nearby_roads         = geo_info.get("nearby_roads", [])

    intersections_text = (
        "\n".join(f"  - {i}" for i in nearby_intersections)
        if nearby_intersections else "  - (No nearby intersections found)"
    )
    roads_text = ", ".join(nearby_roads) if nearby_roads else "N/A"

    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert traffic signal control AI for Gandhinagar, Gujarat, India.
Your job is to adjust traffic signal phases at nearby intersections when an accident occurs.
Always respond in structured bullet points. Be specific with intersection names, direction, and exact seconds.
Only use the intersections and roads provided in the incident data below — do NOT invent or substitute generic names.
<|eot_id|><|start_header_id|>user<|end_header_id|>

INCIDENT ALERT:
- Type          : {acc_type}
- Incident Road : {road}
- Coordinates   : {lat}, {lng}
- Severity      : {severity}
- Lanes blocked : {lanes} lane(s)
- Speed zone    : {speed} km/h
- Timestamp     : {ts}

NEARBY INTERSECTIONS (from live OSMnx road graph — use these EXACTLY):
{intersections_text}

NEARBY AFFECTED ROADS: {roads_text}

TASK: For EACH intersection listed above, provide signal re-timing recommendations.
• [Intersection Name]: [Action] — [Duration] — [Reason]
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
Signal Re-timing Recommendations:
"""


class SignalModule:
    def __init__(self):
        self.name = "Signal Re-timing AI"

    def run(self, incident: dict) -> dict:
        if not incident or not incident.get("accident_detected"):
            return {
                "agent": self.name, "status": "no_incident",
                "recommendation": "No active incident. All signals running on normal schedule.",
                "intersections": [], "incident_road": None, "nearby_roads": [],
                "raw_incident": incident,
            }

        lat = incident.get("location_lat")
        lng = incident.get("location_lng")
        geo_info = {
            "incident_road": incident.get("road_name", "Unknown Road"),
            "nearby_intersections": [], "nearby_roads": [],
        }

        try:
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
        except (ValueError, TypeError):
            lat_f, lng_f = None, None

        if lat_f and lng_f and abs(lat_f) > 0.001 and abs(lng_f) > 0.001:
            geo_info = resolve_incident_roads(lat_f, lng_f)

        resolved_road = geo_info.get("incident_road") or incident.get("road_name", "Unknown Road")
        incident_enriched = {**incident, "road_name": resolved_road}

        prompt   = _build_prompt(incident_enriched, geo_info)
        response = call_llm(prompt, max_tokens=400, temperature=0.3)

        if response.startswith("ERROR:"):
            return {
                "agent": self.name, "status": "error",
                "recommendation": f"LLM unavailable: {response}",
                "intersections": [], "incident_road": resolved_road,
                "nearby_roads": geo_info.get("nearby_roads", []),
                "raw_incident": incident,
            }

        for trim_marker in ["Signal Re-timing Recommendations:", "assistant"]:
            if trim_marker in response:
                response = response.split(trim_marker, 1)[-1].strip()

        intersections = _extract_intersections(response, geo_info.get("nearby_intersections", []))

        return {
            "agent": self.name, "status": "ok",
            "recommendation": response,
            "intersections": intersections,
            "incident_road": resolved_road,
            "nearby_roads": geo_info.get("nearby_roads", []),
            "raw_incident": incident,
        }


def _extract_intersections(text: str, geo_intersections: list) -> list:
    geo_clean = [gi.split("(~")[0].strip() for gi in geo_intersections if gi]
    found = [g for g in geo_clean if g.lower() in text.lower()]
    if found:
        return found[:6]

    intersections = []
    location_keywords = [
        "Circle", "Cross", "Junction", "Road", "Chowk",
        "Roundabout", "Sector", "Gate", "Square", "Flyover", "&"
    ]
    for line in text.split("\n"):
        line = line.strip().lstrip("•-* ")
        name = line.split(":")[0].strip() if ":" in line else ""
        if name and any(kw in name for kw in location_keywords) and len(name) < 80:
            intersections.append(name)
    return intersections[:6]
