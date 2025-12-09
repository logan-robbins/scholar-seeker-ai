#!/usr/bin/env python3
"""Debug script to see what's actually on the arXiv paper page."""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from arxiv_auth_manager import ArxivAuthManager
from playwright.async_api import async_playwright

load_dotenv(Path(__file__).parent.parent / ".env")

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        auth_manager = ArxivAuthManager()
        context = await auth_manager.create_authenticated_context(browser)
        page = await context.new_page()
        
        # Navigate to a paper
        arxiv_id = "1706.03762"
        await page.goto(f"https://arxiv.org/abs/{arxiv_id}", wait_until="networkidle")
        
        print(f"\n=== Checking page for {arxiv_id} ===\n")
        
        # Check for endorsers link
        endorsers_links = await page.query_selector_all('a')
        
        print("All links on the page containing 'endors':")
        for link in endorsers_links:
            href = await link.get_attribute('href')
            text = await link.inner_text()
            if href and 'endors' in href.lower():
                print(f"  FOUND: {text} -> {href}")
        
        print("\nAll links containing 'author':")
        for link in endorsers_links:
            href = await link.get_attribute('href')
            text = await link.inner_text()
            if href and 'author' in href.lower():
                print(f"  {text[:50]} -> {href[:80]}")
        
        # Check full page text for "endors"
        page_text = await page.inner_text('body')
        if 'endors' in page_text.lower():
            print("\n'endors' found in page text")
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if 'endors' in line.lower():
                    print(f"  Line {i}: {line.strip()}")
        else:
            print("\n'endors' NOT found in page text")
        
        print("\n\nPage will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())

