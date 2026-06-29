from flask import Flask, render_template_string, request, jsonify
import requests

app = Flask(__name__)

# ==========================================
# 1단계: 실버로그 어드민 API 연동
# ==========================================
def login_silverlog():
    login_url = "https://silverlog-admin.vercel.app/api/auth/login"
    payload = {"username": "admin", "password": "changeme123"}
    headers = {"Content-Type": "application/json"}
    
    session = requests.Session()
    response = session.post(login_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return session
    return None

# ==========================================
# 2단계: 대시보드 화면 생성 (HTML 렌더링)
# ==========================================
@app.route('/')
def index():
    session = login_silverlog()
    if not session:
        return "❌ 어드민 로그인에 실패했습니다. 아이디/비밀번호를 확인하세요."
        
    res = session.get("https://silverlog-admin.vercel.app/api/catalogue?all=true")
    all_items = res.json()
    if isinstance(all_items, dict):
        all_items = all_items.get("items", all_items.get("data", []))
        
    coupang_items = []
    for item in all_items:
        ref_url = item.get("reference") or ""
        source = item.get("purchaseSource") or ""
        if "coupang.com" in ref_url or source == "쿠팡":
            raw_date = item.get("updatedAt") or item.get("updated_at") or ""
            if raw_date:
                item['formatted_date'] = raw_date[:10] + " " + raw_date[11:16]
            else:
                item['formatted_date'] = "기록 없음"
            coupang_items.append(item)
            
    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>쿠팡 스마트 관리 대시보드</title>
        <style>
            body { font-family: 'Malgun Gothic', sans-serif; background-color: #f4f7f6; padding: 20px; }
            h2 { color: #333; text-align: center; }
            .summary { text-align: center; color: #666; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; background-color: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: center; vertical-align: middle; }
            th { background-color: #ff9f43; color: white; font-size: 15px; }
            tr:hover { background-color: #fff5eb; }
            input[type="number"] { width: 90px; padding: 6px; text-align: right; border: 1px solid #ccc; border-radius: 4px; font-size: 15px; font-weight: bold; background-color: #e8f8f5; color: #117864; }
            select { padding: 6px; border-radius: 4px; border: 1px solid #ccc; }
            .btn { padding: 8px 14px; background-color: #2ecc71; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; transition: 0.2s; }
            .btn:hover { background-color: #27ae60; }
            .btn-link { background-color: #3498db; text-decoration: none; padding: 8px 14px; border-radius: 4px; color: white; display: inline-block; font-weight: bold; }
            .btn-link:hover { background-color: #2980b9; }
            .price-display { font-weight: bold; color: #e74c3c; font-size: 16px; }
            .date-display { font-size: 13px; color: #7f8c8d; }
            @media (max-width: 768px) {
                table, thead, tbody, th, td, tr { display: block; }
                th { display: none; }
                td { text-align: right; position: relative; padding-left: 50%; }
                td::before { content: attr(data-label); position: absolute; left: 10px; width: 45%; text-align: left; font-weight: bold; color: #ff9f43; }
            }
        </style>
    </head>
    <body>
        <h2>📦 실버로그 쿠팡 전용 스마트 대시보드</h2>
        <div class="summary">쿠팡 링크를 확인하고 '새 매입가'를 입력하면, 판매가가 자동 계산되어 DB에 바로 반영됩니다!</div>
        <table>
            <thead>
                <tr>
                    <th>상품명</th>
                    <th>상태 설정</th>
                    <th>새 매입가 입력(원)</th>
                    <th>자동 계산 판매가(원)</th>
                    <th>최근 수정일</th>
                    <th>DB 반영</th>
                    <th>쿠팡 확인</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td data-label="상품명" style="text-align: left;"><strong>{{ item.name }}</strong></td>
                    <td data-label="상태 설정">
                        <select id="status_{{ item._id }}">
                            <option value="true" {% if item.active %}selected{% endif %}>🟢 판매중 (Active)</option>
                            <option value="false" {% if not item.active %}selected{% endif %}>🔴 비활성 (Inactive)</option>
                        </select>
                    </td>
                    <td data-label="새 매입가">
                        <input type="number" id="buyingPrice_{{ item._id }}" value="{{ item.buyingPrice }}" oninput="calculateSalePrice('{{ item._id }}')">
                    </td>
                    <td data-label="계산된 판매가">
                        <span id="displayPrice_{{ item._id }}" class="price-display">{{ item.price }}</span>원
                    </td>
                    <td data-label="최근 수정일">
                        <span id="date_{{ item._id }}" class="date-display">{{ item.formatted_date }}</span>
                    </td>
                    <td data-label="DB 반영">
                        <button class="btn" onclick="updateItem('{{ item._id }}', {{ item.originalPrice }})">적용하기</button>
                    </td>
                    <td data-label="쿠팡 확인">
                        <a href="{{ item.reference }}" target="_blank" class="btn-link">🛒 링크 열기</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <script>
            function calculateSalePrice(itemId) {
                const buyPrice = parseInt(document.getElementById('buyingPrice_' + itemId).value);
                if (!isNaN(buyPrice) && buyPrice > 0) {
                    const marginPrice = buyPrice * 1.07;
                    const salePrice = Math.floor(marginPrice / 100) * 100 + 90;
                    document.getElementById('displayPrice_' + itemId).innerText = salePrice.toLocaleString('ko-KR');
                } else {
                    document.getElementById('displayPrice_' + itemId).innerText = '0';
                }
            }

            function updateItem(itemId, origPrice) {
                const newBuyPrice = parseInt(document.getElementById('buyingPrice_' + itemId).value);
                const newStatus = document.getElementById('status_' + itemId).value === 'true';
                
                if (isNaN(newBuyPrice) || newBuyPrice <= 0) {
                    alert('매입가를 올바르게 입력해주세요.');
                    return;
                }

                const marginPrice = newBuyPrice * 1.07;
                const newSalePrice = Math.floor(marginPrice / 100) * 100 + 90;
                
                fetch('/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        item_id: itemId,
                        price: newSalePrice,
                        originalPrice: origPrice,
                        buyingPrice: newBuyPrice,
                        active: newStatus
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if(data.success) {
                        alert('✅ 성공적으로 업데이트 되었습니다!');
                        const now = new Date();
                        const timeString = now.getFullYear() + '-' +
                                           String(now.getMonth() + 1).padStart(2, '0') + '-' +
                                           String(now.getDate()).padStart(2, '0') + ' ' +
                                           String(now.getHours()).padStart(2, '0') + ':' +
                                           String(now.getMinutes()).padStart(2, '0');
                        const dateSpan = document.getElementById('date_' + itemId);
                        dateSpan.innerText = timeString;
                        dateSpan.style.color = '#e74c3c';
                        dateSpan.style.fontWeight = 'bold';
                    } else {
                        alert('❌ 업데이트 실패: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('네트워크 오류가 발생했습니다: ' + error);
                });
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, items=coupang_items)

# ==========================================
# 3단계: 파이썬이 데이터를 받아 실버로그로 쏴주는 API
# ==========================================
@app.route('/update', methods=['POST'])
def update():
    data = request.json
    session = login_silverlog()
    if not session:
        return jsonify({"success": False, "message": "어드민 로그인 세션 만료"})
        
    update_url = f"https://silverlog-admin.vercel.app/api/catalogue/{data['item_id']}"
    payload = {
        "price": data['price'],
        "originalPrice": data['originalPrice'],
        "buyingPrice": data['buyingPrice'],
        "active": data['active']
    }
    
    res = session.patch(update_url, json=payload)
    if res.status_code == 200:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": f"서버 에러 (코드: {res.status_code})"})