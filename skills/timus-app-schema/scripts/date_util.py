#!/usr/bin/env python3
"""启动日期选项与任务起止日期计算（Python 3 标准库，零第三方依赖）。

供 task-create-form 技能使用：
- options：以基准日（默认今天）为第 1 天，列出后 10 个日期及星期；
- dates：按所选启动日期与「第几天开始 / 第几天结束」换算单条任务的起止日期；
- batch：一次换算多条任务的起止日期，减少脚本调用轮次；
- single：模式 B 自定义创建，校验所选完成日期并换算「今天 -> 完成日期」的 DateTime。

「第 N 天」按 1 基计数：第 1 天 = 启动日期当天，第 N 天 = 启动日期 + (N-1) 天。

日期输出字段说明：
- start_date / end_date：YYYY-MM-DD，向后兼容，用于展示与确认框；
- start_datetime / end_datetime：YYYY-MM-DD HH:mm:ss，Timus DateTime 字段写入专用。
  服务端要求完整时间格式，传纯日期或 T 分隔会报 could not be parsed at index 10。
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta

WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _parse_day(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def _fmt(day: date) -> str:
    return day.strftime("%Y-%m-%d")


def _fmt_datetime(day: date) -> str:
    """服务端 DateTime 字段要求的完整格式：yyyy-MM-dd HH:mm:ss。"""
    return "{} 00:00:00".format(_fmt(day))


def _label(day: date) -> str:
    return "{} {}".format(_fmt(day), WEEKDAY_CN[day.weekday()])


def _nth_day(base: date, n: int) -> date:
    if n < 1:
        raise ValueError("天数必须 >= 1，收到 {}".format(n))
    return base + timedelta(days=n - 1)


def _options(base: date, count: int) -> list[dict[str, object]]:
    return [
        {
            "day_index": index + 1,
            "date": _fmt(base + timedelta(days=index)),
            "weekday": WEEKDAY_CN[(base + timedelta(days=index)).weekday()],
            "label": _label(base + timedelta(days=index)),
        }
        for index in range(count)
    ]


def _range_payload(base: date, start_day: int, end_day: int) -> dict[str, object]:
    """换算单组第 N 天区间，返回展示字段与写入字段。"""
    start = _nth_day(base, start_day)
    end = _nth_day(base, end_day)
    if end < start:
        raise ValueError(
            "结束日期 {} 早于开始日期 {}，请核对第几天开始/结束".format(_fmt(end), _fmt(start))
        )
    return {
        "start_day": start_day,
        "end_day": end_day,
        "start_date": _fmt(start),
        "end_date": _fmt(end),
        "start_datetime": _fmt_datetime(start),
        "end_datetime": _fmt_datetime(end),
        "start_label": _label(start),
        "end_label": _label(end),
    }


def _parse_task(raw: str) -> tuple[str, int, int]:
    """解析 --task '任务名|开始天|结束天'，以竖线分隔，任务名不可含竖线。"""
    parts = raw.split("|")
    if len(parts) != 3 or not parts[0].strip():
        raise ValueError("--task 格式应为 '任务名|开始天|结束天'，收到：{}".format(raw))
    name = parts[0].strip()
    try:
        start_day = int(parts[1])
        end_day = int(parts[2])
    except ValueError:
        raise ValueError("--task 的开始天/结束天必须是整数，收到：{}".format(raw))
    return name, start_day, end_day


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("options", help="列出从基准日起的 N 个日期选项")
    opt.add_argument("--base", help="基准日期 YYYY-MM-DD，默认今天")
    opt.add_argument("--count", type=int, default=10, help="选项数量，默认 10")

    dts = sub.add_parser("dates", help="换算单条任务起止日期")
    dts.add_argument("--start-date", required=True, help="所选启动日期 YYYY-MM-DD")
    dts.add_argument("--start-day", type=int, required=True, help="S.第几天开始")
    dts.add_argument("--end-day", type=int, required=True, help="S.第几天结束")

    bat = sub.add_parser("batch", help="一次换算多条任务的起止日期")
    bat.add_argument("--start-date", required=True, help="所选启动日期 YYYY-MM-DD")
    bat.add_argument(
        "--task",
        action="append",
        default=[],
        metavar="任务名|开始天|结束天",
        help="一条任务，可重复传入；如 --task '环境部署|1|2'",
    )

    sgl = sub.add_parser("single", help="模式 B 自定义创建：校验完成日期并换算今日/完成日期的 DateTime")
    sgl.add_argument("--end-date", required=True, help="所选完成日期 YYYY-MM-DD")
    sgl.add_argument("--base", help="开始日期 YYYY-MM-DD，默认今天")

    args = parser.parse_args()
    try:
        if args.command == "options":
            base = _parse_day(args.base) if args.base else date.today()
            if args.count < 1:
                raise ValueError("选项数量必须 >= 1")
            payload: object = _options(base, args.count)
        elif args.command == "dates":
            base = _parse_day(args.start_date)
            payload = _range_payload(base, args.start_day, args.end_day)
        elif args.command == "batch":
            base = _parse_day(args.start_date)
            if not args.task:
                raise ValueError("batch 至少传入一条 --task")
            items: list[dict[str, object]] = []
            for raw in args.task:
                name, start_day, end_day = _parse_task(raw)
                item: dict[str, object] = {"task": name}
                item.update(_range_payload(base, start_day, end_day))
                items.append(item)
            payload = {"start_date": _fmt(base), "count": len(items), "items": items}
        elif args.command == "single":
            base = _parse_day(args.base) if args.base else date.today()
            end = _parse_day(args.end_date)
            if end < base:
                raise ValueError(
                    "完成日期 {} 早于开始日期 {}，请重新选择完成时间".format(_fmt(end), _fmt(base))
                )
            payload = {
                "start_date": _fmt(base),
                "start_datetime": _fmt_datetime(base),
                "start_label": _label(base),
                "end_date": _fmt(end),
                "end_datetime": _fmt_datetime(end),
                "end_label": _label(end),
            }
    except (ValueError, TypeError) as exc:
        parser.exit(2, "日期计算错误：{}\n".format(exc))

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
