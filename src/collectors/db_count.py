import time
from playwright.sync_api import sync_playwright

def check_content_structure_fixed():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        url = "https://kr.investing.com/crypto/bitcoin/chat"
        print(f"🚀 접속 중: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        # 댓글 로딩 대기
        try:
            page.locator("[data-test='comment-date']").first.wait_for(state="visible", timeout=15000)
            print("✅ 댓글 로딩 완료\n")
        except:
            print("❌ 댓글 로딩 실패")
            return

        date_elements = page.locator("[data-test='comment-date']")
        count = date_elements.count()
        print(f"🔎 발견된 댓글 수: {count}개\n")

        for i in range(min(5, count)):
            print(f"--- [댓글 {i+1}] 최종 구조 검증 ---")
            
            date_el = date_elements.nth(i)
            
            # [핵심 수정] 2단계가 아니라 3단계 위로 올라가야 '댓글 전체 박스'가 나옵니다.
            # span -> div -> div(헤더) -> div(전체박스)
            wrapper = date_el.locator("xpath=../../..")
            
            # 1. 유저명 찾기 (Wrapper 안에서 a 태그 검색)
            try:
                user = wrapper.locator("a").first.inner_text().strip()
            except:
                user = "Unknown"

            # 2. 내용 찾기 (Wrapper 안에서 .break-words 클래스 검색)
            # 스크린샷에 보이는 명확한 클래스명 사용
            try:
                content_el = wrapper.locator(".break-words").first
                content = content_el.inner_text().strip()
            except:
                content = "[[내용 태그(.break-words) 없음]]"

            # 3. 날짜 텍스트
            date_text = date_el.inner_text().strip()

            print(f"👤 유저: {user}")
            print(f"📅 날짜: {date_text}")
            print(f"💬 내용: {content}")
            print("------------------------\n")
            
        browser.close()

if __name__ == "__main__":
    check_content_structure_fixed()