#!/usr/bin/env python3
"""
End-to-end automation to find arXiv endorsers.
1. Fetches recent papers from a category.
2. Checks each paper for eligible endorsers using authenticated browsing.
3. Reports the results.
"""
import asyncio
import argparse
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_papers import fetch_recent_papers
from arxiv_endorsement_browser import check_papers_batch
from arxiv_auth_manager import ArxivAuthManager

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

async def main():
    parser = argparse.ArgumentParser(description="Find eligible arXiv endorsers from recent papers")
    parser.add_argument("--category", default="cs.AI", help="arXiv category to scan (default: cs.AI)")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent papers to check")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (default: False for visibility)")
    parser.add_argument("--output", default="endorsers_report.json", help="Output JSON file")
    parser.add_argument("--delay", type=int, default=30, help="Delay in seconds between paper checks (default: 30)")
    
    args = parser.parse_args()
    
    # 1. Check Credentials
    username = os.getenv("ARXIV_USER") or os.getenv("ARXIV_USERNAME")
    password = os.getenv("ARXIV_PASS") or os.getenv("ARXIV_PASSWORD")
    
    if not username or not password:
        print("Error: ARXIV_USER and ARXIV_PASS must be set in .env", file=sys.stderr)
        return 1

    print(f"🚀 Starting Endorser Search for category: {args.category}")
    print("-" * 60)

    # 2. Load existing results to know which papers to skip
    existing_results = []
    already_checked = set()
    
    if Path(args.output).exists():
        try:
            with open(args.output, 'r') as f:
                existing_data = json.load(f)
                existing_results = existing_data.get('results', [])
                already_checked = {r['arxiv_id'] for r in existing_results}
            
            if already_checked:
                print(f"\n💾 Found {len(already_checked)} already-checked papers in cache")
        except Exception as e:
            print(f"   ⚠️  Could not load existing cache: {e}")
    
    # 3. Fetch Recent Papers (skipping already-cached ones)
    print(f"\n📡 Fetching {args.limit} NEW papers from {args.category} (skipping {len(already_checked)} cached)...")
    try:
        paper_ids = await fetch_recent_papers(args.category, args.limit, skip_ids=list(already_checked))
        print(f"✓ Found {len(paper_ids)} NEW papers: {', '.join(paper_ids)}")
    except Exception as e:
        print(f"✗ Error fetching papers: {e}")
        return 1

    if not paper_ids:
        print("No new papers to process.")
        return 0

    # 5. Check for Endorsers
    print(f"\n🔍 Checking {len(paper_ids)} papers for endorsers (Browser visible: {not args.headless})...")
    
    # Create callback to save results incrementally
    new_results = []
    
    async def save_result_callback(result, idx, total):
        """Save results after each paper is checked."""
        new_results.append(result)
        
        # Merge with existing results and save
        all_results = existing_results + new_results
        check_data = {
            "category": args.category,
            "papers_scanned": len(all_results),
            "results": all_results
        }
        
        with open(args.output, 'w') as f:
            json.dump(check_data, f, indent=2)
        
        print(f"  💾 Saved progress: {len(all_results)} total papers in cache", file=sys.stderr)
    
    async with async_playwright() as p:
        # Launch browser (headless=False by default to satisfy 'REAL browsing' request unless flag set)
        browser = await p.chromium.launch(headless=args.headless)
        
        try:
            results = await check_papers_batch(browser, paper_ids, username, password, args.delay, save_result_callback)
            
            # 6. Report Results
            print("\n📊 SEARCH RESULTS")
            print("=" * 60)
            
            found_count = 0
            all_endorsers = set()
            
            for res in new_results:
                eid = res.get('arxiv_id')
                endorsers = res.get('endorsers', [])
                if endorsers:
                    found_count += 1
                    print(f"\n📄 Paper: {eid}")
                    print(f"   Link: https://arxiv.org/abs/{eid}")
                    print(f"   ✅ Eligible Endorsers found: {len(endorsers)}")
                    for name in endorsers:
                        print(f"      - {name}")
                        all_endorsers.add(name)
                elif res.get('error'):
                    print(f"\n📄 Paper: {eid} - ⚠️ {res.get('error')}")
                else:
                    pass # Silent for no endorsers to keep output clean? Or log it.
            
            print("\n" + "-" * 60)
            print(f"Summary:")
            print(f"  Papers Checked (this run): {len(new_results)}")
            print(f"  Total Papers in Cache: {len(existing_results) + len(new_results)}")
            print(f"  Papers with Endorsers (this run): {found_count}")
            print(f"  Unique Endorsers Found (this run): {len(all_endorsers)}")
            
            print(f"\n✅ All results saved incrementally to {args.output}")
            
        finally:
            await browser.close()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

