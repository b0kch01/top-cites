# Here's the real kicker :D
# Do the captcha then steal the cookies

from playwright.sync_api import sync_playwright


def get_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(
            "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q=quasi-newton+optimization&btnG=",
        )

        page.wait_for_event("close")

        cookies = context.cookies()
        session_cookies = [
            cookie for cookie in cookies if cookie['name'] == 'GSP']

        if len(session_cookies) >= 1:
            print("Found cookies! Let's steal them!",
                  session_cookies[0]["value"])
            return session_cookies[0]["value"]

        raise ValueError("No cookies found")
