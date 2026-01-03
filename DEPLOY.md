# Deployment Instructions

## 1. On Your VPS (The "Collector")
1.  **Clone/Copy** the `ea_repository` folder to your VPS.
2.  **Install Python**: You need **Python 3.8, 3.9, 3.10, or 3.11**.
    *   **WARNING**: Python 3.12+ is **NOT** yet supported by the `MetaTrader5` library. If you have 3.12, please uninstall and install Python 3.11.
    *   **CRITICAL**: You MUST install the **64-bit** version.
    *   To check, run: `python --version` (Must be < 3.12) and `python -c "import struct; print(struct.calcsize('P') * 8)"` (Must be 64).
3.  **Install Requirements**:
    ```bash
    pip install -r requirements_vps.txt
    ```
4.  **Configure `.env`**:
    *   Create a `.env` file in the root folder.
    *   Add your DB URL: `DATABASE_URL=postgresql://...`
    *   Add your DB URL: `DATABASE_URL=postgresql://...`
    *   **NOTE**: `MT5_PATH` in .env is now optional. You can configure paths via the Dashboard.
5.  **Run the Collector**:
    ```bash
    python collector/main_collector.py
    ```
    *   *Keep this window open or use a process manager like NSSM to run it as a service.*

## 🚑 Troubleshooting: Python Version Error
If you see `ERROR: Could not find a version that satisfies the requirement MetaTrader5`, your Python is likely too new (3.12+) or 32-bit.

**How to Downgrade to Python 3.11 (Windows):**
1.  **Uninstall**: Go to `Settings > Apps > Installed Apps`. Find "Python 3.12" (or newer) and click **Uninstall**.
2.  **Download**: Go to [Python.org Downloads (3.11.9)](https://www.python.org/downloads/release/python-3119/)
3.  **Installer**: Scroll down to "Files". Click **"Windows installer (64-bit)"**.
4.  **Install**: Run the installer.
    *   ✅ **CHECK THE BOX**: "Add python.exe to PATH" (Very important!)
    *   Click "Install Now".
5.  **Verify**: Open a new Command Prompt (CMD) and run `python --version`. It should say `3.11.x`.
6.  **Retry**: Run `pip install -r requirements_vps.txt` again.

## 2. On Your Local PC (The "Dashboard")
1.  **Install Python** (if not already).
2.  **Install Requirements**: `pip install -r requirements.txt`
3.  **Configure `.env`**: Same as above (copy the same file).
4.  **Run Dashboard**:
    ```bash
    ```
    streamlit run analysis/1_Dashboard.py
    ```

## 🔄 Updating to V3 (Composite Keys & EAs)
**WARNING**: This update changes the Primary Key logic of the `eas` table.
To ensure clean data without conflicts:
1.  **Stop Collector** on VPS.
2.  **Upload New Files**:
    *   `shared/db_models.py`
    *   `collector/main_collector.py`
    *   `analysis/1_Dashboard.py`
    *   `analysis/pages/2_Manager.py`
    *   `analysis/pages/3_Config.py`
3.  **Reset Database (Recommended)**:
    *   Since we changed the Primary Key structure, it is safest to wipe the tables.
    *   Run `python collector/init_db.py` (after uncommenting the `drop_all` line temporarily) OR manually drop tables in DB.
    *   *Alternatively*, if you don't want to lose data, you can try to migrate, but dropping `eas` table is required at minimum.
4.  **Restart Collector**.

## ☁️ Cloud Configuration
You can now manage MT5 paths from the Dashboard (**Config Page**).
1.  Go to the "Config" page in the Dashboard.
2.  Add/Remove paths.
3.  Click Save.
4.  The Collector on VPS will automatically pick up the changes in its next cycle (every 60s). **No restart required!**
