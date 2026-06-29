"""E2E verify primary buttons and multimodal chatinput theme on running app."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

INDIGO = "rgb(99, 102, 241)"
WHITE_TEXT = "rgb(255, 255, 255)"
WHITE_BG = "rgb(255, 255, 255)"
TEXT_DARK = "rgb(15, 23, 42)"


def main() -> int:
    results: dict[str, object] = {
        "ok": False,
        "page_loaded": False,
        "primary_buttons": [],
        "chatinput": {},
        "errors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            page.goto("http://127.0.0.1:8501/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            page.goto("http://127.0.0.1:8501/Voice", wait_until="domcontentloaded", timeout=60000)
            time.sleep(8)
            results["page_loaded"] = True
            results["page_url"] = "http://127.0.0.1:8501/Voice"

            primaries = page.locator(
                '.dungeon-col-center button[data-testid="stBaseButton-primary"]'
            )
            for i in range(primaries.count()):
                btn = primaries.nth(i)
                if not btn.is_visible():
                    continue
                results["primary_buttons"].append(
                    {
                        "text": btn.inner_text(timeout=3000).strip(),
                        "bg": btn.evaluate(
                            "el => getComputedStyle(el).backgroundColor"
                        ),
                        "color": btn.evaluate("el => getComputedStyle(el).color"),
                    }
                )

            enable = page.get_by_role("button", name="啟用 Agent")
            if enable.count() and enable.first.is_visible():
                enable.first.click()
                time.sleep(5)

            iframe = page.locator('iframe[src*="st_multimodal_chatinput"]')
            if iframe.count():
                results["chatinput"] = {"iframe_found": True}
                for frame in page.frames:
                    if frame.url and "st_multimodal_chatinput" in frame.url:
                        patch = frame.evaluate(
                            """() => {
                            const style = document.getElementById('dungeon-chatinput-light');
                            const textarea = document.querySelector('textarea');
                            const button = document.querySelector('button');
                            return {
                                hasPatch: !!style,
                                patchLen: style ? style.textContent.length : 0,
                                observer: document.documentElement.dataset.dungeonChatinputObserver || null,
                                bodyBg: getComputedStyle(document.body).backgroundColor,
                                textareaColor: textarea ? getComputedStyle(textarea).color : null,
                                buttonBg: button ? getComputedStyle(button).backgroundColor : null,
                            };
                        }"""
                        )
                        results["chatinput"] = {
                            **results["chatinput"],
                            **patch,
                        }
                        break
            else:
                results["chatinput"] = {"iframe_found": False}

            primary_ok = any(
                btn.get("bg") == INDIGO and btn.get("color") == WHITE_TEXT
                for btn in results["primary_buttons"]
                if isinstance(btn, dict)
            )
            chat = results["chatinput"]
            chat_ok = (
                isinstance(chat, dict)
                and chat.get("iframe_found")
                and chat.get("hasPatch")
                and chat.get("bodyBg") == WHITE_BG
                and chat.get("textareaColor") == TEXT_DARK
                and chat.get("buttonBg") == INDIGO
            )
            results["primary_ok"] = primary_ok
            results["chatinput_ok"] = chat_ok
            results["ok"] = primary_ok and chat_ok
        except Exception as exc:
            results["errors"].append(str(exc))
        finally:
            browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
