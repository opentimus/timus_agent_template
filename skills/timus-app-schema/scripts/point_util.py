#!/usr/bin/env python3
"""数值口径工具：点数归一化、总点拆分、流水号派生（Python 3 标准库，零第三方依赖）。

数值口径是两包共用的业务规则，集中在此脚本，助手不再心算：
- normalize：正数、两位小数、四舍五入半进（Decimal ROUND_HALF_UP），拒绝负数 / 0 / 科学计数法；
- split：把总点 T 按权重拆到 N 条，每条两位小数且 Σ 严格等于 T，逐项校验 ≥ 0.01；
- next-pair：给出一条主号与尾号（末位 +1）的流水号对，两份共用同一毫秒前缀；
- next-batch：一条毫秒前缀 + 序号后缀的流水号批次（`-01`、`-02`…）。

输出一律 JSON（ensure_ascii=False）；校验失败打印中文原因到 stderr 并以 exit 2 退出。

用法：
  python3 point_util.py normalize 6.567
  python3 point_util.py split --total 3 --weight 1 --weight 2
  python3 point_util.py split --total 6 --weight 1 --weight 1 --weight 1   # 均分即权重全 1
  python3 point_util.py next-pair --prefix TIN
  python3 point_util.py next-batch --prefix TPAY --count 3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
MIN_POINT = Decimal("0.01")
# 点数原始输入的合法形态：正数，可带小数；不接受正负号、0 开头以外的特殊写法、科学计数法。
RAW_PATTERN = re.compile(r"\d+(?:\.\d+)?|\.\d+")


class PointError(Exception):
    """点数口径或拆分参数不合法。"""


def normalize(raw: str) -> dict[str, object]:
    """把任意合法正数输入归一化为两位小数口径。"""
    text = (raw or "").strip()
    if not text:
        raise PointError("点数不能为空")
    if not RAW_PATTERN.fullmatch(text):
        raise PointError("点数须为正数（可带小数，不接受符号或科学计数法）：{}".format(raw))
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise PointError("点数不是有效数值：{}".format(raw))
    cents = value.quantize(CENT, rounding=ROUND_HALF_UP)
    if cents <= 0:
        raise PointError("点数必须大于 0，收到：{}".format(raw))
    return {
        "raw": text,
        "value": float(cents),
        "text": "{:.2f}".format(cents),
        "cents": int((cents * 100).to_integral_value()),
    }


def split(total: str, weights: list[str]) -> dict[str, object]:
    """把总点 T 按权重拆到 N 条：两位小数、Σ = T、逐项 ≥ 0.01。"""
    head = normalize(total)
    total_cents = Decimal(head["cents"]) / 100
    if not weights:
        raise PointError("split 至少需要一个 --weight")

    parsed: list[int] = []
    for raw in weights:
        text = (raw or "").strip()
        if not re.fullmatch(r"\d+", text) or int(text) < 1:
            raise PointError("权重须为正整数，收到：{}".format(raw))
        parsed.append(int(text))

    weight_sum = sum(parsed)
    running = Decimal("0")
    items: list[dict[str, object]] = []
    for index, weight in enumerate(parsed, start=1):
        share = (total_cents * weight / weight_sum).quantize(CENT, rounding=ROUND_HALF_UP)
        running += share
        items.append({"index": index, "weight": weight, "cents": int((share * 100).to_integral_value())})

    # 尾差全部调整到最后一条，保证 Σ 严格等于 T
    tail_diff = int((total_cents * 100).to_integral_value()) - sum(int(i["cents"]) for i in items)
    items[-1]["cents"] = int(items[-1]["cents"]) + tail_diff

    for item in items:
        cents = int(item["cents"])
        if cents < 1:
            raise PointError(
                "第 {} 条拆分后为 {}，低于最小可写点数 0.01。"
                "请提高总估点、减少任务数或调整权重，本次不写入。".format(item["index"], "{:.2f}".format(cents / 100))
            )
        item["value"] = cents / 100
        item["text"] = "{:.2f}".format(cents / 100)

    total_out = sum(int(i["cents"]) for i in items)
    if total_out != int(head["cents"]):
        raise PointError("拆分合计 {} 与总估点 {} 不一致".format(total_out, head["cents"]))

    return {
        "total": float(total_cents),
        "total_text": head["text"],
        "count": len(items),
        "sum": "{:.2f}".format(total_out / 100),
        "items": items,
    }


def next_pair(prefix: str) -> dict[str, str]:
    """生成一对相邻流水号：主号 = 前缀 + 毫秒，尾号 = 主号数值 +1。"""
    name = (prefix or "").strip().upper()
    if not re.fullmatch(r"[A-Z]+", name):
        raise PointError("前缀须为纯字母（如 TIN / TPAY），收到：{}".format(prefix))
    stamp = int(time.time() * 1000)
    return {
        "prefix": name,
        "primary": "{}-{}".format(name, stamp),
        "secondary": "{}-{}".format(name, stamp + 1),
    }


def next_batch(prefix: str, count: int) -> dict[str, object]:
    """生成同前缀、同毫秒、序号递增的流水号批次（-01、-02…）。"""
    name = (prefix or "").strip().upper()
    if not re.fullmatch(r"[A-Z]+", name):
        raise PointError("前缀须为纯字母（如 TIN / TPAY），收到：{}".format(prefix))
    if count < 1:
        raise PointError("批次数至少为 1，收到：{}".format(count))
    stamp = int(time.time() * 1000)
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
    pair.add_argument("--prefix", required=True, help="前缀，如 TIN / TPAY")

    batch = sub.add_parser("next-batch", help="生成同毫秒的流水号批次")
    batch.add_argument("--prefix", required=True, help="前缀，如 TIN / TPAY")
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
        print("点数口径错误：{}".format(err), file=sys.stderr)
        sys.exit(2)

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
