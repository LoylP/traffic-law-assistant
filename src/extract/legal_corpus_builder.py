#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traffic-law corpus builder (TXT OCR)
- Parse: Chapter -> Article -> Clause -> Point
- Emit: law_corpus.jsonl (one line = one clause/point/article unit)
- Emit: amendment_map.json (mapping target unit -> list of amendments)

Heuristic Amendment Extraction (important):
- Anchor scope at amending-ARTICLE title:
  e.g. "Điều 52. Sửa đổi... Nghị định số 100/2019/NĐ-CP..."
  => all amendments inside that ARTICLE block are assumed targeting ND100
  even if subsequent sentences don't repeat "NĐ100".

Designed for your 3 decrees:
- ND100/2019/NĐ-CP
- ND123/2021/NĐ-CP
- ND168/2024/NĐ-CP (effective 01/01/2025)
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =========================
# CONFIG
# =========================
# Each decree can have multiple files (e.g., ND100 split into ND100.txt and ND100_02.txt)
# Format: (decree_id, [list_of_files])
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

INPUTS = [
    ("100", [str(DATA_DIR / "ND100.txt"), str(DATA_DIR / "ND100_02.txt")]),  # ND100 split into 2 files
    ("123", [str(DATA_DIR / "ND123.txt")]),
    ("168", [str(DATA_DIR / "ND168.txt")]),
]

OUT_DIR = Path("cleaned_txt")
OUT_DIR.mkdir(exist_ok=True)

OUT_JSONL = OUT_DIR / "law_corpus.jsonl"
OUT_AMEND_MAP = OUT_DIR / "amendment_map.json"

# Only keep amendment targets inside this set (avoid ND155/2016, ND117/2020, etc.)
ALLOWED_TARGETS = {"100", "123", "168"}

# If OCR meta doesn't capture effective date for ND168, force it (per your requirement)
FORCE_EFFECTIVE_FROM = {
    "168": "2025-01-01",  # ND168/2024 effective from 01/01/2025
}

# =========================
# OCR tolerant patterns
# =========================
P_PAGE = re.compile(r"^===\s*PAGE\s+(\d+)\s*===$", re.M)

# Chapter: "Chương I" / "CHƯƠNG II"
P_CHAPTER = re.compile(r"(?mi)^\s*CHƯƠNG\s+([IVXLCDM]+)\s*(.*)$")

# Article: "Điều 1." variations due to OCR
P_ART = re.compile(r"(?m)^(Điều|Di[eé]u|D[ií]eu|Dleu|Dieu)\s+(\d+)\.?\s*(.*)$")

# Clause: "1. ...."
P_CLA = re.compile(r"(?m)^\s*(\d+)\.\s+(.*)$")

# Point: "a) ...." (đ included)
P_PNT = re.compile(r"(?m)^\s*([a-zđ])\)\s+(.*)$", re.I)

# Decree number in header: "Số: 168/2024/NĐ-CP" (OCR tolerant: ND-CP / NĐ CP / spaces)
P_DECREE_NO = re.compile(r"(?i)\bS[ốo]\s*:\s*([0-9]{1,4}/[0-9]{4}/(?:NĐ|ND)\s*-\s*CP)\b")

# Issue date heuristic: "ngày 28 tháng 12 năm 2021"
P_ISSUE_DATE = re.compile(r"(?i)\bngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})\b")

# Effective date heuristic: "hiệu lực ... từ 01/01/2025"
P_EFFECTIVE = re.compile(r"(?i)hiệu\s*lực[^0-9]{0,80}(\d{1,2})[/-](\d{1,2})[/-](\d{4})")

# =========================
# Amendment patterns
# =========================
P_ACTION = re.compile(r"(?i)\b(sửa\s*đổi|bổ\s*sung|bãi\s*bỏ|thay\s*thế)\b")

# Target decree mention: "Nghị định số 100/2019/NĐ-CP" (OCR tolerant, including line breaks)
P_TARGET_DECREE = re.compile(
    r"(?i)Nghị\s+định\s+(?:số\s+)?(\d{1,4})/(\d{4})/(?:NĐ|ND)\s*-?\s*CP",
    re.MULTILINE | re.DOTALL
)

# Target references:
P_REF_POINT_CLA_ART = re.compile(r"(?i)điểm\s+([a-zđ])\s+khoản\s+([0-9]+[a-z]?)\s+Điều\s+(\d+)")
P_REF_CLA_ART = re.compile(r"(?i)khoản\s+([0-9]+[a-z]?)\s+Điều\s+(\d+)")
P_REF_ART = re.compile(r"(?i)\bĐiều\s+(\d+)\b")

