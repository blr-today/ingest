import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, Playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        iphone = p.devices["iPhone 13"]

        context = await browser.new_context(**iphone)
        page = await context.new_page()
        await page.goto("https://in.bookmyshow.com/explore/events-bengaluru")

        Path("bms").mkdir(exist_ok=True)
        request_number = 1
        events = []

        async def capture_response(response):
            nonlocal request_number
            if "/api/explore/v1/discover/events-bengaluru" in response.url:
                try:
                    content = await response.json()
                    events.append(content['meta']['ldSchema']['eventsSchema'])
                except Exception as e:
                    print("Failed to parse JSON", e)
                    content="FAILED"

        page.on("response", capture_response)

        while True:
            previous_height = await page.evaluate("document.body.scrollHeight")
            await page.mouse.wheel(0, previous_height)
            await page.wait_for_timeout(1000)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                with open("bms/bms-raw.json", "w") as f:
                    json.dump(events, f, indent=2)
                break

        await browser.close()

asyncio.run(main())
