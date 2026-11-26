#!/usr/bin/env python3
"""离线知识库：构建索引 + 章节加权 BM25 检索。纯标准库，无联网。"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

K1 = 1.5
B = 0.75
HEADING_WEIGHT = 1.0
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z]+|\d+(?:\.\d+)?")
END_RE = re.compile(r"[。！？；。）\">]$")


def tokenize(text: str) -> list[str]:
    """中文按单字 + 相邻二元组切分；英文 / 数字按词切分。"""
    out: list[str] = []
    for match in TOKEN_RE.finditer(text.lower()):
        part = match.group()
        if "\u4e00" <= part[0] <= "\u9fff":
            out.extend(part)
            out.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            out.append(part)
    return out


def _counts(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def build(source: Path) -> dict:
    """一次性分块并建索引。"""
    chunks: list[dict] = []
    chapter = section = pending = ""

    def flush() -> None:
        nonlocal pending
        text = pending.strip()
        pending = ""
        if not text:
            return
        body = tokenize(text)
        heading = tokenize((chapter + " " + section).strip())
        chunks.append({
            "chapter": chapter,
            "section": section,
            "text": text,
            "tf": _counts(body),
            "htf": _counts(heading),
            "len": len(body),
            "hlen": len(heading),
        })

    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            flush()
            if line.startswith("## "):
                chapter = re.sub(r"\s+", "", line[3:])
                section = ""
            continue
        if not line or line.startswith("![") or re.match(r"^（[^）]*）$", line) or line.startswith(("责任编辑", "责任校对")):
            flush()
            continue
        if len(line) < 6 and not line.startswith("【"):
            continue
        if line.startswith("【") and "】" in line:
            flush()
            section = line[1:line.index("】")]
            pending = line
            continue
        if pending and (END_RE.search(pending) or len(pending) > 800):
            flush()
        pending = pending + line if pending else line
    flush()

    df: dict[str, int] = {}
    for chunk in chunks:
        for token in chunk["tf"]:
            df[token] = df.get(token, 0) + 1
    n = len(chunks)
    return {
        "version": 1,
        "source": source.name,
        "config": {"k1": K1, "b": B, "heading_weight": HEADING_WEIGHT},
        "n": n,
        "avgdl": sum(c["len"] for c in chunks) / n if n else 0.0,
        "df": df,
        "chunks": chunks,
    }


def _bm25(tf: dict[str, int], length: float, df: dict[str, int], n: int,
          avgdl: float, terms: set[str], k1: float, b: float) -> float:
    if not length or not avgdl:
        return 0.0
    score = 0.0
    for term in terms:
        freq = tf.get(term, 0)
        if not freq:
            continue
        doc_freq = df.get(term, 0)
        idf = math.log(1 + (n - doc_freq + 0.5) / (doc_freq + 0.5))
        score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * length / avgdl))
    return score


def search(index: dict, query: str, top_k: int = 3) -> list[dict]:
    """运行期检索：返回按相关度降序的证据块。"""
    terms = set(tokenize(query))
    if not terms or not index["chunks"]:
        return []
    cfg = index["config"]
    k1, b, hw = cfg["k1"], cfg["b"], cfg["heading_weight"]
    n, avgdl = index["n"], index["avgdl"]
    scored = []
    for rank, chunk in enumerate(index["chunks"]):
        body = _bm25(chunk["tf"], chunk["len"], index["df"], n, avgdl, terms, k1, b)
        if not body:
            continue
        overlap = len(terms & chunk["htf"].keys()) / len(terms)
        score = body * (1 + hw * overlap)
        if score > 0:
            scored.append({
                "rank": rank,
                "score": round(score, 4),
                "chapter": chunk["chapter"],
                "section": chunk["section"],
                "text": chunk["text"],
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]
