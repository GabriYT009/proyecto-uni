from playwright.sync_api import sync_playwright

HOME = 'http://127.0.0.1:8000/home'
CATALOGO = 'http://127.0.0.1:8000/catalogo/'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print('Opening home page...')
    page.goto(HOME, timeout=10000)
    page.wait_for_selector('.grid', timeout=10000)

    # Click first product (.view with data-id)
    prod = page.query_selector('.grid .view[data-id]')
    if not prod:
        print('No product .view found on home')
    else:
        pid = prod.get_attribute('data-id')
        print('Clicking product with data-id=', pid)
        prod.click()
        page.wait_for_timeout(600)
        modal_shown = page.evaluate("!!(document.getElementById('detailModal') && document.getElementById('detailModal').classList.contains('show'))")
        print('After product click, modal.show =', modal_shown)

    # Reload home and click first category
    page.goto(HOME, timeout=10000)
    page.wait_for_selector('.category-card', timeout=10000)
    cat = page.query_selector('.category-card')
    if not cat:
        print('No category-card found on home')
    else:
        print('Clicking first category-card (should navigate to catalog)')
        cat.click()
        page.wait_for_timeout(800)
        # After clicking category we expect navigation; check URL and modal
        cur_url = page.url
        modal_after_cat = page.evaluate("!!(document.getElementById('detailModal') && document.getElementById('detailModal').classList.contains('show'))")
        print('After category click, page URL =', cur_url)
        print('After category click, modal.show =', modal_after_cat)

    browser.close()
