from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from auth.session import get_auth_user
from cloud_paths import page_data_path, paths_for_user, template_page_data_path

_PAGE_FILE_PATTERN = re.compile(r"^\d+_.+\.py$")

TITLE_OVERRIDES = {
    "0_Voice": "Voice",
}

_MULTIMODAL_CHATINPUT_LIGHT_CSS = """
  html {
    color-scheme: light !important;
  }
  html, body, #root {
    background: #ffffff !important;
    color: #0f172a !important;
  }
  #root > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 4px 8px !important;
  }
  label {
    color: #64748b !important;
  }
  textarea {
    background: #ffffff !important;
    color: #0f172a !important;
    caret-color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
  }
  textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
  }
  button {
    background-color: #6366f1 !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
  }
  button:disabled {
    background-color: #cbd5e1 !important;
    color: #64748b !important;
  }
"""

_MULTIMODAL_CHATINPUT_THEME_FIX = """
<script>
(function () {
  const host = window.parent;
  if (!host || host.__studioMultimodalChatinputThemeFixInstalled) {
    return;
  }
  host.__studioMultimodalChatinputThemeFixInstalled = true;

  const lightCss = __MULTIMODAL_CSS__;

  function isMultimodalChatinputIframe(iframe) {
    const src = iframe.getAttribute("src") || "";
    const title = iframe.getAttribute("title") || "";
    return src.includes("st_multimodal_chatinput") || title.includes("multimodal");
  }

  function patchIframe(iframe) {
    if (!isMultimodalChatinputIframe(iframe)) {
      return;
    }
    const apply = () => {
      try {
        const doc = iframe.contentDocument;
        if (!doc) {
          return;
        }
        let styleEl = doc.getElementById("dungeon-chatinput-light");
        if (!styleEl) {
          styleEl = doc.createElement("style");
          styleEl.id = "dungeon-chatinput-light";
          doc.head.appendChild(styleEl);
        }
        styleEl.textContent = lightCss;
        doc.documentElement.dataset.dungeonChatinputLight = "1";
      } catch (_err) {
        /* ignore cross-origin iframes */
      }
    };
    if (iframe.contentDocument) {
      apply();
    } else {
      iframe.addEventListener("load", apply, { once: true });
    }
  }

  function patchAll() {
    host.document.querySelectorAll("iframe").forEach(patchIframe);
  }

  patchAll();
  new MutationObserver(patchAll).observe(host.document.body, {
    childList: true,
    subtree: true,
  });
})();
</script>
"""


