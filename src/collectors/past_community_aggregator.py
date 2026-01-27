import psycopg2
from datetime import datetime
import time
import requests
import hashlib

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=15432,
        database="app",
        user="postgres",
        password="0000"
    )

def collect_reddit_no_api(ticker):
    # 사용자님이 요청하신 테이블 및 컬럼 정보
    table_name = "news_data"
    id_column = "news_id"
    
    # 수집 기간 설정 (2025-10-01 ~ 2025-10-31)
    # 쿼리 형식: 검색어 + 기간 한정
    search_query = f"{ticker} after:2025-10-01 before:2025-11-01"
    
    # SocialGrep의 공개 검색 엔드포인트를 우회하여 사용 (API 키 불필요 버전)
    url = "https://socialgrep.com/api/search"
    params = {
        'q': search_query,
        'sort': 'oldest' # 옛날 것부터 차례대로
    }

    print(f"🚀 [{ticker}] 2025년 10월 데이터 수집 시작...")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            print(f"❌ 접속 실패: {response.status_code}")
            return

        posts = response.json().get('data', [])
        
        if not posts:
            print(f"❓ [{ticker}] 해당 기간에 데이터가 없습니다.")
            return

        for post in posts:
            # 1. 고유 ID 생성 (news_id)
            raw_id = post.get('id', str(time.time()))
            
            # 2. 데이터 추출
            title = post.get('title', 'No Title')
            description = post.get('selftext', '') or post.get('text', '')
            # 날짜 형식 변환 (문자열 -> datetime)
            pub_at = post.get('created_at') 
            
            # 3. 중복 방지용 해시 (news_id가 문자열일 경우 대비)
            hash_key = hashlib.md5(f"{ticker}{title}{pub_at}".encode()).hexdigest()

            # 4. DB 저장 (news_data 테이블)
            sql = f"""
            INSERT INTO {table_name} ({id_column}, title, description, published_at, ticker, hash_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (hash_key) DO NOTHING;
            """
            
            try:
                cur.execute(sql, (raw_id, title, description, pub_at, ticker, hash_key))
            except Exception as e:
                print(f"⚠️ 저장 오류: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"✅ [{ticker}] {len(posts)}개의 데이터 처리 완료!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        cur.close()
        conn.close()

# 실행
if __name__ == "__main__":
    collect_reddit_no_api("BTC")