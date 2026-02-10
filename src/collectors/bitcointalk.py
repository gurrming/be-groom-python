import re
import time
import hashlib
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

# ==========================================
# [설정 영역: 실행 전 꼭 확인하세요!]
# ==========================================
BASE_URL = "https://bitcointalk.org/index.php?board=57" # 비트코인 투기장

# ⚠️ [중요] DB의 categories 테이블을 확인하고 올바른 ID를 입력하세요.
# 예: SELECT * FROM categories; 해서 비트코인이 1번이면 1 입력.
TARGET_CATEGORY_ID = 1  

STOP_DATE = datetime(2025, 10, 1)
SPLIT_DATE = datetime(2026, 1, 20)

# 테스트를 위해 5개만 긁고 종료합니다.
TEST_LIMIT = 5 
# ==========================================

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def generate_hash_key(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def parse_date(date_str):
    try:
        current_time = datetime.now()
        if "Today" in date_str: return current_time
        if "Yesterday" in date_str: return current_time
        clean_str = re.sub(r'<[^>]+>', '', date_str).strip()
        return datetime.strptime(clean_str, "%B %d, %Y, %I:%M:%S %p")
    except:
        return None

def run_verification():
    print("🔍 [검증 모드] DB 저장 없이 데이터 형식을 터미널에 출력합니다.")
    print(f"👉 설정된 Category ID: {TARGET_CATEGORY_ID} (맞는지 확인 필수!)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = context.new_page()

        try:
            print("\n--- 페이지 접속 중 ---")
            page.goto(f"{BASE_URL}.0", timeout=60000)
            page.wait_for_selector("#bodyarea", timeout=15000)

            topic_links = page.locator("tr td span a").all()
            valid_links = list(set([l.get_attribute("href") for l in topic_links if l.get_attribute("href") and "topic=" in l.get_attribute("href")]))

            count = 0
            for link_url in valid_links:
                if count >= TEST_LIMIT: break

                try:
                    page.goto(link_url, timeout=30000)
                    try:
                        page.wait_for_selector(".post", timeout=10000)
                    except:
                        continue

                    # 데이터 추출
                    first_post_container = page.locator("td.td_headerandpost").first
                    date_text = first_post_container.locator(".smalltext").first.inner_text()
                    published_at = parse_date(date_text)
                    
                    if not published_at: continue

                    # 본문 추출
                    description = first_post_container.locator(".post").evaluate("""(element) => {
                        const clone = element.cloneNode(true);
                        const quotes = clone.querySelectorAll('.quote');
                        const headers = clone.querySelectorAll('.quoteheader');
                        quotes.forEach(q => q.remove());
                        headers.forEach(h => h.remove());
                        return clone.innerText;
                    }""")
                    
                    description = clean_text(description)
                    title = page.title().replace(" - Bitcointalk", "").strip()
                    hash_key = generate_hash_key(link_url)
                    is_test = published_at > SPLIT_DATE

                    # === [검증 포인트] DB에 들어갈 최종 데이터 형태 ===
                    db_row = {
                        "category_id": TARGET_CATEGORY_ID, # 여기 확인!
                        "title": title,
                        "description": description[:50] + "...", # 화면 출력용이라 줄임
                        "published_at": str(published_at),
                        "symbol": "BTC",
                        "platform": "bitcointalk",
                        "hash_key": hash_key,
                        "ups": 0,
                        "is_test": is_test,
                        "sentiment_score": None,
                        "sentiment_label": None
                    }

                    print("-" * 60)
                    print(f"📄 [데이터 {count+1}] DB 매핑 결과 확인")
                    print("-" * 60)
                    # JSON 형태로 예쁘게 출력
                    print(json.dumps(db_row, indent=4, ensure_ascii=False))
                    
                    print(f"\n✅ 검증: category_id={db_row['category_id']} | is_test={db_row['is_test']}")
                    
                    count += 1
                    time.sleep(1)

                except Exception as e:
                    print(f"⚠️ 에러: {e}")
                    continue

        except Exception as e:
            print(f"Fatal Error: {e}")

        browser.close()
        print("\n🏁 검증 완료. 위 데이터 형식이 맞다면 DB 저장을 진행하세요.")

if __name__ == "__main__":
    run_verification()