from __future__ import annotations

import html
import json


def _normalize_colon(s: str) -> str:
    return s.replace("：", ":")


def _stdout_starts_with_prompt(stdout: str, prompt: str) -> bool:
    if not prompt:
        return False
    if stdout.startswith(prompt):
        return True
    return _normalize_colon(stdout).startswith(_normalize_colon(prompt))


def _prompt_prefix_len(stdout: str, prompt: str) -> int:
    if stdout.startswith(prompt):
        return len(prompt)
    norm_stdout = _normalize_colon(stdout)
    norm_prompt = _normalize_colon(prompt)
    if norm_stdout.startswith(norm_prompt):
        return len(prompt)
    return -1


def normalize_inline_terminal_stdout(
    stdout: str,
    *,
    prompt: str = "",
    last_input: str = "",
) -> str:
    """Display-only: input() 後 print() 常與 prompt+輸入黏同一行，插入虛擬換行以便 UI 換行。"""
    if not stdout:
        return stdout

    if prompt and _stdout_starts_with_prompt(stdout, prompt):
        prefix_len = _prompt_prefix_len(stdout, prompt)
        if prefix_len > 0:
            prefix = stdout[:prefix_len]
            rest = stdout[prefix_len:]
            if last_input and rest.startswith(last_input):
                glued = prefix + last_input
                tail = rest[len(last_input) :]
                if tail and not tail.startswith("\n"):
                    return f"{glued}\n{tail}"
                return stdout
            if not last_input and rest and not rest.startswith("\n"):
                return f"{prefix}\n{rest}"

    if not last_input:
        return stdout

    if prompt:
        prefix = f"{prompt}{last_input}"
        if stdout.startswith(prefix):
            rest = stdout[len(prefix) :]
            if rest and not rest.startswith("\n"):
                return f"{prefix}\n{rest}"
        norm_prefix = _normalize_colon(prefix)
        norm_stdout = _normalize_colon(stdout)
        if norm_stdout.startswith(norm_prefix):
            # 還原切點：用 last_input 在 first line 的位置
            first_nl = stdout.find("\n")
            first_line = stdout if first_nl == -1 else stdout[:first_nl]
            idx = first_line.find(last_input)
            if idx != -1:
                split_at = idx + len(last_input)
                if split_at < len(first_line):
                    new_first = first_line[:split_at] + "\n" + first_line[split_at:]
                    if first_nl == -1:
                        return new_first
                    return new_first + stdout[first_nl:]

    first_nl = stdout.find("\n")
    first_line = stdout if first_nl == -1 else stdout[:first_nl]
    idx = first_line.find(last_input)
    if idx == -1:
        return stdout
    split_at = idx + len(last_input)
    if split_at >= len(first_line):
        return stdout
    new_first = first_line[:split_at] + "\n" + first_line[split_at:]
    if first_nl == -1:
        return new_first
    return new_first + stdout[first_nl:]


def split_stdout_pending_prompt(stdout: str, *, awaiting_input: bool) -> tuple[str, str]:
    """將 stdout 拆成已完成輸出與 pending prompt（input 前常無換行）。"""
    if not awaiting_input or not stdout:
        return stdout, ""
    if stdout.endswith("\n"):
        return stdout, ""
    last_nl = stdout.rfind("\n")
    if last_nl == -1:
        return "", stdout
    return stdout[: last_nl + 1], stdout[last_nl + 1 :]


def terminal_iframe_height(completed: str, *, has_prompt: bool, min_height: int = 160) -> int:
    lines = [line for line in completed.splitlines() if line.strip()]
    if has_prompt:
        lines.append("prompt")
    return min(320, max(min_height, 24 * (len(lines) + 2) + 48))


def build_terminal_srcdoc(
    *,
    completed: str,
    prompt: str,
    editable: bool,
    session_key: str,
    placeholder: str = "（尚未啟動）",
) -> str:
    completed_text = completed.rstrip("\n")
    if not completed_text and not prompt:
        completed_text = placeholder

    completed_html = html.escape(completed_text) if completed_text else ""
    input_block = ""
    if editable and prompt:
        input_block = """
    <div class="prompt-line">
      <span class="prompt" id="prompt"></span>
      <input id="line" autocomplete="off" spellcheck="false" aria-label="terminal input" />
    </div>"""
    elif editable and not prompt:
        input_block = """
    <div class="prompt-line">
      <input id="line" autocomplete="off" spellcheck="false" placeholder="輸入後按 Enter 送出" aria-label="terminal input" />
    </div>"""

    prompt_script = ""
    if prompt:
        prompt_script = f"document.getElementById('prompt').textContent = {json.dumps(prompt)};"

    enter_script = ""
    if editable:
        enter_script = f"""
    const SESSION_KEY = {json.dumps(session_key)};
    const input = document.getElementById("line");
    if (input) {{
      input.focus();
      input.addEventListener("keydown", (e) => {{
        if (e.key !== "Enter") return;
        e.preventDefault();
        const line = input.value;
        if (!line.trim()) return;
        window.parent.postMessage({{
          type: "forge_terminal_input",
          session_key: SESSION_KEY,
          line: line,
        }}, "*");
      }});
    }}"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0; padding: 12px;
    background: #0e1117; color: #fafafa;
    font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  pre {{
    margin: 0 0 8px; white-space: pre-wrap; word-break: break-word;
  }}
  .prompt-line {{
    display: flex; align-items: baseline; flex-wrap: wrap; gap: 0;
  }}
  .prompt {{ white-space: pre; color: #fafafa; }}
  input {{
    flex: 1 1 120px; min-width: 80px;
    border: none; outline: none; background: transparent;
    color: #fafafa; font: inherit; padding: 0; margin: 0;
    caret-color: #fafafa;
  }}
  input::placeholder {{ color: #64748b; }}
</style>
</head>
<body>
  <pre id="out">{completed_html}</pre>
  {input_block}
  <script>
    {prompt_script}
    {enter_script}
  </script>
</body>
</html>"""


def build_terminal_bridge_html(session_key: str) -> str:
    """在 parent 頁監聽 terminal iframe 的 postMessage，以 query param 觸發 rerun。"""
    sk_json = json.dumps(session_key)
    return f"""<script>
(function() {{
  const SK = {sk_json};
  const flag = "__forgeTerminalBridge_" + SK;
  if (window[flag]) return;
  window[flag] = true;
  window.addEventListener("message", (e) => {{
    const data = e.data;
    if (!data || data.type !== "forge_terminal_input" || data.session_key !== SK) return;
    const line = String(data.line || "");
    if (!line.trim()) return;
    const url = new URL(window.location.href);
    url.searchParams.set("ft_sk", SK);
    url.searchParams.set("ft_line", line);
    window.location.href = url.toString();
  }});
}})();
</script>"""
