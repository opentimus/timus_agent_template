"""统一 CLI 错误出口：stdout 仅输出 JSON，错误一律走 stderr + exit 2。"""
from __future__ import annotations

import sys


class ToolError(Exception):
    """脚本可预期的用户输入错误。"""


class DateError(ToolError, ValueError):
    """日期换算错误；保留 ValueError 语义以兼容既有调用方。"""


def emit_error(err: BaseException, label: str = "参数错误") -> None:
    print("{}：{}".format(label, err), file=sys.stderr)
