"""
recon.tools.probing — Kiểm tra host sống (httpx).
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Quiet mode: không log chi tiết, chỉ trả kết quả.
"""

from pathlib import Path
from typing import List, Set, Optional

from recon.utils import run_cmd, which, write_lines


def run_httpx(
    hosts: Set[str],
    outdir: Path,
    tool_filter: Optional[Set[str]] = None,
) -> List[str]:
    """Probe danh sách host bằng httpx. Trả về list kết quả."""
    if tool_filter and "httpx" not in tool_filter:
        return []
    if not which("httpx") or not hosts:
        return []

    host_file = outdir / "subdomains" / "all_subs.txt"
    out_file  = outdir / "live" / "live_hosts.txt"

    cmd = [
        "httpx", "-l", str(host_file),
        "-silent", "-status-code", "-title", "-tech-detect",
        "-follow-redirects", "-threads", "50",
        "-o", str(out_file),
    ]
    run_cmd(cmd, timeout=600)

    live = []
    if out_file.exists():
        live = [l.strip() for l in out_file.read_text().splitlines() if l.strip()]

    urls = [l.split()[0] for l in live]
    write_lines(outdir / "live" / "urls.txt", urls)
    return live
