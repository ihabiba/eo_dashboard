# Alert Watcher — runs independently of the dashboard
# Usage: python alert_watcher.py

import time
import json
import datetime
import requests
import pandas as pd

CHECK_INTERVAL = 300  # seconds between checks (5 minutes)

HYDRO_WARN = 0.40
HYDRO_CRIT = 0.60
AGRI_WARN  = 0.55
AGRI_CRIT  = 0.40


def read_token():
    try:
        with open(".streamlit/secrets.toml") as f:
            for line in f:
                if "TELEGRAM_BOT_TOKEN" in line:
                    return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    import os
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def load_subscribers():
    try:
        with open("data/subscribers.json") as f:
            return json.load(f)
    except Exception:
        return []


def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"  Telegram error: {e}")


def build_message(zone, val, status, vcol, module):
    now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    label = "NDTI" if vcol == "turbidity" else "NDVI"
    status_emoji = "🔴" if status == "critical" else "🟡"
    status_line  = "CRITICAL" if status == "critical" else "WARNING"
    return (
        f"<b>{status_emoji} {status_line} — {module} Zone Alert</b>\n\n"
        f"<b>Zone:</b> {zone}\n"
        f"<b>Time:</b> {now}\n"
        f"<b>{label}:</b> {val}\n"
        f"<b>Status:</b> {status_line}\n\n"
        f"Please open the dashboard to review the latest readings and take action if needed.\n\n"
        f"<i>TNB Siltation Monitor — EO Dashboard</i>"
    )


def classify_hydro(val):
    if val >= HYDRO_CRIT: return "critical"
    if val >= HYDRO_WARN: return "warning"
    return "normal"


def classify_agri(val):
    if val < AGRI_CRIT: return "critical"
    if val < AGRI_WARN: return "warning"
    return "normal"


def check_and_alert(token, last_state):
    df = pd.read_csv("data/eo_monitoring_output.csv", parse_dates=["date"])
    subscribers = load_subscribers()
    current_state = {}

    hydro = df[df["use_case"] == "Hydro monitoring"]
    for zone, group in hydro.groupby("zone"):
        val = round(group.sort_values("date").iloc[-1]["NDTI_mean"], 4)
        current_state[f"{zone}__hydro"] = (classify_hydro(val), val)

    agri = df[df["use_case"] == "Agriculture monitoring"]
    for zone, group in agri.groupby("zone"):
        val = round(group.sort_values("date").iloc[-1]["NDVI_mean"], 4)
        current_state[f"{zone}__agri"] = (classify_agri(val), val)

    if subscribers:
        for key, (status, val) in current_state.items():
            if status == "normal":
                continue
            prev_status = last_state.get(key, ("normal", 0))[0]
            if status != prev_status:
                zone, module_key = key.split("__")
                vcol   = "turbidity" if module_key == "hydro" else "ndvi"
                module = "Hydro" if module_key == "hydro" else "Agriculture"
                msg = build_message(zone, val, status, vcol, module)
                for chat_id in subscribers:
                    send_telegram(token, chat_id, msg)
                print(f"  [{status.upper()}] {zone} → sent to {len(subscribers)} subscriber(s)")

    return current_state


def main():
    token = read_token()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .streamlit/secrets.toml")
        return

    print("=" * 50)
    print("TNB Siltation Monitor — Alert Watcher")
    print(f"Checking every {CHECK_INTERVAL // 60} minutes.")
    print("Press Ctrl+C to stop.")
    print("=" * 50)

    last_state = {}
    while True:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            last_state = check_and_alert(token, last_state)
            subs = load_subscribers()
            print(f"[{now}] OK — {len(last_state)} zones monitored, {len(subs)} subscriber(s)")
        except Exception as e:
            print(f"[{now}] Error: {e}")
        time.sleep(CHECK_INTERVAL)


def run_once():
    token = read_token()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found.")
        return
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Running single alert check...")
    check_and_alert(token, {})
    print("Done.")


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
    else:
        main()
