import psycopg2
from psycopg2.extras import RealDictCursor

# 1. DB 연결 설정
DB_CONFIG = {
    "dbname": "app",
    "user": "postgres",
    "password": "0000",
    "host": "localhost",
    "port": "15432"
}

def get_label(score):
    if score >= 0.6: return "POSITIVE"
    elif score <= 0.4: return "NEGATIVE"
    else: return "NEUTRAL"

def update_sentiment_results():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. 분석할 종목(category) 목록 가져오기
        cur.execute("SELECT category_id, symbol FROM category")
        categories = cur.fetchall()

        for cat in categories:
            cat_id = cat['category_id']
            coin_ticker = cat['symbol'].upper() 

            try: # 개별 종목 처리 중 에러가 나도 다른 종목은 계속 진행되도록 루프 안에 try 추가
                # 뉴스 평균
                cur.execute("SELECT AVG(sentiment_score) as avg FROM news_data WHERE ticker = %s", (coin_ticker,))
                news_avg = float(cur.fetchone()['avg'] or 0.5)

                # 커뮤니티 평균
                cur.execute("SELECT AVG(sentiment_score) as avg FROM community_data WHERE ticker = %s", (coin_ticker,))
                comm_avg = float(cur.fetchone()['avg'] or 0.5)

                total_score = (news_avg * 0.4) + (comm_avg * 0.6)
                total_label = get_label(total_score)

                
                cur.execute("""
                    INSERT INTO sentiment_result (category_id, total_score, total_label, news_score, community_score, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (category_id) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        total_label = EXCLUDED.total_label,
                        news_score = EXCLUDED.news_score,
                        community_score = EXCLUDED.community_score,
                        updated_at = NOW();
                """, (cat_id, total_score, total_label, news_avg, comm_avg))
            except Exception as e:
                print(f"⚠️ {coin_ticker} 처리 중 오류 발생: {e}")
                continue

        conn.commit()
        print("전체 종목 감정 지수 집계 완료.")

    except Exception as e:
        print(f"데이터 처리 중 오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    update_sentiment_results()