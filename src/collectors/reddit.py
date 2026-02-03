import asyncio
from playwright.async_api import async_playwright
import hashlib
import time

async def crawl_reddit_bulk(target_count=50): # target_count로 목표 개수 설정
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        print(f"레딧 접속 중... (목표: {target_count}개)")
        await page.goto("https://www.reddit.com/r/CryptoCurrency/new/", wait_until="domcontentloaded")

        print("로봇 체크가 보이면 직접 클릭해 주세요! (기다리는 중...)")
        
        try:
            # 첫 로딩 대기
            await page.wait_for_selector("shreddit-post", timeout=5000)
            
            collected_data = {} # 중복 제거를 위해 dict 사용 (news_id가 key)
            
            while len(collected_data) < target_count:
                # 1. 현재 화면에 있는 모든 게시글 찾기
                posts = await page.query_selector_all('shreddit-post')
                
                for post in posts:
                    title = await post.get_attribute('post-title')
                    if not title: continue
                    
                    # news_id 생성 (중복 방지)
                    news_id = f"reddit_{hashlib.md5(title.encode()).hexdigest()[:10]}"
                    
                    if news_id not in collected_data:
                        collected_data[news_id] = title
                        print(f"[{len(collected_data)}/{target_count}] 수집: {title[:30]}...")
                    
                    if len(collected_data) >= target_count:
                        break
                
                # 2. 화면 아래로 스크롤 (사람처럼 보이게 살짝 기다리며 스크롤)
                print("새로운 글을 불러오기 위해 스크롤 중...")
                await page.mouse.wheel(0, 2000) # 아래로 2000픽셀 이동
                await page.wait_for_timeout(2000) # 로딩 대기 (2초)

            print(f"✅ 총 {len(collected_data)}개의 데이터를 성공적으로 수집했습니다.")
            
        except Exception as e:
            print(f"오류 발생: {e}")

        await browser.close()
        return collected_data

if __name__ == "__main__":
    # 50개를 수집하도록 실행
    final_data = asyncio.run(crawl_reddit_bulk(50))
    # 결과 확인용
    for nid, title in final_data.items():
        print(f"{nid} : {title}")