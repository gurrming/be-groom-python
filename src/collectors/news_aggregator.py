import requests
import os
import psycopg2
import re
import hashlib
from datetime import datetime
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

    def _parse_date(self, date_str):
        """날짜 문자열을 datetime 객체로 변환"""
        if not date_str: return None
        try:
            if len(date_str) == 15 and 'T' in date_str: # AlphaVantage
                return datetime.strptime(date_str, '%Y%m%dT%H%M%S')
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')) # CryptoPanic/ISO
        except:
            return None

    def _get_db_categories(self):
        """DB에서 상위 4개 코인 정보만 선별해서 로드"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            
            # [수정] WHERE 절을 추가하여 원하는 티커만 필터링합니다.
            target_tickers = ('BTC', 'ETH', 'XRP', 'SOL') 
            query = "SELECT symbol, category_name, category_id FROM public.category WHERE symbol IN %s"
            
            cur.execute(query, (target_tickers,))
            
            categories = [
                {
                    'symbol': str(r[0]).strip().upper(), 
                    'name': str(r[1]).strip().upper(),
                    'id': r[2]
                } for r in cur.fetchall()
            ]
            cur.close()
            conn.close()
            return categories
        except Exception as e:
            print(f"⚠️ 카테고리 로드 실패: {e}")
            return []

    def fetch_cryptopanic(self):
        """CryptoPanic: 전체 수집 후 DB 카테고리와 매칭"""
        categories = self._get_db_categories()
        if not categories or not self.tokens["CRYPTOPANIC"]: return

        url = "https://cryptopanic.com/api/developer/v2/posts/"
        params = {"auth_token": self.tokens["CRYPTOPANIC"], "kind": "news", "public": "true", "regions": "en"}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                articles = res.json().get('results', [])
                matched_list = []
                for art in articles:
                    full_text = f"{art.get('title', '')} {art.get('description') or ''}".upper()
                    cp_currencies = [c.get('code', '').upper() for c in art.get('currencies', [])]
                    
                    for cat in categories:
                        if cat['symbol'] in cp_currencies or re.search(rf'\b{re.escape(cat["symbol"])}\b', full_text):
                            item = art.copy()
                            item['assigned_ticker'] = cat['symbol']
                            item['assigned_category_id'] = cat['id']
                            matched_list.append(item)
                self._save_to_db(matched_list, "CRYPTOPANIC")
        except Exception as e:
            print(f"❌ CryptoPanic 에러: {e}")

    def fetch_alpha_vantage(self):
        """AlphaVantage: 전체 수집 후 DB 카테고리와 매칭"""
        categories = self._get_db_categories()
        if not categories or not self.tokens["ALPHAVANTAGE"]: return

        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=crypto&limit=100&apikey={self.tokens['ALPHAVANTAGE']}"
        try:
            res = requests.get(url)
            data = res.json()
            articles = data.get('feed', [])
            matched_list = []
            for art in articles:
                # AV가 제공하는 티커들 추출
                av_tickers = [t.get('ticker', '').replace("CRYPTO:", "").upper() for t in art.get('ticker_sentiment', [])]
                
                for cat in categories:
                    if cat['symbol'] in av_tickers:
                        item = art.copy()
                        item['assigned_ticker'] = cat['symbol']
                        item['assigned_category_id'] = cat['id']
                        matched_list.append(item)
            self._save_to_db(matched_list, "ALPHAVANTAGE")
        except Exception as e:
            print(f"❌ AV 에러: {e}")

    def _save_to_db(self, items, source):
        if not items: return
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            inserted_count = 0

            for item in items:
                title = item.get('title', '')
                ticker = item.get('assigned_ticker')
                category_id = item.get('assigned_category_id')
                dt = self._parse_date(item.get('time_published') or item.get('created_at'))
                date_str = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ""

                # [해시 생성] 제목 + 시간 + 티커 조합 (MD5 32자리)
                clean_title = title.strip() # 앞뒤 공백 제거
                unique_str = f"{clean_title}_{date_str}_{ticker}"
                hash_key = hashlib.md5(unique_str.encode('utf-8')).hexdigest()

                query = """
                INSERT INTO public.coin_news 
                (category_id, title, description, published_at, ticker, hash_key) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash_key) DO NOTHING;
                """
                cur.execute(query, (category_id, title, item.get('description') or item.get('summary'), dt, ticker, hash_key))
                if cur.rowcount > 0: inserted_count += 1

            conn.commit()
            print(f"📊 [{source}] 신규 저장: {inserted_count}건")
        except Exception as e:
            if conn: conn.rollback()
            print(f"❌ DB 에러: {e}")
        finally:
            if conn: conn.close()