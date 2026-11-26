#!/usr/bin/env python3
"""构建期：读 Markdown → 分块 → 写 JSON 索引。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag_index import build


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="构建离线知识库索引")
    parser.add_argument("--source", type=Path, default=here.parent / "references" / "武汉概览.md")
    parser.add_argument("--output", type=Path, default=here.parent / "data" / "index.json")
    args = parser.parse_args()
    if not args.source.is_file():
        print("源文档不存在：{}".format(args.source), file=sys.stderr)
        return 2
    index = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("索引已写入 {}（{} 块）".format(args.output, index["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
