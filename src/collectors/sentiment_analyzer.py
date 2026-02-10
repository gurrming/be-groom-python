import pandas as pd
import torch
from sqlalchemy import create_engine, text
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
from langdetect import detect, DetectorFactory
from tqdm import tqdm
import sys

# 언어 감지 랜덤 시드 고정 (일관성 유지)
DetectorFactory.seed = 0

# ==========================================
# 1. DB 설정 (본인 설정에 맞게 수정)
# ==========================================
DB_USER = "postgres"      
DB_PASSWORD = "0000"  
DB_HOST = "localhost"          
DB_PORT = "15432"               
DB_NAME = "app"       

db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
try:
    engine = create_engine(db_url)
    connection = engine.connect()
    print("✅ DB 연결 성공!")
except Exception as e:
    print(f"❌ DB 연결 실패: {e}")
    sys.exit(1)

# ==========================================
# 2. 맥북(MPS) 가속 장치 설정
# ==========================================
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("🍎 Apple Silicon(M1/M2/M3) GPU 가속(MPS)을 사용합니다.")
elif torch.cuda.is_available():
    device = torch.device("cuda")
    print("🚀 NVIDIA GPU(CUDA)를 사용합니다.")
else:
    device = torch.device("cpu")
    print("🐢 CPU를 사용합니다.")

# ==========================================
# 3. 뉴스 데이터 처리 함수 (기존 방식 유지)
# ==========================================
def analyze_news_incremental():
    table_name = "news_data"
    id_column = "news_id"
    model_name = "ProsusAI/finbert"
    
    print(f"\n======== [{table_name}] 신규 데이터 분석 시작 (FinBERT) ========")

    # 1. 미처리 데이터 가져오기
    query = f"""
    SELECT {id_column}, title, COALESCE(description, '') as description
    FROM {table_name}
    WHERE sentiment_score IS NULL
    ORDER BY {id_column} DESC;
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    total_rows = len(df)
    if total_rows == 0:
        print("   🎉 뉴스 데이터는 모두 처리되었습니다.")
        return

    print(f"👉 분석 대상(뉴스): {total_rows}개")

    # 2. 모델 로드
    try:
        model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        classifier = pipeline("text-classification", model=model, tokenizer=tokenizer, device=device, truncation=True, max_length=512)
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return

    # 3. 데이터 전처리
    df['full_text'] = df.apply(lambda row: f"{row['title']} {row['description']}".strip(), axis=1)
    updates = []

    # 4. 배치 분석
    for i in tqdm(range(0, total_rows, 32), desc="Processing News"):
        batch_df = df.iloc[i : i + 32]
        texts = batch_df['full_text'].tolist()
        ids = batch_df[id_column].tolist()
        
        try:
            results = classifier(texts)
        except Exception as e:
            continue
        
        for doc_id, res in zip(ids, results):
            updates.append({
                "id": int(doc_id),
                "score": float(res['score']),
                "label": str(res['label']) # positive, negative, neutral
            })

    # 5. DB 업데이트
    if updates:
        print(f"💾 {len(updates)}건 뉴스 데이터 저장 중...")
        update_query = text(f"""
            UPDATE {table_name}
            SET sentiment_score = :score,
                sentiment_label = :label
            WHERE {id_column} = :id
        """)
        with engine.begin() as conn:
            conn.execute(update_query, updates)
        print("✅ 뉴스 업데이트 완료!")

# ==========================================
# 4. 커뮤니티 데이터 처리 함수 (Hybrid: KR/EN)
# ==========================================
def analyze_community_hybrid_incremental():
    table_name = "community_data"
    id_column = "community_id"
    
    print(f"\n======== [{table_name}] 신규 데이터 하이브리드 분석 시작 (KR/EN) ========")

    # 1. 미처리 데이터 가져오기
    query = f"""
    SELECT {id_column}, title, COALESCE(description, '') as description
    FROM {table_name}
    WHERE sentiment_score IS NULL
    ORDER BY {id_column} DESC;
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    total_rows = len(df)
    if total_rows == 0:
        print("   🎉 커뮤니티 데이터는 모두 처리되었습니다.")
        return

    print(f"👉 분석 대상(커뮤니티): {total_rows}개 (한국어/영어 자동 분류)")

    # 2. 모델 2개 로드 (한국어 & 영어)
    print("⏳ 모델 로딩 중... (KR-FinBert & CryptoBERT)")
    try:
        # 한국어 모델
        pipe_ko = pipeline("text-classification", model="snunlp/KR-FinBert-SC", device=device, truncation=True, max_length=512)
        # 영어 모델
        pipe_en = pipeline("text-classification", model="ElKulako/cryptobert", device=device, truncation=True, max_length=512)
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return

    df['full_text'] = df.apply(lambda row: f"{row['title']} {row['description']}".strip(), axis=1)
    updates = []

    print("🌊 언어 감지 및 정밀 분석 실행 중...")

    # 3. 개별 데이터 처리 (언어 감지 때문에 반복문 사용)
    for i, row in tqdm(df.iterrows(), total=total_rows, desc="Processing Community"):
        text_content = row['full_text']
        doc_id = row[id_column]
        
        if not text_content: continue

        # A. 언어 감지
        try:
            lang = detect(text_content) # ko, en 등
        except:
            lang = 'en' # 실패 시 영어 모델(이모지 등) 사용

        # B. 모델 선택 및 라벨 통일
        try:
            if lang == 'ko':
                # [한국어] KR-FinBert
                res = pipe_ko(text_content)[0]
                label = res['label'] # neutral, positive, negative
                score = res['score']
            else:
                # [영어] CryptoBERT
                res = pipe_en(text_content)[0]
                raw_label = res['label'] # Neutral, Bullish, Bearish
                score = res['score']
                
                # 라벨 통일 (DB 저장용)
                if raw_label == 'Bullish': label = 'positive'
                elif raw_label == 'Bearish': label = 'negative'
                else: label = 'neutral'
        except:
            continue

        updates.append({
            "id": int(doc_id),
            "score": float(score),
            "label": str(label)
        })

    # 4. DB 업데이트
    if updates:
        print(f"💾 {len(updates)}건 커뮤니티 데이터 저장 중...")
        update_query = text(f"""
            UPDATE {table_name}
            SET sentiment_score = :score,
                sentiment_label = :label
            WHERE {id_column} = :id
        """)
        with engine.begin() as conn:
            conn.execute(update_query, updates)
        print("✅ 커뮤니티 업데이트 완료!")

# ==========================================
# 5. 실행 (뉴스 -> 커뮤니티 순서)
# ==========================================
if __name__ == "__main__":
    # 1. 뉴스 데이터 처리
    analyze_news_incremental()
    
    # 2. 커뮤니티 데이터 처리 (Hybrid)
    analyze_community_hybrid_incremental()
    
    print("\n🎉 모든 신규 데이터 처리가 완료되었습니다!")
    connection.close()