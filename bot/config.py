import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# DB 연결 정보 (기존 설정 활용)

# def get_db_connection():
#     return psycopg2.connect(
#         host="localhost", port="15432",
#         database="app", user="postgres", password="0000"
#     )

import os
import psycopg2
from dotenv import load_dotenv

# .env 파일 안의 정보들을 환경 변수로 불러옵니다.
load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"), 
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
        options="-c client_encoding=UTF8"
    )


def load_categories_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # DB에 저장된 모든 코인을 가져옴
    cur.execute("SELECT symbol, category_id FROM public.category;")
    db_data = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: row[1] for row in db_data}

# 실시간으로 카테고리 맵 생성
CATEGORY_MAP = load_categories_from_db()
COINS = list(CATEGORY_MAP.keys())

# 기존 환경 변수들
SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_ID = int(os.getenv("BOT_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
THREADS = int(os.getenv("THREADS"))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL"))