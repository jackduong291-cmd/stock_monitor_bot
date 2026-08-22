import json
from datetime import datetime
import pytz
from models import Position, MarketSnapshot
from google import genai
from google.genai import types
from config import settings

# Khởi tạo AI Client toàn cục
ai_client = None
if settings.gemini_api_key:
    ai_client = genai.Client(api_key=settings.gemini_api_key)

async def analyze(position: Position, snapshot: MarketSnapshot, market: dict, report_type: str):
    if ai_client is None:
        return '⚠️ Chưa cấu hình AI provider. Hãy điền GEMINI_API_KEY trong mục Environment Variables.'

    now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
    days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    date_info = f"{days[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')}"

    payload = {
        'position': position.__dict__,
        'snapshot': snapshot.__dict__,
        'market_context': market,
        'report_type': report_type
    }
    
    prompt = f'''Bạn là chuyên gia chứng khoán VN. Nhiệm vụ của bạn là sử dụng công cụ Google Search để lấy tin tức mới nhất hôm nay về cổ phiếu {position.symbol}.
Lưu ý: Hôm nay là {date_info}. Nếu hôm nay là ngày nghỉ (Thứ 7, Chủ nhật), thị trường đang đóng cửa, hãy hành văn theo hướng "điểm tin cuối tuần" thay vì dùng từ "sáng nay" hay "phiên hôm nay".
'''
    if report_type == 'intraday':
        prompt += '''
ĐÂY LÀ BÁO CÁO GIỮA PHIÊN. YÊU CẦU CỰC KỲ NGẮN GỌN (TỐI ĐA 3-4 CÂU, DƯỚI 50 TỪ).
Chỉ trả lời 2 ý chính:
1. Có tin tức gì bất thường/đột biến sáng nay không? (Nếu không có, nói "Không có tin xấu").
2. Lời khuyên hành động (HOLD / WATCH / REDUCE / EXIT) so với giá Entry của người dùng.
'''
    else:
        prompt += '''
ĐÂY LÀ BÁO CÁO CUỐI NGÀY. Yêu cầu phân tích chi tiết nhưng súc tích (DƯỚI 500 TỪ):
1. Tổng hợp các tin tức quan trọng nhất trong ngày về doanh nghiệp này.
2. Đánh giá sơ bộ tình hình vĩ mô và dòng tiền (như khối ngoại, thanh khoản).
3. Nhận định xu hướng tiếp theo và đưa ra lời khuyên hành động cho người dùng đang giữ vị thế này.
'''
    prompt += '\n\nDỮ LIỆU ĐẦU VÀO:\n' + json.dumps(payload, ensure_ascii=False, default=str)

    try:
        response = await ai_client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi AI: {str(e)}"
