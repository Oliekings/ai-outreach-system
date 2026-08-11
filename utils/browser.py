import asyncio
import random


async def handle_consent(page):
    """
    Handles common cookie/consent popups across different platforms.
    """
    selectors = [
        # Generic / Google
        'button[aria-label="Accept all"]',
        'button[jsname="b3VHJd"]',
        "#L2AGLb",
        ".QS5gu",
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
        'button:has-text("Allow all")',
        # Facebook specific
        'button[data-cookiebanner="accept_button"]',
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept All")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
        'button:has-text("Only allow essential cookies")',
        # Instagram specific
        'button:has-text("Allow essential and optional cookies")',
    ]

    for sel in selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await btn.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return True
        except Exception:
            continue
    return False
