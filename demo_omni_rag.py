from akasic.storage.graph_store import GraphStore
from akasic.storage.relational_store import RelationalStore
from akasic.storage.vector_store import VectorStore
from akasic.query.planner import QueryPlanner

def mock_embedding(text: str) -> list:
    h = hash(text)
    return [float((h >> i) & 1) for i in range(10)]

def run_demo():
    print("=== AkasicDB Omni RAG Prototype ===")
    g_store = GraphStore()
    r_store = RelationalStore()
    v_store = VectorStore()
    
    print("[1] Loading Graph Topology...")
    g_store.add_edge("Beekeeper_1", "Colony_1", "manages")
    g_store.add_edge("Beekeeper_1", "Hive_2", "manages")
    g_store.add_edge("Beekeeper_2", "Queen_1", "manages")
    
    print("[2] Loading Relational Metadata & Text Chunks...")
    r_store.insert("Colony_1", {"type": "Colony", "timestamp": "2026-09-13", "chunk": "Colony 1 needs specific protective gear for honey extraction."})
    r_store.insert("Hive_2", {"type": "Hive", "timestamp": "2026-06-13", "chunk": "Hive 2 requires monitoring for pests and swarming behaviors."})
    r_store.insert("Queen_1", {"type": "Queen", "timestamp": "2026-02-18", "chunk": "Queen 1 health check."})
    
    print("[3] Generating and Loading Vectors...")
    for entity_id in ["Colony_1", "Hive_2", "Queen_1"]:
        text = r_store.get(entity_id)["chunk"]
        v_store.insert(entity_id, mock_embedding(text))

    planner = QueryPlanner(g_store, r_store, v_store)
    
    question = "What are the essential skills and knowledge needed for new beekeepers to succeed?"
    q_vec = mock_embedding(question)
    print(f"\nUser Question: '{question}'")
    
    selected_time_range = ["2026-06-13", "2026-09-13"]
    print(f"\n[4] Executing Unified Traversal-Join-Similarity Query...")
    op_tree = planner.plan_omni_rag_query(
        start_entities=["Beekeeper_1"],
        edge_type="manages",
        filter_attr="timestamp",
        filter_val=selected_time_range,
        filter_op="IN",
        query_vector=q_vec,
        limit=5
    )
    
    op_tree.open()
    
    print("\n--- Retrieved Context ---")
    retrieved_chunks = []
    while True:
        record = op_tree.next()
        if not record:
            break
        print(f"Match -> Src: {record['src_id']}, Dst: {record['dst_id']}, Sim: {record['similarity']:.4f}")
        print(f"         Chunk: {record['chunk']}")
        retrieved_chunks.append(record['chunk'])
        
    op_tree.close()
    
    print("\n[5] LLM Generation (Mock)")
    context_str = " ".join(retrieved_chunks)
    print(f"LLM Prompt: Context: {context_str} | Question: {question}")
    print("LLM Response: Based on the context, new beekeepers must manage colonies effectively with protective gear, and monitor hives for pests and swarming behaviors.")

if __name__ == "__main__":
    run_demo()
