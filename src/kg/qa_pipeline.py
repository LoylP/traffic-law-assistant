#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from typing import Dict, Any

from graph_query import TrafficLawGraphQuery


class TrafficLawQAPipeline:
    def __init__(self):
        self.engine = TrafficLawGraphQuery()
        self.engine.load_all()

    # =========================
    # RULE-BASED RESPONSE
    # =========================
    def _build_rule_based_text(self, result: Dict[str, Any]) -> str:
        if not result.get("found"):
            return "Không biết / Không có dữ liệu phù hợp."

        ans = result["answer"]

        desc = ans.get("description") or "Không xác định được hành vi"
        fine_min = ans.get("fine_min_text")
        fine_max = ans.get("fine_max_text")
        sanctions = ans.get("additional_sanctions", [])
        remedies = ans.get("remedies", [])
        legal_basis = ans.get("legal_basis", [])

        parts = [f"Hành vi gần khớp nhất: {desc}"]

        if fine_min and fine_max:
            parts.append(f"Mức phạt tiền: từ {fine_min} đến {fine_max}.")
        elif fine_min:
            parts.append(f"Mức phạt tiền: {fine_min}.")

        if sanctions:
            parts.append("Hình thức xử phạt bổ sung: " + "; ".join(sanctions) + ".")

        if remedies:
            parts.append("Biện pháp khắc phục hậu quả: " + "; ".join(remedies) + ".")

        if legal_basis:
            lb = legal_basis[0]
            cite = []
            if lb.get("decree_no"):
                cite.append(lb["decree_no"])
            if lb.get("article") is not None:
                cite.append(f"Điều {lb['article']}")
            if lb.get("clause") not in [None, ""]:
                cite.append(f"Khoản {lb['clause']}")
            if lb.get("point") not in [None, ""]:
                cite.append(f"Điểm {lb['point']}")
            if cite:
                parts.append("Căn cứ pháp lý: " + ", ".join(cite) + ".")

        return "\n".join(parts)

    # =========================
    # LLM PROMPT
    # =========================
    def build_llm_prompt(self, user_query: str, graph_result: Dict[str, Any]) -> str:
        return f"""
Bạn là trợ lý hỏi đáp Luật Giao thông.

Nhiệm vụ:
- Trả lời ngắn gọn, rõ ràng, bằng tiếng Việt.
- Chỉ được dùng dữ liệu đã truy xuất bên dưới.
- Nếu dữ liệu không đủ chắc chắn, trả lời: "Không biết / Không có dữ liệu phù hợp."
- Phải nêu:
  1. Hành vi vi phạm gần khớp
  2. Mức phạt tiền
  3. Hình thức xử phạt bổ sung nếu có
  4. Biện pháp khắc phục hậu quả nếu có
  5. Căn cứ pháp lý cụ thể

Câu hỏi người dùng:
{user_query}

Dữ liệu truy xuất:
{json.dumps(graph_result, ensure_ascii=False, indent=2)}
""".strip()

    # =========================
    # OPTIONAL OPENAI CALL
    # =========================
    def call_llm_openai(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return "Chưa cài thư viện openai. Hãy dùng rule-based hoặc cài openai."

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Chưa có OPENAI_API_KEY. Hãy dùng rule-based hoặc cấu hình API key."

        client = OpenAI(api_key=api_key)

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý hỏi đáp Luật Giao thông."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()

    # =========================
    # MAIN QA
    # =========================
    def ask(
        self,
        user_query: str,
        top_k: int = 5,
        score_threshold: float = 0.1,
        use_llm: bool = False,
        llm_model: str = "gpt-4o-mini",
    ) -> Dict[str, Any]:
        graph_result = self.engine.answer(
            user_query=user_query,
            top_k=top_k,
            score_threshold=score_threshold
        )

        if not graph_result.get("found"):
            return {
                "query": user_query,
                "found": False,
                "answer_text": "Không biết / Không có dữ liệu phù hợp.",
                "graph_result": graph_result,
            }

        if use_llm:
            prompt = self.build_llm_prompt(user_query, graph_result)
            answer_text = self.call_llm_openai(prompt, model=llm_model)
        else:
            answer_text = self._build_rule_based_text(graph_result)

        return {
            "query": user_query,
            "found": True,
            "answer_text": answer_text,
            "graph_result": graph_result,
        }


if __name__ == "__main__":
    qa = TrafficLawQAPipeline()

    test_queries = [
        "xe máy vượt đèn đỏ",
        "ô tô uống rượu lái xe",
        "xe máy không đội mũ bảo hiểm",
        "đi ngược chiều trên cao tốc",
    ]

    for q in test_queries:
        print("=" * 80)
        rs = qa.ask(q, use_llm=False, score_threshold=0.1)
        print("QUERY:", q)
        print("ANSWER:")
        print(rs["answer_text"])
        print()