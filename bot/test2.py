import json
import requests
import os 
from dotenv import load_dotenv # 1. 이 라이브러리가 필요합니다

# 2. .env 파일을 메모리에 로드합니다
load_dotenv()

def send_order_to_server(category_id, price, symbol):
    # .env에서 값을 가져옵니다
    token = os.getenv("SECRET_TOKEN")
    
    # [중요] 토큰이 잘 읽혔는지 눈으로 직접 확인해보세요!
    if not token:
        print("⚠️ [WARNING] .env 파일에서 SECRET_TOKEN을 읽어오지 못했습니다!")
        print(f"현재 경로: {os.getcwd()}") # 현재 실행 경로가 .env 파일 위치와 맞는지 확인
    else:
        # 토큰 앞의 3자리만 출력해서 확인 (보안상 앞자리만)
        print(f"🔑 [INFO] Token Loaded: {token[:3]}***")

    payload = {
        "categoryId": category_id,
        "orderPrice": price,
        "symbol": symbol,
        "botId": 1,
        "orderType": "BUY",
        "orderCount": 1,
    }

    # (이하 전송 로직 동일)
    headers = {
    # 불필요한 User-Agent 등을 다 빼고 필수만 넣어보세요
    'X-Internal-Token': token,
    'Content-Type': 'application/json'  
    }
    
    try:
        url = "https://api.heartbit.site/api/orders"
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 200:
            print(f"✅ [SUCCESS] Order placed for {symbol}")
        else:
            print(f"❌ [FAIL] Status Code: {response.status_code}")
            print(f"   Response Body: {response.text}")

    except Exception as e:
        print(f"⚠️ [ERROR] Connection failed: {e}")

if __name__ == "__main__":
    send_order_to_server(1, 1.03, "BTC")
    #send_order_to_server(642, 1.03, "BTT")