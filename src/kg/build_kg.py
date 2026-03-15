from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import networkx as nx


# =========================
# PATH CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
STRUCTURED_DIR = DATA_DIR / "structured"
KG_DIR = DATA_DIR / "kg"
KG_DIR.mkdir(parents=True, exist_ok=True)

LAW_CORPUS_FILE = STRUCTURED_DIR / "law_corpus.jsonl"
VIOLATIONS_FILE = STRUCTURED_DIR / "violations_300_update.json"

OUT_NODES = KG_DIR / "kg_nodes.jsonl"
OUT_EDGES = KG_DIR / "kg_edges.jsonl"


# =========================
# HELPERS
# =========================
def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_jsonl(path: Path, rows: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def slugify(text: str) -> str:
    text = normalize_text(text).lower()
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def add_node(nodes: Dict[str, dict], node_id: str, node_type: str, **attrs):
    if node_id not in nodes:
        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            **attrs
        }
    else:
        for k, v in attrs.items():
            if k not in nodes[node_id] or nodes[node_id][k] in (None, "", []):
                nodes[node_id][k] = v


def add_edge(edges: List[dict], source: str, relation: str, target: str, **attrs):
    edges.append({
        "source": source,
        "relation": relation,
        "target": target,
        **attrs
    })


def dedup_edges(edges: List[dict]) -> List[dict]:
    seen = set()
    out = []
    for e in edges:
        key = json.dumps(e, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


# =========================
# PARSE LEGAL BASIS
# =========================
def parse_legal_basis_to_citation_id(legal_basis: str) -> Optional[str]:
    """
    Parse:
    - 'NĐ 168/2024/NĐ-CP, Điều 15 Khoản 1 Điểm g'
    - 'NĐ 100/2019/NĐ-CP, Điều 5 Khoản 3'
    - 'corpus://... | NĐ 168/2024/NĐ-CP, Điều 15 Khoản 1 Điểm g'
    -> ND168_2024-D15-K1-Pg
    """
    if not legal_basis:
        return None

    basis = legal_basis.strip()
    if "|" in basis:
        basis = basis.split("|")[-1].strip()

    basis = re.sub(r"\s+", " ", basis)

    pattern = re.compile(
        r"(?:NĐ|Nghị định)\s+(\d+)/(\d+)/NĐ-CP,\s*"
        r"Điều\s+(\d+)"
        r"(?:\s+Khoản\s+([0-9a-zA-Z]+))?"
        r"(?:\s+Điểm\s+([a-zđA-ZĐ]))?",
        re.IGNORECASE
    )

    m = pattern.search(basis)
    if not m:
        return None

    decree_num, year, article, clause, point = m.groups()

    citation_id = f"ND{decree_num}_{year}-D{article}"
    if clause:
        citation_id += f"-K{str(clause).lower()}"
    if point:
        citation_id += f"-P{str(point).lower()}"

    return citation_id


# =========================
# BUILD KG
# =========================
def build_kg(
    law_corpus_path: Path = LAW_CORPUS_FILE,
    violations_path: Path = VIOLATIONS_FILE,
    out_nodes_path: Path = OUT_NODES,
    out_edges_path: Path = OUT_EDGES,
):
    law_units = load_jsonl(law_corpus_path)
    violations = load_json(violations_path)

    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    add_node(nodes, "UNKNOWN_LEGAL_UNIT", "Unknown", name="Unknown legal unit")

    # =========================
    # 1) LEGAL NODES
    # =========================
    for row in law_units:
        citation_id = row["citation_id"]
        decree_id = str(row.get("decree_id", "")).strip()
        decree_no = row.get("decree_no", "")
        chapter_no = row.get("chapter_no")
        chapter_title = row.get("chapter_title", "")
        article = row.get("article")
        article_title = row.get("article_title", "")
        clause = row.get("clause")
        point = row.get("point")
        text = row.get("text", "")
        effective_from = row.get("effective_from")
        issue_date = row.get("issue_date")
        status = row.get("status", "unknown")
        source = row.get("source", row.get("source_file", ""))

        add_node(
            nodes,
            citation_id,
            "LegalUnit",
            citation_id=citation_id,
            decree_id=decree_id,
            decree_no=decree_no,
            chapter_no=chapter_no,
            chapter_title=chapter_title,
            article=article,
            article_title=article_title,
            clause=clause,
            point=point,
            text=text,
            effective_from=effective_from,
            issue_date=issue_date,
            status=status,
            source=source,
            page_start=row.get("page_start"),
            page_end=row.get("page_end"),
        )

        decree_node_id = f"DECREE_{decree_id}"
        add_node(
            nodes,
            decree_node_id,
            "Decree",
            decree_id=decree_id,
            decree_no=decree_no,
            issue_date=issue_date,
            effective_from=effective_from,
            source=source,
        )
        add_edge(edges, citation_id, "BELONGS_TO_DECREE", decree_node_id)

        if chapter_no is not None:
            chapter_node_id = f"{decree_node_id}_CH{chapter_no}"
            add_node(
                nodes,
                chapter_node_id,
                "Chapter",
                decree_id=decree_id,
                chapter_no=chapter_no,
                chapter_title=chapter_title,
                decree_no=decree_no,
            )
            add_edge(edges, citation_id, "IN_CHAPTER", chapter_node_id)

        amended_by = row.get("amended_by", [])
        if amended_by:
            for idx, amend in enumerate(amended_by, start=1):
                amd_id = str(amend.get("amending_decree_id", "")).strip()
                amd_no = amend.get("amending_decree_no", "")
                amd_issue_date = amend.get("amending_issue_date")
                amd_effective = amend.get("amending_effective_from")
                amd_article = amend.get("amending_article")
                action = amend.get("action", "")
                note = amend.get("note", "")

                if amd_id:
                    amend_decree_node = f"DECREE_{amd_id}"
                    add_node(
                        nodes,
                        amend_decree_node,
                        "Decree",
                        decree_id=amd_id,
                        decree_no=amd_no,
                        issue_date=amd_issue_date,
                        effective_from=amd_effective,
                    )
                    add_edge(
                        edges,
                        citation_id,
                        "AMENDED_BY_DECREE",
                        amend_decree_node,
                        action=action,
                        note=note,
                        amending_article=amd_article,
                    )

                amend_event_id = (
                    f"{citation_id}__AMEND__{idx}__"
                    f"{slugify((amd_no or amd_id) + '_' + str(amd_article) + '_' + action)}"
                )
                add_node(
                    nodes,
                    amend_event_id,
                    "AmendmentEvent",
                    amending_decree_id=amd_id,
                    amending_decree_no=amd_no,
                    amending_issue_date=amd_issue_date,
                    amending_effective_from=amd_effective,
                    amending_article=amd_article,
                    action=action,
                    note=note,
                    target_citation_id=citation_id,
                )
                add_edge(edges, citation_id, "AMENDED_BY", amend_event_id)
                if amd_id:
                    add_edge(edges, amend_event_id, "RECORDED_IN_DECREE", f"DECREE_{amd_id}")

    # =========================
    # 2) VIOLATION NODES
    # =========================
    resolved_count = 0
    unresolved_count = 0
    unparsed_count = 0

    for item in violations:
        violation_id = str(item.get("violation_id", "")).strip()
        if not violation_id:
            continue

        violation_node_id = f"VIOLATION_{violation_id}"

        description_natural = item.get("description_natural", "")
        normalized_violation = item.get("normalized_violation", "")
        vehicle_type = item.get("vehicle_type", "khác")
        context_condition = item.get("context_condition", "")
        fine_min = item.get("fine_min")
        fine_max = item.get("fine_max")
        additional_sanctions = item.get("additional_sanctions", "")
        legal_basis = item.get("legal_basis", "")
        confidence_label = item.get("confidence_label", "")

        add_node(
            nodes,
            violation_node_id,
            "Violation",
            violation_id=violation_id,
            description_natural=description_natural,
            normalized_violation=normalized_violation,
            vehicle_type=vehicle_type,
            context_condition=context_condition,
            fine_min=fine_min,
            fine_max=fine_max,
            additional_sanctions=additional_sanctions,
            legal_basis=legal_basis,
            confidence_label=confidence_label,
        )

        vehicle_node_id = f"VEHICLE_{slugify(vehicle_type)}"
        add_node(nodes, vehicle_node_id, "VehicleType", name=vehicle_type)
        add_edge(edges, violation_node_id, "APPLIES_TO", vehicle_node_id)

        legal_unit_id = parse_legal_basis_to_citation_id(legal_basis)

        if legal_unit_id and legal_unit_id in nodes:
            add_edge(
                edges,
                violation_node_id,
                "BASED_ON",
                legal_unit_id,
                legal_basis=legal_basis
            )
            resolved_count += 1
        elif legal_unit_id:
            add_edge(
                edges,
                violation_node_id,
                "BASED_ON_UNRESOLVED",
                legal_unit_id,
                legal_basis=legal_basis
            )
            unresolved_count += 1
        else:
            add_edge(
                edges,
                violation_node_id,
                "BASED_ON_UNPARSED",
                "UNKNOWN_LEGAL_UNIT",
                legal_basis=legal_basis
            )
            unparsed_count += 1

    # =========================
    # 3) NETWORKX
    # =========================
    G = nx.MultiDiGraph()

    for node_id, node_data in nodes.items():
        G.add_node(node_id, **node_data)

    edges = dedup_edges(edges)
    for idx, e in enumerate(edges):
        source = e["source"]
        relation = e["relation"]
        target = e["target"]
        attrs = {k: v for k, v in e.items() if k not in {"source", "relation", "target"}}
        G.add_edge(source, target, key=f"{relation}_{idx}", relation=relation, **attrs)

    # =========================
    # 4) EXPORT
    # =========================
    node_rows = list(nodes.values())
    edge_rows = edges

    save_jsonl(out_nodes_path, node_rows)
    save_jsonl(out_edges_path, edge_rows)

    print(f"Saved nodes: {out_nodes_path} | count = {len(node_rows)}")
    print(f"Saved edges: {out_edges_path} | count = {len(edge_rows)}")
    print(f"Resolved legal basis: {resolved_count}")
    print(f"Unresolved legal basis: {unresolved_count}")
    print(f"Unparsed legal basis: {unparsed_count}")
    print(f"NetworkX graph: {G.number_of_nodes()} nodes | {G.number_of_edges()} edges")


if __name__ == "__main__":
    build_kg()