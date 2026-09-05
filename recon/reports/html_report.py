"""
recon.reports.html_report — Tạo báo cáo HTML (Dark theme).
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hiển thị đầy đủ:
    - Summary stats
    - Subdomains (raw + DNS validated)
    - Emails (từ theHarvester)
    - Live Hosts (từ httpx)
    - URLs collected
"""

from datetime import datetime
from pathlib import Path
from typing import List, Set

from recon.config import VERSION


def _esc(s: str) -> str:
    """HTML escape cơ bản."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def generate_html_report(
    outdir: Path,
    domain: str,
    stats: dict,
    live: List[str],
    subdomains: List[str],
    urls: List[str],
    emails: List[str],
) -> Path:
    """
    Tạo báo cáo HTML dark-theme tĩnh, đầy đủ dữ liệu.

    Args:
        outdir:     Thư mục output gốc cho domain
        domain:     Tên miền mục tiêu
        stats:      Dict thống kê từ engine
        live:       Dòng output text từ httpx
        subdomains: Danh sách subdomain đã validate
        urls:       Danh sách URL thu thập được
        emails:     Danh sách email từ theHarvester
    """
    report = outdir / "REPORT.html"
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    css = """
        :root {
            --bg:      #0d1117;
            --bg2:     #161b22;
            --bg3:     #21262d;
            --border:  #30363d;
            --text:    #e6edf3;
            --muted:   #8b949e;
            --accent:  #58a6ff;
            --green:   #3fb950;
            --yellow:  #d29922;
            --red:     #f85149;
            --orange:  #db6d28;
            --purple:  #bc8cff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, 'Segoe UI', 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        /* ── Sidebar nav ── */
        .sidebar {
            position: fixed; top: 0; left: 0;
            width: 220px; height: 100vh;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            padding: 1.5rem 1rem;
            overflow-y: auto;
            z-index: 100;
        }
        .sidebar h2 {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: .1em;
            color: var(--muted);
            margin-bottom: 1rem;
            border: none;
        }
        .sidebar a {
            display: block;
            padding: 6px 10px;
            border-radius: 6px;
            color: var(--muted);
            text-decoration: none;
            font-size: 0.85rem;
            margin-bottom: 2px;
            transition: background .15s, color .15s;
        }
        .sidebar a:hover { background: var(--bg3); color: var(--text); }
        .sidebar .badge {
            float: right;
            background: var(--bg3);
            border-radius: 10px;
            padding: 1px 7px;
            font-size: 0.72rem;
            color: var(--accent);
        }
        /* ── Main content ── */
        .main {
            margin-left: 220px;
            padding: 2rem 2.5rem;
            max-width: 1200px;
        }
        header { margin-bottom: 2rem; }
        header h1 {
            font-size: 1.6rem;
            color: var(--accent);
            margin-bottom: 0.2rem;
        }
        header .meta { color: var(--muted); font-size: 0.82rem; }
        /* ── Cards stat ── */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2.5rem;
        }
        .stat-card {
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        .stat-card .num {
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
            line-height: 1;
        }
        .stat-card .label {
            font-size: 0.75rem;
            color: var(--muted);
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: .05em;
        }
        /* ── Sections ── */
        section { margin-bottom: 3rem; scroll-margin-top: 1rem; }
        section h2 {
            font-size: 1.1rem;
            color: var(--text);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        section h2 .cnt {
            background: var(--bg3);
            border-radius: 10px;
            padding: 1px 8px;
            font-size: 0.75rem;
            color: var(--accent);
            font-weight: 400;
        }
        /* ── Tables ── */
        .tbl-wrap {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        table th {
            background: var(--bg3);
            color: var(--muted);
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: .05em;
            border-bottom: 1px solid var(--border);
        }
        table td {
            padding: 7px 12px;
            border-bottom: 1px solid var(--border);
            word-break: break-all;
        }
        table tr:last-child td { border-bottom: none; }
        table tr:hover td { background: var(--bg3); }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
        .empty { color: var(--muted); font-style: italic; padding: 12px; }
        .tag {
            display: inline-block;
            padding: 1px 7px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .tag-200 { background: #1a3a1a; color: var(--green); }
        .tag-301, .tag-302, .tag-307, .tag-308 { background: #2a2a0a; color: var(--yellow); }
        .tag-403, .tag-401 { background: #2a1a0a; color: var(--orange); }
        .tag-500, .tag-503 { background: #3a0a0a; color: var(--red); }
        .note { font-size: 0.78rem; color: var(--muted); margin-bottom: 0.8rem; }
        footer {
            margin-top: 4rem;
            padding: 1.5rem 0;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.75rem;
            text-align: center;
        }
        @media (max-width: 768px) {
            .sidebar { display: none; }
            .main { margin-left: 0; padding: 1rem; }
        }
    """

    # ── Helper: build table rows ──
    def _sub_rows(items: List[str]) -> str:
        if not items:
            return "<p class='empty'>No subdomains found.</p>"
        rows = "".join(
            f"<tr><td>{i+1}</td><td>{_esc(s)}</td></tr>"
            for i, s in enumerate(items)
        )
        return (
            "<div class='tbl-wrap'><table>"
            "<tr><th>#</th><th>Subdomain</th></tr>"
            f"{rows}</table></div>"
        )

    def _live_rows(items: List[str]) -> str:
        if not items:
            return "<p class='empty'>No live hosts found.</p>"
        rows = ""
        for i, line in enumerate(items):
            parts = line.split()
            url   = _esc(parts[0]) if parts else ""
            code  = parts[1].strip("[]") if len(parts) > 1 else ""
            rest  = _esc(" ".join(parts[2:])) if len(parts) > 2 else ""
            tag   = f"<span class='tag tag-{code}'>{code}</span>" if code else ""
            link  = f"<a href='{parts[0]}' target='_blank'>{url}</a>" if url else ""
            rows += f"<tr><td>{i+1}</td><td>{link}</td><td>{tag}</td><td>{rest}</td></tr>"
        return (
            "<div class='tbl-wrap'><table>"
            "<tr><th>#</th><th>URL</th><th>Status</th><th>Info</th></tr>"
            f"{rows}</table></div>"
        )

    def _email_rows(items: List[str]) -> str:
        if not items:
            return "<p class='empty'>No emails found.</p>"
        rows = "".join(
            f"<tr><td>{i+1}</td><td>{_esc(e)}</td></tr>"
            for i, e in enumerate(items)
        )
        return (
            "<div class='tbl-wrap'><table>"
            "<tr><th>#</th><th>Email</th></tr>"
            f"{rows}</table></div>"
        )

    def _url_rows(items: List[str]) -> str:
        if not items:
            return "<p class='empty'>No URLs collected.</p>"
        rows = "".join(
            f"<tr><td>{i+1}</td><td><a href='{_esc(u)}' target='_blank'>{_esc(u)}</a></td></tr>"
            for i, u in enumerate(items[:500])
        )
        note = ""
        if len(items) > 500:
            note = f"<p class='note'>Showing first 500 of {len(items)} URLs. Full list: <code>urls/all_urls.txt</code></p>"
        return (
            f"{note}<div class='tbl-wrap'><table>"
            "<tr><th>#</th><th>URL</th></tr>"
            f"{rows}</table></div>"
        )

    # ── Counts ──
    n_subs   = stats.get("subdomains", 0)
    n_dns    = stats.get("subdomains_dns_valid", 0)
    n_live   = stats.get("live", 0)
    n_urls   = stats.get("urls", 0)
    n_emails = stats.get("emails", 0)
    elapsed  = stats.get("elapsed", 0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recon Report — {_esc(domain)}</title>
    <style>{css}</style>
</head>
<body>

<!-- Sidebar -->
<nav class="sidebar">
    <h2>Navigation</h2>
    <a href="#summary">📊 Summary</a>
    <a href="#subdomains">🔍 Subdomains <span class="badge">{n_dns or n_subs}</span></a>
    <a href="#emails">📧 Emails <span class="badge">{n_emails}</span></a>
    <a href="#live">🟢 Live Hosts <span class="badge">{n_live}</span></a>
    <a href="#urls">🔗 URLs <span class="badge">{n_urls}</span></a>
</nav>

<!-- Main -->
<div class="main">
    <header>
        <h1>🔍 Recon Report — {_esc(domain)}</h1>
        <p class="meta">
            Generated: {now} &nbsp;|&nbsp;
            Duration: {elapsed}s &nbsp;|&nbsp;
            bannt recon v{VERSION}
        </p>
    </header>

    <!-- Summary Cards -->
    <section id="summary">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="num">{n_subs}</div>
                <div class="label">Subdomains Raw</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_dns}</div>
                <div class="label">DNS Validated</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_emails}</div>
                <div class="label">Emails Found</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_live}</div>
                <div class="label">Live Hosts</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_urls}</div>
                <div class="label">URLs Collected</div>
            </div>
            <div class="stat-card">
                <div class="num">{elapsed}s</div>
                <div class="label">Duration</div>
            </div>
        </div>
    </section>

    <!-- Subdomains -->
    <section id="subdomains">
        <h2>🔍 Subdomains (DNS Validated) <span class="cnt">{n_dns or n_subs}</span></h2>
        <p class="note">Đã qua DNS validation với dnsx — chỉ hiển thị subdomain có A/CNAME record hợp lệ.</p>
        {_sub_rows(subdomains)}
    </section>

    <!-- Emails -->
    <section id="emails">
        <h2>📧 Emails Found <span class="cnt">{n_emails}</span></h2>
        <p class="note">Thu thập bởi theHarvester từ Google, Bing, crtsh, dnsdumpster, hackertarget, urlscan.</p>
        {_email_rows(emails)}
    </section>

    <!-- Live Hosts -->
    <section id="live">
        <h2>🟢 Live Hosts <span class="cnt">{n_live}</span></h2>
        <p class="note">Probe bằng httpx — hiển thị status code, title, và technology stack.</p>
        {_live_rows(live)}
    </section>

    <!-- URLs -->
    <section id="urls">
        <h2>🔗 URLs Collected <span class="cnt">{n_urls}</span></h2>
        <p class="note">Thu thập bởi gau, waybackurls, katana. Full list: <code>urls/all_urls.txt</code></p>
        {_url_rows(urls)}
    </section>

    <footer>
        Generated by <strong>bannt recon v{VERSION}</strong> &mdash;
        {_esc(domain)} &mdash; {now} &mdash;
        For authorized security testing only.
    </footer>
</div>

</body>
</html>"""

    report.write_text(html, encoding="utf-8")
    return report
