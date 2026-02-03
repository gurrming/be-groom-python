import psycopg2
from transformers import pipeline
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np

# 1. 설정 및 모델 로드
TARGET_COINS = ('BTC', 'ETH', 'SOL', 'XRP')
KEY_WEIGHTS = {"CEO": 1.5, "SEC": 2.0, "ETF": 2.0, "Regulation": 1.5, "Breakout": 1.3}

print("Fin-BERT 모델 로딩 중...")
# Mac(M1/M2/M3)을 사용 중이시라면 device="mps"를 쓰시는 게 빠를 수 있습니다.
# 위 에러 로그에 mps:0이 뜬 것으로 보아 아래처럼 설정하는 것이 좋습니다.
sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert", device="mps") 
text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)

def process_all_data():
    conn = psycopg2.connect(host="localhost", port=15432, user="postgres", password="0000", database="app")
    cur = conn.cursor()

    # [수정됨] 테이블명은 data로, 뉴스 ID는 news_id로 변경
    tasks = [
        ("news_data", "news_id", "description"),
        ("community_data", "community_id", "description")
    ]

    for table_name, id_col, text_col in tasks:
        print(f"\n>>> {table_name} 분석 시작...")
        
        # sentiment_score가 없는 데이터만 추출
        query = f"SELECT {id_col}, title, {text_col} FROM {table_name} WHERE sentiment_score IS NULL"
        cur.execute(query)
        rows = cur.fetchall()
        
        if not rows:
            print(f"--- {table_name}에 처리할 데이터가 없습니다.")
            continue

        for i, (row_id, title, content) in enumerate(rows):
            target_text = content if content and len(content.strip()) > 0 else title
            
            chunks = text_splitter.split_text(target_text)
            chunk_scores = []

            for chunk in chunks:
                res = sentiment_pipeline(chunk)[0]
                score = res['score']
                
                if res['label'] == 'negative': score *= -1
                elif res['label'] == 'neutral': score = 0
                
                weight = 1.0
                for word, w_val in KEY_WEIGHTS.items():
                    if word.lower() in chunk.lower():
                        weight = max(weight, w_val)
                chunk_scores.append(score * weight)

            raw_score = sum(chunk_scores) / len(chunk_scores) if chunk_scores else 0
            final_score = float(np.tanh(raw_score))
            label = 'positive' if final_score > 0.1 else ('negative' if final_score < -0.1 else 'neutral')

            # 업데이트 쿼리
            update_query = f"UPDATE {table_name} SET sentiment_score = %s, sentiment_label = %s WHERE {id_col} = %s"
            cur.execute(update_query, (final_score, label, row_id))

            if (i + 1) % 100 == 0:
                conn.commit()
                print(f"[{table_name}] {i + 1}/{len(rows)} 완료...")

        conn.commit()
        print(f">>> {table_name} 전수 처리 완료!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    process_all_data()