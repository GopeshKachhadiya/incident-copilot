# 🛡️ Incident Co-Pilot: Intelligent Traffic Management

A high-performance command-center dashboard for traffic monitoring, incident detection, and multi-agent emergency response. Built for Gandhinagar Smart City.

## 🚀 Key Features
- **YOLOv8-based Detection:** Real-time accident detection and classification.
- **Multi-Agent Orchestration:** 
  - **Signal Agent:** Dynamic intersection re-timing using Claude/Llama logic.
  - **Diversion Agent:** A*-pathfinding for alternative route calculation.
  - **Alerts Agent:** Public message generation (VMS, Social Media).
  - **Dispatch Agent:** Automated emergency notification.
  - **Chat Agent:** Natural language situational awareness.
- **Interactive Map:** Folium-based visualization with congestion heatmaps and live routing.

## 🛠️ Tech Stack
- **Frontend:** Streamlit with custom Dark Modern CSS
- **Detection:** Ultralytics (YOLOv8)
- **Map:** Folium, OSMnx, NetworkX
- **LLM:** HuggingFace Serverless / Gemini / Claude

## 📦 Setup & Installation
1. Clone the repository: `git clone https://github.com/GopeshKachhadiya/incident-copilot.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set your API keys in `.env` (refer to `config.py` for variables).
4. Run the dashboard: `streamlit run app.py`

*Developed as part of Aetrix,PDEU Hackathon 2026.*
