import asyncio
import random


async def human_pause(min_s=2.0, max_s=5.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page, scrolls=4, fast_mode=False):
    """
    Simulates human scrolling behavior.
    fast_mode=True: halves the scrolls and uses shorter pauses (used in lead_enricher).
    """
    if fast_mode:
        actual_scrolls = max(1, scrolls // 2)
        sleep_min, sleep_max = 0.2, 0.5
        up_sleep_min, up_sleep_max = 0.2, 0.4
    else:
        actual_scrolls = scrolls
        sleep_min, sleep_max = 0.6, 2.0
        up_sleep_min, up_sleep_max = 0.4, 1.0

    for _ in range(actual_scrolls):
        distance = random.randint(250, 750)
        await page.evaluate(f"window.scrollBy(0, {distance})")
        await asyncio.sleep(random.uniform(sleep_min, sleep_max))

    await page.evaluate(f"window.scrollBy(0, -{random.randint(80, 250)})")
    await asyncio.sleep(random.uniform(up_sleep_min, up_sleep_max))


async def handle_consent(page, fast_mode=False):
    """
    Handles common cookie consent banners.
    fast_mode=True: uses shorter pauses (used in lead_enricher).
    """
    selectors = [
        'button[aria-label="Accept all"]',
        'button[jsname="b3VHJd"]',
        "#L2AGLb",
        ".QS5gu",
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
        'button:has-text("Allow all")',
    ]

    if fast_mode:
        sleep1_min, sleep1_max = 0.3, 0.8
        sleep2_min, sleep2_max = 0.5, 1.2
    else:
        sleep1_min, sleep1_max = 0.8, 1.8
        sleep2_min, sleep2_max = 1.2, 2.5

    for sel in selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await asyncio.sleep(random.uniform(sleep1_min, sleep1_max))
                await btn.click()
                await asyncio.sleep(random.uniform(sleep2_min, sleep2_max))
                return True
        except Exception:
            continue
    return False
