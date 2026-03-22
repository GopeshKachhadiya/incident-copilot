import time
import threading
from datetime import datetime

from yolo.csv_merger import get_latest_incident
from agents.agent1_signal   import SignalModule
from agents.agent2_diversion import DiversionModule
from agents.agent3_alerts   import AlertModule
from agents.agent4_chat     import ChatModule
from agents.agent5_dispatch import DispatchModule
from config import FEED_INTERVAL


class Orchestrator:
    def __init__(self):
        self._running       = False
        self._thread        = None
        self._lock          = threading.Lock()
        self._last_ts       = None

        self._signal_agent   = SignalModule()
        self._diversion_agent = DiversionModule()
        self._alert_agent    = AlertModule()
        self._dispatch_agent = DispatchModule()
        self.chat_agent      = ChatModule()

        self._results: dict = {
            "incident": None, "signal": None, "diversion": None,
            "alerts": None, "dispatch": None,
            "geo_info": {}, "last_updated": None, "processing": False,
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[Orchestrator] Started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[Orchestrator] Stopped.")

    def get_results(self) -> dict:
        with self._lock:
            return dict(self._results)

    def get_incident(self) -> dict | None:
        with self._lock:
            return self._results.get("incident")

    def is_processing(self) -> bool:
        with self._lock:
            return self._results.get("processing", False)

    def trigger_now(self, incident: dict | None = None):
        if incident is None:
            incident = get_latest_incident()
        if incident:
            ts = incident.get("timestamp")
            if ts:
                self._last_ts = ts
            self._dispatch_agents(incident)

    def _poll_loop(self):
        while self._running:
            try:
                incident = get_latest_incident()
                if incident and self._is_new(incident):
                    self._dispatch_agents(incident)
            except Exception as e:
                print(f"[Orchestrator] Poll error: {e}")
            time.sleep(FEED_INTERVAL)

    def _is_new(self, incident: dict) -> bool:
        ts = incident.get("timestamp")
        if ts is None:
            return False
        if self._last_ts is None or ts != self._last_ts:
            self._last_ts = ts
            return True
        return False

    def _dispatch_agents(self, incident: dict):
        try:
            from utils.geo_resolver import resolve_incident_roads
            lat = incident.get("location_lat")
            lng = incident.get("location_lng")
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None

            if lat_f and lng_f and abs(lat_f) > 0.001 and abs(lng_f) > 0.001:
                geo_info = resolve_incident_roads(lat_f, lng_f)
                resolved_road = geo_info.get("incident_road") or incident.get("road_name", "Unknown Road")
                incident = {
                    **incident,
                    "road_name":            resolved_road,
                    "nearby_intersections": geo_info.get("nearby_intersections", []),
                    "nearby_roads":         geo_info.get("nearby_roads", []),
                }
                print(f"[Orchestrator] Geo-resolved: '{resolved_road}' | "
                      f"{len(geo_info.get('nearby_intersections', []))} nearby intersections")
            else:
                geo_info = {}
        except Exception as e:
            print(f"[Orchestrator] Geo-enrichment failed: {e}")
            geo_info = {}

        with self._lock:
            self._results["incident"]   = incident
            self._results["geo_info"]   = geo_info
            self._results["processing"] = True

        print(f"[Orchestrator] Dispatching agents for incident at {incident.get('road_name')}")

        results_1 = {}
        results_2 = {}
        results_3 = {}
        results_5 = {}

        def run_agent1():
            nonlocal results_1
            results_1 = self._signal_agent.run(incident)

        def run_agent2():
            nonlocal results_2
            results_2 = self._diversion_agent.run(incident)

        def run_agent3():
            nonlocal results_3
            results_3 = self._alert_agent.run(incident)

        def run_agent5():
            nonlocal results_5
            results_5 = self._dispatch_agent.run(incident)

        threads = [
            threading.Thread(target=run_agent1, daemon=True),
            threading.Thread(target=run_agent2, daemon=True),
            threading.Thread(target=run_agent3, daemon=True),
            threading.Thread(target=run_agent5, daemon=True),
        ]
        for t in threads: t.start()
        for t in threads: t.join(timeout=90)

        self.chat_agent.reset()

        with self._lock:
            self._results["signal"]    = results_1
            self._results["diversion"] = results_2
            self._results["alerts"]    = results_3
            if results_5.get("status") != "skipped":
                self._results["dispatch"] = results_5
            self._results["processing"]   = False
            self._results["last_updated"] = datetime.now().isoformat(timespec="seconds")

        print(f"[Orchestrator] All agents completed at {self._results['last_updated']}")
        print(f"[Orchestrator] Dispatch result: {results_5.get('status')} — {results_5.get('message','')}")
