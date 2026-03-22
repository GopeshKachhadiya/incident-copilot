import re
from llm.hf_client import call_llm

SYSTEM_CONTEXT = "You are a public information officer for a city traffic management centre.\nYou draft emergency traffic alerts in three formats. Be concise, accurate, and professional.\nFollow the exact format requested for each type."


def _build_prompt(incident: dict) -> str:
    road     = incident.get("road_name", "Unknown Road")
    cls      = str(incident.get("accident_class") or "unknown").replace("_", " ").title()
    severity = incident.get("severity", "medium").upper()
    lanes    = incident.get("lanes_blocked", 1)
    speed    = incident.get("speed_zone_kmph", 60)

    return f"""{SYSTEM_CONTEXT}

INCIDENT DATA:
- Road        : {road}
- Accident type: {cls}
- Severity    : {severity}
- Lanes blocked: {lanes}
- Speed zone  : {speed} km/h
- Time        : {incident.get('timestamp', 'now')}

Draft THREE alerts in this EXACT format (include the labels):

[VMS]
<Line 1: max 24 uppercase characters>
<Line 2: max 24 uppercase characters>

[RADIO]
<One paragraph, 50-70 words, professional broadcast tone, include road name and advice>

[SOCIAL]
<Tweet-style post under 200 chars, use 1-2 relevant emoji, include 2-3 hashtags>

OUTPUT:"""


def _parse_response(text: str) -> dict:
    vms    = ""
    radio  = ""
    social = ""

    vms_match    = re.search(r'\[VMS\](.*?)(?:\[RADIO\]|\Z)', text, re.DOTALL | re.IGNORECASE)
    radio_match  = re.search(r'\[RADIO\](.*?)(?:\[SOCIAL\]|\Z)', text, re.DOTALL | re.IGNORECASE)
    social_match = re.search(r'\[SOCIAL\](.*?)(?:\[|\Z)', text, re.DOTALL | re.IGNORECASE)

    if vms_match:    vms    = vms_match.group(1).strip()
    if radio_match:  radio  = radio_match.group(1).strip()
    if social_match: social = social_match.group(1).strip()

    if not vms and not radio and not social:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 3:
            vms    = "\n".join(lines[:2])
            radio  = " ".join(lines[2:5])
            social = " ".join(lines[5:]) if len(lines) > 5 else lines[-1]

    return {
        "vms":    vms    or "ACCIDENT AHEAD\nEXPECT DELAYS",
        "radio":  radio  or "Traffic incident reported. Expect delays.",
        "social": social or "Traffic alert. Check local traffic for updates.",
    }


class AlertModule:
    def __init__(self):
        self.name = "Public Alert Agent"

    def run(self, incident: dict) -> dict:
        if not incident or not incident.get("accident_detected"):
            return {
                "agent": self.name, "status": "no_incident",
                "vms": "", "radio": "No active incident. All clear.",
                "social": "Roads clear. No active incidents.", "raw_incident": incident,
            }

        prompt   = _build_prompt(incident)
        response = call_llm(prompt, max_tokens=500, temperature=0.4)

        if response.startswith("ERROR:"):
            return {
                "agent": self.name, "status": "error",
                "vms": "ERROR", "radio": response, "social": "", "raw_incident": incident,
            }

        parsed = _parse_response(response)
        return {"agent": self.name, "status": "ok", **parsed, "raw_incident": incident}
