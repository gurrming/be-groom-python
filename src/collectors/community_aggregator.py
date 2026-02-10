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
        # RSS 주소 매핑
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
        
        # User-Agent 설정 (필수)
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # [중요] HTTP 상태 코드 확인 (차단 여부 체크)
        status = getattr(feed, 'status', 200)
        if status == 429:
            print(f"⛔ [차단됨-429] {ticker}-{sort_type}: 요청이 너무 많습니다. 잠시 대기 필요.")
            conn.close()
            return
        elif status != 200:
            print(f"⚠️ [접속불가-{status}] {ticker}-{sort_type}")
            conn.close()
            return

        if not feed.entries:
            # 상태 코드는 200인데 글이 정말 없는 경우
            print(f"   [빈 데이터] {ticker}-{sort_type}: 게시글이 없습니다.")
            conn.close()
            return

        for entry in feed.entries:
            title = entry.title
            description = entry.summary if 'summary' in entry else ""
            ups_count = int(entry.get('rank', 0))
            
            # 날짜 파싱 안전장치
            try:
                if hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6]).replace(tzinfo=timezone.utc)
                else:
                    pub_date = datetime.now(timezone.utc)
            except:
                continue
            
            if pub_date < min_date:
                continue

            is_test = pub_date >= split_date
            hash_key = self.generate_hash(f"{title}_{pub_date}")

            # [최종 수정] 
            # 1. 테이블명: community_data
            # 2. 컬럼명: ticker -> symbol
            query = """
                INSERT INTO community_data
                (title, description, published_at, symbol, hash_key, platform, ups, is_test)
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
                # 에러 발생 시 로그 출력 (디버깅용)
                print(f"❌ [DB Error] {ticker}: {e}")
                continue
        
        conn.commit()
        cur.close()
        conn.close()
        
        if new_count > 0:
            print(f"   ✅ [{ticker}-{sort_type}] {new_count}건 저장 완료")

if __name__ == "__main__":
    collector = CommunityBulkCollector()
    all_tickers = list(collector.subreddit_map.keys())
    
    while True:
        print(f"\n⏰ [{datetime.now()}] RSS 수집 시작 (딜레이 적용됨)...")
        
        for ticker in all_tickers:
            for s in ["new", "rising", "hot", "controversial"]:
                collector.collect_bulk(ticker, s)
                # [중요] 레딧 차단 방지를 위해 딜레이를 2초로 늘림
                time.sleep(2)
            
            # 한 종목 끝날 때마다 5초 휴식 (UNI, ATOM 등 뒷순서 차단 방지)
            print(f"   💤 {ticker} 완료. 5초 대기...")
            time.sleep(5)
            
        print("✨ 한 바퀴 완료. 10분 뒤 다시 시작합니다.")
        time.sleep(600)