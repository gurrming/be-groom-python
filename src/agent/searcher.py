import torch
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

class QdrantSearcher:
    def __init__(self):
        # 맥북 가속(MPS) 설정 및 모델 로드
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = SentenceTransformer('intfloat/multilingual-e5-small', device=self.device)
        self.client = QdrantClient(url="http://localhost:6333")

    def search_similar_contexts(self, query_text, category_id, limit=3):
        # E5 모델 지침: 검색어 앞에 'query: ' 추가
        query_vector = self.model.encode(f"query: {query_text}").tolist()
        
        # 특정 종목 필터 설정
        search_filter = Filter(must=[FieldCondition(key="category_id", match=MatchValue(value=category_id))])
        
        results = []
        for col in ["news_collection", "community_collection"]:
            search_res = self.client.search(
                collection_name=col,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit
            )
            # 출처 정보를 포함하여 ID 저장
            for r in search_res:
                results.append({
                    "id": r.id,
                    "source": "news" if "news" in col else "community",
                    "score": r.score
                })
        
        # 유사도 순으로 정렬 후 상위 결과 반환
        return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]