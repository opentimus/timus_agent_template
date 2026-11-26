#!/usr/bin/env python3
"""运行期：加载索引 → 返回最相关的证据块（JSON，stdout）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag_index import search


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="检索离线知识库")
    parser.add_argument("query", help="查询问题")
    parser.add_argument("--index", type=Path, default=here.parent / "data" / "index.json")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if not args.index.is_file():
        print("索引不存在，请先运行 build_index.py：{}".format(args.index), file=sys.stderr)
        return 2
    index = json.loads(args.index.read_text(encoding="utf-8"))
    hits = search(index, args.query, max(1, args.top_k))
    print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
