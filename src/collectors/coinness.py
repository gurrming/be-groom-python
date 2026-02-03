import asyncio
from playwright.async_api import async_playwright
import hashlib

async def crawl_coinness_community_unique():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://coinness.com/community", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 1. 텍스트가 포함된 모든 p 태그 수집
        elements = await page.query_selector_all("p")
        
        seen_ids = set() # 중복 체크용 셋
        final_posts = []

        for el in elements:
            text = (await el.inner_text()).strip()
            
            # 필터링 로직
            if len(text) < 15 or "Copyright" in text:
                continue
            
            # news_id 생성
            news_id = f"coinness_{hashlib.md5(text.encode()).hexdigest()[:10]}"
            
            # 중복되지 않은 것만 리스트에 추가
            if news_id not in seen_ids:
                seen_ids.add(news_id)
                final_posts.append({
                    "news_id": news_id,
                    "title": text[:50], # 제목은 앞부분 50자만
                    "content": text
                })
                print(f"✨ [신규] {text[:40]}...")

        await browser.close()
        return final_posts
if __name__ == "__main__":
    asyncio.run(crawl_coinness_community_unique())