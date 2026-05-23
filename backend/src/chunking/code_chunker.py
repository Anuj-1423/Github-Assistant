from typing import List, Dict, Any
import hashlib

class CodeChunker:
    """
    Intelligent code chunking by function, class, and file-level context.
    Following PRD Section 7.3 requirements.
    """
    def __init__(self, repo_id: str, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.repo_id = repo_id
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_file(self, file_path: str, parse_results: Dict[str, Any], content: str) -> List[Dict[str, Any]]:
        chunks = []
        
        # 1. Class Chunks
        for cls in parse_results.get('classes', []):
            chunk_content = f"File: {file_path}\nClass: {cls['name']}\n\n{cls['code']}"
            chunks.append({
                "chunk_id": f"{self.repo_id}_{file_path}_class_{cls['name']}_{cls['start_line']}",
                "repo_id": self.repo_id,
                "file_path": file_path,
                "chunk_type": "class",
                "symbol_name": cls['name'],
                "start_line": cls['start_line'],
                "end_line": cls['end_line'],
                "content": chunk_content,
                "content_hash": self._generate_hash(cls['code'])
            })

        # 2. Function Chunks
        for func in parse_results.get('functions', []):
            # Check if function is already inside a class chunk (optional, but keep it for now)
            chunk_content = f"File: {file_path}\nFunction: {func['name']}\n\n{func['code']}"
            chunks.append({
                "chunk_id": f"{self.repo_id}_{file_path}_func_{func['name']}_{func['start_line']}",
                "repo_id": self.repo_id,
                "file_path": file_path,
                "chunk_type": "function",
                "symbol_name": func['name'],
                "start_line": func['start_line'],
                "end_line": func['end_line'],
                "content": chunk_content,
                "content_hash": self._generate_hash(func['code'])
            })

        # 3. File Summary Chunk (Respecting configured chunk size)
        imports = "\n".join(parse_results.get('imports', []))
        summary_header = f"File: {file_path}\nType: File Summary\nImports:\n{imports}\n\nContent Preview:\n"
        
        # Calculate available space for content
        header_len = len(summary_header)
        max_content_len = max(500, self.chunk_size - header_len)
        
        summary_content = summary_header + content[:max_content_len]
        chunks.append({
            "chunk_id": f"{self.repo_id}_{file_path}_summary",
            "repo_id": self.repo_id,
            "file_path": file_path,
            "chunk_type": "file_summary",
            "symbol_name": "file_summary",
            "start_line": 1,
            "end_line": len(content.splitlines()),
            "content": summary_content,
            "content_hash": self._generate_hash(summary_content)
        })

        return chunks

    def _generate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
