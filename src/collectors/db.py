import psycopg2

# [설정] DB 접속 정보
db_config = {
    "user": "postgres",
    "password": "0000",
    "database": "app", 
    "host": "localhost",
    "port": 15432
}

def clean_investing_only():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    try:
        print("🧹 Investing.com 데이터 청소를 시작합니다...")
        
        # 1. 삭제 전 개수 확인
        cur.execute("SELECT COUNT(*) FROM public.community_data WHERE platform = 'investing'")
        before_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM public.community_data WHERE platform != 'investing'")
        other_count = cur.fetchone()[0]
        
        print(f"📊 현재 상태:")
        print(f"   - 지울 데이터 (Investing): {before_count}개")
        print(f"   - 보존할 데이터 (Other): {other_count}개")
        
        if before_count == 0:
            print("✅ 지울 데이터가 없습니다.")
            return

        # 2. 진짜 삭제 (플랫폼이 investing인 것만!)
        cur.execute("DELETE FROM public.community_data WHERE platform = 'investing'")
        deleted_count = cur.rowcount
        
        conn.commit()
        print(f"🗑️ 삭제 완료! 총 {deleted_count}개의 Investing 데이터를 지웠습니다.")
        print(f"✨ 다른 커뮤니티 데이터 {other_count}개는 안전하게 남아있습니다.")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_investing_only()