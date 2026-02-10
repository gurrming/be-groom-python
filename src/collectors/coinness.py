import time
import hashlib
import re
from datetime import datetime, timedelta
import psycopg2
from playwright.sync_api import sync_playwright

def parse_date_surgical(full_text):
    """
    텍스트 더미 속에서 '진짜 날짜'만 핀셋으로 집어내듯 찾습니다.
    가격($60,000)이나 퍼센트(10.5%)를 날짜로 착각하지 않도록 방어 로직 추가.
    """
    now = datetime.now()
    
    # 줄바꿈 문자를 공백으로 치환하여 한 줄로 만듦 (매칭 확률 높임)
    clean_text = full_text.replace('\n', '  ')

    # 1. [상대 시간] "N분 전", "N시간 전", "방금 전"
    # (\d{1,2}) : 숫자가 1~2자리인 경우만 찾음 (가격 데이터 방지)
    
    # 1-1. 분 전 (1~59분)
    min_match = re.search(r'(?<!\d)(\d{1,2})\s*분\s*전', clean_text)
    if min_match:
        mins = int(min_match.group(1))
        return now - timedelta(minutes=mins)

    # 1-2. 시간 전 (1~23시간)
    hour_match = re.search(r'(?<!\d)(\d{1,2})\s*시간\s*전', clean_text)
    if hour_match:
        hours = int(hour_match.group(1))
        return now - timedelta(hours=hours)

    # 1-3. 방금 전
    if '방금 전' in clean_text or '방금' in clean_text:
        return now

    # 1-4. 어제
    if '어제' in clean_text:
        return now - timedelta(days=1)

    # 2. [절대 날짜] YYYY.MM.DD 또는 MM.DD
    # 정규식: 숫자.숫자 패턴을 찾되, 유효한 월/일인지 검증
    
    # 날짜 패턴 찾기 (모든 후보군 추출)
    date_candidates = re.findall(r'(\d{2,4})\.(\d{1,2})(?:\.(\d{1,2}))?', clean_text)
    
    for y_str, m_str, d_str in date_candidates:
        try:
            # 일(Day)이 없으면(MM.DD 형식) y_str이 월, m_str이 일이 됨
            if not d_str: 
                # MM.DD 형식 (예: 10.25)
                m, d = int(y_str), int(m_str)
                y = now.year
            else:
                # YYYY.MM.DD 또는 YY.MM.DD
                y, m, d = int(y_str), int(m_str), int(d_str)
                if y < 100: y += 2000 # 25.10.25 -> 2025.10.25

            # 유효성 검사 (월 1~12, 일 1~31) -> 이거 아니면 가격 데이터(10.5)임
            if 1 <= m <= 12 and 1 <= d <= 31:
                parsed_date = datetime(y, m, d)
                
                # 미래 날짜 보정 (현재 2월인데 10월 데이터면 작년으로)
                if parsed_date > now + timedelta(days=2):
                    parsed_date = datetime(y - 1, m, d)
                
                return parsed_date
        except:
            continue

    return None

def extract_symbol_strict(text):
    if not text: return None
    # $BTC, $ETH 등 대문자만 추출 ($50, $1000 제외)
    match = re.search(r'\$([A-Z]{2,10})\b', text)
    return match.group(1) if match else None

def generate_hash(title, description, published_at):
    date_str = published_at.strftime('%Y-%m-%d %H:%M')
    data = f"{title}{description}{date_str}"
    return hashlib.sha256(data.encode()).hexdigest()

def crawl_coinness_safe():
    db_config = {
        "user": "postgres",
        "password": "0000",
        "database": "app", 
        "host": "localhost",
        "port": 15432
    }
    
    target_date = datetime(2025, 10, 1)

    with sync_playwright() as p:
        print("🚀 코인니스 크롤러 시작 (안전 모드)")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://coinness.com/community")
        time.sleep(5)

        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        processed_count = 0
        reached_target = False
        
        while not reached_target:
            all_titles = page.locator('h3').all()
            total_found = len(all_titles)
            new_items = all_titles[processed_count:]
            
            print(f"📊 신규 데이터 {len(new_items)}개 분석 중...")

            for title_elem in new_items:
                try:
                    title = title_elem.inner_text().strip()
                    if not title: continue

                    # 컨테이너 전체 텍스트 가져오기
                    container = title_elem.locator("xpath=../..") 
                    full_text = container.inner_text()
                    
                    # [수정된 함수] 날짜 추출
                    pub_date = parse_date_surgical(full_text)

                    if pub_date is None:
                        # 날짜가 없으면 스킵 (에러 내지 말고 조용히 넘어감)
                        continue

                    # 날짜 체크
                    if pub_date < target_date:
                        print(f"\n✅ 2025년 10월 데이터 도달! ({pub_date.strftime('%Y-%m-%d')})")
                        reached_target = True
                        break

                    # 나머지 데이터 추출
                    description = full_text.replace(title, "").strip()[:500]
                    symbol = extract_symbol_strict(title) or extract_symbol_strict(description)
                    hash_key = generate_hash(title, description, pub_date)

                    # 로그: 날짜와 제목 앞부분만 깔끔하게
                    print(f"[{pub_date.strftime('%m-%d')}] {title[:10]}... (Sym: {symbol})")

                    cur.execute("""
                        INSERT INTO community_data (
                            title, description, published_at, platform, hash_key, symbol, is_test
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (hash_key) DO NOTHING;
                    """, (title, description, pub_date, 'coinness', hash_key, symbol, False))
                    
                except Exception as e:
                    # 치명적이지 않은 에러는 출력하고 계속 진행
                    print(f"⚠️ 항목 건너뜀: {e}")
                    continue
            
            processed_count = total_found
            conn.commit()

            if reached_target: break

            # 더보기 버튼 처리
            try:
                # 텍스트 매칭 범위를 넓힘 (더보기, Load More, More 등)
                more_btn = page.locator('button').filter(has_text=re.compile(r"더보기|Load More|More")).first
                
                if more_btn.is_visible():
                    # print("🔽 더보기...") # 로그 너무 많으면 주석 처리
                    more_btn.click()
                    time.sleep(2)
                else:
                    page.mouse.wheel(0, 5000)
                    time.sleep(2)
            except:
                # 버튼 못 찾으면 그냥 스크롤 시도
                page.mouse.wheel(0, 5000)
                time.sleep(2)

        cur.close()
        conn.close()
        browser.close()

if __name__ == "__main__":
    crawl_coinness_safe()