"""Real Chromium UI smoke test against an already-running localhost server."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    Path("artifacts").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1060}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        page.get_by_role("heading", name="Good answers survive scrutiny.").wait_for()
        page.screenshot(path="artifacts/ui-research.png", full_page=True)
        page.locator('[data-view="challenge"]').click()
        page.locator("#challenge-start").click()
        page.locator("#run-status").filter(has_text="completed").wait_for(timeout=30000)
        assert "6 / 6" in page.locator("#run-score").inner_text()
        assert "0 / 3" in page.locator("#run-score").inner_text()
        page.locator('[data-tab="repairs"]').click()
        assert "Store count increased by 50" in page.locator("#run-content").inner_text()
        page.screenshot(path="artifacts/ui-challenge.png", full_page=True)
        page.locator("#transfer-start").click()
        page.locator("#run-question").filter(has_text="Cedar Retail").wait_for(timeout=30000)
        page.locator("#run-status").filter(has_text="completed").wait_for(timeout=30000)
        assert "no answer-quality improvement" in page.locator("#run-score").inner_text()
        assert "MEMORY OFF" in page.locator("#run-score").inner_text()
        assert "MEMORY ON" in page.locator("#run-score").inner_text()
        page.screenshot(path="artifacts/ui-transfer.png", full_page=True)
        page.locator('[data-view="memory"]').click()
        page.get_by_text("For retail expansion, distinguish gross openings, closures, net additions, and total store count.", exact=True).first.wait_for()
        page.locator('[data-view="evaluation"]').click()
        page.locator("#question-suite tbody tr").nth(7).wait_for()
        assert page.locator("#question-suite tbody tr").count() == 8
        page.set_viewport_size({"width":390,"height":844})
        page.locator('[data-view="research"]').click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path="artifacts/ui-mobile.png", full_page=True)
        assert not errors, errors
        browser.close()
    result = {"status":"passed", "browser":"Chromium (installed Chrome)", "checks":["research view", "challenge run", "correction comparison", "paired lesson transfer", "verified memory", "eight-question suite", "mobile width", "no JavaScript errors"]}
    Path("artifacts/ui-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