# Multi-list helpers:
P_MULTI_KHOAN = re.compile(r"(?i)khoản\s+((?:\d+[a-z]?\s*(?:,|;|và)?\s*)+)")
P_MULTI_DIEM = re.compile(r"(?i)điểm\s+((?:[a-zđ]\s*(?:,|;|và)?\s*)+)")
P_AT_END_ART = re.compile(r"(?i)\bĐiều\s+(\d+)\b")

# =========================
# Normalization / OCR cleanup
# =========================
OCR_REPLACEMENTS = {
    # Điều
    "Diéu": "Điều", "Dléu": "Điều", "Dìêu": "Điều", "Dleu": "Điều", "Dieu": "Điều",
    # Nghị định / NĐ-CP OCR variants
    "Nghi định": "Nghị định",
    "nghi định": "nghị định",
    "sô ": "số ",  # OCR typo
    "ND-CP": "NĐ-CP",
    "NĐ CP": "NĐ-CP",
    "ND CP": "NĐ-CP",
    "NÐ-CP": "NĐ-CP",
    # phổ biến
    "bd sung": "bổ sung",
    "bô sung": "bổ sung",
    "bỗ sung": "bổ sung",
    "bồ sung": "bổ sung",
    "sửa đỗi": "sửa đổi",
    "sửa doi": "sửa đổi",
    "sưa đổi": "sửa đổi",
    "Sưa đổi": "Sửa đổi",
    "thang": "tháng",
    "đôi với": "đối với",
    "dôi với": "đối với",
    "thâm quyền": "thẩm quyền",
    "thâm quyên": "thẩm quyền",
    "xư phạt": "xử phạt",
    "xư ly": "xử lý",
    "điệm": "điểm",
    "diem": "điểm",
    "Hinh thức": "Hình thức",
    "chuc danh": "chức danh",
    "chức danhj": "chức danh",
}

def normalize(text: str) -> str:
    text = text.replace("\x0c", " ")
    for a, b in OCR_REPLACEMENTS.items():
        text = text.replace(a, b)
    text = text.replace("“", "\"").replace("”", "\"").replace("’", "'").replace("–", "-").replace("—", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_pages(full: str) -> List[Tuple[int, str]]:
    """
    If markers exist: return [(page_no, page_text), ...]
    If NOT exist: fallback to [(1, full)]
    """
    pages: List[Tuple[int, str]] = []
    cur: List[str] = []
    cur_no: Optional[int] = None
    saw_marker = False

    for line in full.splitlines():
        m = re.match(r"===\s*PAGE\s+(\d+)\s*===", line.strip())
        if m:
            saw_marker = True
            if cur_no is not None:
                pages.append((cur_no, "\n".join(cur).strip()))
            cur_no = int(m.group(1))
            cur = []
        else:
            cur.append(line)

    if saw_marker:
        if cur_no is not None:
            pages.append((cur_no, "\n".join(cur).strip()))
        return pages

    return [(1, full.strip())]

def roman_to_int(roman: str) -> Optional[int]:
    roman = roman.strip().upper()
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(roman):
        v = vals.get(ch)
        if not v:
            return None
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total

def load_multiple_files(file_list: List[str]) -> str:
    """
    Load multiple files, normalize, and merge their content.
    Used when a single decree is split across multiple files (e.g., ND100.txt + ND100_02.txt).
    """
    contents = []
    for fname in file_list:
        p = Path(fname)
        content = p.read_text(encoding="utf-8", errors="ignore")
        contents.append(content)
    
    merged = "\n".join(contents)
    return normalize(merged)

def detect_doc_meta(raw: str, decree_id: str) -> Dict[str, Optional[str]]:
    meta: Dict[str, Optional[str]] = {
        "decree_no": None,
        "issue_date": None,       # YYYY-MM-DD
        "effective_from": None,   # YYYY-MM-DD
    }
    m = P_DECREE_NO.search(raw[:8000])
    if m:
        meta["decree_no"] = re.sub(r"\s+", "", m.group(1)).replace("ND-CP", "NĐ-CP")

    md = P_ISSUE_DATE.search(raw[:8000])
    if md:
        d, mo, y = md.group(1), md.group(2), md.group(3)
        meta["issue_date"] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    me = P_EFFECTIVE.search(raw)
    if me:
        d, mo, y = me.group(1), me.group(2), me.group(3)
        meta["effective_from"] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    if decree_id in FORCE_EFFECTIVE_FROM:
        meta["effective_from"] = FORCE_EFFECTIVE_FROM[decree_id]

    # Fallback: if no effective_from found, use issue_date
    if not meta["effective_from"] and meta["issue_date"]:
        meta["effective_from"] = meta["issue_date"]

    return meta

def decree_base_id(decree_no: Optional[str], decree_id_fallback: str) -> str:
    """
    Convert "168/2024/NĐ-CP" (or OCR variants) -> "ND168_2024"
    else fallback "ND168"
    """
    if decree_no:
        decree_no = decree_no.replace("ND-CP", "NĐ-CP")
        m = re.match(r"^\s*(\d{1,4})/(\d{4})/(?:NĐ|ND)-CP\s*$", decree_no, flags=re.I)
        if m:
            return f"ND{int(m.group(1))}_{m.group(2)}"
    return f"ND{decree_id_fallback}"

def make_citation_id(base: str, article: Optional[int], clause: Optional[str], point: Optional[str]) -> str:
    parts = [base]
    if article is not None:
        parts.append(f"D{article}")
    if clause is not None:
        parts.append(f"K{clause}")
    if point is not None:
        parts.append(f"P{point.lower()}")
    return "-".join(parts)

# =========================
# Amendment extraction (scope-aware)
# =========================
@dataclass
class AmendRec:
    amending_decree_id: str
    amending_decree_no: Optional[str]
    amending_issue_date: Optional[str]
    amending_effective_from: Optional[str]
    amending_article: Optional[int]
    action: str
    target_decree_id: str
    target_decree_base: str
    target_article: Optional[int]
    target_clause: Optional[str]
    target_point: Optional[str]
    note: str

def _snip(s: str, maxlen: int = 420) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen]

