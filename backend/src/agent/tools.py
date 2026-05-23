from langchain_core.tools import BaseTool, StructuredTool
from typing import List, Dict, Any, Optional
from src.retrieval.hybrid_retriever import HybridRetriever
from src.graph.graph_builder import CodeGraph
import os

class CodeIntelligenceTools:
    def __init__(self, repo_id: str, retriever: HybridRetriever, graph: CodeGraph, repo_path: str):
        self.repo_id = repo_id
        self.retriever = retriever
        self.graph = graph
        self.repo_path = repo_path

    def search_code(self, query: str) -> str:
        """Search for code snippets, functions, or classes using hybrid semantic and keyword search. 
        Useful for finding where specific logic (like 'payment' or 'auth') is implemented."""
        results = self.retriever.retrieve(query, limit=5)
        formatted_results = []
        for r in results:
            formatted_results.append(f"--- File: {r['file_path']} ---\n{r['content']}\n")
        return "\n".join(formatted_results) if formatted_results else "No relevant code found."

    def get_code_relationships(self, symbol_id: str) -> str:
        """Get the callers (incoming) and callees (outgoing) for a specific code symbol (function or class).
        Format for symbol_id is usually 'path/to/file.py::SymbolName'."""
        relations = self.graph.get_neighbors(symbol_id)
        
        output = [f"Relationships for {symbol_id}:"]
        output.append("Incoming (Callers/Contains):")
        for inc in relations['incoming']:
            output.append(f"- {inc['id']} ({inc['relation']})")
        
        output.append("Outgoing (Callees/Contained):")
        for out in relations['outgoing']:
            output.append(f"- {out['id']} ({out['relation']})")
            
        return "\n".join(output)

    def read_file(self, file_path: str) -> str:
        """Read the full content of a file in the repository. Use this when you need more context around a search result."""
        # Sanitize path to stay within repo
        abs_path = os.path.abspath(os.path.join(self.repo_path, file_path))
        if not abs_path.startswith(os.path.abspath(self.repo_path)):
            return "Error: Access denied. Path outside repository."
        
        if not os.path.exists(abs_path):
            return f"Error: File {file_path} not found."
            
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def get_tools(self) -> List[BaseTool]:
        return [
            StructuredTool.from_function(
                func=self.search_code,
                name="search_code",
                description=(
                    "Search for code snippets, functions, or classes using hybrid semantic and keyword search. "
                    "Useful for finding where specific logic is implemented."
                ),
            ),
            StructuredTool.from_function(
                func=self.get_code_relationships,
                name="get_code_relationships",
                description=(
                    "Get incoming and outgoing relationships for a symbol id like "
                    "'path/to/file.py::SymbolName'."
                ),
            ),
            StructuredTool.from_function(
                func=self.read_file,
                name="read_file",
                description="Read the full content of a repository file path.",
            ),
        ]
