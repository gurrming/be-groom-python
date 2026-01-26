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
    "BTC": 1, "ETH": 2, "XRP": 3, "SOL": 4,
    "ADA": 5, "DOGE": 6, "TRX": 7, "DOT": 8,
    "LINK": 9, "MATIC": 10, "SHIB": 11, "LTC": 12,
    "ATOM": 13, "EOS": 14, "FIL": 15, "ALGO": 16
}


COIN_WEIGHTS = {
    "BTC": 0.23,
    "ETH": 0.18,
    "SOL": 0.15,
    "XRP": 0.10,
    "ADA": 0.08,
    "DOGE": 0.08,
    "DOT": 0.05,
    "LTC": 0.05,
    "LINK": 0.02,
    "MATIC": 0.02,
    "SHIB": 0.01,
    "ATOM": 0.01,
    "EOS": 0.01,
    "FIL": 0.01,
    "ALGO": 0.01,
    "TRX": 0.01
}

# ✅ 단일 진실 소스
COINS = sorted(set(CATEGORY_MAP) & set(COIN_WEIGHTS))

