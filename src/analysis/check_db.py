import psycopg2
from datetime import datetime
import os

# DB 설정 (기존과 동일)
DB_CONFIG = {
    "host": "localhost", "port": "15432",
    "database": "app", "user": "postgres", "password": "0000"
}

def check_status():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("="*60)
        print(f"🕵️‍♂️ DB 데이터 전수 조사 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("="*60)

        # 1. 테이블별 데이터 총 개수
        print("\n📊 1. 테이블별 데이터 총 개수")
        for table in ['news_data', 'community_data', 'sentiment_result']:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"   - {table:<20}: {count} 건")

        # 2. 코인별(Symbol) 데이터 분포 (news_data 기준)
        print("\n📈 2. 코인별 뉴스 데이터 분포 (news_data)")
        cur.execute("""
            SELECT symbol, count(*) FROM news_data 
            GROUP BY symbol ORDER BY count(*) DESC
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"   - [{r[0]}] : {r[1]} 건")
        else:
            print("   (데이터 없음)")

        # 3. 데이터 시간 범위 (가장 옛날 ~ 가장 최근)
        print("\n⏰ 3. 수집된 데이터 시간 범위 (published_at 기준)")
        
        # 뉴스
        cur.execute("SELECT min(published_at), max(published_at) FROM news_data")
        news_range = cur.fetchone()
        print(f"   - 뉴스     : {news_range[0]} ~ {news_range[1]}")
        
        # 커뮤니티
        cur.execute("SELECT min(published_at), max(published_at) FROM community_data")
        comm_range = cur.fetchone()
        print(f"   - 커뮤니티 : {comm_range[0]} ~ {comm_range[1]}")

        # 4. 최근 10개 미리보기 (잘못된 심볼이나 제목 확인)
        print("\n👀 4. 가장 최근에 들어온 뉴스 5개 미리보기")
        cur.execute("""
            SELECT symbol, title, published_at 
            FROM news_data 
            ORDER BY published_at DESC LIMIT 5
        """)
        recents = cur.fetchall()
        for r in recents:
            print(f"   [{r[0]}] {str(r[2])[:19]} | {r[1][:40]}...")

        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ DB 연결/조회 실패: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_status()