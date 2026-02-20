import psycopg2
from qdrant_client import QdrantClient

# 1. DB 연결 설정 (사용하시는 설정에 맞게 수정)
DB_CONFIG = {
    "host": "localhost", "port": "15432",
    "database": "app", "user": "postgres", "password": "0000"
}

def check_postgres():
    print("🔵 [PostgreSQL 데이터 확인]")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for table in ["news_data", "community_data"]:
            cur.execute(f"SELECT count(*) FROM {table};")
            count = cur.fetchone()[0]
            print(f" - {table} 테이블: 총 {count}개 데이터 저장됨")
            
            if count > 0:
                cur.execute(f"SELECT title FROM {table} ORDER BY published_at DESC LIMIT 1;")
                latest = cur.fetchone()[0]
                print(f"   ㄴ 최신 글 제목: {latest[:50]}...")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Postgres 연결 실패: {e}")

def check_qdrant():
    print("\n🟢 [Qdrant 벡터 DB 데이터 확인]")
    try:
        client = QdrantClient(url="http://localhost:6333")
        
        for col in ["news_collection", "community_collection"]:
            # 컬렉션 정보 가져오기
            col_info = client.get_collection(collection_name=col)
            print(f" - {col} 방: 총 {col_info.points_count}개 벡터 저장됨")
            
            # 샘플 데이터 1개 훔쳐보기
            if col_info.points_count > 0:
                sample, _ = client.scroll(collection_name=col, limit=1)
                payload = sample[0].payload
                print(f"   ㄴ 샘플 Payload: {payload}")
                
    except Exception as e:
        print(f"❌ Qdrant 연결 실패: {e}")


if __name__ == "__main__":
    check_postgres()
    check_qdrant()