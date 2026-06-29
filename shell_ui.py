from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st

from auth.session import get_auth_user
from cloud_paths import page_data_path, paths_for_user, template_page_data_path

_PAGE_FILE_PATTERN = re.compile(r"^\d+_.+\.py$")

TITLE_OVERRIDES = {
    "1_Home": "Home",
}

_MULTIMODAL_CHATINPUT_THEME_FIX = """
<script>
(function () {
  const host = window.parent;
  if (!host || host.__studioMultimodalChatinputThemeFixInstalled) {
    return;
  }
  host.__studioMultimodalChatinputThemeFixInstalled = true;

  function patchIframe(iframe) {
    try {
      const doc = iframe.contentDocument;
      if (!doc || doc.__studioMultimodalChatinputThemeFixApplied) {
        return;
      }
      doc.__studioMultimodalChatinputThemeFixApplied = true;

      const style = doc.createElement("style");
      style.textContent = `
        textarea {
          color: var(--text-color) !important;
          caret-color: var(--text-color) !important;
        }
        textarea::placeholder {
          color: color-mix(in srgb, var(--text-color) 55%, transparent) !important;
          opacity: 1;
        }
      `;
      doc.head.appendChild(style);
    } catch (_err) {
      /* ignore cross-origin iframes */
    }
  }

  function patchAll() {
    host.document.querySelectorAll("iframe").forEach((iframe) => {
      if (iframe.contentDocument) {
        patchIframe(iframe);
      } else {
        iframe.addEventListener("load", () => patchIframe(iframe), { once: true });
      }
    });
  }

  patchAll();
  new MutationObserver(patchAll).observe(host.document.body, {
    childList: true,
    subtree: true,
  });
})();
</script>
"""

_THEME_FIX_IFRAME_HEIGHT = 1


def page_title_from_path(path: Path) -> str:
    stem = path.stem
    if stem in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[stem]
    if "_" in stem:
        return stem.split("_", 1)[1].replace("_", " ")
    return stem.replace("_", " ")


def discover_file_pages(pages_dir: Path) -> list[Path]:
    if not pages_dir.is_dir():
        return []
    pages = [
        path
        for path in pages_dir.glob("*.py")
        if not path.name.startswith("_") and _PAGE_FILE_PATTERN.match(path.name)
    ]
    return sorted(pages, key=lambda path: path.stem)


def build_navigation_pages(
    *,
    app_root: Path,
    overview_callable: Callable[[], None],
) -> dict[str, list[Any]]:
    file_pages = [
        st.Page(str(path), title=page_title_from_path(path))
        for path in discover_file_pages(app_root / "pages")
    ]
    return {
        "Dungeon": [
            st.Page(overview_callable, title="總覽", default=True),
            *file_pages,
        ]
    }


def page_slug(page_name: str) -> str:
    return page_name.strip().lower().replace(" ", "_")


def load_page_data(page_name: str) -> dict:
    user = get_auth_user(st.session_state)
    if user is not None:
        path = page_data_path(page_name, paths_for_user(user.google_sub))
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return raw if isinstance(raw, dict) else {}
            except (OSError, json.JSONDecodeError):
                pass
    template = template_page_data_path(page_name)
    if template.is_file():
        try:
            raw = json.loads(template.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_page_data(page_name: str, data: dict) -> None:
    user = get_auth_user(st.session_state)
    if user is None:
        return
    path = page_data_path(page_name, paths_for_user(user.google_sub))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_extra_context(page_name: str, **fields: object) -> str:
    lines = [f"【目前頁面】{page_name}"]
    for key, value in fields.items():
        lines.append(f"【{key}】{value}")
    return "\n".join(lines)


def inject_multimodal_chatinput_theme_fix() -> None:
    """st-multimodal-chatinput hardcodes white textarea text; fix for light themes."""
    st.iframe(_MULTIMODAL_CHATINPUT_THEME_FIX, height=_THEME_FIX_IFRAME_HEIGHT)


def inject_style() -> None:
    st.markdown(
        """
<style>
    .block-container { padding-top: 2rem; }
    .studio-card {
        border: 1px solid rgba(250, 250, 250, 0.12);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        background: rgba(255, 255, 255, 0.035);
    }
    .studio-muted { color: rgba(250, 250, 250, 0.65); }
    .studio-agent-title-spacer {
        height: 0.75rem;
    }
    .studio-agent-title-text {
        font-size: 1.25rem;
        font-weight: 800;
        line-height: 1.5;
        margin-bottom: 0.55rem;
    }
</style>
""",
        unsafe_allow_html=True,
    )
    # 不在此注入 iframe theme fix：會 patch 所有 iframe（含 multimodal 元件）導致輸入失效。
