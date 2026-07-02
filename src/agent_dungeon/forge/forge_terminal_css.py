from __future__ import annotations

# 只匹配 terminal border 內層 VerticalBlock（marker 為直接子 ElementContainer 內容）。
_INLINE_TERMINAL_MARKER = "[data-forge-terminal='inline']"
_INLINE_TERMINAL_DIRECT_CHILD_MARKER = (
    f"> [data-testid=\"stElementContainer\"]:has({_INLINE_TERMINAL_MARKER})"
)
_INLINE_TERMINAL_BLOCK = (
    ".dungeon-col-center [data-testid=\"stLayoutWrapper\"] "
    "> [data-testid=\"stVerticalBlock\"]"
    f":has({_INLINE_TERMINAL_DIRECT_CHILD_MARKER})"
)
_INLINE_TERMINAL_BORDER = (
    ".dungeon-col-center [data-testid=\"stLayoutWrapper\"]:has("
    f"> [data-testid=\"stVerticalBlock\"] > [data-testid=\"stElementContainer\"]:has({_INLINE_TERMINAL_MARKER}))"
)


def inline_terminal_css_block() -> str:
    block = _INLINE_TERMINAL_BLOCK
    border = _INLINE_TERMINAL_BORDER
    m = _INLINE_TERMINAL_MARKER
    return f"""
  {border} {{
    padding-top: 0 !important;
    padding-bottom: 0.35rem !important;
  }}
  {block} > [data-testid="stElementContainer"]:has({m}) {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }}
  {block} {{
    gap: 0 !important;
  }}
  {block} [data-testid="stElementContainer"]:has([data-testid="stCode"]) {{
    margin-top: 0 !important;
    padding-top: 0 !important;
  }}
  {block} [data-testid="stCode"] {{
    max-width: 100%;
    overflow-x: auto;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }}
  {block} [data-testid="stCode"] pre,
  {block} [data-testid="stCode"] code {{
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
  }}
  {block} [data-testid="stForm"] {{
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
  }}
  {block} [data-testid="stForm"] [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
  }}
  {block} [data-testid="stElementContainer"]:has([data-testid="stForm"]),
  {block} [data-testid="stElementContainer"]:has([data-testid="stTextInput"]) {{
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }}
  {block} [data-testid="column"] {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }}
  {block} [data-testid="stTextInput"] input {{
    min-height: 2rem !important;
    padding-top: 0.35rem !important;
    padding-bottom: 0.35rem !important;
    background-color: #f8fafc !important;
    border: 1px solid #94a3b8 !important;
    border-radius: 6px !important;
    color: #0f172a !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
  }}
  {block} [data-testid="stTextInput"] input:focus {{
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15) !important;
  }}
  {block} [data-testid="stTextInput"] input:disabled {{
    background-color: #0f172a !important;
    color: #94a3b8 !important;
    border-color: #334155 !important;
    -webkit-text-fill-color: #94a3b8 !important;
    box-shadow: none !important;
  }}
  {block} [data-testid="stFormSubmitButton"] button {{
    min-height: 2rem !important;
    padding-top: 0.35rem !important;
    padding-bottom: 0.35rem !important;
    border: 1px solid #cbd5e1 !important;
  }}
  {block} [data-testid="stForm"] [data-testid="stCaptionContainer"] {{
    display: none !important;
  }}
"""


def inline_terminal_css_markdown() -> str:
    return f"<style>{inline_terminal_css_block()}</style>"
