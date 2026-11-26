#!/usr/bin/env python3
"""运行期：读源文档 → 检索 → 返回最相关的证据块（JSON，stdout）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag_index import build, search

DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "references" / "武汉概览.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="检索离线知识库")
    parser.add_argument("query", help="查询问题")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="源文档路径")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if not args.source.is_file():
        print("源文档不存在：{}".format(args.source), file=sys.stderr)
        return 2
    hits = search(build(args.source), args.query, max(1, args.top_k))
    print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
