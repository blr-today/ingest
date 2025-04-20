#!/usr/bin/env python3
import sys
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def fetch_page(url, headless=True):
    """
    Fetch a webpage using Playwright in headless mode, wait for redirects,
    and dump the DOM to stdout. Error messages are written to stderr.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            page = await browser.new_page()
            await stealth_async(page)
            # Listen for console messages and redirect errors to stderr
            page.on("console", lambda msg: 
                print(f"CONSOLE {msg.type}: {msg.text}", file=sys.stderr) 
                if msg.type in ["error", "warning"] else None)
            
            # Navigate to URL and wait until network is idle (handles redirects)
            res = await page.goto(url, wait_until="networkidle")

            return (await res.body()).decode("utf-8")
            
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(fetch_page(url))
