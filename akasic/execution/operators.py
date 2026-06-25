from typing import List, Dict, Any, Tuple, Optional
from akasic.storage.graph_store import GraphStore
from akasic.storage.relational_store import RelationalStore
from akasic.storage.vector_store import VectorStore

class Operator:
    def open(self):
        pass
    def next(self) -> Optional[Dict[str, Any]]:
        pass
    def close(self):
        pass

class SequentialScan(Operator):
    def __init__(self, entities: List[str]):
        self.entities = entities
        self.cursor = 0

    def open(self):
        self.cursor = 0

    def next(self) -> Optional[Dict[str, Any]]:
        if self.cursor < len(self.entities):
            val = self.entities[self.cursor]
            self.cursor += 1
            return {"entity_id": val}
        return None

class TraversalJoinSimilarity(Operator):
    """
    Implements the core operator of AkasicDB combining Vector, Graph, and Relational.
    This simulates pushing down graph traversal, metadata filtering, and 
    ordering by vector similarity into a single execution node.
    """
    def __init__(self, 
                 graph_store: GraphStore, 
                 relational_store: RelationalStore, 
                 vector_store: VectorStore,
                 start_entities: List[str],
                 edge_type: str,
                 filter_attr: str,
                 filter_val: Any,
                 filter_op: str,
                 query_vector: List[float],
                 limit: int):
        self.graph_store = graph_store
        self.relational_store = relational_store
        self.vector_store = vector_store
        
        self.start_entities = start_entities
        self.edge_type = edge_type
        self.filter_attr = filter_attr
        self.filter_val = filter_val
        self.filter_op = filter_op
        self.query_vector = query_vector
        self.limit = limit
        
        self.results = []
        self.cursor = 0

    def open(self):
        candidate_destinations = set()
        
        # 1. Graph Traversal
        for src in self.start_entities:
            neighbors = self.graph_store.get_neighbors(src, self.edge_type)
            for n in neighbors:
                candidate_destinations.add((src, n))
                
        valid_results = []
        # 2. Relational Filtering & Vector Scoring
        for src, dst in candidate_destinations:
            props = self.relational_store.get(dst)
            if self.filter_attr in props:
                val = props[self.filter_attr]
                # Evaluate filter
                passed = False
                if self.filter_op == '==' and val == self.filter_val: passed = True
                elif self.filter_op == 'IN' and val in self.filter_val: passed = True
                elif self.filter_op == '>=' and val >= self.filter_val: passed = True
                elif self.filter_op == '<=' and val <= self.filter_val: passed = True
                
                if passed:
                    # Vector similarity
                    vec = self.vector_store.get(dst)
                    score = 0.0
                    if vec and self.query_vector:
                        score = self.vector_store.cosine_similarity(self.query_vector, vec)
                    
                    valid_results.append({
                        "src_id": src,
                        "dst_id": dst,
                        "chunk": props.get("chunk", ""),
                        "timestamp": props.get("timestamp", ""),
                        "similarity": score
                    })
                    
        # 3. Global Top-K
        valid_results.sort(key=lambda x: x["similarity"], reverse=True)
        self.results = valid_results[:self.limit]
        self.cursor = 0

    def next(self) -> Optional[Dict[str, Any]]:
        if self.cursor < len(self.results):
            val = self.results[self.cursor]
            self.cursor += 1
            return val
        return None

    def close(self):
        self.results = []
        self.cursor = 0
