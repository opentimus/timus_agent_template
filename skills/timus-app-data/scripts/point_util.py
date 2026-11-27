#!/usr/bin/env python3
"""数值口径：两位小数、按权重拆分（Σ 严格相等）与流水号。参数见 -h。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from errors import ToolError, emit_error

CENT = Decimal("0.01")
# 点数原始输入的合法形态：正数，可带小数；不接受正负号、科学计数法。
RAW_PATTERN = re.compile(r"\d+(?:\.\d+)?|\.\d+")


class PointError(ToolError):
    """点数口径或拆分参数不合法。"""


def _check_prefix(prefix: str) -> str:
    name = (prefix or "").strip().upper()
    if not re.fullmatch(r"[A-Z]+", name):
        raise PointError("前缀须为纯字母，收到：{}".format(prefix))
    return name


def _decimal_cents(raw: str) -> Decimal:
    text = (raw or "").strip()
    if not text:
        raise PointError("点数不能为空")
    if not RAW_PATTERN.fullmatch(text):
        raise PointError("点数须为正数（可带小数，不接受符号或科学计数法）：{}".format(raw))
    try:
        cents = Decimal(text).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise PointError("点数不是有效数值或超出可处理范围：{}".format(raw))
    if cents <= 0:
        raise PointError("点数必须大于 0，收到：{}".format(raw))
    return cents


def normalize(raw: str) -> dict[str, object]:
    cents = _decimal_cents(raw)
    return {"text": "{:.2f}".format(cents), "cents": int((cents * 100).to_integral_value())}


def split(total: str, weights: list[str]) -> dict[str, object]:
    """把总点 T 按权重拆到 N 条：两位小数、Σ = T、逐项 ≥ 0.01。"""
    total_cents = _decimal_cents(total)
    total_int = int((total_cents * 100).to_integral_value())
    if not weights:
        raise PointError("split 至少需要一个 --weight")

    parsed: list[int] = []
    for raw in weights:
        text = (raw or "").strip()
        if not re.fullmatch(r"\d+", text) or int(text) < 1:
            raise PointError("权重须为正整数，收到：{}".format(raw))
        parsed.append(int(text))

    weight_sum = sum(parsed)
    items: list[dict[str, object]] = []
    for index, weight in enumerate(parsed, start=1):
        share = (total_cents * weight / weight_sum).quantize(CENT, rounding=ROUND_HALF_UP)
        items.append({"index": index, "weight": weight, "cents": int((share * 100).to_integral_value())})

    tail_diff = total_int - sum(int(i["cents"]) for i in items)
    items[-1]["cents"] = int(items[-1]["cents"]) + tail_diff

    for item in items:
        cents = int(item["cents"])
        if cents < 1:
            raise PointError(
                "第 {} 条拆分后为 {}，低于最小可写点数 0.01。"
                "请提高总估点、减少任务数或调整权重，本次不写入。".format(item["index"], "{:.2f}".format(cents / 100))
            )
        item["text"] = "{:.2f}".format(cents / 100)

    return {"total": "{:.2f}".format(total_cents), "items": items}


_last_stamp = 0


def _stamp(prefix: str) -> tuple[str, int]:
    """毫秒 + 进程内单调递增，避免同毫秒重复流水号。"""
    global _last_stamp
    name = _check_prefix(prefix)
    _last_stamp = max(int(time.time() * 1000), _last_stamp + 1)
    return name, _last_stamp


def next_pair(prefix: str) -> dict[str, str]:
    """生成一对相邻流水号：主号 = 前缀 + 毫秒，尾号 = 主号数值 +1。"""
    name, stamp = _stamp(prefix)
    return {
        "prefix": name,
        "primary": "{}-{}".format(name, stamp),
        "secondary": "{}-{}".format(name, stamp + 1),
    }


def next_batch(prefix: str, count: int) -> dict[str, object]:
    """生成同前缀、同毫秒、序号递增的流水号批次（-01、-02…）。"""
    name, stamp = _stamp(prefix)
    if count < 1:
        raise PointError("批次数至少为 1，收到：{}".format(count))
    return {
        "prefix": name,
        "stamp": str(stamp),
        "count": count,
        "numbers": ["{}-{}-{:02d}".format(name, stamp, index) for index in range(1, count + 1)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="点数口径与流水号派生工具")
    sub = parser.add_subparsers(dest="command", required=True)

    nor = sub.add_parser("normalize", help="归一化为两位小数口径")
    nor.add_argument("raw", help="原始点数，如 6.567")

    spl = sub.add_parser("split", help="按权重拆分总点为多条（两位小数，Σ = 总点）")
    spl.add_argument("--total", required=True, help="本批总点 T")
    spl.add_argument("--weight", action="append", default=[], metavar="W", help="各条权重（正整数），可重复；均分即每条权重 1")

    pair = sub.add_parser("next-pair", help="生成一对相邻流水号")
    pair.add_argument("--prefix", required=True, help="前缀（纯字母）")

    batch = sub.add_parser("next-batch", help="生成同毫秒的流水号批次")
    batch.add_argument("--prefix", required=True, help="前缀（纯字母）")
    batch.add_argument("--count", type=int, required=True, help="条数")

    args = parser.parse_args()
    try:
        if args.command == "normalize":
            payload: object = normalize(args.raw)
        elif args.command == "split":
            payload = split(args.total, list(args.weight))
        elif args.command == "next-pair":
            payload = next_pair(args.prefix)
        else:
            payload = next_batch(args.prefix, args.count)
    except PointError as err:
        emit_error(err, "点数口径错误")
        sys.exit(2)

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
