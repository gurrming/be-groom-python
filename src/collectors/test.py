import pandas as pd
import psycopg2

def find_real_gaps_after_oct(ticker='BTC'):
    conn = psycopg2.connect(host="localhost", port=15432, user="postgres", password="0000", database="app")
    
    # 1. 10월 1일 이후 가격 데이터만 가져오기
    price_query = f"""
        SELECT trade_time, trade_price 
        FROM market_price 
        WHERE ticker='{ticker}' AND trade_time >= '2025-10-01 00:00:00+09'
    """
    price_df = pd.read_sql(price_query, conn)
    price_df['trade_time'] = pd.to_datetime(price_df['trade_time'], utc=True)
    
    # 2. 감정 데이터 가져오기
    sent_query = f"""
        SELECT date_trunc('hour', published_at) as hr, AVG(sentiment_score) as sent_score
        FROM (
            SELECT ticker, published_at, sentiment_score FROM news_data
            UNION ALL
            SELECT ticker, published_at, sentiment_score FROM community_data
        ) combined
        WHERE ticker = '{ticker}' AND published_at >= '2025-10-01 00:00:00+09'
        GROUP BY hr
    """
    sent_df = pd.read_sql(sent_query, conn)
    sent_df['hr'] = pd.to_datetime(sent_df['hr'], utc=True)
    
    # 3. 데이터 병합
    merged = pd.merge(price_df, sent_df, left_on='trade_time', right_on='hr', how='left')
    
    # 4. 공백 구간 분석
    real_missing = merged[merged['sent_score'].isna()].copy()
    
    conn.close()

    print(f"📊 [{ticker}] 10월 이후 진짜 공백 분석")
    print(f"- 수집 시작 이후 총 시간: {len(merged)}시간")
    print(f"- 데이터 존재 시간: {len(merged) - len(real_missing)}시간")
    print(f"- 데이터 공백 시간: {len(real_missing)}시간")
    print(f"- **데이터 밀도(Density): {((len(merged) - len(real_missing)) / len(merged) * 100):.2f}%**")
    print("-" * 50)
    
    if not real_missing.empty:
        print("🕒 [가장 최근 공백 시간대 10개]")
        print(real_missing['trade_time'].tail(10).dt.strftime('%Y-%m-%d %H:%M').values)
    
    return real_missing

# 실행
real_missing_df = find_real_gaps_after_oct('BTC')