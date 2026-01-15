# 🤖 자동 주문 트래픽 시뮬레이터

Spring Boot 주문 API의 부하 테스트 및 자동 거래 시뮬레이션을 위한 Python 기반 봇입니다.

## 주요 기능
- 다중 스레드 주문 요청
- 랜덤 매수/매도 시뮬레이션
- 실시간 성공/실패 로그 출력
- .env 기반 환경 설정 분리

## 실행 방법
가상 환경 외에 기본적으로 해야할 것들 config.py에서 여기서 코인이 로컬 DB랑 맞는지 확인
CATEGORY_MAP = {
    "BTC": , "ETH": , "SOL": , "XRP": ,
    "ADA": , "DOGE": , "DOT": , "LTC": ,
    "LINK": , "TRX": , "ATOM": , "FIL": ,
    "ALGO": , "SHIB": , "EOS": , "MATIC": 
}
수정 후 command + s 를 눌러서 꼭 저장하기!!!!!!!

.env 파일은 깃허브에 올리지 말라는데 이미 올려버려서 어쩔 수 없이 
각자 로컬 DB의 bot_member_id랑 맞는지 확인하기

실행은 꼭 run_bot.py에서만 실행시키기 나머지는 상관없는거

🛠 BOT 실행 환경 세팅 가이드 (필수)

⚠️ 기존 가상환경(venv)이 있다면 반드시 삭제 후 재생성하세요.
Python 패키지 인식 문제는 대부분 “깨진 가상환경” 때문에 발생합니다.

1️⃣ 기존 가상환경 삭제

프로젝트 루트에서 실행

rm -rf venv

2️⃣ Python 버전 확인 (권장: 3.9 ~ 3.11)
python --version


❌ Python 3.13 / 3.14 사용 시 일부 라이브러리 호환 문제 발생 가능
✅ Python 3.9 ~ 3.11 권장

3️⃣ 가상환경 새로 생성
macOS / Linux
python -m venv venv

4️⃣ 가상환경 활성화
macOS / Linux
source venv/bin/activate

활성화되면 프롬프트에 (venv) 표시가 나와야 합니다.

5️⃣ pip 최신화 (중요)
python -m pip install --upgrade pip

6️⃣ 의존성 설치
pip install -r requirements.txt


❗ 에러 발생 시:

가상환경이 활성화 상태인지

pip가 venv 경로를 사용하는지 확인

which python
which pip


출력 경로에 venv가 포함되어야 정상입니다.

8️⃣ 프로젝트 구조 확인 (필수)

아래 구조가 아니면 실행이 깨질 수 있습니다.

project_root/
 ├─ venv/
 ├─ .env
 ├─ requirements.txt
 ├─ bot/
 │   ├─ __init__.py   ← 반드시 있어야 함
 │   ├─ run_bot.py
 │   ├─ config.py
 │   ├─ price.py
 │   ├─ worker.py
 │   └─ order.py

touch bot/__init__.py

9️⃣ BOT 실행 방법 (권장 방식)
✅ 가장 안정적인 실행 (권장)
python bot/run_bot.py


⚠️ 패키지 방식 실행 (구조 정확해야 함)
python -m bot.run_bot


이 방식은 다음 조건이 모두 충족되어야 합니다:

bot/__init__.py 존재

프로젝트 루트에서 실행

import가 bot.xxx 또는 .xxx 형태
