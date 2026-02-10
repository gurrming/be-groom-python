import feedparser
import hashlib
import psycopg2
import re
import time
import schedule  # [추가] 스케줄링 라이브러리
from datetime import datetime, timezone
from time import mktime

class RssCollector:
    def __init__(self):
        # DB 연결 정보
        self.db_params = {
            "host": "localhost", "port": "15432",
            "database": "app", "user": "postgres", "password": "0000"
        }
        
        # 주요 코인 미디어 RSS URL 리스트
        self.feeds = {
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "CoinTelegraph": "https://cointelegraph.com/rss",
            "Decrypt": "https://decrypt.co/feed",
            "BitcoinMagazine": "https://bitcoinmagazine.com/.rss/full/",
            "CryptoSlate": "https://cryptoslate.com/feed/",
            "NewsBTC": "https://www.newsbtc.com/feed/"
        }
        
        # 테스트 데이터 분기점
        self.split_date = datetime(2026, 1, 20, tzinfo=timezone.utc)

    def _get_db_categories(self):
        """DB에서 수집 대상 코인(카테고리) 정보를 가져옵니다."""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            cur.execute("SELECT symbol, category_name, category_id FROM public.category")
            categories = [{'symbol': r[0].strip().upper(), 'name': r[1].strip().upper(), 'id': r[2]} for r in cur.fetchall()]
            conn.close()
            return categories
        except Exception as e:
            print(f"⚠️ DB 연결/카테고리 로드 실패: {e}")
            return []

    def _save_to_db(self, items, source):
        """수집된 데이터를 news_data 테이블에 저장합니다."""
        if not items: return
        
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            inserted_count = 0
            
            query = """
            INSERT INTO public.news_data
            (category_id, title, description, published_at, symbol, hash_key, is_test) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (hash_key) DO NOTHING;
            """
            
            for item in items:
                cur.execute(query, item)
                if cur.rowcount > 0:
                    inserted_count += 1
            
            conn.commit()
            if inserted_count > 0:
                print(f"   💾 [{source}] {inserted_count}건 신규 저장 완료")
            else:
                print(f"   root [{source}] 새로운 데이터 없음 (중복)")
                
        except Exception as e:
            if conn: conn.rollback()
            print(f"❌ DB 저장 에러: {e}")
        finally:
            if conn: conn.close()

    def collect_rss(self):
        """RSS 피드를 순회하며 데이터를 수집합니다."""
        categories = self._get_db_categories()
        if not categories:
            print("❌ 카테고리 정보가 없어 중단합니다.")
            return

        total_saved_all = 0
        print(f"\n📡 [RSS] 주요 언론사 뉴스 수집 시작... (시간: {datetime.now()})")

        for source_name, url in self.feeds.items():
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    print(f"⚠️ [{source_name}] 데이터를 가져오지 못했습니다.")
                    continue
                
                print(f"👉 [{source_name}] 최신 글 {len(feed.entries)}개 분석 중...", end=' ')
                
                items_to_save = []
                
                for entry in feed.entries:
                    dt = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
                    else:
                        dt = datetime.now(timezone.utc)

                    title = entry.title
                    raw_desc = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                    description = re.sub('<[^<]+?>', '', raw_desc)[:800].strip()

                    title_upper = title.upper()
                    matched_cat = None
                    
                    for cat in categories:
                        if re.search(rf"\b{cat['symbol']}\b", title_upper) or \
                           re.search(rf"\b{cat['name']}\b", title_upper):
                            matched_cat = cat
                            break
                    
                    if matched_cat:
                        hash_key = hashlib.md5(f"{title}_{dt}_{matched_cat['symbol']}".encode()).hexdigest()
                        is_test = dt >= self.split_date
                        
                        items_to_save.append((
                            matched_cat['id'], title, description, dt, 
                            matched_cat['symbol'], hash_key, is_test
                        ))

                if items_to_save:
                    print(f"-> {len(items_to_save)}건 매칭 확인")
                    self._save_to_db(items_to_save, source_name)
                    total_saved_all += len(items_to_save)
                else:
                    print("-> 매칭되는 코인 없음")

            except Exception as e:
                print(f"\n❌ [{source_name}] 처리 중 에러: {e}")

        print(f"\n✨ [RSS] 전체 수집 완료. 총 {total_saved_all}건 저장됨.")
        print("-" * 50)

# --- [수정된 실행 블록] ---
def job():
    """스케줄러에 의해 실행될 작업 함수"""
    try:
        collector = RssCollector()
        collector.collect_rss()
    except Exception as e:
        print(f"⚠️ 작업 실행 중 치명적 오류 발생: {e}")

if __name__ == "__main__":
    print("⏳ RSS 자동 수집기가 시작되었습니다. (Ctrl+C로 종료)")
    
    # 1. 프로그램 시작 시 즉시 한 번 실행 (선택 사항)
    job()
    
    # 2. 스케줄 설정 (원하는 시간으로 변경 가능)
    # schedule.every(10).seconds.do(job)  # 테스트용: 10초마다
    # schedule.every(1).minutes.do(job)   # 1분마다
    schedule.every(30).minutes.do(job)    # 30분마다
    # schedule.every(1).hours.do(job)     # 1시간마다

    # 3. 무한 루프로 스케줄 유지
    while True:
        try:
            schedule.run_pending()
            time.sleep(1) # CPU 과부하 방지를 위한 1초 대기
        except KeyboardInterrupt:
            print("\n🛑 프로그램을 종료합니다.")
            break