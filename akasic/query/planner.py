from akasic.storage.graph_store import GraphStore
from akasic.storage.relational_store import RelationalStore
from akasic.storage.vector_store import VectorStore
from akasic.execution.operators import TraversalJoinSimilarity
from typing import List, Any

class QueryPlanner:
    def __init__(self, graph_store: GraphStore, relational_store: RelationalStore, vector_store: VectorStore):
        self.g_store = graph_store
        self.r_store = relational_store
        self.v_store = vector_store

    def plan_omni_rag_query(self, 
                            start_entities: List[str], 
                            edge_type: str, 
                            filter_attr: str, 
                            filter_val: Any, 
                            filter_op: str, 
                            query_vector: List[float], 
                            limit: int) -> TraversalJoinSimilarity:
        operator = TraversalJoinSimilarity(
            graph_store=self.g_store,
            relational_store=self.r_store,
            vector_store=self.v_store,
            start_entities=start_entities,
            edge_type=edge_type,
            filter_attr=filter_attr,
            filter_val=filter_val,
            filter_op=filter_op,
            query_vector=query_vector,
            limit=limit
        )
        return operator
