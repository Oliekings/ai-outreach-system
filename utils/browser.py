"""
Unified browser behavior utilities.
Replaces duplicate human_pause, human_scroll, human_type, and handle_consent functions across the codebase.
"""

import asyncio
import random


async def human_pause(min_s: float = 2.0, max_s: float = 5.0):
    """Pause execution for a random amount of time between min_s and max_s."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page, scrolls: int = 4):
    """Scroll the page a few times to simulate human reading."""
    for _ in range(scrolls):
        await page.evaluate(f"window.scrollBy(0, {random.randint(250, 750)})")
        await asyncio.sleep(random.uniform(0.6, 2.0))
    await page.evaluate(f"window.scrollBy(0, -{random.randint(80, 250)})")
    await asyncio.sleep(random.uniform(0.4, 1.0))


async def human_type(element, text: str):
    """Type like a human — character by character with variable speed."""
    for char in text:
        await element.type(char)
        await asyncio.sleep(random.uniform(0.03, 0.15))
    await human_pause(0.5, 1.5)

async def handle_consent(page, fast_mode: bool = False):
    """Attempt to find and click common cookie consent buttons."""
    selectors = [
        'button[aria-label="Accept all"]',
        'button[jsname="b3VHJd"]',
        "#L2AGLb",
        ".QS5gu",
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept All")',
        'button:has-text("Allow essential and optional cookies")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
        'button[data-cookiebanner="accept_button"]',
        'button:has-text("Only allow essential cookies")',
    ]
    for sel in selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                if fast_mode:
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                else:
                    await human_pause(1.0, 2.0)
                return True
        except Exception:
            continue
    return False
