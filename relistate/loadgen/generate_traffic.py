import os
import random
import time

import requests

BASE_URL = os.getenv("APP_URL", "http://relistate-web:8000")
INTERVAL = float(os.getenv("TRAFFIC_INTERVAL_SECONDS", "5"))

while True:
    try:
        choice = random.random()
        if choice < 0.75:
            flag = random.choice(["dark_mode_beta", "express_checkout"])
            response = requests.get(BASE_URL + "/api/v1/flags/evaluate",
                                    params={"flag": flag}, timeout=10)
        elif choice < 0.90:
            response = requests.get(BASE_URL + "/console", timeout=10)
        elif choice < 0.98:
            response = requests.post(
                BASE_URL + "/api/v1/flags/rules",
                json={"flag": "express_checkout", "enabled": random.choice([True, False])},
                timeout=10,
            )
        else:
            response = requests.get(BASE_URL + "/healthz", timeout=10)
        print("traffic:", response.status_code, response.url, flush=True)
    except requests.RequestException as error:
        print("waiting for ReliState:", error, flush=True)
    time.sleep(INTERVAL)
