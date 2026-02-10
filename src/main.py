import threading
import schedule
import time
from datetime import datetime, timedelta, timezone
from collectors.news_aggregator import NewsAggregator

# 공용 인스턴스
collector = NewsAggregator()

def fetch_historical_bulk():
    """
    2025년 10월 1일부터 현재까지의 데이터를 수집합니다.
    """
    print("\n📚 [과거 데이터 수집 모드] 2025-10-01 ~ 현재 데이터 수집 시작...")
    
    # 1. CryptoPanic: 날짜를 거슬러 올라가며 수집 (Loop)
    target_date = datetime(2025, 10, 1, tzinfo=timezone.utc)
    
    # 별도 스레드로 실행하여 병렬 처리
    t_cp = threading.Thread(
        target=collector.fetch_cryptopanic, 
        args=(target_date,), # target_date 인자 전달
        name="History-CryptoPanic"
    )
    t_cp.start()

    # 2. AlphaVantage: 월 단위로 쪼개서 수집 (1000건 제한 회피용)
    # 2025년 10월부터 현재까지 월별로 루프
    start_dt = datetime(2025, 10, 1)
    now = datetime.now()
    
    while start_dt < now:
        # 한 달 간격 설정 (매월 1일 ~ 말일/다음달 1일)
        # 간단하게 30일 단위로 끊어서 요청
        end_dt = start_dt + timedelta(days=30)
        if end_dt > now:
            end_dt = now
            
        t_str = start_dt.strftime('%Y%m%dT%H%M')
        e_str = end_dt.strftime('%Y%m%dT%H%M')
        
        print(f"📥 AlphaVantage 기간 요청: {t_str} ~ {e_str}")
        collector.fetch_alpha_vantage(start_time=t_str, end_time=e_str)
        
        start_dt = end_dt + timedelta(minutes=1) # 다음 구간 시작
        time.sleep(2) # API Rate Limit 고려

    t_cp.join() # CryptoPanic 완료 대기
    print("🎉 과거 데이터 수집이 모두 완료되었습니다.")

def job():
    """주기적 실행 (최신 데이터만)"""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n⏰ [{now_str}] 실시간 통합 뉴스 수집 프로세스 시작...")
    
    # 평소에는 인자 없이 호출 (Top 4 코인만, 최신 데이터만)
    t1 = threading.Thread(target=collector.fetch_cryptopanic, name="CryptoPanic")
    t2 = threading.Thread(target=collector.fetch_alpha_vantage, name="AlphaVantage")

    t1.start()
    t2.start()

    t1.join()
    t2.join()
    print(f"✨ [{datetime.now().strftime('%H:%M:%S')}] 실시간 수집 완료.")

if __name__ == "__main__":
    # --- [중요] 과거 데이터 수집 실행 ---
    # 최초 1회 실행 후에는 주석 처리해도 됩니다.
    print("🚀 시스템 시작: 과거 데이터 확인 중...")
    fetch_historical_bulk() 
    
    # --- 스케줄러 실행 ---
    # 60분 간격 스케줄링 (실시간 데이터)
    schedule.every(60).minutes.do(job)

    print("\n🚀 뉴스 통합 수집 스케줄러 가동 중 (60분 간격)...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 종료합니다.")
            break
        except Exception as e:
            print(f"⚠️ 스케줄러 오류: {e}")
            time.sleep(60)