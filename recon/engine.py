"""
recon.engine — Pipeline Orchestrator.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Phases:
    1    Subdomain Enumeration  (subfinder, amass, assetfinder, findomain, theHarvester)
    1.5  DNS Validation         (dnsx)
    2    Live Host Probing      (httpx)
    3    URL Collection         (gau, waybackurls, katana)
"""

import time
from pathlib import Path
from typing import Set

from recon.config import (
    VERSION, C,
    log, hr, phase_header, tool_status, section_result,
    setup_file_logging, close_file_logging,
)

from recon.tools.subdomains import collect_subdomains
from recon.tools.dns        import run_dnsx
from recon.tools.probing    import run_httpx
from recon.tools.urls       import collect_urls

from recon.reports import generate_html_report
from recon.utils   import clean_domain


class ReconEngine:
    """Pipeline orchestrator - dieu phoi toan bo quy trinh recon."""

    def __init__(
        self,
        domain: str,
        outdir: Path,
        threads: int = 5,
        selected_tools: Set[str] = None,
        skipped_tools: Set[str] = None,
        log_file: bool = False,
    ):
        self.domain  = clean_domain(domain)
        self.outdir  = outdir / self.domain
        self.threads = threads

        # Tool filter
        self.tool_filter = None
        if selected_tools:
            self.tool_filter = selected_tools
        elif skipped_tools:
            from recon.config import ALL_TOOL_NAMES
            self.tool_filter = ALL_TOOL_NAMES - skipped_tools

        self.stats = {
            "subdomains":          0,
            "subdomains_dns_valid": 0,
            "live":                0,
            "urls":                0,
            "emails":              0,
        }

        # Tạo thư mục output
        self.outdir.mkdir(parents=True, exist_ok=True)
        for d in ["raw", "subdomains", "live", "urls"]:
            (self.outdir / d).mkdir(exist_ok=True)

        if log_file:
            setup_file_logging(self.outdir / "recon.log")

    # ------------------------------------------
    def run(self) -> dict:
        start = time.time()

        # === PHASE 1 ==================================================
        phase_header("1 / 3", "Subdomain Enumeration")
        t0 = time.time()
        subs, emails = collect_subdomains(
            self.domain, self.outdir, self.threads, self.tool_filter,
        )
        self.stats["subdomains"] = len(subs)
        self.stats["emails"]     = len(emails)
        elapsed1 = time.time() - t0

        tool_status(
            "Enumeration", "ok",
            f"{C.BOLD}{len(subs)}{C.END} subdomains  "
            f"{C.G}{len(emails)}{C.END} emails",
            elapsed1,
        )

        # === PHASE 1.5 ================================================
        phase_header("1.5", "DNS Validation")
        t0 = time.time()
        dns_valid = run_dnsx(subs, self.outdir, self.tool_filter)
        if dns_valid:
            subs = dns_valid
        self.stats["subdomains_dns_valid"] = len(subs)
        elapsed15 = time.time() - t0

        drop = self.stats["subdomains"] - len(subs)
        tool_status(
            "dnsx", "ok",
            f"{C.BOLD}{len(subs)}{C.END} valid  "
            f"{C.DIM}(-{drop} filtered){C.END}",
            elapsed15,
        )

        # === PHASE 2 ==================================================
        phase_header("2 / 3", "Live Host Probing")
        t0   = time.time()
        live = run_httpx(subs, self.outdir, self.tool_filter)
        live_urls = [l.split()[0] for l in live]
        self.stats["live"] = len(live_urls)
        elapsed2 = time.time() - t0

        tool_status(
            "httpx", "ok",
            f"{C.BOLD}{len(live_urls)}{C.END} live hosts",
            elapsed2,
        )

        # === PHASE 3 ==================================================
        phase_header("3 / 3", "URL Collection")
        t0   = time.time()
        urls = collect_urls(self.domain, subs, self.outdir, self.tool_filter)
        self.stats["urls"] = len(urls)
        elapsed3 = time.time() - t0

        tool_status(
            "URL harvest", "ok",
            f"{C.BOLD}{len(urls)}{C.END} unique URLs",
            elapsed3,
        )

        # -- Timing --
        elapsed = time.time() - start
        self.stats["elapsed"] = round(elapsed, 1)

        # -- HTML Report --
        hr()
        log(f"Generating HTML report...", "run")
        report_path = generate_html_report(
            outdir     = self.outdir,
            domain     = self.domain,
            stats      = self.stats,
            live       = live,
            subdomains = sorted(subs),
            urls       = sorted(urls),
            emails     = sorted(emails),
        )
        log(f"Report -> {C.BOLD}{report_path}{C.END}", "ok")

        # -- Final Results --
        self._print_results()
        close_file_logging()
        return self.stats

    # ------------------------------------------
    def _print_results(self):
        s = self.stats
        print()
        hr("=", C.G)
        print(
            f"  {C.G}{C.BOLD}RECON COMPLETE{C.END}"
            f"  {C.DIM}-{C.END}"
            f"  {C.BOLD}{self.domain}{C.END}"
        )
        hr("=", C.G)

        section_result("Subdomains (raw)",    s["subdomains"],           "found")
        section_result("Subdomains (DNS Valid)", s["subdomains_dns_valid"], "valid",    highlight=True)
        section_result("Emails",              s["emails"],               "harvested")
        section_result("Live hosts",          s["live"],                 "responding", highlight=True)
        section_result("URLs",                s["urls"],                 "collected")

        hr()
        # Timing bar
        elapsed = s["elapsed"]
        speed   = round(s["subdomains"] / elapsed, 1) if elapsed > 0 else 0
        print(
            f"  {C.G}[+] Finished{C.END}  "
            f"{C.DIM}in{C.END}  {C.BOLD}{elapsed}s{C.END}  "
            f"{C.DIM}|{C.END}  "
            f"{C.DIM}{speed} subs/s{C.END}"
        )

        # Report path
        rp = self.outdir / "REPORT.html"
        print(f"  {C.DIM}Report  ->  {rp}{C.END}")
        hr("=", C.G)
        print()
