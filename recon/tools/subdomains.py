"""
recon.tools.subdomains — Liệt kê subdomain.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Chạy song song: subfinder, amass, assetfinder, findomain, theHarvester
theHarvester bổ sung email từ OSINT sources (Google, Bing, crtsh, ...)
"""

import concurrent.futures
import re
import time
from pathlib import Path
from typing import Set, Tuple

from recon.config import C
from recon.utils  import is_subdomain_of, run_cmd, which, write_lines


# Tool → binary mapping
SUBDOMAIN_TOOLS = {
    "subfinder":    "subfinder",
    "amass":        "amass",
    "assetfinder":  "assetfinder",
    "findomain":    "findomain",
    "theharvester": "theHarvester",
}


# ─────────────────────────────────────────────
# WRAPPER — thêm per-tool status logging
# ─────────────────────────────────────────────

def _run_with_status(name: str, fn, domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    """Chạy tool fn."""
    try:
        subs, emails = fn(domain, outdir)
        return subs, emails
    except Exception as e:
        return set(), set()


# ─────────────────────────────────────────────
# INDIVIDUAL TOOLS
# ─────────────────────────────────────────────

def run_subfinder(domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    out     = run_cmd(["subfinder", "-d", domain, "-silent", "-all"])
    results = {l.strip() for l in out.splitlines() if is_subdomain_of(l, domain)}
    write_lines(outdir / "raw" / "subfinder.txt", results)
    return results, set()


def run_amass(domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    out     = run_cmd(["amass", "enum", "-passive", "-d", domain, "-silent"], timeout=900)
    results = {l.strip() for l in out.splitlines() if is_subdomain_of(l, domain)}
    write_lines(outdir / "raw" / "amass.txt", results)
    return results, set()


def run_assetfinder(domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    out     = run_cmd(["assetfinder", "--subs-only", domain])
    results = {l.strip() for l in out.splitlines() if is_subdomain_of(l, domain)}
    write_lines(outdir / "raw" / "assetfinder.txt", results)
    return results, set()


def run_findomain(domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    out     = run_cmd(["findomain", "-t", domain, "-q"])
    results = {l.strip() for l in out.splitlines() if is_subdomain_of(l, domain)}
    write_lines(outdir / "raw" / "findomain.txt", results)
    return results, set()


def run_theharvester(domain: str, outdir: Path) -> Tuple[Set[str], Set[str]]:
    """
    theHarvester: thu thập subdomain + email từ OSINT sources.
    Sources: Google, Bing, crtsh, dnsdumpster, hackertarget, urlscan, anubis
    """
    out_xml = outdir / "raw" / "theharvester"
    cmd = [
        "theHarvester",
        "-d", domain,
        "-b", "google,bing,crtsh,dnsdumpster,hackertarget,urlscan,anubis",
        "-f", str(out_xml),
    ]
    out = run_cmd(cmd, timeout=300)

    subdomains: Set[str] = set()
    emails:     Set[str] = set()

    _email_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    _sub_re   = re.compile(r"(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}")

    for line in out.splitlines():
        line = line.strip()
        for em in _email_re.findall(line):
            emails.add(em.lower())
        for m in _sub_re.finditer(line):
            candidate = m.group(0).lower().rstrip(".")
            if is_subdomain_of(candidate, domain):
                subdomains.add(candidate)

    write_lines(outdir / "raw" / "theharvester_subs.txt", subdomains)
    write_lines(outdir / "raw" / "theharvester_emails.txt", emails)
    return subdomains, emails


_RUNNERS = {
    "subfinder":    run_subfinder,
    "amass":        run_amass,
    "assetfinder":  run_assetfinder,
    "findomain":    run_findomain,
    "theharvester": run_theharvester,
}


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

def collect_subdomains(
    domain: str,
    outdir: Path,
    threads: int = 5,
    tool_filter: Set[str] = None,
) -> Tuple[Set[str], Set[str]]:
    """
    Chạy song song tất cả tool subdomain có sẵn.
    Hiển thị per-tool status (running → ok/err/skip).

    Returns:
        (all_subdomains, all_emails)
    """
    all_subs:   Set[str] = set()
    all_emails: Set[str] = set()

    # Phân loại: available / skipped / missing
    available = {}
    for name, binary in SUBDOMAIN_TOOLS.items():
        if tool_filter and name not in tool_filter:
            continue
        if not which(binary):
            continue
        available[name] = _RUNNERS[name]

    if not available:
        all_subs.add(domain)
        write_lines(outdir / "subdomains" / "all_subs.txt", all_subs)
        return all_subs, all_emails

    # Chạy song song
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(threads, len(available))
    ) as exe:
        futures = {
            exe.submit(_run_with_status, name, fn, domain, outdir): name
            for name, fn in available.items()
        }
        for fut in concurrent.futures.as_completed(futures):
            try:
                subs, emails = fut.result()
                all_subs.update(subs)
                all_emails.update(emails)
            except Exception:
                pass

    all_subs.add(domain)
    write_lines(outdir / "subdomains" / "all_subs.txt", all_subs)
    write_lines(outdir / "subdomains" / "all_emails.txt", all_emails)
    return all_subs, all_emails
