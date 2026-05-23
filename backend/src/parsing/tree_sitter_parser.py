import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Query, QueryCursor
from typing import List, Dict, Any, Optional
import os

class TreeSitterParser:
    def __init__(self, language_name: str):
        self.language_name = language_name
        if language_name == "python":
            self.language = Language(tspython.language())
        elif language_name == "typescript":
            self.language = Language(tstypescript.language_typescript())
        elif language_name == "javascript":
            self.language = Language(tsjavascript.language())
        else:
            raise ValueError(f"Unsupported language: {language_name}")
        
        self.parser = Parser(self.language)

    def parse_file(self, content: str) -> Dict[str, Any]:
        tree = self.parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        return {
            "functions": self._extract_symbols(root_node, "function", content),
            "classes": self._extract_symbols(root_node, "class", content),
            "imports": self._extract_imports(root_node, content),
            "calls": self._extract_calls(root_node, content) # Global calls
        }

    def _extract_symbols(self, root_node, symbol_type: str, content: str) -> List[Dict]:
        query_text = ""
        if self.language_name == "python":
            if symbol_type == "function":
                query_text = "(function_definition name: (identifier) @name) @symbol"
            else:
                query_text = "(class_definition name: (identifier) @name) @symbol"
        elif self.language_name in ["typescript", "javascript"]:
            if symbol_type == "function":
                query_text = """
                (function_declaration name: (identifier) @name) @symbol
                (method_definition name: (property_identifier) @name) @symbol
                (lexical_declaration (variable_declarator name: (identifier) @name value: (arrow_function))) @symbol
                """
            else:
                query_text = "(class_declaration name: (identifier) @name) @symbol"
        
        if not query_text:
            return []

        query = Query(self.language, query_text)
        cursor = QueryCursor(query)
        matches = cursor.matches(root_node)
        
        symbols = []
        for _, captures in matches:
            symbol_nodes = captures.get("symbol", [])
            name_nodes = captures.get("name", [])
            
            if symbol_nodes:
                node = symbol_nodes[0]
                name = "anonymous"
                if name_nodes:
                    name = content[name_nodes[0].start_byte:name_nodes[0].end_byte]
                
                # Extract calls WITHIN this symbol
                symbol_calls = self._extract_calls(node, content)
                
                symbols.append({
                    "name": name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "code": content[node.start_byte:node.end_byte],
                    "calls": symbol_calls
                })
            
        return symbols

    def _extract_imports(self, root_node, content: str) -> List[str]:
        query_text = ""
        if self.language_name == "python":
            query_text = """
            (import_statement) @import
            (import_from_statement) @import
            """
        elif self.language_name in ["typescript", "javascript"]:
            query_text = "(import_statement) @import"
        
        if not query_text:
            return []

        query = Query(self.language, query_text)
        cursor = QueryCursor(query)
        matches = cursor.matches(root_node)
        
        imports = []
        for _, captures in matches:
            for node in captures.get("import", []):
                imports.append(content[node.start_byte:node.end_byte])
        return imports

    def _extract_calls(self, root_node, content: str) -> List[str]:
        query_text = ""
        if self.language_name == "python":
            query_text = """
            (call function: (identifier) @call)
            (call function: (attribute attribute: (identifier) @call))
            """
        elif self.language_name in ["typescript", "javascript"]:
            query_text = """
            (call_expression function: (identifier) @call)
            (call_expression function: (member_expression property: (property_identifier) @call))
            """
        
        if not query_text:
            return []

        query = Query(self.language, query_text)
        cursor = QueryCursor(query)
        matches = cursor.matches(root_node)
        
        calls = set()
        for _, captures in matches:
            for node in captures.get("call", []):
                calls.add(content[node.start_byte:node.end_byte])
        return list(calls)

def get_parser(file_extension: str) -> Optional[TreeSitterParser]:
    lang_map = {
        ".py": "python",
        ".ts": "typescript",
        ".js": "javascript",
        ".tsx": "typescript",
        ".jsx": "javascript"
    }
    lang = lang_map.get(file_extension)
    if lang:
        try:
            return TreeSitterParser(lang)
        except Exception:
            return None
    return None
