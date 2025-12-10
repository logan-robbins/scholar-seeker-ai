#!/usr/bin/env python3
"""
Fetch recent paper IDs from an arXiv category page.
"""
import asyncio
import sys
import re
import time
from datetime import datetime, timedelta
from typing import List
from playwright.async_api import async_playwright

async def fetch_recent_papers(category: str = "cs.AI", limit: int = 20, skip_ids: List[str] = None) -> List[str]:
    """
    Fetch recent paper IDs from arXiv category page with pagination support.
    Uses show parameter to get more papers per request (skip=X&show=Y).
    
    Args:
        category: arXiv category (e.g., "cs.AI")
        limit: Number of NEW papers to fetch (not counting skip_ids)
        skip_ids: List of paper IDs to skip (e.g., already cached papers)
    """
    paper_ids = []
    skip_ids = skip_ids or []
    skip_ids_set = set(skip_ids)  # For faster lookups
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # arXiv recent page supports pagination with ?skip=X&show=Y
        # Valid show values: 25, 50, 100, 250
        # Using 50 to be very respectful of arXiv's servers
        skip = 0
        show_per_page = 50
        page_num = 0
        
        while len(paper_ids) < limit:
            # Rate limiting: 10 second delay before each request (except first)
            if page_num > 0:
                print(f"  Waiting 10 seconds before next page...", file=sys.stderr)
                await asyncio.sleep(10)
            
            url = f"https://arxiv.org/list/{category}/recent?skip={skip}&show={show_per_page}"
            print(f"Fetching from {url}...", file=sys.stderr)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # arXiv lists have links like /abs/2307.09288
                links = await page.query_selector_all('a[href^="/abs/"]')
                
                papers_found_this_page = 0
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        match = re.search(r'/abs/(\d+\.\d+)', href)
                        if match:
                            pid = match.group(1)
                            # Skip if already in our list or in the skip list
                            if pid not in paper_ids and pid not in skip_ids_set:
                                paper_ids.append(pid)
                                papers_found_this_page += 1
                                if len(paper_ids) >= limit:
                                    break
                
                # If we didn't find any new papers on this page, we've exhausted the listing
                if papers_found_this_page == 0:
                    print(f"  No more new papers found, stopping at {len(paper_ids)} papers", file=sys.stderr)
                    break
                
                skip += show_per_page
                page_num += 1
                    
            except Exception as e:
                print(f"  Warning: Could not fetch from {url}: {e}", file=sys.stderr)
                page_num += 1
                break
        
        await browser.close()
    
    print(f"✓ Fetched {len(paper_ids)} unique papers", file=sys.stderr)
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

