"""Heading-boundary chunker.

Splits a markdown body into chunks, one per H2 section. Anything before
the first H2 (introduction / context) becomes a chunk named "_intro".
Within a section, we keep up to ~1000 chars together to stay under the
MiniLM context budget; longer sections are split on paragraph boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
MAX_CHARS = 1000


@dataclass
class Chunk:
    section_path: str
    body: str


def chunk_body(body: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    matches = list(H2_RE.finditer(body))

    # Anything before the first H2 = intro
    first_pos = matches[0].start() if matches else len(body)
    intro = body[:first_pos].strip()
    # Strip the H1 if it's the first line.
    intro_lines = [ln for ln in intro.splitlines() if not ln.startswith("# ")]
    intro = "\n".join(intro_lines).strip()
    if intro:
        chunks.extend(_split_paragraphs("_intro", intro))

    # Each H2 section through the next H2 (or EOF)
    for i, m in enumerate(matches):
        section_title = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        if not section_body:
            continue
        chunks.extend(_split_paragraphs(section_title, section_body))

    return chunks


def _split_paragraphs(section_title: str, text: str) -> list[Chunk]:
    if len(text) <= MAX_CHARS:
        return [Chunk(section_path=section_title, body=text)]
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[Chunk] = []
    buf: list[str] = []
    cur_len = 0
    for p in paras:
        if cur_len + len(p) > MAX_CHARS and buf:
            out.append(Chunk(section_path=section_title, body="\n\n".join(buf)))
            buf = [p]
            cur_len = len(p)
        else:
            buf.append(p)
            cur_len += len(p) + 2
    if buf:
        out.append(Chunk(section_path=section_title, body="\n\n".join(buf)))
    return out
