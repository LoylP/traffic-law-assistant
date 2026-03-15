import os
import json
from dotenv import load_dotenv
from hybrid_search import LegalRetriever
from llm_processor import GeminiQueryProcessor
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
KG_DIR = DATA_DIR / "kg"
STRUCTURED_DIR = DATA_DIR / "structured"
KG_DIR.mkdir(parents=True, exist_ok=True)

KG_NODES_FILE= KG_DIR / 'kg_nodes.jsonl'
EMB_CACHE_DIR= KG_DIR / 'embedding_cache'
AMENDMENT_MAP_FILE = STRUCTURED_DIR / 'amendment_map.json'

def display_result(result, rank, amendment_map):
    node = result['raw_node']
    
    print(f"\n【 KẾT QUẢ #{rank} - Độ tương đồng cao 】")
    print(f"Hành vi: {node.get('description_natural', 'N/A')}")
    print(f"Mức phạt: {node.get('fine_min', 'Không rõ')} - {node.get('fine_max', 'N/A')}")
    print(f"Phương tiện: {node.get('vehicle_type', 'N/A')}")
    print(f"Trích dẫn: {node.get('legal_basis', 'N/A')}")
    print(f"Hình phạt bổ sung: {node.get('additional_sanctions', 'N/A')}")

    # Thêm thông tin về sửa đổi luật
    citation_id = node.get('citation_id')
    if citation_id and citation_id in amendment_map:
        amendments = amendment_map[citation_id]
        for amendment in amendments:
            amending_decree = amendment.get('amending_decree_id', 'N/A')
            note = amendment.get('note', '')
            print(f"📝 Đã được sửa đổi bởi Nghị định {amending_decree}: {note}")

    print("-" * 50)

def main():
    # Cấu hình đường dẫn từ .env hoặc mặc định
    kg_path = KG_NODES_FILE
    cache_dir = EMB_CACHE_DIR
    amendment_path = AMENDMENT_MAP_FILE

    print("🚀 Đang khởi động hệ thống tra cứu luật giao thông...")
    
    try:
        retriever = LegalRetriever(kg_path, cache_dir)
        llm_engine = GeminiQueryProcessor()
        
        # Load amendment map
        if amendment_path.exists():
            with open(amendment_path, 'r', encoding='utf-8') as f:
                amendment_map = json.load(f)
            # Normalize keys by removing "_2019"
            normalized_amendment_map = {k.replace("_2019", ""): v for k, v in amendment_map.items()}
        else:
            normalized_amendment_map = {}
            print("⚠️ Không tìm thấy file amendment_map.json")
        
        print("\n✅ Hệ thống sẵn sàng! (Nhập 'exit' để thoát)")
        
        while True:
            query = input("\n👤 Câu hỏi của bạn: ").strip()
            if query.lower() in ['exit', 'quit', 'thoát']:
                break
            if not query:
                continue

            print("🔍 Đang phân tích câu hỏi bằng Gemini...")
            refined_query = llm_engine.rewrite(query)
            print(f"✨ Từ khóa tìm kiếm: {refined_query}")

            print("🔎 Đang truy vấn Knowledge Graph...")
            results = retriever.search(refined_query, top_k=1)

            if not results:
                print("❌ Không tìm thấy vi phạm nào phù hợp với câu hỏi của bạn.")
            else:
                for i, res in enumerate(results, 1):
                    display_result(res, i, normalized_amendment_map)
                    
    except Exception as e:
        print(f"💥 Lỗi khởi động: {e}")

if __name__ == "__main__":
    main()