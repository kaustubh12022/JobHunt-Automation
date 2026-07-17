import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Launching Chromium headful mode...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating to example.com...")
        await page.goto("https://example.com")
        print("Browser is open! Waiting for 10 seconds so you can see it...")
        await asyncio.sleep(10)
        await browser.close()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
