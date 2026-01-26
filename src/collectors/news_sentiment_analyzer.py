import psycopg2
from transformers import pipeline
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np

# 1. 분석 설정
TARGET_COINS = ('BTC', 'ETH', 'SOL', 'XRP')
KEY_WEIGHTS = {"CEO": 1.5, "SEC": 2.0, "ETF": 2.0, "Regulation": 1.5, "Breakout": 1.3}

# 모델 로드 (처음 실행 시 다운로드 시간이 걸립니다)
print("모델을 로딩 중입니다... 잠시만 기다려 주세요.")
sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

def test_analysis():
    conn = psycopg2.connect(host="localhost", port=15432, user="postgres", password="0000", database="app")
    cur = conn.cursor()

    query = "SELECT news_id, title, description, ticker FROM public.coin_news WHERE ticker IN %s AND description IS NOT NULL LIMIT 5"
    cur.execute(query, (TARGET_COINS,))
    rows = cur.fetchall()

    print("\n" + "="*80)
    print(f"{'ID':<5} | {'TICKER':<6} | {'SENTIMENT':<10} | {'SCORE':<8} | {'TITLE'}")
    print("-"*80)

    for news_id, title, description, ticker in rows:
        chunks = text_splitter.split_text(description)
        chunk_scores = []

        for chunk in chunks:
            res = sentiment_pipeline(chunk)[0]
            # 점수 변환 로직
            score = res['score']
            if res['label'] == 'negative': score *= -1
            elif res['label'] == 'neutral': score = 0
            
            # 가중치 계산
            weight = 1.0
            for word, w_val in KEY_WEIGHTS.items():
                if word.lower() in chunk.lower():
                    weight = max(weight, w_val)
            chunk_scores.append(score * weight)

        raw_score = sum(chunk_scores) / len(chunk_scores) if chunk_scores else 0
        
        # [수정] Tanh 함수를 사용하여 -1 ~ 1 사이로 부드럽게 압축
        # 가중치가 많이 붙을수록 1이나 -1에 아주 가까워집니다.
        final_score = np.tanh(raw_score)
        label = 'POS' if final_score > 0.1 else ('NEG' if final_score < -0.1 else 'NEU')

        # 터미널 출력
        short_title = title[:45] + "..." if len(title) > 45 else title
        print(f"{news_id:<5} | {ticker:<6} | {label:<10} | {final_score:>8.4f} | {short_title}")

    print("="*80 + "\n")
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_analysis()