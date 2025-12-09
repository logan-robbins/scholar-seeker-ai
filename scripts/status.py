#!/usr/bin/env python3
"""
Status checker for arXiv browser automation setup.

Shows:
- Environment configuration
- Authentication state
- Cache status
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)

def check_status():
    """Check and display system status."""
    
    print("=" * 80)
    print("arXiv BROWSER AUTOMATION - STATUS CHECK")
    print("=" * 80)
    print()
    
    # Check credentials
    print("📋 CREDENTIALS")
    print("-" * 80)
    arxiv_user = os.getenv("ARXIV_USER") or os.getenv("ARXIV_USERNAME")
    arxiv_pass = os.getenv("ARXIV_PASS") or os.getenv("ARXIV_PASSWORD")
    
    if arxiv_user and arxiv_pass:
        print(f"  ✓ Username: {arxiv_user}")
        print(f"  ✓ Password: {'*' * len(arxiv_pass)}")
    else:
        print("  ✗ Credentials not found in .env")
        print("    Create .env with: ARXIV_USER and ARXIV_PASS")
    print()
    
    # Check authentication state
    print("🔐 AUTHENTICATION STATE")
    print("-" * 80)
    auth_state_path = Path.home() / ".arxiv_reviewer_cache" / "arxiv_auth_state.json"
    
    if auth_state_path.exists():
        size = auth_state_path.stat().st_size
        mtime = auth_state_path.stat().st_mtime
        from datetime import datetime
        mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"  ✓ Auth state exists: {auth_state_path}")
        print(f"  ✓ File size: {size} bytes")
        print(f"  ✓ Last modified: {mod_time}")
        print()
        print("  💡 Browser automation will use saved session (no login needed)")
    else:
        print(f"  ✗ No saved auth state at {auth_state_path}")
        print()
        print("  💡 Run: uv run python scripts/arxiv_auth_manager.py --login")
    print()
    
    # Check cache directory
    print("💾 CACHE DIRECTORY")
    print("-" * 80)
    cache_dir = Path.home() / ".arxiv_reviewer_cache"
    
    if cache_dir.exists():
        print(f"  ✓ Cache directory: {cache_dir}")
        
        # List contents
        files = list(cache_dir.iterdir())
        if files:
            print(f"  ✓ Files: {len(files)}")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print(f"    - {f.name} ({size_kb:.1f} KB)")
        else:
            print("  ℹ Empty cache directory")
    else:
        print(f"  ✗ Cache directory not found: {cache_dir}")
        print("    Will be created on first run")
    print()
    
    # Check dependencies
    print("📦 DEPENDENCIES")
    print("-" * 80)
    
    try:
        import playwright
        print(f"  ✓ playwright: installed")
    except ImportError:
        print("  ✗ playwright not installed")
        print("    Run: uv sync && uv run playwright install chromium")
    
    try:
        import requests
        print(f"  ✓ requests: installed")
    except ImportError:
        print("  ✗ requests not installed")
    
    try:
        import dotenv
        print(f"  ✓ python-dotenv: installed")
    except ImportError:
        print("  ✗ python-dotenv not installed")
    
    print()
    
    # Quick start
    print("🚀 QUICK START")
    print("-" * 80)
    
    if arxiv_user and arxiv_pass and auth_state_path.exists():
        print("  ✓ All set! Ready to run browser automation")
        print()
        print("  Try:")
        print("    uv run python scripts/arxiv_endorsement_browser.py \\")
        print("      --paper-ids '2307.09288' \\")
        print("      --export-json results.json")
    elif arxiv_user and arxiv_pass:
        print("  ⚠ Credentials found but not authenticated yet")
        print()
        print("  Next step:")
        print("    uv run python scripts/arxiv_auth_manager.py --login --verify")
    else:
        print("  ⚠ Setup required")
        print()
        print("  Steps:")
        print("    1. Create .env with ARXIV_USER and ARXIV_PASS")
        print("    2. Run: uv run python scripts/arxiv_auth_manager.py --login")
        print("    3. Check status: uv run python scripts/status.py")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    check_status()

