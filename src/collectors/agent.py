import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, func
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from fastapi.middleware.cors import CORSMiddleware

# 1. DB 접속 정보 (알려주신 정보 반영)
DATABASE_URL = "postgresql://postgres:0000@localhost:15432/app"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. SQLAlchemy 2.0 스타일 Base
class Base(DeclarativeBase):
    pass

# 3. 테이블 매핑
class NewsData(Base):
    __tablename__ = "news_data"
    news_id = Column(Integer, primary_key=True, index=True)
    coin_name = Column(String)
    sentiment_score = Column(Float)

class CommunityData(Base):
    __tablename__ = "community_data"
    community_id = Column(Integer, primary_key=True, index=True)
    coin_name = Column(String)
    sentiment_score = Column(Float)

# 4. FastAPI 앱 초기화 (명세서 스타일 반영)
app = FastAPI(
    title="HeartBit AI 분석 API",
    description="뉴스 및 커뮤니티 데이터를 기반으로 한 AI 심리 분석 서비스를 제공합니다.",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. API 엔드포인트 (기존 명세서 규칙: /api/... 사용)
@app.get(
    "/api/sentiment/{coin_name}", 
    tags=["AI 분석 API"], 
    summary="코인 시장 심리 분석 조회"
)
def get_coin_sentiment(coin_name: str, db: Session = Depends(get_db)):
    # 뉴스 데이터 평균 (40% 비중)
    news_avg = db.query(func.avg(NewsData.sentiment_score))\
                 .filter(NewsData.coin_name == coin_name.upper())\
                 .scalar() or 0.5
    
    # 커뮤니티 데이터 평균 (60% 비중)
    comm_avg = db.query(func.avg(CommunityData.sentiment_score))\
                 .filter(CommunityData.coin_name == coin_name.upper())\
                 .scalar() or 0.5
    
    # 통합 점수 계산
    total_score = (news_avg * 0.4) + (comm_avg * 0.6)
    
    return {
        "coin": coin_name.upper(),
        "total_score": round(total_score, 2),
        "news_score": round(news_avg, 2),
        "community_score": round(comm_avg, 2)
    }

# 서버 체크용 기본 경로
@app.get("/", tags=["System"])
def health_check():
    return {"status": "AI Agent Server is running", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)