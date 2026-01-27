import threading
import schedule
import time
from datetime import datetime
# 파일명이 news_aggregator.py 이므로 아래와 같이 임포트합니다.
from collectors.news_aggregator import NewsAggregator

# 공용 인스턴스 생성
collector = NewsAggregator()

def job():
    # 현재 시간을 가져오기 위해 datetime.now() 사용
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n⏰ [{now_str}] 통합 뉴스 수집 프로세스 시작...")
    
    # 스레드 생성
    t1 = threading.Thread(target=collector.fetch_cryptopanic, name="CryptoPanic")
    t2 = threading.Thread(target=collector.fetch_alpha_vantage, name="AlphaVantage")

    t1.start()
    t2.start()
    print(f"📡 {t1.name}, {t2.name} 수집 스레드 가동...")

    t1.join()
    t2.join()

    print(f"✨ [{datetime.now().strftime('%H:%M:%S')}] 모든 수집 작업이 완료되었습니다.")

if __name__ == "__main__":
    # 1. 만약 과거 12월 데이터를 한 번에 가져와야 한다면 아래 주석을 해제하세요.
    # print("📜 12월 벌크 수집 시작...")
    # collector.fetch_alpha_vantage(start_time="20251201T0000", end_time="20251231T2359")

    # 2. 첫 즉시 실행
    job() 
    
    # 3. 60분 간격 스케줄링
    schedule.every(60).minutes.do(job)

    print("🚀 뉴스 통합 수집 스케줄러 가동 중 (60분 간격)...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 사용자에 의해 스케줄러가 종료되었습니다.")
            break
        except Exception as e:
            print(f"⚠️ 스케줄러 오류 발생: {e}")
            time.sleep(60)