작성해주신 내용을 바탕으로 팀원들이 한눈에 보고 따라 할 수 있도록 **[프로젝트 실행 매뉴얼]** 형태로 깔끔하게 정리해 드립니다. 이 내용을 그대로 복사해서 `README.md`에 업데이트하거나 공지용으로 사용하세요.

---

# 🤖 자동 주문 트래픽 시뮬레이터 (Python Bot)

Spring Boot 주문 API 부하 테스트 및 자동 거래 시뮬레이션을 위한 봇입니다.

## 🛠️ 초기 환경 세팅 (필수)

가상환경 문제나 라이브러리 충돌을 방지하기 위해 **기존 환경을 지우고 새로 설정**하는 것을 권장합니다.

### 1. 기존 가상환경 초기화

```bash
# 1. 기존 가상환경 삭제
rm -rf venv

# 2. 가상환경 생성 (Python 3.9 ~ 3.11 권장)
python -m venv venv

# 3. 가상환경 활성화
source venv/bin/activate  # (Windows는 .\venv\Scripts\activate)

# 4. pip 최신화 및 의존성 설치
python -m pip install --upgrade pip
pip install -r requirements.txt

```

### 2. 프로젝트 구조 체크

아래와 같이 `bot/` 폴더 안에 `__init__.py`가 반드시 있어야 모듈 인식이 됩니다.

```text
project_root/
 ├─ venv/
 ├─ .env                <-- (중요: 보안 주의)
 ├─ requirements.txt
 ├─ run_bot.py          <-- 실행 파일
 └─ bot/
     ├─ __init__.py     <-- 없을 경우 touch bot/__init__.py 로 생성
     ├─ run_bot.py
     ├─ config.py       <-- 설정 파일 수정 필요
     └─ ...

```

---

## ⚙️ 중요 설정 변경 (Local DB 연동)

팀원마다 로컬 DB의 ID 값이 다르므로 실행 전 **반드시** 아래 내용을 수정해야 합니다.

### 1. 코인 ID (CATEGORY_MAP) 수정

로컬 PostgreSQL 터미널에서 아래 쿼리를 실행하여 본인의 ID를 확인하세요.

```sql
SELECT category_id, category_name, symbol FROM category;

```

-- 1. 삭제 대상(리스트에 없는 4개)과 연결된 주문/거래 내역 먼저 정리
DELETE FROM trade WHERE order_id IN (
    SELECT order_id FROM orders 
    WHERE category_id NOT IN (1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20)
);

DELETE FROM orders 
WHERE category_id NOT IN (1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20);

DELETE FROM interest 
WHERE category_id NOT IN (1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20);

DELETE FROM asset 
WHERE category_id NOT IN (1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20);

-- 2. 해당하지 않는 나머지 4개 코인 삭제
DELETE FROM category 
WHERE category_id NOT IN (1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20);

-- 3. 최종 남은 16개 코인 확인
SELECT category_id, symbol, category_name FROM category ORDER BY category_id;

확인된 ID를 `bot/config.py` 파일의 `CATEGORY_MAP`에 업데이트하고 **저장(Cmd+S)** 하세요.

### 2. 멤버 ID (BOT_MEMBER_ID) 수정

주문을 실행할 봇 계정의 ID를 확인합니다.

```sql
SELECT member_id, name FROM member;

```

확인된 ID를 `.env`파일의 `BOT_MEMBER_ID` 설정값에 넣으세요.

---

## 🚀 실행 방법

반드시 프로젝트 루트(최상위 폴더)에서 **`run_bot.py`**를 통해 실행하세요.

```bash
# 가상환경 활성화 상태에서 실행
python run_bot.py

```

---

## ⚠️ 주의사항 및 트러블슈팅

* **Python 버전:** `3.13` 이상에서는 일부 라이브러리(torch 등)가 불안정할 수 있으니 `3.9~3.11` 사용을 권장합니다.
* **환경 변수:** `.env` 파일에 작성자님의 개인 정보가 포함되어 있을 수 있습니다. 팀원들은 각자 본인의 로컬 환경에 맞게 `.env` 내용을 수정해야 합니다.
* **경로 확인:** `which python` 명령어를 쳤을 때 경로에 `venv`가 포함되어 있지 않다면 가상환경이 켜지지 않은 것입니다.
* **필수 패키지:** `psycopg2-binary`, `schedule`, `transformers` 등이 `requirements.txt`에 포함되어 있는지 확인하세요.

---