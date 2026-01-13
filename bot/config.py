# bot/config.py
import os
from dotenv import load_dotenv

load_dotenv()

SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_MEMBER_ID = int(os.getenv("BOT_MEMBER_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

THREADS = int(os.getenv("THREADS", 1))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL", 1))

# 업비트 API
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

CATEGORY_MAP = {
    "BTC": 41, "ETH": 42, "SOL": 43, "XRP": 44, "BNB": 45,
    "ADA": 46, "DOGE": 47, "AVAX": 48, "DOT": 49, "LTC": 50,
    "LINK": 51, "TRX": 52, "ATOM": 53, "FIL": 54, "ALGO": 55,
    "VET": 56, "XTZ": 57, "SHIB": 58, "EOS": 59, "MATIC": 60
}

COINS = list(CATEGORY_MAP.keys())

# bot/config.py

COIN_WEIGHTS = {
    "BTC": 0.40,
    "ETH": 0.25,
    "SOL": 0.10,
    "XRP": 0.08,
    "ADA": 0.05,
    "DOGE": 0.04,
    "AVAX": 0.03,
    "DOT": 0.02,
    "LTC": 0.02,
    "LINK": 0.01
}

