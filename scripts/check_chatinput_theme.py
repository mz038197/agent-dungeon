"""Verify multimodal chatinput light-theme patch in running Streamlit app."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright


def main() -> int:
    results: dict[str, object] = {
        "ok": False,
        "iframe_found": False,
        "patch_applied": False,
        "styles": {},
        "error": None,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            page.goto("http://127.0.0.1:8501/Voice", wait_until="networkidle", timeout=60000)
            time.sleep(3)
            iframe_el = page.locator('iframe[src*="st_multimodal_chatinput"]').first
            iframe_el.wait_for(state="attached", timeout=30000)
            results["iframe_found"] = True
            target = None
            for _ in range(20):
                for frame in page.frames:
                    if frame.url and "st_multimodal_chatinput" in frame.url:
                        target = frame
                        break
                if target is not None:
                    patch = target.evaluate(
                        """() => {
                        const style = document.getElementById('dungeon-chatinput-light');
                        return {
                            hasPatch: !!style,
                            patchLen: style ? style.textContent.length : 0,
                        };
                    }"""
                    )
                    if patch.get("hasPatch") and patch.get("patchLen", 0) > 100:
                        break
                time.sleep(0.5)
            if target is None:
                results["error"] = "multimodal frame not found in page.frames"
            else:
                patch = target.evaluate(
                    """() => {
                    const style = document.getElementById('dungeon-chatinput-light');
                    const textarea = document.querySelector('textarea');
                    const button = document.querySelector('button');
                    return {
                        hasPatch: !!style,
                        patchLen: style ? style.textContent.length : 0,
                        dataset: document.documentElement.dataset.dungeonChatinputLight || null,
                        bodyBg: getComputedStyle(document.body).backgroundColor,
                        textareaColor: textarea ? getComputedStyle(textarea).color : null,
                        textareaBg: textarea ? getComputedStyle(textarea).backgroundColor : null,
                        buttonBg: button ? getComputedStyle(button).backgroundColor : null,
                    };
                }"""
                )
                results["styles"] = patch
                results["patch_applied"] = bool(
                    patch.get("hasPatch") and patch.get("patchLen", 0) > 100
                )
                button_bg = str(patch.get("buttonBg", ""))
                body_bg = str(patch.get("bodyBg", ""))
                textarea_color = str(patch.get("textareaColor", ""))
                results["ok"] = (
                    results["patch_applied"]
                    and button_bg == "rgb(99, 102, 241)"
                    and body_bg == "rgb(255, 255, 255)"
                    and textarea_color == "rgb(15, 23, 42)"
                )
                if button_bg == "rgb(98, 0, 234)":
                    results["old_purple_button"] = True
        except Exception as exc:
            results["error"] = str(exc)
        finally:
            browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
