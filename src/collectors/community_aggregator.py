import feedparser
import hashlib
import psycopg2
import time
from datetime import datetime, timezone

class CommunityBulkCollector:
    def __init__(self):
        self.db_config = {
            "host": "localhost", "port": "15432",
            "database": "app", "user": "postgres", "password": "0000"
        }
        self.subreddit_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp",
            "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot", "POL": "0xPolygon",
            "LINK": "chainlink", "TRX": "tronix", "LTC": "litecoin", "SHIB": "SHIBArmy",
            "AVAX": "Avax", "UNI": "Uniswap", "ATOM": "cosmosnetwork", "FIL": "filecoin"
        }

    def generate_hash(self, text):
        return hashlib.md5(text.encode()).hexdigest()

    def collect_bulk(self, ticker, sort_type):
        subreddit = self.subreddit_map.get(ticker, ticker.lower())
        min_date = datetime(2025, 10, 1, tzinfo=timezone.utc)
        split_date = datetime(2026, 1, 20, tzinfo=timezone.utc)

        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        new_count = 0
        
        url = f"https://www.reddit.com/r/{subreddit}/{sort_type}/.rss"
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        for entry in feed.entries:
            title = entry.title
            description = entry.summary if 'summary' in entry else ""
            ups_count = int(entry.get('rank', 0))
            pub_date = datetime(*entry.updated_parsed[:6]).replace(tzinfo=timezone.utc)
            
            if pub_date < min_date:
                continue

            is_test = pub_date >= split_date
            hash_key = self.generate_hash(f"{title}_{pub_date}")

            # [수정 완료] target_table 변수 대신 직접 테이블명 기입
            query = """
                INSERT INTO community_data
                (title, description, published_at, ticker, hash_key, platform, ups, is_test)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash_key) 
                DO UPDATE SET ups = EXCLUDED.ups;
            """
            
            try:
                cur.execute(query, (
                    title, description, pub_date, ticker.upper(), 
                    hash_key, 'reddit', ups_count, is_test
                ))
                if cur.rowcount > 0:
                    new_count += 1
            except Exception as e:
                conn.rollback()
                continue
        
        conn.commit()
        cur.close()
        conn.close()
        if new_count > 0:
            print(f"   - [{ticker}-{sort_type}] {new_count}건 추가 완료")

if __name__ == "__main__":
    collector = CommunityBulkCollector()
    all_tickers = list(collector.subreddit_map.keys())
    
    while True:
        print(f"\n⏰ [{datetime.now()}] RSS 수집 시작 (10분 주기)...")
        for ticker in all_tickers:
            for s in ["new", "rising", "hot", "controversial"]:
                collector.collect_bulk(ticker, s)
            time.sleep(0.5)
            
        print("✨ 한 바퀴 완료. 10분 뒤 다시 시작합니다.")
        time.sleep(600)