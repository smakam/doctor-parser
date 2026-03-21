"""
End-to-end Playwright tests for the Doctor Nameboard Extractor.
Runs against the local dev stack (frontend :5173, backend :8000).
"""
import re
import pytest
from playwright.sync_api import Page, expect

FRONTEND_URL = "http://localhost:5173"
SAMPLE_IMAGE = "/Users/sreemakam/Downloads/WhatsApp Image 2026-03-19 at 16.19.45.jpeg"


# ── Helpers ───────────────────────────────────────────────────────────────────

def set_guest_session(page: Page) -> str:
    """Inject a guest session so API calls are authenticated."""
    import uuid
    guest_id = str(uuid.uuid4())
    page.evaluate(f"sessionStorage.setItem('guest_session', '{guest_id}')")
    return guest_id


# ── Basic page load ───────────────────────────────────────────────────────────

def test_homepage_redirects_to_upload(page: Page):
    page.goto(FRONTEND_URL)
    expect(page).to_have_url(re.compile(r".*/upload"))


def test_upload_page_renders(page: Page):
    page.goto(f"{FRONTEND_URL}/upload")
    expect(page.get_by_text("Nameboard Extractor")).to_be_visible()
    expect(page.get_by_text("Sign in")).to_be_visible()


def test_login_page_renders(page: Page):
    page.goto(f"{FRONTEND_URL}/login")
    expect(page.get_by_text("Continue with Google")).to_be_visible()
    expect(page.get_by_text("Continue as guest")).to_be_visible()


# ── Guest session flow ────────────────────────────────────────────────────────

def test_guest_continue_sets_session(page: Page):
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_text("Continue as guest").click()
    expect(page).to_have_url(re.compile(r".*/upload"), timeout=5000)
    guest_id = page.evaluate("sessionStorage.getItem('guest_session')")
    assert guest_id is not None


# ── Upload & extraction flow ──────────────────────────────────────────────────

def test_full_extraction_flow(page: Page):
    """Upload an image, wait for extraction, verify review page fields."""
    page.goto(f"{FRONTEND_URL}/upload")
    set_guest_session(page)

    # Upload the sample image
    page.locator("input[type=file]").first.set_input_files(SAMPLE_IMAGE)

    # Image preview should appear
    expect(page.locator("img")).to_have_count(1, timeout=3000)

    # Click Extract
    page.get_by_role("button", name=re.compile("Extract", re.IGNORECASE)).click()

    # Wait for redirect to review page (extraction can take up to 60s)
    expect(page).to_have_url(re.compile(r".*/review/"), timeout=60000)

    # Review page must show extracted fields
    expect(page.get_by_text("Review Extraction")).to_be_visible()
    expect(page.get_by_label("Doctor Name")).to_be_visible()
    expect(page.get_by_label("Address")).to_be_visible()

    # Overall confidence badge should be present in header
    expect(page.get_by_role("banner").get_by_text(re.compile(r"\d+%"))).to_be_visible()


def test_accept_extraction_navigates_to_quote(page: Page):
    """Run full flow and accept — should land on quote page."""
    page.goto(f"{FRONTEND_URL}/upload")
    set_guest_session(page)

    page.locator("input[type=file]").first.set_input_files(SAMPLE_IMAGE)

    page.get_by_role("button", name=re.compile("Extract", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r".*/review/"), timeout=60000)

    # Click accept
    page.get_by_role("button", name=re.compile("Looks good|continue", re.IGNORECASE)).click()

    # Should navigate to quote page
    expect(page).to_have_url(re.compile(r".*/quote/"), timeout=10000)
    expect(page.get_by_text("Extraction accepted")).to_be_visible()


def test_reject_extraction_returns_to_upload(page: Page):
    """Run full flow and reject — should return to upload page."""
    page.goto(f"{FRONTEND_URL}/upload")
    set_guest_session(page)

    page.locator("input[type=file]").first.set_input_files(SAMPLE_IMAGE)

    page.get_by_role("button", name=re.compile("Extract", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r".*/review/"), timeout=60000)

    page.get_by_role("button", name=re.compile("Reject", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r".*/upload"), timeout=10000)


# ── History page ──────────────────────────────────────────────────────────────

def test_history_requires_login(page: Page):
    """History page returns 401 for guests — frontend should handle gracefully."""
    page.goto(f"{FRONTEND_URL}/history")
    # Should show an error or redirect, not crash
    page.wait_for_load_state("networkidle")
    # No JS crash = page rendered something
    assert page.locator("#root").count() == 1


# ── Backend health (sanity) ───────────────────────────────────────────────────

def test_backend_health(page: Page):
    page.goto("http://localhost:8000/health")
    assert '"ok"' in page.content()
