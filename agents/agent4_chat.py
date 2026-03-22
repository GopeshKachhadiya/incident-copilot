from llm.hf_client import call_llm
from map_engine.graph_manager import G
import osmnx as ox

GANDHINAGAR_KNOWLEDGE = """
Gandhinagar is built on a grid system with numbered Circles (S1-S30) and Sectors.
Key landmarks and their rough locations:
- PDEU (Pandit Deendayal Energy University): SE Corner of the city (near NH-147).
- GNLU (Gujarat National Law University): Near Koba Cross Roads.
- Akshardham Temple: Central Gandhinagar (Sector 20 area).
- Infocity: Major IT hub near the SW entrance (Koba-Sargasan axis).
- Koba Circle: Main junction for entry from Ahmedabad.
- Secretariat: In the heart of the "Capital Complex" grid.
"""

SYSTEM_CONTEXT = f"""You are an AI traffic co-pilot for Gandhinagar city.
You have access to the full OSMnx drive network (S1-S30 circles and all sectors).
Use the following Knowledge Base for city context:
{GANDHINAGAR_KNOWLEDGE}

When asked about locations, refer to them by their Gandhinagar names (Circles/Sectors).
Answer directly and concisely based on real-time incident data.
If an incident is near a university or circle, mention it.
Keep answers under 120 words."""


class ChatModule:
    def __init__(self):
        self.name = "Officer Q&A Module"
        self.history: list[dict] = []
        self.max_history_turns = 8

    def reset(self):
        self.history = []

    def ask(self, question: str, incident: dict) -> str:
        incident_context = _format_incident_context(incident)
        prompt = _build_prompt(question, incident_context, self.history)
        response = call_llm(prompt, max_tokens=250, temperature=0.3)
        self.history.append({"role": "officer", "content": question})
        self.history.append({"role": "ai",      "content": response})
        if len(self.history) > self.max_history_turns * 2:
            self.history = self.history[-(self.max_history_turns * 2):]
        return response

    def get_history(self) -> list[dict]:
        return self.history


def _format_incident_context(incident: dict | None) -> str:
    if not incident:
        return "No active incident currently logged."
    if not incident.get("accident_detected", False):
        return "No active incident detected at this time."
    return (
        f"Active incident at {incident.get('road_name', 'Unknown')}. "
        f"Type: {str(incident.get('accident_class') or 'N/A').replace('_', ' ')}. "
        f"Severity: {incident.get('severity', 'N/A')}. "
        f"Lanes blocked: {incident.get('lanes_blocked', 0)}. "
        f"Detection confidence: {float(incident.get('detection_conf', 0)):.0%}. "
        f"Timestamp: {incident.get('timestamp', 'N/A')}."
    )


def _build_prompt(question: str, incident_context: str, history: list) -> str:
    history_str = ""
    if history:
        for turn in history[-6:]:
            role = "Officer" if turn["role"] == "officer" else "AI Co-Pilot"
            history_str += f"{role}: {turn['content']}\n"

    return f"""{SYSTEM_CONTEXT}

CURRENT INCIDENT STATUS:
{incident_context}

{"CONVERSATION SO FAR:" + chr(10) + history_str if history_str else ""}

Officer: {question}
AI Co-Pilot:"""
