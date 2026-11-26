#!/usr/bin/env python3
"""离线知识库：从源文档分块 + 章节加权 BM25 检索。纯标准库，无联网。"""
from __future__ import annotations

import math
import re
from pathlib import Path

K1 = 1.5
B = 0.75
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


def build(source: Path) -> list[dict]:
    """读 Markdown 分块，返回带词频的 chunk 列表。"""
    chunks: list[dict] = []
    chapter = section = pending = ""

    def flush() -> None:
        nonlocal pending
        text = pending.strip()
        pending = ""
        if not text:
            return
        body = tokenize(text)
        chunks.append({
            "chapter": chapter,
            "section": section,
            "text": text,
            "tf": _counts(body),
            "htf": _counts(tokenize((chapter + " " + section).strip())),
            "len": len(body),
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
        if not TOKEN_RE.search(line) and not line.startswith("【"):
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
    return chunks


def search(chunks: list[dict], query: str, top_k: int = 3) -> list[dict]:
    """检索：返回按相关度降序的证据块。"""
    terms = set(tokenize(query))
    if not terms or not chunks:
        return []
    n = len(chunks)
    avgdl = sum(c["len"] for c in chunks) / n
    df: dict[str, int] = {}
    for chunk in chunks:
        for token in chunk["tf"]:
            df[token] = df.get(token, 0) + 1

    scored: list[dict] = []
    for chunk in chunks:
        score = 0.0
        for term in terms:
            freq = chunk["tf"].get(term, 0)
            if not freq:
                continue
            doc_freq = df.get(term, 0)
            idf = math.log(1 + (n - doc_freq + 0.5) / (doc_freq + 0.5))
            score += idf * freq * (K1 + 1) / (freq + K1 * (1 - B + B * chunk["len"] / avgdl))
        if not score:
            continue
        score *= 1 + len(terms & chunk["htf"].keys()) / len(terms)
        scored.append({
            "score": round(score, 4),
            "chapter": chunk["chapter"],
            "section": chunk["section"],
            "text": chunk["text"],
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]
