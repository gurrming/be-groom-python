import requests
import psycopg2

def sync_upbit_categories():
    # 1. 업비트 최신 KRW 마켓 정보 가져오기
    url = "https://api.upbit.com/v1/market/all"
    res = requests.get(url)
    all_markets = res.json()
    krw_markets = [m for m in all_markets if m['market'].startswith('KRW-')]
    
    # 최신 심볼 리스트와 이름 매핑 생성
    current_symbols = []
    symbol_name_map = {}
    # 예외 처리: 이오스 등 특정 코인 이름 강제 지정
    SPECIAL_NAMES = {'EOS': '이오스', 'ADA': '에이다', 'ALGO': '알고랜드'}

    for m in krw_markets:
        symbol = m['market'].replace('KRW-', '')
        current_symbols.append(symbol)
        symbol_name_map[symbol] = SPECIAL_NAMES.get(symbol, m['korean_name'])

    db_params = {"host": "localhost", "port": "15432", "database": "app", "user": "postgres", "password": "0000"}
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    try:
        # ON CONFLICT 시 이름을 업데이트하도록 설정
        upsert_query = """
        INSERT INTO public.category (category_name, symbol)
        VALUES (%s, %s)
        ON CONFLICT (symbol) 
        DO UPDATE SET category_name = EXCLUDED.category_name;
        """
        for symbol, name in symbol_name_map.items():
            cur.execute(upsert_query, (name, symbol))

        # 현재 업비트 리스트에 없는 symbol을 DB에서 삭제
        delete_query = "DELETE FROM public.category WHERE symbol NOT IN %s;"
        cur.execute(delete_query, (tuple(current_symbols),))
        deleted_count = cur.rowcount

        conn.commit()
        print(f"✅ 동기화 완료: 현재 {len(current_symbols)}개 코인 유지 중")
        if deleted_count > 0:
            print(f"🗑️ 상장 폐지/삭제된 코인 {deleted_count}개 정리 완료")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sync_upbit_categories()