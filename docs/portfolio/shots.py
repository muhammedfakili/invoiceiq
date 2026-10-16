"""Portfolio images for InvoiceIQ: cover + 4 screens of the running app.

Needs the API and UI running (docker compose up, or uvicorn + streamlit locally).
Run:  uv run --with playwright python docs/portfolio/shots.py
"""

import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "portfolio"
URL = "http://localhost:8501"
W, H = 1568, 698  # same size as the other portfolio screenshots

HIDE = """
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stHeader"] {display:none !important;}
"""


def settle(page: Page, ms: int = 2500) -> None:
    page.wait_for_timeout(ms)
    page.add_style_tag(content=HIDE)


def pick(page: Page, name: str) -> None:
    page.get_by_test_id("stSelectbox").scroll_into_view_if_needed()
    box = page.get_by_test_id("stSelectbox").locator("input")
    box.click()
    box.fill(name)  # the selectbox filters as you type
    page.keyboard.press("Enter")
    settle(page)
    page.mouse.move(900, 400)
    page.mouse.wheel(0, -3000)  # back to the top
    page.wait_for_timeout(400)


def scroll_main(page: Page, to_text: str, offset: int = 0) -> None:
    page.get_by_text(to_text).first.scroll_into_view_if_needed()
    page.mouse.move(900, 400)
    page.mouse.wheel(0, offset)
    page.wait_for_timeout(600)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")

        cover = browser.new_page(viewport={"width": 1000, "height": 800})
        cover.goto((OUT / "cover.html").as_uri())
        cover.locator(".card").screenshot(path=str(OUT / "00-cover.png"))

        page = browser.new_context(viewport={"width": W, "height": H}, color_scheme="dark").new_page()
        page.goto(URL)
        page.wait_for_selector("text=API ready", timeout=60_000)
        page.get_by_role("button", name="Try sample invoices").click()
        page.get_by_test_id("stSelectbox").wait_for(timeout=300_000)  # 6 real extractions
        settle(page)

        # 1. a phone photo on a table, read straight from the image: deposit -> amount due < total
        pick(page, "inv27-uk-photo.jpg")
        page.screenshot(path=str(OUT / "01-photo-extracted.png"))

        # 2. a wrong total (as if mistyped or misread) is caught by the arithmetic check
        pick(page, "inv11-de-pdf.pdf")
        total = page.get_by_label("Total", exact=True)
        original_total = float(total.input_value().replace(",", "."))
        total.fill(str(round(original_total + 90, 2)))
        page.get_by_role("button", name="Save and re-check").click()
        settle(page, 3500)
        scroll_main(page, "shipping or fees left out", -330)
        page.screenshot(path=str(OUT / "02-flagged-total.png"))

        # 3. every check that ran, for a PDF where the customer's name is printed biggest
        pick(page, "inv16-fr-pdf.pdf")
        page.get_by_test_id("stExpander").get_by_text("All checks").click()
        settle(page, 1000)
        page.get_by_test_id("stExpander").evaluate("e => e.scrollIntoView({block: 'start'})")
        page.mouse.move(900, 400)
        page.mouse.wheel(0, -40)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "03-all-checks.png"))

        # 4. the reviewer corrects the flagged total, the checks pass again; approve three and export
        for name in ("inv16-fr-pdf.pdf", "inv27-uk-photo.jpg", "inv11-de-pdf.pdf"):
            pick(page, name)
            if name == "inv11-de-pdf.pdf":
                total_box = page.get_by_test_id("stNumberInput").filter(has_text=re.compile(r"^\s*Total")).locator("input")
                total_box.fill(str(original_total))
                page.get_by_role("button", name="Save and re-check").click()
                settle(page, 3500)
            page.get_by_role("button", name=re.compile(r"Approve$")).click()
            page.get_by_text("Approved and included in the export").wait_for(timeout=30_000)
            settle(page)
        scroll_main(page, "Download Excel", 200)
        page.screenshot(path=str(OUT / "04-approved-export.png"))

        browser.close()
    print("saved to", OUT)


if __name__ == "__main__":
    main()
