# 🚀 프로젝트 HeartBit: 암호화폐 자동 분석 및 거래 시뮬레이션 시스템

## 1. 프로젝트 개요

**HeartBit**는 뉴스 및 커뮤니티 데이터를 실시간으로 수집하여 AI(BERT, LLM)가 감성을 분석하고, 투자 적합성을 판단하여 리포트를 제공하는 **End-to-End 자동화 시스템**입니다. 추가적으로 **자동 주문 봇**을 통해 트래픽 부하 테스트 및 모의 투자를 수행할 수 있습니다.

* **목표:** 데이터 기반의 객관적인 암호화폐 투자 지표 제공 및 대용량 트래픽 처리 테스트
* **핵심 기술:** Python(Data Engineering/AI), Spring Boot(Backend), React(Frontend), PostgreSQL(DB)

---

## 2. 전체 시스템 아키텍처 (Workflow)

데이터는 **[수집] → [저장] → [분석] → [서빙] → [시각화]** 순서로 흐르며, **[봇]**은 별도로 주문 트래픽을 생성합니다.

```mermaid
graph LR
    A[Data Sources] -->|Crwal/RSS| B(Python Collectors)
    B -->|Raw Data| C[(PostgreSQL DB)]
    C -->|Unprocessed Data| D(Python AI Analyzer)
    D -->|Sentiment Score| C
    E(Python LLM Reporter) -->|Read Score + RSI| C
    E -->|Write Report| C
    F[Spring Boot API] -->|Read Report| C
    G[React Frontend] -->|Polling (1min)| F
    H[Python Traffic Bot] -->|Order Request| F

```

---

## 3. 세부 파이프라인 (Backend Process)

백그라운드에서 4개의 Python 프로세스가 `nohup`으로 24시간 돌아가며 데이터를 생성합니다.

### ① 데이터 수집 (Collectors) - 실시간

* **뉴스 수집기 (`news_collector.py`):** RSS를 통해 주요 암호화폐 뉴스 수집.
* **커뮤니티 수집기 (`community_aggregator.py`):** Reddit 데이터를 수집.
* *특이사항:* 429(Too Many Requests) 차단 방지를 위해 User-Agent 위장 및 Random Delay 적용.



### ② 감성 분석 (Analyzer) - 10분 주기

* **감성 분석기 (`sentiment_analyzer.py`):**
* 수집된 데이터 중 점수가 없는(`NULL`) 데이터를 조회.
* **모델:** `FinBERT`(뉴스), `CryptoBERT`(커뮤니티/SNS).
* **로직:** 텍스트 번역(한→영) → 모델 추론 → 긍정/부정 점수(-1.0 ~ 1.0) DB 저장.



### ③ 리포트 생성 (Reporter) - 30분 주기

* **LLM 분석가 (`llm.py`):**
* 최근 24시간 뉴스/커뮤니티 점수 평균 계산.
* RSI(상대강도지수) 기술적 지표 계산.
* **LLM(Command R+):** 위 데이터를 종합하여 투자 리포트(Markdown) 및 매매 신호(BUY/SELL/HOLD) 생성.
* **저장:** `sentiment_result` 테이블에 최종 결과 저장 (UPSERT 방식).



---

## 4. 데이터베이스 구조 (PostgreSQL)

주요 테이블과 컬럼의 역할입니다.

| 테이블명 | 주요 컬럼 | 역할 |
| --- | --- | --- |
| **`news_data`** | `news_id`, `title`, `news_result`(점수), `published_at` | 뉴스 원본 및 감성 점수 저장 |
| **`community_data`** | `community_id`, `title`, `community_result`(점수), `ups` | 커뮤니티 글 및 감성 점수 저장 |
| **`sentiment_result`** | `category_id` (PK), `total_label`, `news_result`, `community_result`, `full_report`, `rsi` | **최종 분석 결과 테이블** (프론트 표시용) |
| **`orders`** | `order_id`, `member_id`, `category_id`, `price`, `amount` | 주문 내역 (Bot 및 사용자 생성) |

---

## 5. 애플리케이션 (App & Web)

### ☕ Spring Boot (Backend API)

