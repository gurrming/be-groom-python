import os
import re
import hashlib
import requests
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class NewsAggregator:
    def __init__(self):
        self.db_params = {
            "host": "localhost", "port": "15432",
            "database": "app", "user": "postgres", "password": "0000"
        }
        self.tokens = {
            "CRYPTOPANIC": os.getenv('CRYPTOPANIC_TOKEN'),
            "ALPHAVANTAGE": os.getenv('ALPHA_VANTAGE_API_KEY')
        }
        self.split_date = datetime(2026, 1, 20, tzinfo=timezone.utc)

    def _parse_date(self, date_str):
        if not date_str: return None
        try:
            if len(date_str) == 15 and 'T' in date_str: # AlphaVantage
                return datetime.strptime(date_str, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        except:
            return None

    def _get_db_categories(self, limit_top_4=False):
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            if limit_top_4:
                target_tickers = ('BTC', 'ETH', 'XRP', 'SOL')
                cur.execute("SELECT symbol, category_name, category_id FROM public.category WHERE symbol IN %s", (target_tickers,))
            else:
                cur.execute("SELECT symbol, category_name, category_id FROM public.category")
            
            categories = [{'symbol': r[0].strip().upper(), 'name': r[1].strip().upper(), 'id': r[2]} for r in cur.fetchall()]
            cur.close()
            conn.close()
            return categories
        except Exception as e:
            print(f"⚠️ 카테고리 로드 실패: {e}")
            return []

    def _save_to_integrated_db(self, items, source):
        if not items: return
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            inserted_count = 0

            for item in items:
                title = item.get('title', '')
                ticker = item.get('assigned_ticker', '')
                category_id = item.get('assigned_category_id')
                description = item.get('description') or item.get('summary', '')
                dt = self._parse_date(item.get('time_published') or item.get('created_at'))
                
                if not dt: continue
                is_test = dt >= self.split_date
                date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                hash_key = hashlib.md5(f"{title.strip()}_{date_str}_{ticker}".encode()).hexdigest()

                # 통합 테이블 news_data 사용
                query = """
                INSERT INTO public.news_data
                (category_id, title, description, published_at, ticker, hash_key, is_test) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash_key) DO NOTHING;
                """
                cur.execute(query, (category_id, title, description, dt, ticker, hash_key, is_test))
                if cur.rowcount > 0: inserted_count += 1

            conn.commit()
            print(f"📊 [{source}] 통합 저장 완료: {inserted_count}건")
        except Exception as e:
            if conn: conn.rollback()
            print(f"❌ DB 저장 에러: {e}")
        finally:
            if conn: conn.close()

    def fetch_alpha_vantage(self, start_time=None, end_time=None):
        categories = self._get_db_categories(limit_top_4=(start_time is None))
        if not categories or not self.tokens["ALPHAVANTAGE"]: return

        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=1000&apikey={self.tokens['ALPHAVANTAGE']}"
        if start_time: url += f"&time_from={start_time}"
        if end_time: url += f"&time_to={end_time}"
        
        try:
            res = requests.get(url)
            data = res.json()
            articles = data.get('feed', [])
            matched_list = []
            for art in articles:
                title = (art.get('title') or '').upper()
                av_tickers = [t.get('ticker', '').replace("CRYPTO:", "").upper() for t in art.get('ticker_sentiment', [])]
                for cat in categories:
                    if cat['symbol'] in av_tickers or re.search(rf"\b{cat['symbol']}\b", title) or re.search(rf"\b{cat['name']}\b", title):
                        item = art.copy()
                        item['assigned_ticker'] = cat['symbol']
                        item['assigned_category_id'] = cat['id']
                        matched_list.append(item)
            self._save_to_integrated_db(matched_list, "AlphaVantage")
        except Exception as e: print(f"❌ AV 에러: {e}")

    def fetch_cryptopanic(self):
        categories = self._get_db_categories(limit_top_4=True)
        url = "https://cryptopanic.com/api/developer/v2/posts/"
        params = {"auth_token": self.tokens["CRYPTOPANIC"], "kind": "news", "regions": "en"}
        try:
            res = requests.get(url, params=params)
            articles = res.json().get('results', [])
            matched_list = []
            for art in articles:
                title = art.get('title', '').upper()
                cp_currencies = [c.get('code', '').upper() for c in art.get('currencies', [])]
                for cat in categories:
                    if cat['symbol'] in cp_currencies or re.search(rf"\b{cat['symbol']}\b", title) or re.search(rf"\b{cat['name']}\b", title):
                        item = art.copy()
                        item['assigned_ticker'] = cat['symbol']
                        item['assigned_category_id'] = cat['id']
                        matched_list.append(item)
            self._save_to_integrated_db(matched_list, "CryptoPanic")
        except Exception as e: print(f"❌ CryptoPanic 에러: {e}")