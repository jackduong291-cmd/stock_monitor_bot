import json
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

    payload = {
        'position': position.__dict__,
        'snapshot': snapshot.__dict__,
        'market_context': market,
        'report_type': report_type
    }
    
    prompt = f'''Bạn là chuyên gia chứng khoán VN. Nhiệm vụ của bạn là sử dụng công cụ Google Search để lấy tin tức mới nhất hôm nay về cổ phiếu {position.symbol} và tình hình vĩ mô, đặc biệt chú ý dòng tiền.
Sau khi quét tin tức, hãy thực hiện phân tích (LƯU Ý: Rất ngắn gọn, súc tích, ĐÁP ÁN DƯỚI 500 TỪ):
'''
    if report_type == 'intraday':
        prompt += '''
- Báo cáo TRONG PHIÊN: Hãy đánh giá giá Entry của người dùng có an toàn không dựa trên áp lực mua bán hiện tại và tin tức nóng vừa quét được. 
- Kết luận ngắn gọn: HOLD / WATCH / REDUCE / EXIT.
'''
    else:
        prompt += '''
- Báo cáo CUỐI NGÀY: Tổng hợp tin tức cả ngày. Phân tích trạng thái đóng cửa để DỰ ĐOÁN XU HƯỚNG NGÀY MAI.
- Nhận định xu hướng tiếp theo và đưa ra lời khuyên.
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
