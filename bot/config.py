# bot/config.py
import os
from dotenv import load_dotenv

load_dotenv()

SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_ID = int(os.getenv("BOT_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

THREADS = int(os.getenv("THREADS", 1))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL", 1))

# 업비트 API
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# bot/config.py

CATEGORY_MAP = {
    "BTC": 1, "ETH": 2, "SOL": 3, "XRP": 4,
    "ADA": 6, "DOGE": 7, "DOT": 9, "LTC": 10,
    "LINK": 11, "TRX": 12, "ATOM": 13, "FIL": 14,
    "ALGO": 15, "SHIB": 18, "EOS": 19, "MATIC": 20
}

COIN_WEIGHTS = {
    "BTC": 0.40,
    "ETH": 0.25,
    "SOL": 0.10,
    "XRP": 0.08,
    "ADA": 0.05,
    "DOGE": 0.04,
    "DOT": 0.02,
    "LTC": 0.02,
    "LINK": 0.01
}

# ✅ 단일 진실 소스
COINS = sorted(set(CATEGORY_MAP) & set(COIN_WEIGHTS))

