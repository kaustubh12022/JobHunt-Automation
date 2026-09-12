import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:5000")
        await page.screenshot(path="live_home.png")
        await browser.close()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
