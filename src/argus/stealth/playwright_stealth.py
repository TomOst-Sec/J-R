"""Stealth Playwright browser wrapper for anti-detection."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

from argus.stealth.browser_profiles import BrowserProfile, get_random_profile

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# Common CAPTCHA indicators
_CAPTCHA_INDICATORS = [
    "recaptcha", "hcaptcha", "captcha-delivery",
    "cf-challenge", "challenge-platform", "turnstile",
    "g-recaptcha", "h-captcha",
]

# Stealth JS patches
_STEALTH_SCRIPTS = """
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// Realistic plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ],
});

// Realistic languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Chrome-specific properties
window.chrome = {
    runtime: { onMessage: { addListener: () => {} } },
};
"""


class StealthBrowser:
    """Playwright wrapper with anti-detection measures."""

    def __init__(self, profile: BrowserProfile | None = None, seed: int | None = None) -> None:
        self._profile = profile or get_random_profile(seed)
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def launch(self) -> None:
        """Launch a stealth Chromium browser."""
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            viewport={
                "width": self._profile.viewport_width,
                "height": self._profile.viewport_height,
            },
            user_agent=self._profile.user_agent,
            locale=self._profile.language,
            timezone_id=self._profile.timezone,
        )
        # Apply stealth patches to all new pages
        await self._context.add_init_script(_STEALTH_SCRIPTS)

    async def new_page(self) -> Page:
        """Create a new stealth page."""
        if not self._context:
            await self.launch()
        assert self._context is not None
        return await self._context.new_page()

    async def navigate_with_delay(self, page: Page, url: str) -> None:
        """Navigate to URL with human-like delay."""
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def human_scroll(self, page: Page) -> None:
        """Simulate human-like scrolling."""
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def detect_captcha(self, page: Page) -> bool:
        """Check if page contains CAPTCHA indicators."""
        try:
            content = await page.content()
            lower = content.lower()
            return any(indicator in lower for indicator in _CAPTCHA_INDICATORS)
        except Exception:
            return False

    async def close(self) -> None:
        """Close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()

    @property
    def profile(self) -> BrowserProfile:
        return self._profile
