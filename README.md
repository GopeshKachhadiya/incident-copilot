# 🚦 Incident Copilot — Smart City Traffic Incident Management System

> **LLM-powered multi-agent traffic incident co-pilot for Gandhinagar Smart City** — real-time incident detection, A* diversion routing, adaptive signal re-timing, public alert generation, and conversational officer chat.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Agents](#agents)
- [Screenshots](#screenshots)

---

## 🔍 Overview

**Incident Copilot** is a fully agentic, AI-driven command-center dashboard built for the Gandhinagar Smart City initiative. It integrates real-time traffic monitoring, automatic incident detection via computer vision, and a multi-agent orchestration layer that autonomously coordinates emergency diversion routing, traffic signal adjustments, and public alert broadcasts — all from a single Streamlit dashboard.

When a traffic incident is detected (accident, obstruction, roadblock), the system:
1. Detects and classifies the incident using YOLOv8
2. Calculates optimal A* diversion routes through the city graph
3. Re-times affected traffic signals to ease congestion
4. Generates coordinated public alerts (VMS, Radio, Social Media)
5. Dispatches emergency services with intelligent routing
6. Provides a conversational chat interface for officers on duty

---

## ✨ Features

- 🤖 **Multi-Agent Orchestration** — Specialized AI agents for signals, diversion, alerts, dispatch, and chat
- 🗺️ **Real-Time Map Visualization** — Interactive Folium map with live incident markers and diversion paths
- 🧭 **A\* Diversion Routing** — Shortest-path rerouting using OpenStreetMap graph data (osmnx + networkx)
- 🚦 **Adaptive Signal Re-timing** — Automatically adjusts signal timings on affected corridors
- 📢 **Multi-Channel Alert Generation** — VMS boards, Radio broadcast scripts, and Social Media posts
- 🚑 **Emergency Dispatch** — Coordinates police, ambulance, and fire services
- 💬 **Conversational Officer Chat** — LLM-powered Q&A for situational awareness
- 📊 **Live Traffic Feed** — Processes real-time traffic data from CSV feed (color-coded by flow)

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Dashboard / Frontend** | [Streamlit](https://streamlit.io/), [Streamlit-Folium](https://github.com/randyzwitch/streamlit-folium) |
| **Computer Vision** | [YOLOv8](https://github.com/ultralytics/ultralytics), [OpenCV](https://opencv.org/) |
| **Mapping & Routing** | [Folium](https://python-visualization.github.io/folium/), [osmnx](https://osmnx.readthedocs.io/), [networkx](https://networkx.org/), [geopy](https://geopy.readthedocs.io/) |
| **AI / LLM** | [Google Gemini API](https://ai.google.dev/), LangChain-style agent orchestration |
| **Data** | CSV traffic feeds, real-time incident logs |
| **Language** | Python 3.10+ |

---

## 🏗️ Architecture

```
incident-copilot/
├── app.py                    # Main Streamlit dashboard entry point
├── config.py                 # Configuration and environment variables
├── agents/                   # Multi-agent orchestration layer
│   ├── orchestrator.py       # Main orchestrator for all agents
│   ├── agent1_signal.py      # Traffic signal re-timing agent
│   ├── agent2_diversion.py   # A* route diversion agent
│   ├── agent3_alerts.py      # Public alert generation agent
│   ├── agent4_chat.py        # Conversational officer assistant
│   └── agent5_dispatch.py    # Emergency dispatch agent
├── map_engine/               # Folium map rendering utilities
├── yolo/                     # YOLOv8 incident detection integration
├── llm/                      # LLM wrapper utilities 
├── utils/                    # Helper scripts
├── data/
│   └── traffic_feed.csv      # Real-time traffic feed data
└── requirements.txt
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/GopeshKachhadiya/incident-copilot.git
cd incident-copilot

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY or other LLM keys

# 5. Run the dashboard
streamlit run app.py
```

---

## 🚀 Usage

1. Open the Streamlit dashboard at `http://localhost:8501`
2. Upload or select a live incident feed / video
3. The system automatically detects incidents via YOLOv8
4. Click **"Run Agents"** to trigger the full multi-agent pipeline
5. View diversion routes on the interactive map
6. Monitor generated alerts in the **Alerts** panel
7. Use the **Chat** tab to ask situational questions to the officer assistant

---

## 🤖 Agents

| Agent | Role |
|-------|------|
| **Signal Agent** | Recalculates and re-times traffic signals on congested corridors |
| **Diversion Agent** | Computes A* shortest-path diversion routes via osmnx city graph |
| **Alert Agent** | Generates VMS messages, radio broadcast scripts, and social media posts |
| **Dispatch Agent** | Routes emergency vehicles (police, ambulance, fire) to incident location |
| **Chat Agent** | LLM-powered conversational assistant for officers on duty |

---

## 📄 License

This project is developed as part of the Gandhinagar Smart City initiative.

---

<div align="center">Built with ❤️ for safer, smarter cities</div>
