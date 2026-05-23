import networkx as nx
from typing import List, Dict, Any, Optional
import json
import os

class CodeGraph:
    def __init__(self, repo_id: str, storage_dir: Optional[str] = None):
        self.repo_id = repo_id
        if storage_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(root_dir, "storage", "graphs")
        self.storage_path = os.path.join(storage_dir, f"{repo_id}.json")
        os.makedirs(storage_dir, exist_ok=True)
        
        self.graph = nx.DiGraph()

    def build_from_parse_results(self, all_parse_results: List[Dict[str, Any]]):
        """
        Builds the relationship graph from all parsed files in the repo.
        Following PRD Section 7.7 requirements.
        """
        self.graph.clear()
        
        # 1. Add Nodes (Files, Classes, Functions)
        for result in all_parse_results:
            file_path = result['file_path']
            self.graph.add_node(file_path, type='file')

            for cls in result.get('classes', []):
                cls_id = f"{file_path}::{cls['name']}"
                self.graph.add_node(cls_id, type='class', name=cls['name'], file_path=file_path)
                self.graph.add_edge(file_path, cls_id, relation='contains')

            for func in result.get('functions', []):
                func_id = f"{file_path}::{func['name']}"
                self.graph.add_node(func_id, type='function', name=func['name'], file_path=file_path)
                
                # Check if it's inside a class (basic heuristic: line range overlap)
                parent = file_path
                for cls in result.get('classes', []):
                    if cls['start_line'] <= func['start_line'] and cls['end_line'] >= func['end_line']:
                        parent = f"{file_path}::{cls['name']}"
                        break
                
                self.graph.add_edge(parent, func_id, relation='contains')

        # 2. Add Edges (Calls & Imports)
        for result in all_parse_results:
            file_path = result['file_path']
            
            # Link Imports
            # Note: Import strings can be complex (e.g. 'from src.utils import x')
            # For now, we do a basic contains check for cross-file links
            for imp in result.get('imports', []):
                for other_res in all_parse_results:
                    other_path = other_res['file_path']
                    if other_path != file_path and (other_path.replace("\\", "/").split("/")[-1] in imp or imp in other_path):
                        self.graph.add_edge(file_path, other_path, relation='imports')

            # Link Function/Class Calls
            symbols = result.get('functions', []) + result.get('classes', [])
            for sym in symbols:
                sym_id = f"{file_path}::{sym['name']}"
                for call in sym.get('calls', []):
                    targets = self._resolve_call_targets(call, all_parse_results, file_path)
                    for target_id in targets:
                        if self.graph.has_node(target_id):
                            self.graph.add_edge(sym_id, target_id, relation='calls')

    def _resolve_call_targets(self, call_name: str, all_results: List[Dict], current_file: str) -> List[str]:
        targets = []
        # 1. Look in the same file first
        for res in all_results:
            if res['file_path'] == current_file:
                for f in res.get('functions', []) + res.get('classes', []):
                    if f['name'] == call_name:
                        targets.append(f"{res['file_path']}::{f['name']}")
        
        # 2. Look in other files if not found or always? 
        # For now, look everywhere but we could optimize with import knowledge
        if not targets:
            for res in all_results:
                if res['file_path'] != current_file:
                    for f in res.get('functions', []) + res.get('classes', []):
                        if f['name'] == call_name:
                            targets.append(f"{res['file_path']}::{f['name']}")
        
        return targets

    def get_neighbors(self, node_id: str) -> Dict[str, List[Dict]]:
        """Returns callers and callees for a given node."""
        if not self.graph.has_node(node_id):
            return {"incoming": [], "outgoing": []}
        
        callers = []
        for p in self.graph.predecessors(node_id):
            edge_data = self.graph.get_edge_data(p, node_id)
            node_data = self.graph.nodes[p]
            callers.append({"id": p, "relation": edge_data['relation'], "type": node_data.get('type')})
            
        callees = []
        for s in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, s)
            node_data = self.graph.nodes[s]
            callees.append({"id": s, "relation": edge_data['relation'], "type": node_data.get('type')})
            
        return {
            "incoming": callers,
            "outgoing": callees
        }

    def save(self):
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, 'w') as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                # NetworkX version compatibility
                if isinstance(data, dict) and 'nodes' in data:
                    self.graph = nx.node_link_graph(data)
                else:
                    self.graph = nx.DiGraph()
