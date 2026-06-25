from collections import defaultdict
from typing import Dict, List, Set, Tuple

class GraphStore:
    def __init__(self):
        # Adjacency list for graph topology: src_id -> list of (edge_type, dst_id)
        self.edges = defaultdict(list)
        self.nodes = set()

    def add_node(self, node_id: str):
        self.nodes.add(node_id)

    def add_edge(self, src_id: str, dst_id: str, edge_type: str):
        self.add_node(src_id)
        self.add_node(dst_id)
        self.edges[src_id].append((edge_type, dst_id))

    def get_neighbors(self, src_id: str, edge_type: str = None) -> List[str]:
        neighbors = []
        for e_type, dst_id in self.edges.get(src_id, []):
            if edge_type is None or e_type == edge_type:
                neighbors.append(dst_id)
        return neighbors
