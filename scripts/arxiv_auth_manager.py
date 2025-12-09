#!/usr/bin/env python3
"""
arXiv Authentication Manager with Playwright state persistence.

Handles login once and saves the authentication state for reuse.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    print("Error: Playwright is not installed.", file=sys.stderr)
    print("Install with: uv sync && uv run playwright install chromium", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv


ARXIV_LOGIN_URL = "https://arxiv.org/login"
DEFAULT_AUTH_STATE_PATH = Path.home() / ".arxiv_reviewer_cache" / "arxiv_auth_state.json"


class ArxivAuthManager:
    """Manages arXiv authentication with state persistence."""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_state_path: Optional[Path] = None,
    ):
        """
        Initialize the auth manager.
        
        Args:
            username: arXiv username (if None, loads from env)
            password: arXiv password (if None, loads from env)
            auth_state_path: Path to save/load auth state
        """
        # Load .env if it exists
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        self.username = username or os.getenv("ARXIV_USER") or os.getenv("ARXIV_USERNAME")
        self.password = password or os.getenv("ARXIV_PASS") or os.getenv("ARXIV_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError(
                "arXiv credentials not found. Set ARXIV_USER and ARXIV_PASS "
                "in .env or pass directly to constructor."
            )
        
        self.auth_state_path = auth_state_path or DEFAULT_AUTH_STATE_PATH
        self.auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    
    def has_saved_auth(self) -> bool:
        """Check if we have a saved authentication state."""
        return self.auth_state_path.exists()
    
    async def login_and_save_state(self, browser: Browser) -> bool:
        """
        Perform login and save the authentication state.
        
        Returns True if successful, False otherwise.
        """
        print(f"Logging in to arXiv as {self.username}...", file=sys.stderr)
        
        # Create a new context for login
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(ARXIV_LOGIN_URL, wait_until="networkidle")
            await asyncio.sleep(1)
            
            # Fill in credentials
            try:
                await page.fill('input[name="username"]', self.username, timeout=5000)
            except:
                try:
                    await page.fill('input[id="username"]', self.username, timeout=5000)
                except:
                    await page.fill('input[type="text"]', self.username, timeout=5000)
            
            try:
                await page.fill('input[name="password"]', self.password, timeout=5000)
            except:
                try:
                    await page.fill('input[id="password"]', self.password, timeout=5000)
                except:
                    await page.fill('input[type="password"]', self.password, timeout=5000)
            
            print("  Filled in credentials, submitting...", file=sys.stderr)
            
            # Submit the form
            submit_clicked = False
            for selector in ['button[type="submit"]', 'input[type="submit"]', 'text=/sign in|log in/i']:
                try:
                    await page.click(selector, timeout=5000)
                    submit_clicked = True
                    break
                except:
                    continue
            
            if not submit_clicked:
                await page.press('input[type="password"]', 'Enter')
            
            # Wait for navigation
            print("  Waiting for login response...", file=sys.stderr)
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            # Verify login success
            current_url = page.url
            
            if "login" in current_url and "error" in current_url.lower():
                print("✗ Login failed - check credentials", file=sys.stderr)
                await context.close()
                return False
            
            # Try to verify we're logged in
            try:
                await page.wait_for_selector('text=/logout|log out/i', timeout=5000)
            except:
                if "login" in current_url:
                    print("✗ Login failed - still on login page", file=sys.stderr)
                    await context.close()
                    return False
            
            # Save the authentication state
            await context.storage_state(path=str(self.auth_state_path))
            print(f"✓ Login successful, state saved to {self.auth_state_path}", file=sys.stderr)
            
            await context.close()
            return True
            
        except Exception as e:
            print(f"✗ Error during login: {e}", file=sys.stderr)
            await context.close()
            return False
    
    async def create_authenticated_context(
        self,
        browser: Browser,
        force_reauth: bool = False,
    ) -> Optional[BrowserContext]:
        """
        Create a browser context with arXiv authentication.
        
        If saved auth state exists and force_reauth is False, loads it.
        Otherwise, performs login and saves the state.
        
        Args:
            browser: Playwright browser instance
            force_reauth: If True, force a new login even if state exists
            
        Returns:
            Authenticated BrowserContext or None if login failed
        """
        # Check if we need to login
        if force_reauth or not self.has_saved_auth():
            success = await self.login_and_save_state(browser)
            if not success:
                return None
        else:
            print(f"✓ Loading saved authentication from {self.auth_state_path}", file=sys.stderr)
        
        # Create context with saved state
        try:
            context = await browser.new_context(storage_state=str(self.auth_state_path))
            return context
        except Exception as e:
            print(f"✗ Error loading auth state: {e}", file=sys.stderr)
            print("  Attempting fresh login...", file=sys.stderr)
            
            # Delete invalid state and retry
            if self.auth_state_path.exists():
                self.auth_state_path.unlink()
            
            success = await self.login_and_save_state(browser)
            if not success:
                return None
            
            return await browser.new_context(storage_state=str(self.auth_state_path))
    
    async def verify_auth(self, context: BrowserContext) -> bool:
        """
        Verify that the authentication is still valid.
        
        Returns True if authenticated, False otherwise.
        """
        page = await context.new_page()
        try:
            # Visit a page that requires authentication
            await page.goto("https://arxiv.org/user/", timeout=10000)
            
            # Check if we're still logged in
            try:
                await page.wait_for_selector('text=/logout|log out/i', timeout=5000)
                await page.close()
                return True
            except:
                # If we're redirected to login, auth expired
                if "login" in page.url:
                    await page.close()
                    return False
                await page.close()
                return True
        except Exception as e:
            print(f"  Warning: Could not verify auth: {e}", file=sys.stderr)
            await page.close()
            return False
    
    def clear_auth_state(self):
        """Remove saved authentication state."""
        if self.auth_state_path.exists():
            self.auth_state_path.unlink()
            print(f"✓ Cleared auth state from {self.auth_state_path}", file=sys.stderr)


async def main():
    """Test the auth manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="arXiv Authentication Manager")
    parser.add_argument("--login", action="store_true", help="Perform login and save state")
    parser.add_argument("--verify", action="store_true", help="Verify existing auth")
    parser.add_argument("--clear", action="store_true", help="Clear saved auth state")
    args = parser.parse_args()
    
    if args.clear:
        auth_manager = ArxivAuthManager()
        auth_manager.clear_auth_state()
        return 0
    
    auth_manager = ArxivAuthManager()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            if args.login or not auth_manager.has_saved_auth():
                # Perform login
                success = await auth_manager.login_and_save_state(browser)
                if not success:
                    print("✗ Login failed", file=sys.stderr)
                    return 1
            
            if args.verify or args.login:
                # Verify authentication
                context = await auth_manager.create_authenticated_context(browser)
                if context:
                    is_valid = await auth_manager.verify_auth(context)
                    if is_valid:
                        print("✓ Authentication is valid", file=sys.stderr)
                    else:
                        print("✗ Authentication expired or invalid", file=sys.stderr)
                        return 1
                    await context.close()
                else:
                    print("✗ Could not create authenticated context", file=sys.stderr)
                    return 1
            else:
                print(f"✓ Auth state exists at {auth_manager.auth_state_path}", file=sys.stderr)
        
        finally:
            await browser.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
