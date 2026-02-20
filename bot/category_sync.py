import os
from dotenv import load_dotenv
import requests
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

def sync_upbit_categories():
    # 1. 업비트 정보 가져오기 (기존 로직 동일)
    url = "https://api.upbit.com/v1/market/all"
    res = requests.get(url)
    all_markets = res.json()
    krw_markets = [m for m in all_markets if m['market'].startswith('KRW-')]
    
    SPECIAL_NAMES = {'EOS': '이오스', 'ADA': '에이다', 'ALGO': '알고랜드'}
    upbit_symbols = {}
    for m in krw_markets:
        symbol = m['market'].replace('KRW-', '')
        upbit_symbols[symbol] = SPECIAL_NAMES.get(symbol, m['korean_name'])

    # DB 접속 정보 (사용자 제공 정보 반영)
    db_params = {
        "host": "heartbit-db-k.ct8oi6y6qlmp.ap-northeast-2.rds.amazonaws.com",
        "port": "5432",
        "database": "heartbit",
        "user": "postgre",
        "password": "heartbit,,1234",
        "connect_timeout": 15,
        "sslmode": "require"      
    }

    # db_params = {
    #     "user": "postgres",
    #     "password": "0000",
    #     "database": "app", 
    #     "host": "localhost",
    #     "port": 15432,
    #     "connect_timeout": 5,
    #     "sslmode": "disable"      
    # }

    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    try:
        # [STEP 1] DB에 저장된 기존 카테고리 정보 전체 조회
        cur.execute("SELECT symbol, category_name, is_active FROM public.category;")
        db_rows = cur.fetchall()
        db_data = {row[0]: {"name": row[1], "active": row[2]} for row in db_rows}

        new_count = 0
        update_count = 0
        reactivate_count = 0

        # [STEP 2] 업비트 리스트를 돌며 비교 분석
        for symbol, name in upbit_symbols.items():
            if symbol not in db_data:
                # A. 아예 없는 새로운 코인 -> INSERT (이때만 ID가 생성됨)
                cur.execute(
                    "INSERT INTO public.category (category_name, symbol, is_active) VALUES (%s, %s, TRUE);",
                    (name, symbol)
                )
                new_count += 1
            else:
                # B. 이미 있는 코인
                existing = db_data[symbol]
                # 이름이 바뀌었거나, 비활성 상태라면 -> UPDATE (ID 보존)
                if existing['name'] != name or existing['active'] is False:
                    cur.execute(
                        "UPDATE public.category SET category_name = %s, is_active = TRUE WHERE symbol = %s;",
                        (name, symbol)
                    )
                    if existing['active'] is False: reactivate_count += 1
                    else: update_count += 1

        # [STEP 3] 상장 폐지 처리 (Delete 대신 Soft Delete)
        # 업비트에는 없는데 DB에는 active인 것들만 비활성화
        symbols_to_disable = [s for s in db_data.keys() if s not in upbit_symbols and db_data[s]['active'] is True]
        
        if symbols_to_disable:
            cur.execute(
                "UPDATE public.category SET is_active = FALSE WHERE symbol IN %s;",
                (tuple(symbols_to_disable),)
            )

        conn.commit()
        print(f"✅ 동기화 완료!")
        print(f"✨ 신규 추가: {new_count}개 / 🔄 이름 수정: {update_count}개 / ♻️ 재활성화: {reactivate_count}개")
        print(f"💤 상장 폐지(비활성화): {len(symbols_to_disable)}개")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sync_upbit_categories()