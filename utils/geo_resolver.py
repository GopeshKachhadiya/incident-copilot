import math
from typing import Optional


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _clean_name(raw) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, list):
        parts = [str(p) for p in raw if p and str(p).lower() not in ("nan", "none", "")]
        return " / ".join(parts) if parts else None
    s = str(raw).strip()
    return s if s.lower() not in ("nan", "none", "") else None


def resolve_incident_roads(lat: float, lng: float, radius_km: float = 1.5, max_intersections: int = 6) -> dict:
    try:
        from map_engine.graph_manager import G
        import osmnx as ox

        nearest_node = ox.distance.nearest_nodes(G, lng, lat)

        incident_road_names = set()
        for _, _, edge_data in G.edges(nearest_node, data=True):
            name = _clean_name(edge_data.get("name"))
            if name:
                incident_road_names.add(name)
        for _, v, edge_data in G.in_edges(nearest_node, data=True):
            name = _clean_name(edge_data.get("name"))
            if name:
                incident_road_names.add(name)

        incident_road = " / ".join(sorted(incident_road_names)) or "Unknown Road"

        nearby_road_names = set()
        degree_map = dict(G.degree())

        candidates = []
        for node, data in G.nodes(data=True):
            if node == nearest_node:
                continue
            node_lat = data.get("y", 0)
            node_lng = data.get("x", 0)
            dist = _haversine_km(lat, lng, node_lat, node_lng)
            if dist <= radius_km:
                degree = degree_map.get(node, 0)
                candidates.append((node, data, dist, degree))

        candidates.sort(key=lambda x: (-x[3], x[2]))

        intersection_names = []
        seen = set()

        for node, data, dist, degree in candidates:
            if len(intersection_names) >= max_intersections:
                break

            node_roads = set()
            for _, _, ed in G.edges(node, data=True):
                n = _clean_name(ed.get("name"))
                if n:
                    node_roads.add(n)
            for _, _, ed in G.in_edges(node, data=True):
                n = _clean_name(ed.get("name"))
                if n:
                    node_roads.add(n)

            for road in node_roads:
                nearby_road_names.add(road)

            if degree >= 3 and len(node_roads) >= 2:
                label = " & ".join(sorted(node_roads)[:2])
                if label not in seen:
                    seen.add(label)
                    intersection_names.append(f"{label} (~{dist*1000:.0f}m)")

        nearby_road_names.discard(incident_road)
        for r in incident_road_names:
            nearby_road_names.discard(r)

        return {
            "incident_road":        incident_road,
            "nearby_intersections": intersection_names[:max_intersections],
            "nearby_roads":         sorted(nearby_road_names)[:8],
        }

    except Exception as e:
        print(f"[GeoResolver] Failed to resolve roads: {e}")
        return {
            "incident_road":        "Unknown Road",
            "nearby_intersections": [],
            "nearby_roads":         [],
        }
