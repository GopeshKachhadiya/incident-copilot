import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from llm.hf_client import call_llm


def _get_env():
    return {
        "user":     os.getenv("EMAIL_USER", "").strip(),
        "password": os.getenv("EMAIL_PASS", "").replace(" ", "").strip(),
        "hospital": os.getenv("HOSPITAL_EMAIL", "").strip(),
        "fire":     os.getenv("FIRE_DEPT_EMAIL", "").strip(),
        "lat":      float(os.getenv("MAP_CENTER_LAT", "23.2166")),
        "lng":      float(os.getenv("MAP_CENTER_LNG", "72.6417")),
    }


def _generate_hospital_email(incident: dict) -> tuple:
    road     = incident.get("road_name", "Unknown Road")
    lat      = incident.get("location_lat", "N/A")
    lng      = incident.get("location_lng", "N/A")
    severity = incident.get("severity", "high").upper()
    acc_type = str(incident.get("accident_class") or "Accident").replace("_", " ").title()
    lanes    = incident.get("lanes_blocked", "?")
    ts       = incident.get("timestamp", "N/A")

    prompt = f"""[INST]
You are an AI emergency coordinator sending an alert to a HOSPITAL emergency department.
Write a short, clinical dispatch notification. Focus on MEDICAL RESPONSE NEEDS.
Do NOT add greetings. Max 4 sentences. Professional tone.

Incident: {acc_type} | Severity: {severity} | Road: {road}
GPS: {lat}, {lng} | Lanes Blocked: {lanes} | Time: {ts}
[/INST]"""

    body = call_llm(prompt, max_tokens=130, temperature=0.1)
    if not body or "ERROR:" in body or "[Variable Message" in body:
        body = (
            f"MEDICAL ALERT — {acc_type.upper()} REPORTED\n\n"
            f"Incident Time: {ts}\nLocation: {road}\n"
            f"GPS (Ambulance Route): {lat}, {lng}\n"
            f"Severity: {severity} | Lanes Blocked: {lanes}\n\n"
            f"Please activate trauma protocol and dispatch ambulance immediately.\n"
            f"Expect multiple casualties. Prepare emergency bay."
        )
    subject = f"🚑 MEDICAL ALERT: {acc_type} at {road} — {severity} Severity"
    return subject, body


def _generate_fire_email(incident: dict) -> tuple:
    road     = incident.get("road_name", "Unknown Road")
    lat      = incident.get("location_lat", "N/A")
    lng      = incident.get("location_lng", "N/A")
    severity = incident.get("severity", "high").upper()
    acc_type = str(incident.get("accident_class") or "Accident").replace("_", " ").title()
    lanes    = incident.get("lanes_blocked", "?")
    ts       = incident.get("timestamp", "N/A")

    prompt = f"""[INST]
You are an AI emergency coordinator sending an alert to the FIRE DEPARTMENT rescue team.
Write a short, tactical dispatch notification. Focus on RESCUE AND SCENE MANAGEMENT.
Do NOT add greetings. Max 4 sentences. Use operational tone.

Incident: {acc_type} | Severity: {severity} | Road: {road}
GPS: {lat}, {lng} | Lanes Blocked: {lanes} | Time: {ts}
[/INST]"""

    body = call_llm(prompt, max_tokens=130, temperature=0.1)
    if not body or "ERROR:" in body or "[Variable Message" in body:
        body = (
            f"FIRE & RESCUE DISPATCH — {acc_type.upper()}\n\n"
            f"Incident Time: {ts}\nLocation: {road}\n"
            f"GPS (Scene Access): {lat}, {lng}\n"
            f"Severity: {severity} | Lanes Blocked: {lanes}\n\n"
            f"Possible vehicle entrapment. Fuel spill/fire risk cannot be ruled out.\n"
            f"Deploy rescue unit and fire tender immediately. Secure perimeter."
        )
    subject = f"🔥 RESCUE DISPATCH: {acc_type} at {road} — {severity} Severity"
    return subject, body


class DispatchModule:
    def __init__(self):
        self._last_notified_timestamp = None

    def run(self, incident: dict) -> dict:
        if not incident or not incident.get("accident_detected", False):
            return {"status": "no_incident"}

        ts = incident.get("timestamp")
        if ts and ts == self._last_notified_timestamp:
            return {"status": "skipped", "reason": "Already notified for this incident"}
        if ts:
            self._last_notified_timestamp = ts

        env = _get_env()
        hospital_subject, hospital_body = _generate_hospital_email(incident)
        fire_subject,     fire_body     = _generate_fire_email(incident)

        print(f"[Agent 5] Hospital email:\nSubject: {hospital_subject}\n{hospital_body}\n")
        print(f"[Agent 5] Fire email:\nSubject: {fire_subject}\n{fire_body}\n")

        emails_sent = []
        errors      = []

        if not env["user"] or not env["password"]:
            print("[Agent 5] No credentials — simulating dispatch.")
            return {
                "status": "success",
                "emails_sent": ["Hospital (SIMULATED)", "Fire Service (SIMULATED)"],
                "errors": [], "hospital_body": hospital_body, "fire_body": fire_body,
                "hospital_subject": hospital_subject, "fire_subject": fire_subject,
                "message": "No credentials — dispatch simulated.",
            }

        targets = [
            ("Hospital",     env["hospital"], hospital_subject, hospital_body),
            ("Fire Service", env["fire"],     fire_subject,     fire_body),
        ]

        for name, addr, subject, body in targets:
            if not addr:
                errors.append(f"{name}: no email address in .env")
                continue
            try:
                msg = MIMEMultipart()
                msg["From"] = env["user"]
                msg["To"]   = addr
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as srv:
                    srv.ehlo(); srv.starttls(); srv.ehlo()
                    srv.login(env["user"], env["password"])
                    srv.send_message(msg)
                emails_sent.append(f"{name} ({addr})")
                print(f"[Agent 5] Sent {name} email to {addr}")
            except smtplib.SMTPAuthenticationError:
                err = f"{name}: Gmail auth failed — regenerate App Password"
                errors.append(err); print(f"[Agent 5] {err}")
            except Exception as e:
                err = f"{name}: {str(e)}"
                errors.append(err); print(f"[Agent 5] {err}")

        status  = "success" if emails_sent else "failed"
        message = f"Sent to: {', '.join(emails_sent)}" if emails_sent else f"Failed: {'; '.join(errors)}"

        return {
            "status": status, "emails_sent": emails_sent, "errors": errors,
            "hospital_body": hospital_body, "fire_body": fire_body,
            "hospital_subject": hospital_subject, "fire_subject": fire_subject,
            "message": message,
        }
