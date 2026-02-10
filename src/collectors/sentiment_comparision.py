import pandas as pd
import torch
from sqlalchemy import create_engine
from transformers import pipeline
from sklearn.metrics import accuracy_score, f1_score, classification_report
import sys

# ==========================================
# 1. DB 설정
# ==========================================
DB_USER = "postgres"      
DB_PASSWORD = "0000"  
DB_HOST = "localhost"          
DB_PORT = "15432"               
DB_NAME = "app" 

db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)

# ==========================================
# 2. 모델 로드 (Mac MPS 가속 지원)
# ==========================================
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("🍎 Apple MPS 가속을 사용합니다.")
else:
    device = torch.device("cpu")
    print("🐢 CPU를 사용합니다.")

print("⏳ 모델을 로드 중입니다... (FinBERT & CryptoBERT)")

# 파이프라인 로드
pipe_fin = pipeline("text-classification", model="ProsusAI/finbert", device=device, truncation=True, max_length=512)
pipe_crypto = pipeline("text-classification", model="ElKulako/cryptobert", device=device, truncation=True, max_length=512)

# ==========================================
# 3. 라벨 통합 함수 (채점을 위해 통일)
# ==========================================
# 0: 부정(Negative/Bearish), 1: 중립(Neutral), 2: 긍정(Positive/Bullish)
def map_label(label):
    label = label.lower()
    if label in ['negative', 'bearish']:
        return 0
    elif label in ['neutral']:
        return 1
    elif label in ['positive', 'bullish']:
        return 2
    return 1 # 예외는 중립

# ==========================================
# 4. 테스트 시작
# ==========================================
def evaluate_models(sample_count=20):
    print("\n" + "="*70)
    print(f"📝 지금부터 {sample_count}개의 데이터에 대해 '정답'을 입력해주세요.")
    print("   (키보드로 입력: 0=부정, 1=중립, 2=긍정)")
    print("="*70)

    # 뉴스 10개 + 커뮤니티 10개 섞어서 가져오기
    query = """
    (SELECT title, 'NEWS' as type FROM news_data ORDER BY RANDOM() LIMIT 10)
    UNION ALL
    (SELECT title, 'COMMUNITY' as type FROM community_data ORDER BY RANDOM() LIMIT 10)
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        # 순서 섞기
        df = df.sample(frac=1).reset_index(drop=True)

    y_true = []       # 사용자가 입력한 정답
    y_pred_fin = []   # FinBERT 예측값
    y_pred_crypto = [] # CryptoBERT 예측값

    for i, row in df.iterrows():
        text = row['title']
        dtype = row['type']
        
        print(f"\n[{i+1}/{sample_count}] ({dtype}) : {text}")
        
        while True:
            try:
                user_input = input("   👉 정답은? (0:악재, 1:중립, 2:호재): ")
                if user_input in ['0', '1', '2']:
                    y_true.append(int(user_input))
                    break
            except:
                pass
            print("   ⚠️ 0, 1, 2 중에서 입력해주세요.")

        # 모델 예측 실행
        res_fin = pipe_fin(text)[0]
        res_crypto = pipe_crypto(text)[0]
        
        y_pred_fin.append(map_label(res_fin['label']))
        y_pred_crypto.append(map_label(res_crypto['label']))

    # ==========================================
    # 5. 채점 결과 (Score Report)
    # ==========================================
    print("\n" + "="*70)
    print("📊 최종 성적표 (Performance Report)")
    print("="*70)

    # 정확도 계산
    acc_fin = accuracy_score(y_true, y_pred_fin)
    acc_crypto = accuracy_score(y_true, y_pred_crypto)

    # F1 Score (Macro Average: 클래스별 평균)
    f1_fin = f1_score(y_true, y_pred_fin, average='macro')
    f1_crypto = f1_score(y_true, y_pred_crypto, average='macro')

    print(f"1️⃣  FinBERT (뉴스 특화)")
    print(f"   - 정확도(Accuracy): {acc_fin:.2%}")
    print(f"   - F1 Score       : {f1_fin:.4f}")
    
    print(f"\n2️⃣  CryptoBERT (코인 특화)")
    print(f"   - 정확도(Accuracy): {acc_crypto:.2%}")
    print(f"   - F1 Score       : {f1_crypto:.4f}")

    print("-" * 50)
    if f1_fin > f1_crypto:
        print("🏆 종합 우승: FinBERT가 이번 샘플에서 더 정확했습니다.")
    elif f1_crypto > f1_fin:
        print("🏆 종합 우승: CryptoBERT가 이번 샘플에서 더 정확했습니다.")
    else:
        print("🤝 무승부입니다.")

if __name__ == "__main__":
    evaluate_models(20) # 20개만 테스트