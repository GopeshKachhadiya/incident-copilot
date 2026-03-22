import math
from llm.hf_client import call_llm
from map_engine.graph_manager import G
import osmnx as ox
import networkx as nx

SYSTEM_CONTEXT = """You are a traffic diversion routing expert for Gandhinagar, Gujarat.
You receive incident data and A* computed alternate routes that avoid the blocked accident zone.
Write a clear, concise diversion plan for a traffic officer to implement immediately.
Include: activation sequence, estimated traffic redistribution percentages, expected clearance time.
Use bullet points. Keep under 200 words."""


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    return _haversine_km(lat1, lng1, lat2, lng2) * 1000.0


def _bearing(lat1, lng1, lat2, lng2) -> float:
    dlng = math.radians(lng2 - lng1)
    y = math.sin(dlng) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlng))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _make_heuristic(G_graph, target_node: int):
    t_lat = G_graph.nodes[target_node]["y"]
    t_lng = G_graph.nodes[target_node]["x"]
    def heuristic(u, v):
        u_lat = G_graph.nodes[u]["y"]
        u_lng = G_graph.nodes[u]["x"]
        return _haversine_m(u_lat, u_lng, t_lat, t_lng)
    return heuristic


def _path_to_route_info(G_graph, path: list, name: str) -> dict:
    coords = [(G_graph.nodes[n]["y"], G_graph.nodes[n]["x"]) for n in path]
    length_m = sum(G_graph[u][v][0].get("length", 0) for u, v in zip(path[:-1], path[1:]))
    duration_min = round((length_m / 1000.0) / 30.0 * 60.0, 1)
    return {
        "name": name,
        "distance_km": round(length_m / 1000.0, 2),
        "duration_min": duration_min,
        "coords": coords,
        "node_count": len(path),
    }


def _find_bracket_nodes(inc_lat: float, inc_lng: float, incident_node: int):
    candidates = []
    for node, data in G.nodes(data=True):
        if node == incident_node:
            continue
        d = _haversine_km(inc_lat, inc_lng, data["y"], data["x"])
        if 0.8 <= d <= 1.8:
            b = _bearing(inc_lat, inc_lng, data["y"], data["x"])
            candidates.append((node, data["y"], data["x"], d, b))

    if len(candidates) < 4:
        return None, None

    candidates.sort(key=lambda x: x[3])
    best_origin = candidates[len(candidates) // 4]
    origin_bearing = best_origin[4]

    best_dest = None
    best_angle_diff = 0
    for c in candidates:
        if c[0] == best_origin[0]:
            continue
        angle_diff = abs(((c[4] - origin_bearing + 360) % 360) - 180)
        if angle_diff < 60 and c[3] > best_origin[3] * 0.5:
            if angle_diff > best_angle_diff or best_dest is None:
                best_angle_diff = angle_diff
                best_dest = c

    if best_dest is None:
        best_dest = candidates[-1]

    return best_origin[0], best_dest[0]


def _compute_routes(incident: dict) -> dict:
    inc_lat = incident.get("location_lat", 23.2166)
    inc_lng = incident.get("location_lng", 72.6417)

    try:
        incident_node = ox.distance.nearest_nodes(G, inc_lng, inc_lat)

        if incident.get("manual_start_lat") and incident.get("manual_start_lng"):
            origin_node = ox.distance.nearest_nodes(G, incident["manual_start_lng"], incident["manual_start_lat"])
            dest_node   = ox.distance.nearest_nodes(G, incident["manual_end_lng"],   incident["manual_end_lat"])
        else:
            origin_node, dest_node = _find_bracket_nodes(inc_lat, inc_lng, incident_node)

        if origin_node is None or dest_node is None:
            return _fallback_result(inc_lat, inc_lng)

        heur_full = _make_heuristic(G, dest_node)
        try:
            orig_path = nx.astar_path(G, origin_node, dest_node, heuristic=heur_full, weight="length")
            original_route = _path_to_route_info(G, orig_path, "Original Route (Blocked )")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            original_route = None

        G_blocked = G.copy()
        if incident_node in G_blocked:
            G_blocked.remove_node(incident_node)

        nodes_to_block = [
            n for n, data in G.nodes(data=True)
            if n != origin_node and n != dest_node
            and _haversine_m(inc_lat, inc_lng, data["y"], data["x"]) < 100
        ]
        for n in nodes_to_block:
            if n in G_blocked:
                G_blocked.remove_node(n)

        alt_routes = []

        if origin_node in G_blocked and dest_node in G_blocked:
            try:
                heur_alt = _make_heuristic(G_blocked, dest_node)
                alt_path = nx.astar_path(G_blocked, origin_node, dest_node, heuristic=heur_alt, weight="length")
                if len(alt_path) >= 3:
                    r = _path_to_route_info(G_blocked, alt_path, "Alt Route A — A* Detour ")
                    alt_routes.append(r)
            except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXError) as e:
                print(f"[DiversionModule] Primary alt route failed: {e}")

        if len(alt_routes) < 2:
            dest_data = G.nodes[dest_node]
            for doffset_lat, doffset_lng in [(0.004, 0.002), (-0.003, 0.004), (0.002, -0.004), (-0.004, -0.002)]:
                try:
                    dest2 = ox.distance.nearest_nodes(G, dest_data["x"] + doffset_lng, dest_data["y"] + doffset_lat)
                    if dest2 not in G_blocked or dest2 == origin_node:
                        continue
                    heur_alt2 = _make_heuristic(G_blocked, dest2)
                    alt_path2 = nx.astar_path(G_blocked, origin_node, dest2, heuristic=heur_alt2, weight="length")
                    if len(alt_path2) >= 4:
                        r2 = _path_to_route_info(G_blocked, alt_path2, "Alt Route B — A* Detour ")
                        if not alt_routes or abs(r2["distance_km"] - alt_routes[0]["distance_km"]) > 0.2:
                            alt_routes.append(r2)
                            break
                except Exception:
                    continue

        if not alt_routes:
            if original_route:
                forced_route = dict(original_route)
                forced_route["name"] = "Forced Route (No Alternatives Available)"
                alt_routes = [forced_route]
            else:
                alt_routes = _fallback_routes(inc_lat, inc_lng)

        origin_coords = (G.nodes[origin_node]["y"], G.nodes[origin_node]["x"])
        dest_coords   = (G.nodes[dest_node]["y"],   G.nodes[dest_node]["x"])

        return {
            "origin_coords":      origin_coords,
            "dest_coords":        dest_coords,
            "original_route":     original_route,
            "alternative_routes": alt_routes,
        }

    except Exception as e:
        print(f"[DiversionModule] Routing error: {e}")
        return _fallback_result(inc_lat, inc_lng)


