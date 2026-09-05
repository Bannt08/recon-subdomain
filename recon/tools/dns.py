"""
recon.tools.dns — DNS Validation bằng dnsx.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
dnsx resolve từng subdomain và trả về:
    - A record (IPv4)
    - CNAME record
    - Lọc bỏ subdomain không resolve được

Cách dùng tối ưu:
    - Đọc all_subs.txt làm input
    - dnsx chạy song song, nhanh hơn nhiều so từng request
    - Output: chỉ giữ subdomain có ít nhất 1 DNS record hợp lệ
"""

from pathlib import Path
from typing import Set, Optional

from recon.utils  import run_cmd, which, write_lines, read_lines


def run_dnsx(
    subdomains: Set[str],
    outdir: Path,
    tool_filter: Optional[Set[str]] = None,
) -> Set[str]:
    """
    Validate DNS cho toàn bộ danh sách subdomain bằng dnsx.

    Chiến lược:
        1. Ghi subdomains ra file tạm
        2. Chạy: dnsx -l <file> -silent -resp -a -cname -threads 100
        3. Parse output: lấy domain column (trước khoảng trắng đầu tiên)
        4. Lưu kết quả vào raw/dnsx.txt và cập nhật subdomains/all_subs.txt

    Args:
        subdomains:  Set subdomain cần validate
        outdir:      Thư mục output (đã có các thư mục con raw/, subdomains/)
        tool_filter: Nếu set, chỉ chạy nếu "dnsx" có trong filter

    Returns:
        Set subdomain đã được DNS validate. Rỗng nếu dnsx không có sẵn
        (caller sẽ giữ nguyên danh sách gốc).
    """
    if tool_filter and "dnsx" not in tool_filter:
        return set()
    if not which("dnsx") or not subdomains:
        return set()

    # Ghi input ra file
    input_file  = outdir / "subdomains" / "all_subs.txt"
    output_file = outdir / "raw" / "dnsx.txt"

    # Đảm bảo file input tồn tại (đã được write_lines ghi trước đó)
    if not input_file.exists():
        write_lines(input_file, subdomains)

    cmd = [
        "dnsx",
        "-l",       str(input_file),
        "-silent",
        "-resp",           # In kèm DNS response value
        "-a",              # Resolve A record (IPv4)
        "-cname",          # Resolve CNAME
        "-threads", "100", # Tốc độ cao
        "-o",       str(output_file),
    ]

    run_cmd(cmd, timeout=300)

    # Parse output: mỗi dòng dạng "sub.domain.com [1.2.3.4]"
    valid: Set[str] = set()
    raw_lines = read_lines(output_file)
    for line in raw_lines:
        parts = line.split()
        if parts:
            valid.add(parts[0].lower().rstrip("."))

    if valid:
        # Cập nhật all_subs.txt với danh sách đã validated
        write_lines(outdir / "subdomains" / "all_subs_dns_valid.txt", valid)

    return valid
