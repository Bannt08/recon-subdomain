"""
recon.tools.urls — Thu thập URL (gau, waybackurls, katana).
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
gau + waybackurls chạy song song, katana chạy sau (cần live urls.txt).
"""

import concurrent.futures
import os
import subprocess
import time
from pathlib import Path
from typing import Set, Optional

from recon.config import C
from recon.utils  import read_lines, run_cmd, which, write_lines


URL_TOOLS = {
    "gau":         "gau",
    "waybackurls": "waybackurls",
    "katana":      "katana",
}


# ─────────────────────────────────────────────
# INDIVIDUAL TOOLS
# ─────────────────────────────────────────────

def run_gau(domain: str, outdir: Path) -> Set[str]:
    results = set()
    out = run_cmd(["gau", "--threads", "5", domain], timeout=300)
    for line in out.splitlines():
        if line.strip():
            results.add(line.strip())
    write_lines(outdir / "raw" / "gau.txt", results)
    return results


def run_waybackurls(hosts: Set[str], outdir: Path) -> Set[str]:
    results = set()
    try:
        proc = subprocess.Popen(
            ["waybackurls"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True,
            env=os.environ.copy(),
        )
        stdin_data = "\n".join(list(hosts)[:50])
        out, _ = proc.communicate(input=stdin_data, timeout=180)
        for line in out.splitlines():
            if line.strip():
                results.add(line.strip())
    except Exception:
        pass
    write_lines(outdir / "raw" / "waybackurls.txt", results)
    return results


def run_katana(outdir: Path) -> Set[str]:
    url_file = outdir / "live" / "urls.txt"
    if not url_file.exists():
        return set()
    out_file = outdir / "urls" / "katana.txt"
    cmd = [
        "katana", "-list", str(url_file),
        "-silent", "-jc", "-d", "2",
        "-o", str(out_file),
    ]
    run_cmd(cmd, timeout=600)
    return read_lines(out_file)


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

def collect_urls(
    domain: str,
    hosts: Set[str],
    outdir: Path,
    tool_filter: Optional[Set[str]] = None,
) -> Set[str]:
    """Thu thập URL song song (gau + waybackurls), rồi katana."""
    all_urls: Set[str] = set()

    parallel_tools = {}
    has_katana = False

    for name, binary in URL_TOOLS.items():
        if tool_filter and name not in tool_filter:
            continue
        if not which(binary):
            continue
        if name == "katana":
            has_katana = True
        else:
            parallel_tools[name] = binary

    if not parallel_tools and not has_katana:
        write_lines(outdir / "urls" / "all_urls.txt", all_urls)
        return all_urls

    # ── gau + waybackurls song song ──
    if parallel_tools:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(parallel_tools)) as exe:
            futs = {}

            if "gau" in parallel_tools:
                futs[exe.submit(run_gau, domain, outdir)] = "gau"

            if "waybackurls" in parallel_tools:
                futs[exe.submit(run_waybackurls, hosts, outdir)] = "waybackurls"

            for fut in concurrent.futures.as_completed(futs):
                try:
                    result = fut.result()
                    all_urls.update(result)
                except Exception:
                    pass

    # ── Katana sau (cần live urls.txt từ httpx trước) ──
    if has_katana:
        result = run_katana(outdir)
        all_urls.update(result)

    write_lines(outdir / "urls" / "all_urls.txt", all_urls)
    return all_urls
