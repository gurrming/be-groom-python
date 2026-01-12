import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_MEMBER_ID = int(os.getenv("BOT_MEMBER_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")


THREADS = int(os.getenv("THREADS", 1))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL", 1))

# categoryId (DB 기준)
CATEGORY_MAP = {
    "BTC": 41, "ETH": 42, "SOL": 43, "XRP": 44, "BNB": 45,
    "ADA": 46, "DOGE": 47, "AVAX": 48, "DOT": 49, "LTC": 50,
    "LINK": 51, "TRX": 52, "ATOM": 53, "FIL": 54, "ALGO": 55,
    "VET": 56, "XTZ": 57, "SHIB": 58, "EOS": 59, "MATIC": 60
}

COINS = list(CATEGORY_MAP.keys())

BASE_PRICE = {
    "BTC": 50000,
    "ETH": 3000,
    "SOL": 120,
    "XRP": 0.8,
    "BNB": 350,
    "ADA": 1.2,
    "DOGE": 0.25,
    "AVAX": 25,
    "DOT": 10,
    "LTC": 150,
    "LINK": 15,
    "TRX": 0.1,
    "ATOM": 9,
    "FIL": 6,
    "ALGO": 0.2,
    "VET": 0.03,
    "XTZ": 0.9,
    "SHIB": 0.00001,
    "EOS": 0.7,
    "MATIC": 0.8
}
