from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:5055")
    page.wait_for_timeout(1000)

    # Login
    page.get_by_placeholder("Authorization Key").fill("test_key")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Enter Dashboard").click()
    page.wait_for_timeout(2000)

    # Hover over buttons to see tooltips

    # Overview page - play button
    page.evaluate("() => { const b = document.querySelector('button[aria-label=\"Run task\"]'); if(b) { b.scrollIntoView(); b.focus(); } }")
    page.wait_for_timeout(1000)

    # Scale page - rocket button
    page.evaluate("() => { const n = document.querySelector('.nav-item[class*=\"active\"]'); if(n) n.click(); }")
    page.goto("http://localhost:5055/#/scale")
    page.evaluate("() => { document.querySelector('div.nav-item:nth-child(4)').click(); }")
    page.wait_for_timeout(1000)

    page.evaluate("() => { const b = document.querySelector('button[aria-label=\"Launch in this city\"]'); if(b) { b.scrollIntoView(); b.focus(); b.dispatchEvent(new MouseEvent('mouseover')); } }")
    page.wait_for_timeout(1000)

    # Outreach page - dry run button
    page.evaluate("() => { document.querySelector('div.nav-item:nth-child(2)').click(); }")
    page.wait_for_timeout(1000)

    page.evaluate("() => { const b = document.querySelector('button[aria-label=\"Dry run\"]'); if(b) { b.scrollIntoView(); b.focus(); b.dispatchEvent(new MouseEvent('mouseover')); } }")
    page.wait_for_timeout(1000)

    # Leads page - close modal button
    page.evaluate("() => { document.querySelector('.nav-item:nth-child(2)').click(); }")
    page.wait_for_timeout(1000)

    # Find a lead row to click
    page.evaluate("() => { const b = document.querySelector('tr[style*=\"cursor: pointer\"]'); if(b) { b.click(); } }")
    page.wait_for_timeout(1000)

    page.evaluate("() => { const b = document.querySelector('button[aria-label=\"Close modal\"]'); if(b) { b.scrollIntoView(); b.focus(); b.dispatchEvent(new MouseEvent('mouseover')); } }")
    page.wait_for_timeout(1000)

    # Take screenshot at the key moment
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
