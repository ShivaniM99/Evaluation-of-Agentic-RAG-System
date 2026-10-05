"""Parse and resolve the synthesizer's inline citations: [Doc Filename | Section | Page X]."""
import re

_CITE = re.compile(r"\[([^\[\]|]+)\|([^\[\]|]+)\|\s*(?:p\.|pp\.|page|pages)?\s*([^\[\]]+?)\s*\]", re.I)
_ABSTAIN = re.compile(
    r"insufficient evidence|not found in the available documentation|no relevant information|"
    r"could not find|couldn't find|does not (?:contain|provide) (?:any )?information|not (?:covered|documented)",
    re.I)


def _norm_doc(s: str) -> str:
    s = s.strip().lower()
    return s[:-4] if s.endswith(".pdf") else s


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def parse_citations(answer: str) -> list[dict]:
    out = []
    for m in _CITE.finditer(answer or ""):
        out.append({"doc": m.group(1).strip(), "section": m.group(2).strip(),
                    "page": m.group(3).strip(), "span": m.span(), "raw": m.group(0)})
    return out


def parse_marker(marker: str) -> dict | None:
    """Parse one marker string, with or without surrounding brackets (judges often drop them)."""
    m = (marker or "").strip()
    if not m.startswith("["):
        m = f"[{m}]"
    found = parse_citations(m)
    return found[0] if found else None


def resolve_citation(cite: dict, chunks: list[dict]) -> dict | None:
    """Return the retrieved chunk a citation points at, or None if it is fabricated."""
    doc = _norm_doc(cite["doc"])
    sec = _norm(cite["section"])
    same_doc = [c for c in chunks if _norm_doc(str(c.get("doc", ""))) == doc]
    if not same_doc:
        return None
    for c in same_doc:
        if _norm(str(c.get("section", ""))) == sec:
            return c
    for c in same_doc:  # tolerate truncated / reworded section titles
        cs = _norm(str(c.get("section", "")))
        if sec and (sec in cs or cs in sec):
            return c
    return None


def is_abstention(answer: str, chunks: list[dict]) -> bool:
    """True if the answer itself declines to answer. Empty retrieval alone is not enough: an answer asserted from
    no evidence is a hallucination, not an abstention."""
    if not (answer or "").strip():
        return True
    return bool(_ABSTAIN.search(answer)) and not parse_citations(answer)


def page_matches(cite_page: str, chunk_page) -> bool:
    nums = lambda s: set(re.findall(r"\d+", str(s)))
    a, b = nums(cite_page), nums(chunk_page)
    return bool(a & b) if a and b else True  # unparseable page info: don't penalize
