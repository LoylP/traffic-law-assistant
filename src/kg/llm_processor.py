import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiQueryProcessor:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Vui lòng cấu hình GOOGLE_API_KEY trong file .env")
            
        genai.configure(api_key=api_key)
        # Sử dụng flash để tốc độ nhanh nhất
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        self.system_prompt = """Bạn là bộ tiền xử lý truy vấn cho hệ thống tra cứu luật giao thông Việt Nam.

        Nhiệm vụ:
        - Đọc câu hỏi tự nhiên của người dùng.
        - Viết lại thành 1 truy vấn ngắn, rõ, sát hành vi vi phạm để truy xuất knowledge graph.
        - Giữ lại phương tiện, hành vi vi phạm, điều kiện ngữ cảnh nếu có.
        - Không trả lời tư vấn pháp lý.
        - Không giải thích dài dòng.

        Bắt buộc chỉ trả về JSON hợp lệ theo đúng format:
        {"rewritten_query":"..."}
        """

    def rewrite(self, user_query):
        prompt = f"{self.system_prompt}\n\nCâu hỏi: {user_query}"
        try:
            response = self.model.generate_content(prompt)
            # Làm sạch chuỗi JSON (đôi khi Gemini trả về kèm markdown ```json)
            raw_text = response.text.strip()
            if "{" in raw_text:
                json_part = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
                data = json.loads(json_part)
                return data.get("rewritten_query", user_query)
            return user_query
        except Exception as e:
            print(f"Lỗi LLM: {e}")
            return user_query