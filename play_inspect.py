import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.tradingview.com/symbols/XAUUSD/', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        html = await page.content()
        print(html[:1000])
        scripts = await page.query_selector_all('script')
        for script in scripts:
            inner = await script.inner_text()
            if 'price' in inner and 'XAUUSD' in inner and len(inner) < 200000:
                print('SCRIPT', inner[:500])
                break
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
