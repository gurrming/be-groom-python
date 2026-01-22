import pyupbit
import os
from dotenv import load_dotenv

load_dotenv() # .env 파일 로드

class UpbitMarketCollector:
    def __init__(self):
        # 환경 변수에서 키 가져오기
        access = os.getenv('UPBIT_ACCESS_KEY')
        secret = os.getenv('UPBIT_SECRET_KEY')
        self.upbit = pyupbit.Upbit(access, secret)

    def get_all_market_data(self, ticker="KRW-BTC"):
        # 1. 현재가/호가 정보 전체
        orderbook = pyupbit.get_orderbook(ticker)
        
        # 2. 최근 캔들 데이터 전체 (일단 200개 가져옵니다)
        df = pyupbit.get_ohlcv(ticker, interval="minute60", count=200)
        
        # 거르지 않고 딕셔너리에 다 담아서 반환
        return {
            "orderbook_raw": orderbook,
            "ohlcv_raw": df.to_dict() # 데이터프레임을 딕셔너리로 변환
        }