* **역할:** DB와 프론트엔드 사이의 중계자 및 주문 처리.
* **API:** `GET /api/analysis`, `POST /api/orders`
* **로직:** `sentiment_result` 테이블 조회 및 주문 트랜잭션 처리.
* **CORS:** React 개발 환경(localhost:3000) 허용 설정 완료.

### ⚛️ React (Frontend Dashboard)

* **역할:** 사용자에게 분석 결과를 시각화하여 제공.
* **핵심 기능:**
* **자동 업데이트:** `setInterval`을 사용하여 **1분마다** 자동으로 최신 데이터를 가져옴.
* **동적 UI:** 점수에 따라 게이지 색상(🔴호재/🔵악재) 및 캐릭터(🐂황소/🐻곰) 자동 변경.



---

## 6. 메인 시스템 실행 방법 (How to Run)

### 1) Python (데이터 파이프라인)

터미널에서 스크립트 하나로 모든 수집/분석기를 실행합니다.

```bash
# 프로젝트 루트에서 실행
./start_all.sh
# 로그 확인
tail -f logs/analysis.log

```

### 2) Spring Boot (API 서버)

IDE(IntelliJ) 또는 터미널에서 실행합니다. (Port: `8080`)

### 3) React (웹 대시보드)

```bash
npm run dev

```

(Address: `http://localhost:5173`)

---

## 7. [부록] 🤖 자동 주문 트래픽 시뮬레이터 (Python Bot)

Spring Boot 주문 API 부하 테스트 및 자동 거래 시뮬레이션을 위한 봇 매뉴얼입니다.

### 🛠️ 초기 환경 세팅 (필수)

가상환경 문제나 라이브러리 충돌을 방지하기 위해 **기존 환경을 지우고 새로 설정**하는 것을 권장합니다.

**1. 기존 가상환경 초기화**

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

**2. 프로젝트 구조 체크**
아래와 같이 `bot/` 폴더 안에 `__init__.py`가 반드시 있어야 모듈 인식이 됩니다.

```text
project_root/
 ├─ venv/
 ├─ .env                <-- (중요: 보안 주의)
 ├─ requirements.txt
 ├─ run_bot.py          <-- 실행 파일
 └─ bot/
     ├─ __init__.py     <-- 없을 경우 touch bot/__init__.py 로 생성
     ├─ config.py       <-- 설정 파일 수정 필요
     └─ ...

```

### ⚙️ 중요 설정 변경 (Local DB 연동)

팀원마다 로컬 DB의 ID 값이 다르므로 실행 전 **반드시** 아래 내용을 수정해야 합니다.

**1. 코인 ID (CATEGORY_MAP) 수정**
로컬 PostgreSQL 터미널에서 아래 쿼리를 실행하여 본인의 ID를 확인하세요.

```sql
SELECT category_id, category_name, symbol FROM category;

```

**2. 멤버 ID (BOT_MEMBER_ID) 수정**
주문을 실행할 봇 계정의 ID를 확인합니다.

```sql
SELECT member_id, name FROM member;

```

확인된 ID를 `.env`파일의 `BOT_MEMBER_ID` 설정값에 넣으세요.

### 🚀 실행 방법

반드시 프로젝트 루트(최상위 폴더)에서 **`run_bot.py`**를 통해 실행하세요.

```bash
# 가상환경 활성화 상태에서 실행
python run_bot.py

```

### ⚠️ 주의사항 및 트러블슈팅

* **Python 버전:** `3.13` 이상에서는 일부 라이브러리(torch 등)가 불안정할 수 있으니 `3.9~3.11` 사용을 권장합니다.
* **환경 변수:** `.env` 파일에 개인 정보가 포함되므로 팀원들은 각자 로컬 환경에 맞게 수정해야 합니다.
* **경로 확인:** `which python` 명령어를 쳤을 때 경로에 `venv`가 포함되어 있지 않다면 가상환경이 켜지지 않은 것입니다.

---

## 8. 향후 로드맵 (Next Steps)

1. **RAG (검색 증강 생성) 도입:** PostgreSQL `pgvector`를 활용해 뉴스 데이터를 벡터화 저장하여 LLM 정확도 향상.
2. **MLOps 도입:** Docker Compose로 전체 인프라 컨테이너화 및 Airflow 도입.