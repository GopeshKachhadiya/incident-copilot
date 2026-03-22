import os
import osmnx as ox
import networkx as nx
import streamlit as st
from config import CITY_NAME, MAP_CENTER_LAT, MAP_CENTER_LNG

@st.cache_resource
def get_graph():
    bbox = (72.60, 23.14, 72.69, 23.25)
    graph_path = os.path.join("data", "gandhinagar_bbox.graphml")

    if os.path.exists(graph_path):
        try:
            return ox.load_graphml(graph_path)
        except:
            pass

    print(f"[GraphManager] Downloading Gandhinagar OSMnx via BBox: {bbox}...")
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive", simplify=True)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    os.makedirs("data", exist_ok=True)
    ox.save_graphml(G, graph_path)
    return G


print("[GraphManager] Initializing Gandhinagar Road Network...")
G = get_graph()
print(f"[GraphManager] Graph ready: {len(G.nodes)} nodes, {len(G.edges)} edges.")