def multimodal_chatinput_light_theme_js() -> str:
    """JS helper for dungeon shell observer — patches multimodal chatinput iframes only."""
    css_literal = json.dumps(_MULTIMODAL_CHATINPUT_LIGHT_CSS.strip())
    return f"""
  function patchMultimodalChatinputIframes(doc) {{
    const lightCss = {css_literal};
    function isTarget(iframe) {{
      const src = iframe.getAttribute("src") || "";
      const title = iframe.getAttribute("title") || "";
      return src.includes("st_multimodal_chatinput") || title.includes("multimodal");
    }}
    function ensureChatinputLightTheme(idoc) {{
      let styleEl = idoc.getElementById("dungeon-chatinput-light");
      if (!styleEl) {{
        styleEl = idoc.createElement("style");
        styleEl.id = "dungeon-chatinput-light";
        idoc.head.appendChild(styleEl);
      }}
      styleEl.textContent = lightCss;
      idoc.documentElement.dataset.dungeonChatinputLight = "1";
      idoc.documentElement.style.colorScheme = "light";
    }}
    function installInnerObserver(idoc) {{
      if (idoc.documentElement.dataset.dungeonChatinputObserver) {{
        return;
      }}
      idoc.documentElement.dataset.dungeonChatinputObserver = "1";
      let pending = 0;
      new MutationObserver(() => {{
        if (pending) return;
        pending = host.requestAnimationFrame(() => {{
          pending = 0;
          ensureChatinputLightTheme(idoc);
        }});
      }}).observe(
        idoc.documentElement,
        {{ childList: true, subtree: true }}
      );
    }}
    function apply(iframe) {{
      if (!isTarget(iframe)) return;
      iframe.style.pointerEvents = "auto";
      try {{
        const idoc = iframe.contentDocument;
        if (!idoc) return;
        ensureChatinputLightTheme(idoc);
        installInnerObserver(idoc);
      }} catch (_err) {{}}
    }}
    function bindLoad(iframe) {{
      if (iframe.dataset.dungeonChatinputLoadBound === "1") {{
        return;
      }}
      iframe.dataset.dungeonChatinputLoadBound = "1";
      iframe.addEventListener("load", () => apply(iframe));
    }}
    doc.querySelectorAll("iframe").forEach((iframe) => {{
      bindLoad(iframe);
      if (iframe.contentDocument) {{
        apply(iframe);
      }}
    }});
    if (!host.__dungeonMultimodalChatinputHostObserver) {{
      host.__dungeonMultimodalChatinputHostObserver = true;
      new MutationObserver(() => {{
        patchMultimodalChatinputIframes(host.document);
      }}).observe(host.document.body, {{ childList: true, subtree: true }});
    }}
  }}
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


def navigation_page_path(relative_path: str) -> str:
    """Normalize page paths for st.Page / st.page_link / st.switch_page."""
    return relative_path.replace("\\", "/")


def page_url_from_relative_page(relative_path: str) -> str:
    """Return the public Streamlit URL for a file page like pages/0_Voice.py."""
    return f"/{page_title_from_path(Path(relative_path))}"


_OVERVIEW_PAGE: Any = None


def overview_page() -> Any:
    """Return the st.Page object for the default overview screen."""
    if _OVERVIEW_PAGE is None:
        raise RuntimeError("build_navigation_pages() must run before overview_page()")
    return _OVERVIEW_PAGE


def build_navigation_pages(
    *,
    app_root: Path,
    overview_callable: Callable[[], None],
) -> dict[str, list[Any]]:
    global _OVERVIEW_PAGE
    _OVERVIEW_PAGE = st.Page(overview_callable, title="總覽", default=True)
    file_pages = [
        st.Page(
            navigation_page_path(path.relative_to(app_root).as_posix()),
            title=page_title_from_path(path),
        )
        for path in discover_file_pages(app_root / "pages")
    ]
    return {
        "Dungeon": [
            _OVERVIEW_PAGE,
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
    """Build a pure data snapshot for user-message 【目前頁面狀態】.

    - First line is always 【目前頁面】
    - Use 左欄* / 中欄* prefixes for widget snapshots; 共享資料檔 for JSON path
    - Do not include 【任務】 or imperative instructions
    """
    lines = [f"【目前頁面】{page_name}"]
    for key, value in fields.items():
        lines.append(f"【{key}】{value}")
    return "\n".join(lines)


def inject_multimodal_chatinput_theme_fix() -> None:
    """Light-theme patch for st-multimodal-chatinput iframe (body + textarea)."""
    script = _MULTIMODAL_CHATINPUT_THEME_FIX.replace(
        "__MULTIMODAL_CSS__",
        json.dumps(_MULTIMODAL_CHATINPUT_LIGHT_CSS.strip()),
    )
    st.iframe(script, height=_THEME_FIX_IFRAME_HEIGHT)


_HIDE_CHROME_SELECTORS = (
    '[data-testid="stHeader"]',
    '[data-testid="stToolbar"]',
    '[data-testid="stDecoration"]',
    "footer",
)

_FLUSH_TOP_CSS = """
  .stApp,
  [data-testid="stAppViewContainer"],
  section.stMain,
  section.main {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  header.stAppHeader,
  [data-testid="stAppHeader"],
  [data-testid="stToolbar"],
  [data-testid="stDecoration"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
    visibility: hidden !important;
  }
  [data-testid="stAppViewBlockContainer"],
  .stAppViewBlockContainer,
  section.stMain .block-container,
  section.main .block-container,
  [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  [data-testid="stMainBlockContainer"].dungeon-shell-flush {
    margin-top: calc(-1 * var(--dungeon-shell-offset, 0px)) !important;
  }
"""

_STYLE_MARKER_COLLAPSE = """
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor),
  [data-testid="stElementContainer"]:has(#dungeon-footer-anchor) {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    border: none !important;
  }
"""


_COMPONENT_POINTER_PASS_THROUGH_JS = """
  function disableComponentPointerCapture() {
    const iframe = window.frameElement;
    if (!iframe) {
      return;
    }
    iframe.style.pointerEvents = "none";
    iframe.style.height = "0px";
    iframe.style.minHeight = "0px";
    iframe.style.border = "none";
    const container = iframe.closest('[data-testid="stElementContainer"]');
    if (container) {
      container.style.pointerEvents = "none";
      container.style.height = "0px";
      container.style.minHeight = "0px";
      container.style.overflow = "hidden";
    }
  }
  disableComponentPointerCapture();
"""


def component_pointer_pass_through_js() -> str:
    return _COMPONENT_POINTER_PASS_THROUGH_JS.strip()


def inject_css_block(css: str, *, element_id: str = "dungeon-app-css") -> None:
    """Inject CSS into document.head — avoids Streamlit markdown layout placeholders."""
    components.html(
        f"""
<script>
(function() {{
{component_pointer_pass_through_js()}
  const host = window.parent;
  const id = {json.dumps(element_id)};
  let el = host.document.getElementById(id);
  if (!el) {{
    el = host.document.createElement("style");
    el.id = id;
    host.document.head.appendChild(el);
  }}
  el.textContent = {json.dumps(css)};
}})();
</script>
""",
        height=0,
    )


def shell_base_css(*, extra_css: str = "") -> str:
    hide_rule = ", ".join(_HIDE_CHROME_SELECTORS)
    return f"""
  {hide_rule} {{ display: none !important; }}
  {_FLUSH_TOP_CSS}
  {_STYLE_MARKER_COLLAPSE}
  .block-container {{ padding-top: 0; }}
  .studio-card {{
      border: 1px solid rgba(250, 250, 250, 0.12);
      border-radius: 18px;
      padding: 1rem 1.1rem;
      background: rgba(255, 255, 255, 0.035);
  }}
  .studio-muted {{ color: rgba(250, 250, 250, 0.65); }}
  .studio-agent-title-spacer {{
      height: 0.75rem;
  }}
  .studio-agent-title-text {{
      font-size: 1.25rem;
      font-weight: 800;
      line-height: 1.5;
      margin-bottom: 0.55rem;
  }}
  {extra_css}
"""


def inject_hide_streamlit_chrome(*, hide_sidebar: bool = False, extra_css: str = "") -> None:
    selectors = list(_HIDE_CHROME_SELECTORS)
    if hide_sidebar:
        selectors.extend(
            [
                '[data-testid="stSidebar"]',
                '[data-testid="stSidebarCollapsedControl"]',
            ]
        )
    hide_rule = ", ".join(selectors)
    inject_css_block(
        f"""
  {hide_rule} {{ display: none !important; }}
  {_FLUSH_TOP_CSS}
  {_STYLE_MARKER_COLLAPSE}
  {extra_css}
"""
    )


def render_mission_demo(*, user_text: str, agent_text: str) -> None:
    safe_user = html.escape(user_text)
    safe_agent = html.escape(agent_text)
    st.markdown(
        f"""
<div class="mission-demo-host">
  <div class="mission-demo">
    <div class="mission-demo-caption">通關後會像這樣</div>
    <div class="mission-demo-bubble mission-demo-user">
      <span class="mission-demo-role">User</span>
      <span class="mission-demo-text">{safe_user}</span>
    </div>
    <div class="mission-demo-bubble mission-demo-agent">
      <span class="mission-demo-role">Agent</span>
      <span class="mission-demo-text">{safe_agent}</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_dungeon_hint(message: str) -> None:
    st.markdown(
        f'<div class="dungeon-hint">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def inject_style() -> None:
    inject_css_block(shell_base_css())
    # 不在此注入 iframe theme fix：會 patch 所有 iframe（含 multimodal 元件）導致輸入失效。
