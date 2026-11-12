"""Real browser smoke checks and screenshots, using only temporary test data.

Run from the repository root: python tests/browser_check.py
Install Chromium first: python -m playwright install chromium
Or select installed Edge: set BROWSER_CHANNEL=msedge (PowerShell: $env:BROWSER_CHANNEL='msedge').
"""
import os
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from website import create_app, db  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / 'docs' / 'screenshots'
SAMPLES = [
    'A little intention for the week\n\nMake time for deep work. Finish one thing before starting the next. Leave a little room for the unexpected.',
    'Ideas worth coming back to\n\nA reading nook by the window. A weekend without notifications. A notebook full of possibilities.',
    'Project notebook\n\nKeep the app simple. Make every interaction feel thoughtful. Build something I can understand and explain.',
    'Things to remember\n\nProgress is a collection of small steps. Write it down, give it space, and come back with fresh eyes.',
    'A good day starts here\n\nCoffee. A clear desk. Three things that matter. One small step in the right direction.',
    'Learning, one note at a time\n\nUnderstand the fundamentals. Ask better questions. Put what I learn into practice.',
]


def assert_layout(page, width, height):
    page.set_viewport_size({'width': width, 'height': height})
    if not page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'):
        overflowing = page.evaluate('''() => [...document.querySelectorAll('body *')]
            .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
            .map(el => [el.tagName, el.className, el.getBoundingClientRect().right])''')
        page.screenshot(path=str(SCREENSHOTS / 'layout-failure.png'), full_page=True)
        raise AssertionError(f'Overflow at {width}px: {overflowing}')
    for image in page.locator('img').all():
        expect(image).to_have_js_property('complete', True)
        assert image.evaluate('(img) => img.naturalWidth > 0')


def screenshot(page, name):
    page.screenshot(path=str(SCREENSHOTS / name), full_page=True, animations='disabled')


def run():
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='noted-browser-') as temp:
        app = create_app({'SECRET_KEY': secrets.token_hex(32), 'TESTING': True,
                          'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + (Path(temp) / 'browser.db').as_posix()})
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                options = {'headless': True}
                if os.environ.get('BROWSER_CHANNEL'):
                    options['channel'] = os.environ['BROWSER_CHANNEL']
                browser = playwright.chromium.launch(**options)
                context = browser.new_context(viewport={'width': 1440, 'height': 960}, reduced_motion='reduce')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if 'Content Security Policy' in msg.text else None)
                base = f'http://127.0.0.1:{server.server_port}'
                page.goto(base + '/login')
                for width, height in [(1440, 960), (900, 900), (768, 1024), (390, 844), (320, 740)]:
                    assert_layout(page, width, height)
                assert_layout(page, 1440, 960)
                screenshot(page, 'login-desktop.png')
                assert_layout(page, 390, 844)
                screenshot(page, 'login-mobile.png')
                page.get_by_role('link', name='Create an account', exact=True).first.click()
                for width, height in [(1440, 960), (900, 900), (768, 1024), (390, 844), (320, 740)]:
                    assert_layout(page, width, height)
                assert_layout(page, 1440, 960)
                screenshot(page, 'registration-desktop.png')
                page.get_by_label('First name', exact=True).fill('Emmanuel')
                page.get_by_label('Email address', exact=True).fill('preview@example.test')
                page.locator('#password1').fill('temporary-preview-password')
                page.locator('#password2').fill('temporary-preview-password')
                page.get_by_role('button', name='Create your notebook').click()
                expect(page.get_by_role('heading', name='A fresh page. All yours.')).to_be_visible()
                page.get_by_role('button', name='Dismiss message').click()
                screenshot(page, 'dashboard-empty.png')
                for text in SAMPLES:
                    page.get_by_label('Your new note').fill(text)
                    expect(page.locator('#character-count')).to_have_text(str(len(text)))
                    page.get_by_role('button', name='Save note').click()
                    expect(page.locator('.alert-success')).to_contain_text('Note saved.')
                page.get_by_role('button', name='Dismiss message').click()
                expect(page.locator('.note-card')).to_have_count(6)
                for width, height in [(1440, 960), (1024, 768), (900, 900), (768, 1024), (700, 900), (390, 844), (320, 740)]:
                    assert_layout(page, width, height)
                assert_layout(page, 1440, 960)
                screenshot(page, 'dashboard-desktop.png')
                assert_layout(page, 390, 844)
                screenshot(page, 'dashboard-mobile.png')
                # Whitespace is rejected in the browser without making a request.
                page.get_by_label('Your new note').fill('   ')
                page.get_by_role('button', name='Save note').click()
                assert not page.locator('#note').evaluate('(el) => el.checkValidity()')
                page.get_by_label('Your new note').fill('')
                # Cancellation and Escape keep the note and return focus.
                page.locator('.delete-note').first.click()
                expect(page.get_by_role('dialog')).to_be_visible()
                expect(page.get_by_role('button', name='Keep note')).to_be_focused()
                page.keyboard.press('Escape')
                expect(page.get_by_role('dialog')).not_to_be_visible()
                expect(page.locator('.delete-note').first).to_be_focused()
                expect(page.locator('.note-card')).to_have_count(6)
                # Failed requests surface an error and retain the card.
                page.route('**/delete-note', lambda route: route.fulfill(
                    status=400, content_type='application/json', body='{"error":"Please reload and try again."}'))
                page.locator('.delete-note').first.click()
                page.get_by_role('button', name='Delete note', exact=True).click()
                expect(page.locator('#note-feedback')).to_have_text('Please reload and try again.')
                expect(page.locator('.note-card')).to_have_count(6)
                page.unroute('**/delete-note')
                page.locator('.delete-note').first.click()
                page.get_by_role('button', name='Delete note', exact=True).click()
                expect(page.locator('.note-card')).to_have_count(5)
                page.get_by_role('button', name='Log out', exact=True).click()
                expect(page.get_by_role('heading', name='Welcome back.')).to_be_visible()
                page.get_by_label('Email address', exact=True).fill('preview@example.test')
                page.get_by_label('Password', exact=True).fill('temporary-preview-password')
                page.get_by_role('button', name='Log in to your notebook').click()
                expect(page.locator('.note-card')).to_have_count(5)
                # Long unbroken note content must also wrap on phones.
                page.get_by_label('Your new note').fill('unbroken-' + 'x' * 2000)
                page.get_by_role('button', name='Save note').click()
                assert_layout(page, 320, 740)
                assert not errors, errors
                browser.close()
                print('PASS: browser auth, create/view/delete, cancellation, failure feedback, keyboard focus, long content, CSP, and responsive checks.')
                print('PASS: public pages at 320/390/768/900/1440px; dashboard additionally at 700/1024px.')
                print('Screenshots:', SCREENSHOTS)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == '__main__':
    run()
