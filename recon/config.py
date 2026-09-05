import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

VERSION = "3.0.0"

TOOL_REGISTRY: Dict[str, str] = {
    # Subdomain enumeration (Phase 1)
    "subfinder":    "subfinder",
    "amass":        "amass",
    "assetfinder":  "assetfinder",
    "findomain":    "findomain",
    "theharvester": "theHarvester",  # OSINT: subdomain + email
    # DNS Validation (Phase 1.5 — sau khi collect xong)
    "dnsx":         "dnsx",
    # Live probing (Phase 2)
    "httpx":        "httpx",
    # URL collection (Phase 3)
    "gau":          "gau",
    "waybackurls":  "waybackurls",
    "katana":       "katana",
}

# All tool names (to validate --tools / --skip-tools)
ALL_TOOL_NAMES: Set[str] = set(TOOL_REGISTRY.keys())


def get_available_tools(
    selected: Set[str] = None,
    skipped: Set[str] = None,
) -> Dict[str, str]:
    available = {}
    for name, binary in TOOL_REGISTRY.items():
        if selected and name not in selected:
            continue
        if skipped and name in skipped:
            continue
        path = shutil.which(binary)
        if path:
            available[name] = path
    return available


# ===============================================
# ANSI COLOR CODES
# ===============================================
class C:
    """ANSI escape codes cho terminal output có màu."""
    R    = "\033[91m"   # Red
    G    = "\033[92m"   # Green
    Y    = "\033[93m"   # Yellow
    B    = "\033[94m"   # Blue
    M    = "\033[95m"   # Magenta
    C    = "\033[96m"   # Cyan
    W    = "\033[97m"   # White
    BOLD = "\033[1m"
    DIM  = "\033[2m"
    END  = "\033[0m"


# ===============================================
# UI PRIMITIVES  (box-drawing, separators)
# ===============================================

# Độ rộng cố định của terminal output
_W = 62


def _strip_ansi(s: str) -> str:
    """Xóa ANSI escape codes để tính độ dài thực."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)


def _pad(text: str, width: int, fill: str = " ") -> str:
    """Pad text đến width thực (bỏ qua ANSI codes khi đếm)."""
    visible = len(_strip_ansi(text))
    return text + fill * max(0, width - visible)


def hr(char: str = "-", color: str = C.DIM) -> None:
    """In một đường kẻ ngang."""
    print(f"{color}{char * _W}{C.END}")


def phase_header(num: str, title: str, tools: str = "") -> None:
    """In header cho một phase chuyên nghiệp và gọn gàng."""
    badge = f" PHASE {num}: {title} "
    right = max(0, _W - 4 - len(badge))
    print(f"\n{C.G}{C.BOLD}---[{badge}]{'-' * right}{C.END}")


def tool_status(name: str, status: str, detail: str = "", elapsed: float = None) -> None:
    """
    In trạng thái một tool.
    status: "run" | "ok" | "warn" | "skip" | "err"

    Vi du:
      [*] subfinder    running...
      [+] subfinder    142 subdomains   (3.2s)
      [-] amass        not found
      [~] findomain    skipped
    """
    icons = {
        "run":  (C.M,  "[*]"),
        "ok":   (C.G,  "[+]"),
        "warn": (C.Y,  "[!]"),
        "err":  (C.R,  "[-]"),
        "skip": (C.DIM,"[~]"),
    }
    clr, icon = icons.get(status, (C.W, "·"))

    name_col   = f"{clr}{icon}{C.END} {C.W}{C.BOLD}{name:<14}{C.END}"
    detail_col = f"{clr}{detail}{C.END}" if detail else ""
    time_col   = f"  {C.DIM}({elapsed:.1f}s){C.END}" if elapsed is not None else ""

    print(f"    {name_col} {detail_col}{time_col}")


def section_result(label: str, value, unit: str = "", highlight: bool = False) -> None:
    val_str = str(value)
    clr     = C.G if highlight else C.W
    print(
        f"  {C.W}{label:<26}{C.END}"
        f"  {clr}{C.BOLD}{val_str:<6}{C.END}"
        f"  {C.DIM}{unit}{C.END}"
    )


# ===============================================
# FILE LOGGING
# ===============================================
_log_file = None


def setup_file_logging(log_path: Path) -> None:
    global _log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _log_file = open(log_path, "a", encoding="utf-8")
    log(f"Log file: {log_path}", "info")


def close_file_logging() -> None:
    global _log_file
    if _log_file:
        _log_file.close()
        _log_file = None


# ===============================================
# LOG FUNCTION
# ===============================================
def log(msg: str, level: str = "info") -> None:
    """
    Ghi log ra terminal (có màu) và file (plain text).

    Levels:
        info  [*]  Green   - info
        ok    [+]  Green   - success
        warn  [!]  Yellow  - warning
        err   [-]  Red     - error
        run   [>]  Magenta - running
        skip  [~]  Dim     - skipped
        find  [»]  Green   - found
    """
    ts     = datetime.now().strftime("%H:%M:%S")
    colors = {
        "info": C.G, "ok": C.G, "warn": C.Y, "err": C.R,
        "run":  C.M, "skip": C.DIM, "find": C.G,
    }
    prefix = {
        "info": "[*]", "ok": "[+]", "warn": "[!]", "err": "[-]",
        "run":  "[>]", "skip": "[~]", "find": "[»]",
    }

    pfx = prefix.get(level, "[*]")
    clr = colors.get(level, C.W)

    print(f"{C.DIM}{ts}{C.END}  {clr}{pfx}{C.END}  {msg}")

    if _log_file:
        plain = _strip_ansi(msg)
        _log_file.write(f"{pfx} {ts}  {plain}\n")
        _log_file.flush()
