import threading
import schedule
import time
from collectors.news_aggregator import NewsAggregator

# collector 인스턴스 생성
collector = NewsAggregator()

def job():
    print(f"\n⏰ [{time.strftime('%Y-%m-%d %H:%M:%S')}] 정기 뉴스 수집 프로세스 시작...")
    
    # 수정된 클래스는 내부에서 DB 카테고리를 직접 조회하므로 TARGET_COINS를 인자로 줄 필요가 없습니다.
    threads = [
        threading.Thread(target=collector.fetch_cryptopanic, name="CryptoPanic"),
        threading.Thread(target=collector.fetch_alpha_vantage, name="AlphaVantage")
    ]

    for t in threads:
        t.start()
        print(f"📡 {t.name} 수집 쓰레드 가동...")

    for t in threads:
        t.join()

    print(f"✨ [{time.strftime('%H:%M:%S')}] 모든 수집 작업이 완료되었습니다.")

def main():
    # 1. 즉시 한 번 실행하여 정상 작동 확인
    job() 
    
    # 2. 60분 간격으로 스케줄링
    schedule.every(60).minutes.do(job)

    print("🚀 뉴스 수집 스케줄러 가동 중 (60분 간격)...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 사용자에 의해 수집기가 종료되었습니다.")
            break
        except Exception as e:
            print(f"⚠️ 스케줄러 오류 발생: {e}")
            time.sleep(60) # 오류 발생 시 1분 대기 후 재시도

if __name__ == "__main__":
    main()