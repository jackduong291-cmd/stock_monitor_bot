import json
from models import Position, MarketSnapshot

async def analyze(position: Position, snapshot: MarketSnapshot, market: dict, report_type: str, model=None):
    if model is None:
        return '⚠️ Chưa cấu hình AI provider. Hãy điền GEMINI_API_KEY trong file .env.'

    payload = {
        'position': position.__dict__,
        'snapshot': snapshot.__dict__,
        'market_context': market,
        'report_type': report_type
    }
    
    prompt = f'''Bạn là chuyên gia chứng khoán VN. Nhiệm vụ của bạn là sử dụng công cụ Google Search để lấy tin tức mới nhất hôm nay về cổ phiếu {position.symbol} và tình hình vĩ mô, đặc biệt chú ý dòng tiền (như lệnh lớn mua/bán, khối ngoại).
Sau khi quét tin tức, hãy thực hiện phân tích:
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
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi AI: {str(e)}"
