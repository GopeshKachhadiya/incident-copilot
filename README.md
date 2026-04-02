# Incident Copilot - Smart City Traffic Incident Management System

LLM-powered multi-agent traffic incident co-pilot for Gandhinagar Smart City.

## Overview
Incident Copilot is an AI-driven command-center dashboard for Gandhinagar Smart City. It integrates real-time traffic monitoring, incident detection via YOLOv8, and a multi-agent layer for diversion routing, signal re-timing, and public alerts.

## Features
* Multi-Agent Orchestration (signals, diversion, alerts, dispatch, chat)
* * Real-Time Map Visualization (Folium)
  * * A* Diversion Routing (osmnx + networkx)
    * * Adaptive Signal Re-timing
      * * Multi-Channel Alert Generation (VMS, Radio, Social Media)
        * * Conversational Officer Chat (Google Gemini API)
         
          * ## Tech Stack
          * * Frontend: Streamlit
            * * Vision: YOLOv8, OpenCV
              * * Mapping: Folium, osmnx
                * * AI: Google Gemini API
                  * * Language: Python 3.10+
                   
                    * ## Installation
                    * 1. git clone https://github.com/GopeshKachhadiya/incident-copilot.git
                      2. 2. pip install -r requirements.txt
                         3. 3. streamlit run app.py
                            4. 
