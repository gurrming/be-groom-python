import feedparser
import hashlib
import psycopg2
import time
import schedule
import requests
import random
import logging
import sys
import torch
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
from datetime import datetime, timezone
from time import mktime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('reddit_collector.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class CommunityCollector:
    def __init__(self):
        self.db_params = {
            "host": "localhost", "port": "15432",
            "database": "app", "user": "postgres", "password": "0000"
        }
        
        # 벡터 DB 및 임베딩 모델 설정
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.embed_model = SentenceTransformer('intfloat/multilingual-e5-small', device=self.device)
        self.qdrant_client = QdrantClient(url="http://localhost:6333")
        self.collection_name = "community_collection"

        self.subreddit_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp",
            "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot", "LINK": "chainlink"
        }
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def _get_category_mapping(self):
        """DB에서 symbol과 category_id 매핑 정보 가져오기"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            cur.execute("SELECT symbol, category_id FROM public.category")
            rows = cur.fetchall()
            conn.close()
            return {r[0].upper(): r[1] for r in rows}
        except: return {}

    def _save_to_db(self, items, ticker, sort_type, cat_id):
        if not items: return 0
        conn = None
        saved_count = 0
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            query = """
                INSERT INTO public.community_data
                (symbol, title, description, published_at, hash_key, platform, ups, is_test, category_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash_key) DO UPDATE SET ups = EXCLUDED.ups
                RETURNING community_id;
            """
            for item in items:
                # category_id 포함하여 DB 저장
                db_item = item + (cat_id,)
                cur.execute(query, db_item)
                result = cur.fetchone()
                
                if result:
                    comm_id = result[0]
                    symbol, title, description, dt, hash_key, platform, ups, is_test = item
                    
                    # Qdrant 저장 (뉴스 페이로드와 규격 통일)
                    vector = self.embed_model.encode(f"passage: {description}").tolist()
                    self.qdrant_client.upsert(
                        collection_name=self.collection_name,
                        points=[PointStruct(
                            id=comm_id,
                            vector=vector,
                            payload={
                                "category_id": cat_id,
                                "sentiment": 0.0,
                                "source_type": "community",
                                "symbol": symbol
                            }
                        )]
                    )
                    saved_count += 1
            conn.commit()
            if saved_count > 0: 
                logging.info(f"💾 [{ticker}-{sort_type}] {saved_count}건 저장 및 벡터화 완료")
        except Exception as e:
            if conn: conn.rollback()
            logging.error(f"❌ DB 저장 에러: {e}")
        finally:
            if conn: conn.close()
        return saved_count

    def collect_reddit(self):
        logging.info("👽 [Reddit-RSS] 수집 사이클 시작")
        cat_map = self._get_category_mapping()
        
        for ticker, subreddit in self.subreddit_map.items():
            cat_id = cat_map.get(ticker.upper())
            if not cat_id: continue # 매핑된 ID가 없으면 스킵

            for sort_type in ["new", "hot"]:
                url = f"https://www.reddit.com/r/{subreddit}/{sort_type}/.rss"
                try:
                    headers = {'User-Agent': random.choice(self.user_agents)}
                    resp = requests.get(url, headers=headers, timeout=15)
                    if resp.status_code != 200: continue
                    feed = feedparser.parse(resp.content)
                    if not feed.entries: continue

                    items_to_save = []
                    for entry in feed.entries:
                        dt = datetime.now(timezone.utc)
                        if hasattr(entry, 'published_parsed'):
                            dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                        title = entry.title
                        description = getattr(entry, 'summary', '')
                        hash_key = hashlib.md5(f"{title}_{dt}".encode('utf-8')).hexdigest()
                        items_to_save.append((ticker, title, description, dt, hash_key, 'reddit', 0, True))

                    self._save_to_db(items_to_save, ticker, sort_type, cat_id)
                    time.sleep(random.randint(5, 10))
                except Exception as e:
                    logging.error(f"⚠️ 에러 발생 [{ticker}]: {e}")
        logging.info("✨ 수집 사이클 종료.")

def job(): CommunityCollector().collect_reddit()

if __name__ == "__main__":
    job()
    schedule.every(30).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)