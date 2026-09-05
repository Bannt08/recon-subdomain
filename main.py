#!/usr/bin/env python3
"""
Entry point: CLI interface cho bannt recon.
Sử dụng: python main.py -d domain.com
    python main.py -d example.com
    python main.py -dL domains.txt
    python main.py -d target.com --tools subfinder,httpx,dnsx
"""

import argparse
import sys
from pathlib import Path

# Fix encoding cho Windows terminal
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from recon.config import (
    VERSION, C, ALL_TOOL_NAMES, get_available_tools,
    log, hr, tool_status, section_result,
)
from recon.engine import ReconEngine


def _banner() -> str:
    return f"""{C.G}{C.BOLD}
  _                     _                             
 | |__   __ _ _ __  _ __| |_       _ __ ___  ___ ___  _ __  
 | '_ \\ / _` | '_ \\| '_ \\ __|____ | '__/ _ \\/ __/ _ \\| '_ \\ 
 | |_) | (_| | | | | | | | ||____|| | |  __/ (_| (_) | | | |
 |_.__/ \\__,_|_| |_|_| |_|\\__|    |_|  \\___|\\___\\___/|_| |_|
{C.END}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""

Examples:
  python main.py -d example.com
  python main.py -dL domains.txt

        """,
    )

    # -- Target --
    target = parser.add_argument_group("Target")
    target.add_argument("-d", "--domain", nargs="+", help="One or more target domains")
    target.add_argument("-dL", "--domain-list", type=str, help="File containing list of domains")

    # -- Output --
    output = parser.add_argument_group("Output")
    output.add_argument("-o", "--output", default="output", help="Output directory (default: output/)")
    output.add_argument("--log-file", action="store_true", help="Also write logs to output/domain/recon.log")

    # -- Tool Selection --
    tools = parser.add_argument_group("Tool Selection")
    tools.add_argument("--tools", type=str, help="Only run these tools (comma-separated)")
    tools.add_argument("--skip-tools", type=str, help="Skip these tools (comma-separated)")

    # -- Scanning options --
    scan = parser.add_argument_group("Scanning Options")
    scan.add_argument("-t", "--threads", type=int, default=5, help="Max parallel threads (default: 5)")

    # -- Misc --
    misc = parser.add_argument_group("Misc")
    misc.add_argument("--dry-run", action="store_true", help="Check tool availability")
    misc.add_argument("-v", "--version", action="version", version=f"bannt recon v{VERSION}")

    return parser.parse_args()


def parse_tool_list(tool_string: str) -> set:
    tools = {t.strip().lower() for t in tool_string.split(",") if t.strip()}
    invalid = tools - ALL_TOOL_NAMES
    if invalid:
        log(f"Unknown tools: {', '.join(invalid)}", "err")
        log(f"Available: {', '.join(sorted(ALL_TOOL_NAMES))}", "info")
        sys.exit(1)
    return tools


def check_tools(selected: set = None, skipped: set = None) -> None:
    available = get_available_tools(selected, skipped)
    from recon.config import TOOL_REGISTRY

    log("Checking tool availability...", "info")
    print()

    phases = {
        "Subdomain Enumeration": ["subfinder", "amass", "assetfinder", "findomain", "theharvester"],
        "DNS Validation":        ["dnsx"],
        "Live Probing":          ["httpx"],
        "URL Collection":        ["gau", "waybackurls", "katana"],
    }

    for phase, names in phases.items():
        print(f"  {C.DIM}---[ {phase} ]{'-' * max(0, 52 - len(phase))}{C.END}")
        for name in names:
            if name not in TOOL_REGISTRY:
                continue
            binary = TOOL_REGISTRY[name]
            if selected and name not in selected:
                tool_status(name, "skip", "filtered")
            elif skipped and name in skipped:
                tool_status(name, "skip", "skipped by user")
            elif name in available:
                tool_status(name, "ok", available[name])
            else:
                tool_status(name, "warn", "not found in PATH")
        print()

    total = (
        len(selected) if selected
        else (len(TOOL_REGISTRY) - len(skipped) if skipped else len(TOOL_REGISTRY))
    )
    hr()
    section_result("Tools available", f"{len(available)} / {total}")
    if len(available) == 0:
        log("No tools found! Install tools to use bannt recon.", "err")
    print()


def main() -> None:
    args = parse_args()
    print(_banner())

    selected_tools = parse_tool_list(args.tools) if args.tools else None
    skipped_tools  = parse_tool_list(args.skip_tools) if args.skip_tools else None

    if args.dry_run:
        check_tools(selected_tools, skipped_tools)
        return

    domains = []
    if args.domain:
        domains.extend(args.domain)
    if args.domain_list:
        dl_path = Path(args.domain_list)
        if dl_path.exists():
            with open(dl_path) as f:
                domains.extend([l.strip() for l in f if l.strip() and not l.startswith("#")])
        else:
            log(f"Domain list file not found: {dl_path}", "err")
            sys.exit(1)

    if not domains:
        log("No domains specified! Use -d or -dL", "err")
        sys.exit(1)

    outdir = Path(args.output)

    all_stats = {}
    for i, domain in enumerate(domains, 1):
        if len(domains) > 1:
            print(f"\n  {C.G}{C.BOLD}[{i}/{len(domains)}]{C.END}  {C.BOLD}{domain}{C.END}")
            hr()

        engine = ReconEngine(
            domain=domain,
            outdir=outdir,
            threads=args.threads,
            selected_tools=selected_tools,
            skipped_tools=skipped_tools,
            log_file=args.log_file,
        )
        stats = engine.run()
        all_stats[domain] = stats

    if len(domains) > 1:
        hr("=", C.G)
        log(f"{C.BOLD}All {len(domains)} domains completed!{C.END}", "ok")
        hr("=", C.G)



if __name__ == "__main__":
    main()
