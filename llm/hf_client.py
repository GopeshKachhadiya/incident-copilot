import time
import requests
from config import HF_API_KEY, HF_API_URL

MAX_RETRIES     = 3
RETRY_DELAY     = 4
REQUEST_TIMEOUT = 60


def call_llm(prompt: str, max_tokens: int = 400, temperature: float = 0.3) -> str:
    if not HF_API_KEY or HF_API_KEY == "hf_YOUR_KEY_HERE":
        return _mock_response(prompt)

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "do_sample": temperature > 0,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True, "use_cache": False},
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "").strip()
                return str(data).strip()
            elif resp.status_code == 503:
                print(f"[LLM] Model loading (attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return f"ERROR: HTTP {resp.status_code} — {resp.text[:200]}"
        except requests.exceptions.Timeout:
            print(f"[LLM] Request timed out (attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            return f"ERROR: Network error — {str(e)}"

    return "ERROR: All retries exhausted. Check your HF_API_KEY and model availability."


def _mock_response(prompt: str) -> str:
    prompt_lower = prompt.lower()

    incident_road = "Unknown Road"
    for line in prompt.split("\n"):
        stripped = line.strip()
        if "incident road" in stripped.lower() or "location    :" in stripped.lower():
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                road_candidate = parts[1].strip()
                if road_candidate and road_candidate.lower() not in ("n/a", "unknown road", ""):
                    incident_road = road_candidate
                    break

    intersections = []
    in_intersections = False
    for line in prompt.split("\n"):
        stripped = line.strip()
        if "nearby intersections" in stripped.lower():
            in_intersections = True
            continue
        if in_intersections:
            if stripped.startswith("-"):
                name = stripped.lstrip("- ").split("(~")[0].strip()
                if name and "No nearby" not in name:
                    intersections.append(name)
            elif stripped and not stripped.startswith("-") and intersections:
                break

    if not intersections:
        intersections = [f"{incident_road} Junction", "Nearby Cross Road"]

    if "signal" in prompt_lower or "intersection" in prompt_lower:
        actions = [
            ("Extend green phase by 45s on approach from incident side", "+45s green"),
            ("Reduce cycle to 60s to prevent queue spillback", "Cycle → 60s"),
            ("Activate diversion signal mode (flashing yellow)", "Flashing yellow"),
            ("Hold red on incident-side approach, release after 90s", "Hold red 90s"),
        ]
        lines = []
        for i, inter in enumerate(intersections[:4]):
            action_text, duration = actions[i % len(actions)]
            lines.append(
                f"• {inter}: {action_text} — {duration} "
                f"— Congestion spilling from {incident_road} requires coordinated flow control"
            )
        return (
            f"SIGNAL RE-TIMING for incident on {incident_road}:\n"
            + "\n".join(lines)
            + f"\n\nAll {len(intersections[:4])} intersections updated for incident on {incident_road}."
        )

    elif "diversion" in prompt_lower or "route" in prompt_lower:
        nearby = intersections[0] if intersections else "Nearby Junction"
        return (
            f"DIVERSION ROUTE RECOMMENDATION for {incident_road}:\n\n"
            f"Primary: Redirect traffic via parallel roads avoiding {incident_road}.\n"
            f"• Activate diversion at {nearby} immediately\n"
            f"• Deploy CMS signs 500m before {incident_road} incident point\n"
            f"• Estimated traffic redistribution: 60% to alternate roads, 40% to internal grid\n\n"
            f"Expected queue clearance: 8-12 minutes."
        )

    elif "alert" in prompt_lower or "public" in prompt_lower or "vms" in prompt_lower:
        road_upper = incident_road.upper()
        return (
            f"[VMS]\nACCIDENT ON {road_upper[:22]}\nUSE ALTERNATE ROUTE NOW\n\n"
            f"[RADIO]\nTraffic alert: An incident on {incident_road} is causing significant delays. "
            f"Drivers are advised to use alternative routes. "
            f"Emergency services are on scene. Allow extra 15-20 minutes travel time.\n\n"
            f"[SOCIAL]\n🚨 TRAFFIC ALERT: Accident on {incident_road}, Gandhinagar. "
            f"Major delays. Use alternate routes. Emergency crews on scene. "
            f"#GandhinagarTraffic #TrafficAlert #Gujarat"
        )

    elif "hospital" in prompt_lower or "medical" in prompt_lower:
        return (
            f"MEDICAL ALERT — Incident on {incident_road}. "
            f"Dispatch ambulance to GPS coordinates listed. "
            f"Severity and trauma protocol activation required immediately."
        )

    elif "fire" in prompt_lower or "rescue" in prompt_lower:
        return (
            f"FIRE & RESCUE DISPATCH — Incident on {incident_road}. "
            f"Deploy rescue unit and fire tender. "
            f"Possible vehicle entrapment. Secure perimeter immediately."
        )

    else:
        return (
            f"Incident confirmed on {incident_road}. Severity assessed from incoming data. "
            f"All four response protocols have been activated. Awaiting officer confirmation."
        )
