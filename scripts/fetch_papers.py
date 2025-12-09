#!/usr/bin/env python3
"""
Fetch recent paper IDs from an arXiv category page.
"""
import asyncio
import sys
import re
from typing import List
from playwright.async_api import async_playwright

async def fetch_recent_papers(category: str = "cs.AI", limit: int = 20) -> List[str]:
    """
    Fetch recent paper IDs from arXiv category page.
    """
    url = f"https://arxiv.org/list/{category}/recent"
    print(f"Fetching recent papers from {url}...", file=sys.stderr)
    
    paper_ids = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url, wait_until="domcontentloaded")
        
        # arXiv lists usually have links like /abs/2307.09288
        # We look for the 'abstract' links which contain the ID
        links = await page.query_selector_all('a[href^="/abs/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                # Extract ID from /abs/2307.09288
                match = re.search(r'/abs/(\d+\.\d+)', href)
                if match:
                    pid = match.group(1)
                    if pid not in paper_ids:
                        paper_ids.append(pid)
                        if len(paper_ids) >= limit:
                            break
        
        await browser.close()
    
    return paper_ids

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch recent arXiv paper IDs")
    parser.add_argument("--category", default="cs.AI", help="arXiv category (default: cs.AI)")
    parser.add_argument("--limit", type=int, default=20, help="Number of papers to fetch")
    args = parser.parse_args()
    
    try:
        ids = asyncio.run(fetch_recent_papers(args.category, args.limit))
        print(",".join(ids))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

