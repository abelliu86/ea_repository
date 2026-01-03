# EA Performance Repository (v0.1)

A centralized system to track, analyze, and manage Expert Advisors (EAs) across multiple MetaTrader 5 (MT5) terminals and accounts.

## 🚀 Features

### **1. Data Collector (`collector/`)**
*   **Multi-Terminal Sync**: Connects to multiple MT5 terminals on a VPS.
*   **Multi-Account Support**: Distinguishes trades by MT5 Account ID.
*   **Auto-Discovery**: Automatically detects new EAs (Magic Numbers) and registers them.
*   **Cloud Config**: Reads configuration (paths) from the database—no need to edit files on VPS.
*   **Resilient**: Handles connection failures and re-tries automatically.

### **2. Analytics Dashboard (`analysis/`)**
*   **Performance Metrics**: Net Profit, Win Rate, Profit Factor, Expected Payoff.
*   **Equity Curves**: Visualizes account growth over time.
*   **Filters**: Drill down by Account, Strategy Name, Symbol, or Date.
*   **EA Manager**: Rename Magic Numbers to human-readable Strategy Names.
*   **Config Manager**: Add/Remove VPS terminal paths remotely.

## 🛠️ Architecture
*   **Database**: PostgreSQL (NeonDB) for storage.
*   **Backend**: Python `MetaTrader5` library for data extraction.
*   **Frontend**: Streamlit for visualization and management.

## 📦 Installation
See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions.