def _fallback_result(lat, lng):
    return {
        "origin_coords": None, "dest_coords": None,
        "original_route": None,
        "alternative_routes": _fallback_routes(lat, lng),
    }


def _fallback_routes(lat: float, lng: float) -> list:
    return [{
        "name": "Alt Route A (Fallback East detour) ",
        "distance_km": 1.4, "duration_min": 4.5,
        "coords": [
            (lat - 0.005, lng - 0.005), (lat - 0.002, lng + 0.006),
            (lat + 0.003, lng + 0.010), (lat + 0.008, lng + 0.005),
        ],
        "node_count": 4,
    }]


def _build_prompt(incident: dict, original_route: dict | None, alt_routes: list) -> str:
    orig_summary = (
        f"BLOCKED: {original_route['name']} — {original_route['distance_km']} km"
        if original_route else "Original route: unavailable (blocked)"
    )
    alt_summary = "\n".join(
        f"  • {r['name']}: {r['distance_km']} km, ~{r['duration_min']} min"
        for r in alt_routes
    )
    return f"""{SYSTEM_CONTEXT}

INCIDENT REPORT:
- Location    : {incident.get('road_name', 'Unknown')}
- Type        : {str(incident.get('accident_class') or 'unknown').replace('_', ' ').title()}
- Severity    : {incident.get('severity', 'unknown').upper()}
- Lanes blocked: {incident.get('lanes_blocked', 1)} lane(s)

ROUTING STATUS:
- {orig_summary}
- A* COMPUTED ALTERNATIVES (incident intersection blocked):
{alt_summary}

TASK: Write a traffic diversion plan. Include:
  1. Which alternate route to activate first and why
  2. Where to deploy officers / CMS signs
  3. Estimated traffic redistribution (%)
  4. Expected clearance time

DIVERSION PLAN:"""


class DiversionModule:
    def __init__(self):
        self.name = "A* Diversion Route Module"

    def run(self, incident: dict) -> dict:
        if not incident or not incident.get("accident_detected"):
            return {
                "agent": self.name, "status": "no_incident",
                "recommendation": "No active incident. No diversions needed.",
                "routes": [], "original_route": None, "raw_incident": incident,
            }

        route_data = _compute_routes(incident)
        alt_routes = route_data["alternative_routes"]
        orig_route = route_data["original_route"]
        response   = call_llm(_build_prompt(incident, orig_route, alt_routes), max_tokens=400, temperature=0.25)

        return {
            "agent":          self.name,
            "status":         "ok" if not response.startswith("ERROR:") else "error",
            "recommendation": response,
            "routes":         alt_routes,
            "original_route": orig_route,
            "raw_incident":   incident,
        }