def _parse_multi_numbers(s: str) -> List[str]:
    s = s.strip()
    s = re.sub(r"(?i)\bvà\b", ",", s)
    s = s.replace(";", ",")
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        m = re.match(r"^(\d+[a-z]?)$", tok, flags=re.I)
        if m:
            out.append(m.group(1).lower())
    return sorted(set(out), key=lambda x: (int(re.match(r"\d+", x).group()), x))

def _parse_multi_points(s: str) -> List[str]:
    s = s.strip()
    s = re.sub(r"(?i)\bvà\b", ",", s)
    s = s.replace(";", ",")
    out = []
    for tok in s.split(","):
        tok = tok.strip().lower()
        if tok and re.match(r"^[a-zđ]$", tok):
            out.append(tok)
    return sorted(set(out))

def extract_amendments(amending_decree_id: str, amending_files: List[str]) -> Dict[str, List[dict]]:
    """
    Returns amendment_map:
      key = target_citation_id like "ND100_2019-D28-K6-Pd"
      value = list[AmendRec as dict]
    
    amending_files: list of file paths to load and merge
    """
    raw0 = load_multiple_files(amending_files)
    meta = detect_doc_meta(raw0, amending_decree_id)

    pages = split_pages(raw0)
    doc = "\n".join(ptxt for _, ptxt in pages).strip()
    if not doc:
        doc = raw0

    # Split into amending-article blocks
    art_spans: List[Tuple[int, int, int]] = []  # (start, end, article_no)
    arts = [(m.start(), int(m.group(2))) for m in P_ART.finditer(doc)]
    arts.sort(key=lambda x: x[0])
    if not arts:
        art_spans = [(0, len(doc), -1)]
    else:
        for i in range(len(arts)):
            s, a_no = arts[i]
            e = arts[i + 1][0] if i + 1 < len(arts) else len(doc)
            art_spans.append((s, e, a_no))

    amap: Dict[str, List[dict]] = {}

    def resolve_target_from_text(text: str) -> Optional[Tuple[str, str]]:
        """
        Find target decree mention. Return (target_decree_id, target_base_id).
        Only allow within ALLOWED_TARGETS.
        """
        m = P_TARGET_DECREE.search(text)
        if not m:
            return None
        num = str(int(m.group(1)))
        year = m.group(2)
        if num not in ALLOWED_TARGETS:
            return None
        return (num, f"ND{num}_{year}")

    for s, e, am_article_no in art_spans:
        blk = doc[s:e]
        if not blk.strip():
            continue

        # STEP 1: Determine target decree scope (anchor at ARTICLE title/lead)
        lead = blk[:650]
        scoped_target = resolve_target_from_text(lead) or resolve_target_from_text(blk[:1600])
        if scoped_target is None:
            continue

        target_decree_id, target_base = scoped_target

        # Must contain an action keyword somewhere in block
        if not P_ACTION.search(blk):
            continue

        # STEP 2: Extract references inside block
        pieces = re.split(r"(?<=[\.\;\:])\s+|\n+", blk)

        for piece in pieces:
            if not piece.strip():
                continue
            act_m = P_ACTION.search(piece)
            if not act_m:
                continue
            action = act_m.group(1).lower()

            # Piece can override target decree mention
            override = resolve_target_from_text(piece)
            if override is not None:
                target_decree_id, target_base = override

            if target_decree_id not in ALLOWED_TARGETS:
                continue

            # 2.1 point + clause + article
            m1 = P_REF_POINT_CLA_ART.search(piece)
            if m1:
                p = m1.group(1).lower()
                k = m1.group(2).lower()
                d = int(m1.group(3))
                cid = make_citation_id(target_base, d, k, p)
                rec = AmendRec(
                    amending_decree_id=amending_decree_id,
                    amending_decree_no=meta.get("decree_no"),
                    amending_issue_date=meta.get("issue_date"),
                    amending_effective_from=meta.get("effective_from"),
                    amending_article=None if am_article_no == -1 else am_article_no,
                    action=action,
                    target_decree_id=target_decree_id,
                    target_decree_base=target_base,
                    target_article=d,
                    target_clause=k,
                    target_point=p,
                    note=_snip(piece),
                )
                amap.setdefault(cid, []).append(rec.__dict__)
                continue

            # 2.2 multi điểm / multi khoản within same "Điều X"
            art_m = P_AT_END_ART.search(piece)
            if art_m:
                d = int(art_m.group(1))
                km = P_MULTI_KHOAN.search(piece)
                clause_list = _parse_multi_numbers(km.group(1)) if km else []
                pm = P_MULTI_DIEM.search(piece)
                point_list = _parse_multi_points(pm.group(1)) if pm else []

                if clause_list:
                    if point_list:
                        for k in clause_list:
                            for p in point_list:
                                cid = make_citation_id(target_base, d, k, p)
                                rec = AmendRec(
                                    amending_decree_id=amending_decree_id,
                                    amending_decree_no=meta.get("decree_no"),
                                    amending_issue_date=meta.get("issue_date"),
                                    amending_effective_from=meta.get("effective_from"),
                                    amending_article=None if am_article_no == -1 else am_article_no,
                                    action=action,
                                    target_decree_id=target_decree_id,
                                    target_decree_base=target_base,
                                    target_article=d,
                                    target_clause=k,
                                    target_point=p,
                                    note=_snip(piece),
                                )
                                amap.setdefault(cid, []).append(rec.__dict__)
                        continue
                    else:
                        for k in clause_list:
                            cid = make_citation_id(target_base, d, k, None)
                            rec = AmendRec(
                                amending_decree_id=amending_decree_id,
                                amending_decree_no=meta.get("decree_no"),
                                amending_issue_date=meta.get("issue_date"),
                                amending_effective_from=meta.get("effective_from"),
                                amending_article=None if am_article_no == -1 else am_article_no,
                                action=action,
                                target_decree_id=target_decree_id,
                                target_decree_base=target_base,
                                target_article=d,
                                target_clause=k,
                                target_point=None,
                                note=_snip(piece),
                            )
                            amap.setdefault(cid, []).append(rec.__dict__)
                        continue

            # 2.3 clause + article (single)
            m2 = P_REF_CLA_ART.search(piece)
            if m2:
                k = m2.group(1).lower()
                d = int(m2.group(2))
                cid = make_citation_id(target_base, d, k, None)
                rec = AmendRec(
                    amending_decree_id=amending_decree_id,
                    amending_decree_no=meta.get("decree_no"),
                    amending_issue_date=meta.get("issue_date"),
                    amending_effective_from=meta.get("effective_from"),
                    amending_article=None if am_article_no == -1 else am_article_no,
                    action=action,
                    target_decree_id=target_decree_id,
                    target_decree_base=target_base,
                    target_article=d,
                    target_clause=k,
                    target_point=None,
                    note=_snip(piece),
                )
                amap.setdefault(cid, []).append(rec.__dict__)
                continue

            # 2.4 article-only
            m3 = P_REF_ART.search(piece)
            if m3:
                d = int(m3.group(1))
                cid = make_citation_id(target_base, d, None, None)
                rec = AmendRec(
                    amending_decree_id=amending_decree_id,
                    amending_decree_no=meta.get("decree_no"),
                    amending_issue_date=meta.get("issue_date"),
                    amending_effective_from=meta.get("effective_from"),
                    amending_article=None if am_article_no == -1 else am_article_no,
                    action=action,
                    target_decree_id=target_decree_id,
                    target_decree_base=target_base,
                    target_article=d,
                    target_clause=None,
                    target_point=None,
                    note=_snip(piece),
                )
                amap.setdefault(cid, []).append(rec.__dict__)
                continue

    # de-dup per key
    for k in list(amap.keys()):
        seen = set()
        uniq = []
        for rec in amap[k]:
            s = json.dumps(rec, ensure_ascii=False, sort_keys=True)
            if s not in seen:
                seen.add(s)
                uniq.append(rec)
        amap[k] = uniq

    return amap

