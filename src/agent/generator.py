import os
import json
import re
import requests
import pandas as pd
import psycopg2
from langchain_cohere import ChatCohere
from searcher import QdrantSearcher
from fetcher import ContextFetcher

class ReportGenerator:
    def __init__(self, db_config, target_coins):
        self.db_config = db_config
        self.target_coins = target_coins
        # 검색기 및 결합기 초기화
        self.searcher = QdrantSearcher()
        self.fetcher = ContextFetcher(db_config)
        self.chat = ChatCohere(model="command-r-plus-08-2024", temperature=0.3)

    def extract_json(self, text):
        try:
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match: return json.loads(match.group(1))
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match: return json.loads(match.group(1))
            return json.loads(text)
        except: return None

    def get_rsi_analysis(self, ticker):
        try:
            url = "https://api.upbit.com/v1/candles/days"
            res = requests.get(url, params={"market": ticker, "count": 200})
            df = pd.DataFrame(res.json()).iloc[::-1]
            df['close'] = df['trade_price']
            delta = df['close'].diff()
            up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
            rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1], f"RSI: {rsi.iloc[-1]:.1f}"
        except: return 50.0, "RSI 계산 실패"

    def fetch_current_data(self, symbol):
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        cur.execute("SELECT title FROM news_data WHERE symbol = %s ORDER BY published_at DESC LIMIT 5", (symbol,))
        news = "\n".join([f"- {r[0]}" for r in cur.fetchall()])
        cur.close()
        conn.close()
        return news

    def save_report(self, cat_id, report_json, rsi_val):
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        query = """
            INSERT INTO sentiment_result (category_id, total_score, total_label, summary, full_report, rsi, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (category_id) DO UPDATE SET
                total_score = EXCLUDED.total_score, total_label = EXCLUDED.total_label,
                summary = EXCLUDED.summary, full_report = EXCLUDED.full_report, rsi = EXCLUDED.rsi, created_at = NOW();
        """
        cur.execute(query, (
            cat_id, report_json.get("confidence_score", 50), report_json.get("signal", "HOLD"),
            report_json.get("primary_reason", ""), report_json.get("full_report", ""), float(rsi_val)
        ))
        conn.commit()
        conn.close()

    def run_analysis(self):
        for coin in self.target_coins:
            print(f">>> [{coin['name']}] RAG 분석 시작...")
            # 1. 최신 뉴스 및 지표 수집
            current_news = self.fetch_current_data(coin['symbol'])
            rsi_val, rsi_msg = self.get_rsi_analysis(coin['ticker'])
            
            # 2. Qdrant 검색 및 과거 맥락 결합 (RAG)
            search_results = self.searcher.search_similar_contexts(current_news, coin['id'])
            past_context = self.fetcher.get_past_original_text(search_results)
            
            # 3. 강화된 프롬프트 구성
            prompt = f"""
            [대상: {coin['name']}]
            [현재 뉴스]: {current_news}
            [지표]: {rsi_msg}
            [과거 유사 사례]: {past_context if past_context else "기록 없음"}
            
            과거 사례를 참고하여 투자 리포트를 JSON으로 작성하세요.
            {{
                "signal": "BUY/SELL/HOLD",
                "confidence_score": 0~100,
                "primary_reason": "한 줄 요약",
                "full_report": "마크다운 형식의 상세 리포트"
            }}
            """
            
            resp = self.chat.invoke(prompt)
            result_json = self.extract_json(resp.content)
            if result_json:
                self.save_report(coin['id'], result_json, rsi_val)
                print(f"✅ {coin['name']} 리포트 저장 완료")