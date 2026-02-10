import torch
from transformers import pipeline
from langdetect import detect, DetectorFactory

# 결과 재현을 위해 시드 고정
DetectorFactory.seed = 0

# 문제의 데이터 5개 (사용자님 로그 기반)
samples = [
    {"text": "경은 강 무.....무섭다...", "manual_trans": "It is sc...scary..."},
    {"text": "Chatti app powered by $CHAT on Solana is here to change how social media works", "manual_trans": "Chatti app powered by $CHAT on Solana is here to change how social media works"},
    {"text": "성남 김 오늘 점심때까지  보합 에 갖다 놓으세요~~ 느낌 알쥬?", "manual_trans": "Put it at flat(neutral) by lunch today~~ You know the feeling right?"},
    {"text": "Multicall drained token <a href=...>", "manual_trans": "Multicall drained token"},
    {"text": "국 대 그냥 롱이네 누가 사는거야", "manual_trans": "Just long position. Who is buying?"}
]

# 모델 로드 (영어 전문가 CryptoBERT)
model_name = "ElKulako/cryptobert"
if torch.backends.mps.is_available():
    device = 0 # MPS
else:
    device = -1

pipe = pipeline("text-classification", model=model_name, device=device)

print(f"\n{'='*80}")
print(f"🕵️‍♂️ 정밀 진단: 언어 감지 & 번역 전략 테스트")
print(f"{'='*80}\n")

for i, item in enumerate(samples):
    text = item['text']
    trans_text = item['manual_trans']
    
    # 1. 언어 감지 확인
    try:
        detected_lang = detect(text)
    except:
        detected_lang = "error"
    
    # 2. CryptoBERT에게 번역된 문장 먹여보기
    res = pipe(trans_text)[0]
    
    print(f"[글 {i+1}]")
    print(f"  📝 원문: {text[:50]}...")
    print(f"  🔍 감지된 언어: {detected_lang} ", end="")
    
    if detected_lang == 'ko' and i in [1, 3]: # 영어인데 한글로 오인된 경우
        print("❌ (영어인데 한국어로 착각함 -> 한국어 모델이 억지로 해석해서 망함)")
    elif detected_lang == 'ko':
        print("✅ (정상)")
    else:
        print("✅ (정상)")

    print(f"  🇺🇸 번역 후 CryptoBERT 예측: \"{trans_text}\"")
    print(f"  👉 결과: {res['label']} ({res['score']:.4f})")
    print("-" * 50)