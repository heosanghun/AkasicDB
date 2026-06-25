import math
from typing import Dict, List, Tuple

class VectorStore:
    def __init__(self):
        # entity_id -> vector
        self.vectors: Dict[str, List[float]] = {}

    def insert(self, entity_id: str, vector: List[float]):
        self.vectors[entity_id] = vector

    def get(self, entity_id: str) -> List[float]:
        return self.vectors.get(entity_id)

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)

    def similarity_search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        results = []
        for entity_id, vector in self.vectors.items():
            score = self.cosine_similarity(query_vector, vector)
            results.append((entity_id, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
