import os
import sys
import time
import random

# Add parent directory to path to import akasic modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from akasic.storage.graph_store import GraphStore
from akasic.storage.relational_store import RelationalStore
from akasic.storage.vector_store import VectorStore
from akasic.query.planner import QueryPlanner

def mock_embedding(text: str) -> list:
    h = hash(text)
    return [float((h >> i) & 1) for i in range(10)]

def run_benchmark():
    print("=== AkasicDB Synthetic Data Engine Load Test ===")
    
    g_store = GraphStore()
    r_store = RelationalStore()
    v_store = VectorStore()
    
    num_vessels = 100
    num_blocks = 500
    num_containers = 10000
    num_cranes = 50
    
    print(f"Generating Synthetic Data: {num_vessels} Vessels, {num_blocks} Blocks, {num_containers} Containers, {num_cranes} Cranes...")
    
    start_time = time.time()
    
    # 1. Graph Data Generation
    # Distribute blocks to vessels
    blocks_per_vessel = num_blocks // num_vessels
    for v_id in range(num_vessels):
        v_name = f"Vessel_{v_id}"
        for b in range(blocks_per_vessel):
            b_name = f"YardBlock_{v_id * blocks_per_vessel + b}"
            g_store.add_edge(v_name, b_name, "discharges_to")
            
            # 2. Relational & Vector Data for Blocks
            chunk_text = f"Block {b_name} has {random.randint(10, 90)}% congestion."
            r_store.insert(b_name, {
                "type": "Block",
                "timestamp": f"2026-06-25 14:00",
                "congestion": random.randint(10, 90),
                "chunk": chunk_text
            })
            v_store.insert(b_name, mock_embedding(chunk_text))
            
    # Distribute containers to blocks
    containers_per_block = num_containers // num_blocks
    for b_id in range(num_blocks):
        b_name = f"YardBlock_{b_id}"
        for c in range(containers_per_block):
            c_name = f"Container_{b_id * containers_per_block + c}"
            g_store.add_edge(b_name, c_name, "contains")
            
            # Randomly assign handled_by crane
            crane_name = f"Crane_{random.randint(0, num_cranes - 1)}"
            g_store.add_edge(c_name, crane_name, "handled_by")
            
            # Relational & Vector Data for Containers
            rehandling_prob = random.uniform(0.0, 30.0)
            chunk_text = f"Container {c_name} requires special handling. Rehandling prob: {rehandling_prob:.1f}%."
            r_store.insert(c_name, {
                "type": "Container",
                "timestamp": f"2026-06-25 14:10",
                "rehandling_prob": rehandling_prob,
                "chunk": chunk_text
            })
            v_store.insert(c_name, mock_embedding(chunk_text))
            
    # Relational & Vector Data for Cranes
    for cr_id in range(num_cranes):
        cr_name = f"Crane_{cr_id}"
        chunk_text = f"Crane {cr_name} operational status: Normal. Moves: {random.randint(50, 300)}."
        r_store.insert(cr_name, {
            "type": "Equipment",
            "timestamp": f"2026-06-25 14:20",
            "chunk": chunk_text
        })
        v_store.insert(cr_name, mock_embedding(chunk_text))

    ingestion_time = time.time() - start_time
    total_entities = num_blocks + num_containers + num_cranes
    total_edges = num_blocks + num_containers + num_containers # vessel->block, block->container, container->crane
    
    print(f"[Done] Ingestion Time: {ingestion_time:.4f} seconds")
    print(f"Total Graph Nodes: {len(g_store.nodes)}")
    print(f"Total Graph Edges Generated: {total_edges}")
    print(f"Total Vector Embeddings: {len(v_store.vectors)}")
    print(f"Total Relational Records: {len(r_store.records)}")
    
    print("\n--- Running Omni RAG Pipeline Query ---")
    planner = QueryPlanner(g_store, r_store, v_store)
    
    query_text = "Check congestion and rehandling risks for Vessel_50 operations."
    q_vec = mock_embedding(query_text)
    
    # Target Vessel_50 and one of its blocks and its containers to simulate the RAG router picking the intent
    target_vessel = "Vessel_50"
    target_block = "YardBlock_250" # 50 * 5 = 250
    # Containers in Block 250: Container_5000 to 5019
    target_containers = [f"Container_{i}" for i in range(5000, 5020)]
    
    start_entities = [target_vessel, target_block] + target_containers
    
    q_start_time = time.time()
    
    op_tree = planner.plan_omni_rag_query(
        start_entities=start_entities,
        edge_type=None,
        filter_attr="timestamp",
        filter_val=["2026-06-25 14:00", "2026-06-25 14:10", "2026-06-25 14:20"],
        filter_op="IN",
        query_vector=q_vec,
        limit=10
    )
    
    op_tree.open()
    results = []
    while True:
        record = op_tree.next()
        if not record:
            break
        results.append(record)
    op_tree.close()
    
    query_time = time.time() - q_start_time
    
    print(f"[Done] Query Execution Time: {query_time:.4f} seconds ({(query_time*1000):.2f} ms)")
    print(f"Retrieved Top-{len(results)} valid chunks successfully after Triple-Store join and filtering.")
    print("Sample Top 1 Result:")
    if results:
        print(f" - Target Node: {results[0]['dst_id']}")
        print(f" - Cosine Similarity: {results[0]['similarity']:.4f}")
        print(f" - Chunk: {results[0]['chunk']}")

if __name__ == "__main__":
    run_benchmark()
