#!/usr/bin/env python3
"""
Browser automation for checking arXiv endorsement status.

Usage:
    uv run python scripts/arxiv_endorsement_browser.py \
      --paper-ids 2307.09288,2401.12345 \
      --export-json results.json
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    print("Error: Playwright is not installed.", file=sys.stderr)
    print("Install with: uv sync && uv run playwright install chromium", file=sys.stderr)
    sys.exit(1)

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from arxiv_auth_manager import ArxivAuthManager

# Load .env
env_path = script_dir.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

DEFAULT_DELAY_SECONDS = 30


async def check_paper_endorsements(
    page: Page,
    arxiv_id: str,
) -> Optional[Dict[str, object]]:
    """
    Navigate to a paper and extract endorsement information.
    
    Returns dict with:
        - arxiv_id: str
        - authors: List[str]
        - endorsers: List[str]  (subset of authors who can endorse)
        - check_timestamp: str
        - raw_html: str (for debugging)
    """
    paper_url = f"https://arxiv.org/abs/{arxiv_id}"
    print(f"  Checking {arxiv_id}...", file=sys.stderr)
    
    try:
        # Navigate to paper page
        await page.goto(paper_url, wait_until="networkidle")
        
        # Extract authors from the paper page first
        authors = []
        try:
            author_elements = await page.query_selector_all('.authors a')
            for elem in author_elements:
                author_name = await elem.inner_text()
                if author_name:
                    authors.append(author_name.strip())
        except Exception as e:
            print(f"    Warning: Could not extract authors: {e}", file=sys.stderr)
        
        # Look for the endorsers link
        # Try multiple selectors
        endorsers_link = await page.query_selector('a[href*="show-endorsers"]')
        if not endorsers_link:
            # Try finding by text if href selector fails
            try:
                endorsers_link = await page.get_by_text("Which authors of this paper are endorsers?", exact=False).first.element_handle()
            except:
                pass
        
        if not endorsers_link:
            print(f"    No endorsers link found (paper may be too new)", file=sys.stderr)
            return {
                "arxiv_id": arxiv_id,
                "authors": authors,
                "endorsers": [],
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_html": "",
                "error": "No endorsers link found",
            }
        
        # Click the endorsers link
        await endorsers_link.click()
        await page.wait_for_load_state("networkidle")
        
        # Check if we got a 404 or error page
        page_title = await page.title()
        if "not found" in page_title.lower() or "error" in page_title.lower():
            print(f"    Endorsers page not available", file=sys.stderr)
            return {
                "arxiv_id": arxiv_id,
                "authors": authors,
                "endorsers": [],
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_html": await page.content(),
                "error": "Endorsers page not found",
            }
        
        # Extract endorsement information
        page_content = await page.content()
        
        # Parse the endorsers page
        endorsers = await extract_endorsers_from_page(page, authors)
        
        print(f"    Found {len(endorsers)}/{len(authors)} endorsers", file=sys.stderr)
        
        return {
            "arxiv_id": arxiv_id,
            "authors": authors,
            "endorsers": endorsers,
            "check_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_html": page_content,
        }
    
    except Exception as e:
        print(f"    Error checking paper: {e}", file=sys.stderr)
        return {
            "arxiv_id": arxiv_id,
            "authors": authors if 'authors' in locals() else [],
            "endorsers": [],
            "check_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_html": "",
            "error": str(e),
        }


async def extract_endorsers_from_page(page: Page, known_authors: List[str]) -> List[str]:
    """Extract the list of endorsers from the endorsers page."""
    endorsers = []
    
    try:
        # Strategy 1: Look for explicit "can endorse" text
        page_text = await page.inner_text('body')
        
        for author in known_authors:
            if author in page_text:
                author_section = page_text[page_text.find(author):page_text.find(author)+200]
                
                if any(indicator in author_section.lower() for indicator in 
                       ['yes', 'can endorse', 'eligible', '✓', '✔']):
                    endorsers.append(author)
        
        # Strategy 2: Look for structured lists
        list_items = await page.query_selector_all('li, tr')
        for item in list_items:
            item_text = await item.inner_text()
            for author in known_authors:
                if author in item_text:
                    if any(indicator in item_text.lower() for indicator in 
                           ['yes', 'can endorse', 'eligible', '✓', '✔']):
                        if author not in endorsers:
                            endorsers.append(author)
    
    except Exception as e:
        print(f"    Warning: Error extracting endorsers: {e}", file=sys.stderr)
    
    return endorsers


async def check_papers_batch(
    browser: Browser,
    paper_ids: List[str],
    username: str,
    password: str,
) -> List[Dict[str, object]]:
    """Check endorsements for a batch of papers with rate limiting."""
    results = []
    
    # Use auth manager to get authenticated context
    auth_manager = ArxivAuthManager(username=username, password=password)
    context = await auth_manager.create_authenticated_context(browser)
    
    if not context:
        print("✗ Failed to authenticate - aborting", file=sys.stderr)
        return []
    
    # Verify authentication is still valid
    is_valid = await auth_manager.verify_auth(context)
    if not is_valid:
        print("✗ Authentication expired, trying fresh login...", file=sys.stderr)
        await context.close()
        
        # Retry with forced re-auth
        context = await auth_manager.create_authenticated_context(browser, force_reauth=True)
        if not context:
            print("✗ Re-authentication failed - aborting", file=sys.stderr)
            return []
    
    page = await context.new_page()
    
    # Process each paper
    for idx, paper_id in enumerate(paper_ids, start=1):
        print(f"\n[{idx}/{len(paper_ids)}] Processing {paper_id}", file=sys.stderr)
        
        result = await check_paper_endorsements(page, paper_id)
        if result:
            results.append(result)
        
        # Rate limiting - wait between papers (except for last one)
        if idx < len(paper_ids):
            print(f"  Waiting {DEFAULT_DELAY_SECONDS} seconds before next paper...", file=sys.stderr)
            await asyncio.sleep(DEFAULT_DELAY_SECONDS)
    
    await context.close()
    return results


async def main_async(paper_ids: str, export_json: Optional[str]) -> int:
    """Async main function."""
    
    # Parse paper IDs
    papers = [pid.strip() for pid in paper_ids.split(',')]
    
    if not papers:
        print("Error: No paper IDs provided", file=sys.stderr)
        return 1
    
    # Get credentials from environment
    username = os.getenv("ARXIV_USER") or os.getenv("ARXIV_USERNAME")
    password = os.getenv("ARXIV_PASS") or os.getenv("ARXIV_PASSWORD")
    
    if not username or not password:
        print("Error: ARXIV_USER and ARXIV_PASS must be set in .env", file=sys.stderr)
        return 1
    
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            results = await check_papers_batch(browser, papers, username, password)
            
            # Print summary
            print("\n" + "=" * 80, file=sys.stderr)
            print("Summary", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(f"Papers checked: {len(results)}", file=sys.stderr)
            
            total_endorsers = sum(len(r.get("endorsers", [])) for r in results)
            print(f"Total endorsers found: {total_endorsers}", file=sys.stderr)
            
            # Show papers with endorsers
            papers_with_endorsers = [r for r in results if r.get("endorsers")]
            if papers_with_endorsers:
                print(f"\nPapers with endorsers ({len(papers_with_endorsers)}):", file=sys.stderr)
                for result in papers_with_endorsers:
                    print(f"  {result['arxiv_id']}: {len(result['endorsers'])} endorsers", 
                          file=sys.stderr)
            
            # Export if requested
            if export_json:
                with open(export_json, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\nExported results to {export_json}", file=sys.stderr)
        
        finally:
            await browser.close()
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check arXiv endorsement status using browser automation"
    )
    
    parser.add_argument(
        "--paper-ids",
        required=True,
        help="Comma-separated list of arXiv IDs to check",
    )
    parser.add_argument(
        "--export-json",
        help="Export results to JSON file",
    )
    
    args = parser.parse_args()
    return asyncio.run(main_async(args.paper_ids, args.export_json))


if __name__ == "__main__":
    sys.exit(main())
