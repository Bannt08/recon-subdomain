"""
recon.utils — Hàm tiện ích dùng chung.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Chứa:
    - which()            : Kiểm tra tool có tồn tại trong PATH
    - run_cmd()          : Thực thi command-line với timeout
    - clean_domain()     : Chuẩn hóa tên miền (bỏ scheme, path)
    - is_subdomain_of()  : Kiểm tra sub có thuộc domain không
    - write_lines()      : Ghi danh sách dòng ra file (sorted, unique)
    - read_lines()       : Đọc file thành set các dòng
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Union


# ─────────────────────────────────────────────
# TOOL AVAILABILITY
# ─────────────────────────────────────────────
def which(cmd: str) -> Optional[str]:
    """
    Kiểm tra xem một command-line tool có tồn tại trong PATH không.

    Args:
        cmd: Tên tool (vd: "subfinder", "httpx")

    Returns:
        Đường dẫn đầy đủ nếu tìm thấy, None nếu không
    """
    return shutil.which(cmd)



# ─────────────────────────────────────────────
# COMMAND EXECUTION
# ─────────────────────────────────────────────
def run_cmd(
    cmd: List[str],
    timeout: int = 600,
    cwd: str = None,
    env: dict = None,
) -> str:
    """
    Thực thi một command-line tool và trả về stdout + stderr.

    Args:
        cmd:     Danh sách arguments (vd: ["subfinder", "-d", "example.com"])
        timeout: Thời gian tối đa (giây) trước khi hủy
        cwd:     Thư mục làm việc
        env:     Biến môi trường bổ sung

    Returns:
        Chuỗi kết hợp stdout + stderr, hoặc chuỗi rỗng nếu timeout
    """
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=full_env,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        return str(e)


# ─────────────────────────────────────────────
# DOMAIN HELPERS
# ─────────────────────────────────────────────
def clean_domain(d: str) -> str:
    """
    Chuẩn hóa tên miền: bỏ scheme (http/https), bỏ path, lowercase.

    Ví dụ:
        "https://Example.Com/path" -> "example.com"
        "  HTTP://test.io  "       -> "test.io"
    """
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    return d


def is_subdomain_of(sub: str, domain: str) -> bool:
    """
    Kiểm tra xem `sub` có phải là subdomain (hoặc chính) của `domain` không.

    Args:
        sub:    Tên miền cần kiểm tra (vd: "api.example.com")
        domain: Tên miền gốc (vd: "example.com")

    Returns:
        True nếu sub == domain hoặc sub kết thúc bằng ".domain"
    """
    sub = sub.lower().strip()
    domain = domain.lower()
    return sub == domain or sub.endswith("." + domain)


# ─────────────────────────────────────────────
# FILE I/O
# ─────────────────────────────────────────────
def write_lines(path: Path, lines: Union[Set[str], List[str]]) -> None:
    """
    Ghi danh sách dòng ra file — sorted, unique, bỏ dòng trống.

    Tự động tạo thư mục cha nếu chưa tồn tại.

    Args:
        path:  Đường dẫn file output
        lines: Tập hợp hoặc danh sách các dòng cần ghi
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for line in sorted(set(lines)):
            if line.strip():
                f.write(line.strip() + "\n")


def read_lines(path: Path) -> Set[str]:
    """
    Đọc file thành set các dòng (bỏ dòng trống, strip whitespace).

    Args:
        path: Đường dẫn file cần đọc

    Returns:
        Set các dòng, hoặc set rỗng nếu file không tồn tại
    """
    if not path.exists():
        return set()
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}
