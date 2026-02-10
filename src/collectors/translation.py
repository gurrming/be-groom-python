import pandas as pd
import torch
from sqlalchemy import create_engine, text
from transformers import pipeline
from tqdm import tqdm
import sys
import re

# ==========================================
# 1. DB 설정
# ==========================================
DB_USER = "postgres"      
DB_PASSWORD = "0000"  
DB_HOST = "localhost"          
DB_PORT = "15432"               
DB_NAME = "app"       

db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
try:
    engine = create_engine(db_url)
    print("✅ DB 연결 성공!")
except Exception as e:
    print(f"❌ DB 연결 실패: {e}")
    sys.exit(1)

# ==========================================
# 2. 디바이스 설정
# ==========================================
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("🍎 Apple MPS 가속 ON")
else:
    device = torch.device("cpu")

# ==========================================
# 3. [핵심] 코인 은어 사전 (치환용)
# ==========================================
SLANG_DICT = {
    # [🔴 확실한 악재/공포 - Bearish]
    "떡락": " HUGE CRASH ",
    "폭락": " PLUMMET ",
    "나락": " HELL DUMP ",
    "하락장": " BEAR MARKET ",
    "한강": " SUICIDE DEPRESSION ",
    "돔황챠": " RUN AWAY ",
    "돔황차": " RUN AWAY ",
    "탈출": " ESCAPE ", 
    "손절": " PANIC SELL ",
    "패닉셀": " PANIC SELL ",
    "설거지": " SCAM DUMP ",
    "흑우": " VICTIM ",
    "물렸": " TRAPPED LOSS ",
    "시체": " BAG HOLDER ",
    "상폐": " DELISTING ",
    "스캠": " SCAM ",
    "망했": " RUINED ",
    "무섭다": " FEAR ",
    "무서워": " FEAR ",
    "공포": " FEAR ",
    "떨린다": " FEAR ",
    "숏": " SHORT POSITION ",
    "drained": " HACKED ",
    "털렸다": " HACKED ",
    "해킹": " HACKED ",
    "풀매도": " ALL IN SELL ",

    # [🟢 확실한 호재/희망 - Bullish]
    "떡상": " HUGE PUMP ",
    "불장": " BULL MARKET ",
    "투더문": " MOONING ",
    "가즈아": " TO THE MOON ",
    "쏠거야": " PUMPING ",
    "존버": " HODL ",
    "홀딩": " HODL ",
    "졸업": " RETIRE RICH ",
    "익절": " TAKE PROFIT ",
    "수익": " PROFIT ",
    "발라먹": " PROFIT TRADE ",
    "반등": " REBOUND ",
    "말아올려": " PUMP UP ",
    "풀매수": " ALL IN BUY ",
    "영끌": " ALL IN BUY ",
    "물타기": " BUY THE DIP ",
    "롱": " LONG POSITION ",
    "상승": " RISE ",
    
    # [⚪️ 중립/기타]
    "조정": " CORRECTION ",
    "횡보": " SIDEWAYS ",
    "구조대": " RECOVERY PRICE ",
    "기사님": " MARKET MAKER ",
    "세력": " WHALE ",
    
    # [욕설 처리 - 감정 강조용]
    "시벌": " DAMN ",
    "개같": " DAMN ",
    "미친": " CRAZY "
}

def inject_slang(text):
    """
    한글 문장에 있는 은어를 영어 키워드로 강제 치환합니다.
    예: "와 떡락하네" -> "와 HUGE CRASH 하네"
    """
    if not text: return ""
    
    # 딕셔너리 순회하며 치환
    for slang, eng_keyword in SLANG_DICT.items():
        if slang in text:
            text = text.replace(slang, eng_keyword)
            
    return text

def has_korean_char(text):
    return bool(re.search("[가-힣]", text))

def analyze_with_dictionary_injection():
    print(f"\n======== [은어 사전 주입 + 번역] 최종 분석 시작 ========")

    # 1. 데이터 가져오기
    query = """
    SELECT community_id, title, COALESCE(description, '') as description
    FROM community_data
    ORDER BY community_id DESC;
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    total_rows = len(df)
    if total_rows == 0: return

    print(f"👉 총 {total_rows}개 데이터 처리")
    print("   1단계: 은어 사전 치환 (떡락 -> HUGE CRASH)")
    print("   2단계: 한영 번역 (Helsinki Model)")
    print("   3단계: 감성 분석 (CryptoBERT)")

    # 2. 모델 로드 (빠른 번역기 + 분석기)
    print("⏳ 모델 로딩 중...")
    
    # 로컬 번역기 (Helsinki - 빠르고 가벼움)
    translator = pipeline("translation", model="Helsinki-NLP/opus-mt-ko-en", device=device, truncation=True, max_length=512)
    # 감성 분석기
    classifier = pipeline("text-classification", model="ElKulako/cryptobert", device=device, truncation=True, max_length=512)

    df['full_text'] = df.apply(lambda row: f"{row['title']} {row['description']}".strip(), axis=1)

    updates = []
    # 배치 사이즈 (메모리 문제 없으면 32 추천)
    batch_size = 8 

    print("🌊 처리 시작...")

    for i in tqdm(range(0, total_rows, batch_size), desc="Processing"):
        batch_df = df.iloc[i : i + batch_size]
        original_texts = batch_df['full_text'].tolist()
        doc_ids = batch_df['community_id'].tolist()
        
        # 1. 은어 주입 (Inject Slang)
        injected_texts = [inject_slang(t) for t in original_texts]
        
        # 2. 번역 (Translation) - 한글이 남은 것만 번역
        final_texts = []
        texts_to_translate = []
        indices_to_translate = []
        
        for idx, txt in enumerate(injected_texts):
            # 영어가 이미 많이 섞여있지만, 여전히 한글 조사가 남아있으므로 번역기 돌림
            # 단, "HUGE CRASH" 같은 영어는 번역기가 그대로 두는 경향이 있음
            if has_korean_char(txt):
                texts_to_translate.append(txt)
                indices_to_translate.append(idx)
            final_texts.append(txt) # 기본은 주입된 텍스트

        if texts_to_translate:
            try:
                # 번역 실행
                translations = translator(texts_to_translate, batch_size=len(texts_to_translate))
                for k_idx, res in zip(indices_to_translate, translations):
                    final_texts[k_idx] = res['translation_text']
            except:
                pass

        # 3. 감성 분석 (Sentiment Analysis)
        try:
            results = classifier(final_texts, batch_size=len(final_texts))
        except:
            continue

        # 4. 결과 저장
        for doc_id, res in zip(doc_ids, results):
            raw_label = res['label']
            if raw_label == 'Bullish': label = 'positive'
            elif raw_label == 'Bearish': label = 'negative'
            else: label = 'neutral'

            updates.append({
                "id": int(doc_id),
                "score": float(res['score']),
                "label": str(label)
            })

    # DB 업데이트
    if updates:
        print(f"💾 {len(updates)}건 DB 저장 중...")
        update_query = text("""
            UPDATE community_data
            SET sentiment_score = :score,
                sentiment_label = :label
            WHERE community_id = :id
        """)
        with engine.begin() as conn:
            conn.execute(update_query, updates)
        print("✅ 완료! 은어 처리가 완벽하게 적용되었습니다.")

if __name__ == "__main__":
    analyze_with_dictionary_injection()