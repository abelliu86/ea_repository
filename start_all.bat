@echo off
TITLE EA Repository Startup Manager

:: Navigate to Project Directory
cd /d "C:\Users\admin\.gemini\antigravity\scratch\ea_repository"

echo Starting EA Collector...
start "EA Collector" /MIN python collector/main_collector.py

echo Starting Streamlit Dashboard...
start "EA Dashboard" /MIN python -m streamlit run analysis/1_Dashboard.py --server.port 8501 --server.headless true

echo Starting Cloudflare Tunnel...
start "Cloudflare Tunnel" /MIN cloudflared tunnel run ea-dashboard

echo All services started! You can minimize this window.
timeout /t 5
