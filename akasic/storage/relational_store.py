from typing import Dict, List, Any

class RelationalStore:
    def __init__(self):
        # Table-like structure: entity_id -> { attribute: value }
        self.records: Dict[str, Dict[str, Any]] = {}

    def insert(self, entity_id: str, properties: Dict[str, Any]):
        self.records[entity_id] = properties

    def get(self, entity_id: str) -> Dict[str, Any]:
        return self.records.get(entity_id, {})

    def filter(self, attribute: str, value: Any, op: str = '==') -> List[str]:
        # Simple scan simulation for prototype
        results = []
        for entity_id, props in self.records.items():
            if attribute in props:
                prop_val = props[attribute]
                if op == '==' and prop_val == value:
                    results.append(entity_id)
                elif op == '>=' and prop_val >= value:
                    results.append(entity_id)
                elif op == '<=' and prop_val <= value:
                    results.append(entity_id)
                elif op == 'IN' and prop_val in value:
                    results.append(entity_id)
        return results