def merge_amendment_maps(*maps: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for mp in maps:
        for k, v in mp.items():
            out.setdefault(k, []).extend(v)

    for k in list(out.keys()):
        seen = set()
        uniq = []
        for rec in out[k]:
            s = json.dumps(rec, ensure_ascii=False, sort_keys=True)
            if s not in seen:
                seen.add(s)
                uniq.append(rec)
        out[k] = uniq
    return out

# =========================
# Main parsing: Chapter -> Article -> Clause -> Point
# =========================
def parse_one(decree_id: str, file_list: List[str], amend_map: Dict[str, List[dict]]) -> List[dict]:
    raw0 = load_multiple_files(file_list)
    meta = detect_doc_meta(raw0, decree_id)
    base = decree_base_id(meta.get("decree_no"), decree_id)
    
    # Create source string from file_list (for attribution)
    source_str = "; ".join([Path(f).name for f in file_list])
    
    # Determine document status: original or amended
    # For ND100: original (no amender found in primary content)
    # For ND123/ND168: amended versions of ND100
    if decree_id == "100":
        doc_status = "original"
    else:
        doc_status = "amended"

    pages = split_pages(raw0)
    joined: List[str] = []
    line_pages: List[int] = []
    for pno, ptxt in pages:
        for ln in ptxt.splitlines():
            joined.append(ln)
            line_pages.append(pno)
    doc = "\n".join(joined).strip()
    if not doc:
        doc = raw0

    # Chapters
    chap_marks: List[Tuple[int, Optional[int], str]] = []
    for m in P_CHAPTER.finditer(doc):
        chap_roman = m.group(1)
        chap_no = roman_to_int(chap_roman) if chap_roman else None
        chap_title = (m.group(2) or "").strip()
        chap_marks.append((m.start(), chap_no, chap_title))
    chap_marks.sort(key=lambda x: x[0])

    def chapter_for_pos(pos: int) -> Tuple[Optional[int], Optional[str]]:
        cur_no, cur_title = None, None
        for s, no, title in chap_marks:
            if s <= pos:
                cur_no, cur_title = no, title
            else:
                break
        return cur_no, cur_title

    # Articles
    arts: List[Tuple[int, int, str]] = []
    for m in P_ART.finditer(doc):
        try:
            arts.append((m.start(), int(m.group(2)), (m.group(3) or "").strip()))
        except Exception:
            pass
    arts.sort(key=lambda x: x[0])
    arts.append((len(doc), -1, ""))

    chunks: List[dict] = []

    for i in range(len(arts) - 1):
        a_start, article_no, article_title = arts[i]
        a_end, _, _ = arts[i + 1]
        a_block = doc[a_start:a_end].strip()
        if not a_block:
            continue

        chap_no, chap_title = chapter_for_pos(a_start)

        # page range (best-effort)
        a_lines = a_block.splitlines()
        first_line = a_lines[0].strip() if a_lines else ""
        page_start = page_end = None
        try:
            idx0 = next(j for j, ln in enumerate(joined) if ln.strip() == first_line)
            page_start = line_pages[idx0]
            page_end = line_pages[min(idx0 + len(a_lines) - 1, len(line_pages) - 1)]
        except StopIteration:
            pass

        a_body = "\n".join(a_lines[1:]).strip() if len(a_lines) > 1 else ""

        clauses = list(P_CLA.finditer(a_body))
        if not clauses:
            cid = make_citation_id(base, article_no, None, None)
            amended_by = amend_map.get(cid, [])
            chunks.append({
                "citation_id": cid,
                "decree_id": decree_id,
                "decree_no": meta.get("decree_no"),
                "issue_date": meta.get("issue_date"),
                "effective_from": meta.get("effective_from"),
                "status": "amended" if amended_by else "original",
                "chapter_no": chap_no,
                "chapter_title": chap_title,
                "article": article_no,
                "article_title": article_title,
                "clause": None,
                "point": None,
                "text": a_block,
                "source": source_str,
                "page_start": page_start,
                "page_end": page_end,
                "amended_by": amended_by,
            })
            continue

        for k, cm in enumerate(clauses):
            s = cm.start()
            e = clauses[k + 1].start() if k + 1 < len(clauses) else len(a_body)
            clause_no = cm.group(1).strip().lower()
            clause_text = a_body[s:e].strip()

            points = list(P_PNT.finditer(clause_text))
            if not points:
                cid = make_citation_id(base, article_no, clause_no, None)
                amended_by = amend_map.get(cid, []) or amend_map.get(make_citation_id(base, article_no, None, None), [])
                chunks.append({
                    "citation_id": cid,
                    "decree_id": decree_id,
                    "decree_no": meta.get("decree_no"),
                    "issue_date": meta.get("issue_date"),
                    "effective_from": meta.get("effective_from"),
                    "status": "amended" if amended_by else "original",
                    "chapter_no": chap_no,
                    "chapter_title": chap_title,
                    "article": article_no,
                    "article_title": article_title,
                    "clause": clause_no,
                    "point": None,
                    "text": f"Điều {article_no}\n{clause_text}",
                    "source": source_str,
                    "page_start": page_start,
                    "page_end": page_end,
                    "amended_by": amended_by,
                })
            else:
                for t, pm in enumerate(points):
                    ps = pm.start()
                    pe = points[t + 1].start() if t + 1 < len(points) else len(clause_text)
                    point = pm.group(1).lower()
                    point_text = clause_text[ps:pe].strip()

                    cid = make_citation_id(base, article_no, clause_no, point)
                    amended_by = (
                        amend_map.get(cid)
                        or amend_map.get(make_citation_id(base, article_no, clause_no, None))
                        or amend_map.get(make_citation_id(base, article_no, None, None))
                        or []
                    )

                    chunks.append({
                        "citation_id": cid,
                        "decree_id": decree_id,
                        "decree_no": meta.get("decree_no"),
                        "issue_date": meta.get("issue_date"),
                        "effective_from": meta.get("effective_from"),
                        "status": "amended" if amended_by else "original",
                        "chapter_no": chap_no,
                        "chapter_title": chap_title,
                        "article": article_no,
                        "article_title": article_title,
                        "clause": clause_no,
                        "point": point,
                        "text": f"Điều {article_no}\n{point_text}",
                        "source": source_str,
                        "page_start": page_start,
                        "page_end": page_end,
                        "amended_by": amended_by,
                    })

    return chunks

# =========================
# MAIN
# =========================
def main():
    # 1) Extract amendment maps from all decrees (any decree can be an amender)
    amend_maps: List[Dict[str, List[dict]]] = []
    for did, files in INPUTS:
        try:
            mp = extract_amendments(did, files)
            if mp:
                amend_maps.append(mp)
        except FileNotFoundError as e:
            print(f"[WARN] missing file(s) for decree {did}: {e}")

    amend_map = merge_amendment_maps(*amend_maps)

    # quick sanity logs
    print("amend keys:", len(amend_map))
    print("has ND123 amender?:", any(
        any(r.get("amending_decree_id") == "123" for r in v)
        for v in amend_map.values()
    ))

    # 2) Build corpus for all decrees and attach amended_by from amend_map
    all_chunks: List[dict] = []
    for did, files in INPUTS:
        print("Parsing", did, "from", files)
        try:
            all_chunks.extend(parse_one(did, files, amend_map))
        except FileNotFoundError as e:
            print(f"[WARN] skip missing file(s) for decree {did}: {e}")

    # 3) Write outputs
    with OUT_JSONL.open("w", encoding="utf-8") as w:
        for obj in all_chunks:
            w.write(json.dumps(obj, ensure_ascii=False) + "\n")

    with OUT_AMEND_MAP.open("w", encoding="utf-8") as w:
        json.dump(amend_map, w, ensure_ascii=False, indent=2)

    print("Saved:", OUT_JSONL, "| chunks:", len(all_chunks))
    print("Saved:", OUT_AMEND_MAP, "| keys:", len(amend_map))
    print("NOTE: amendment_map keys are citation_id of TARGET units (ND100_2019..., ND123_2021..., ND168_2024...)")

if __name__ == "__main__":
    main()