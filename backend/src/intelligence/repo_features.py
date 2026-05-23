import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List

from src.graph.graph_builder import CodeGraph


class RepoFeatureService:
    SUPPORTED_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".java"}
    IGNORE_DIRS = {
        ".git",
        ".next",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
    }

    def __init__(self, repo_id: str, repo_path: str, graph: CodeGraph, store: Any):
        self.repo_id = repo_id
        self.repo_path = os.path.abspath(repo_path)
        self.graph = graph
        self.store = store

    def generate_repo_tree(self) -> Dict[str, Any]:
        """Generates a hierarchical tree structure of the repository files."""
        try:
            files = self._collect_repo_files()
            root = {"name": os.path.basename(self.repo_path), "type": "directory", "children": []}
            
            def add_to_tree(path_parts, current_node):
                if not path_parts:
                    return
                
                part = path_parts[0]
                is_file = len(path_parts) == 1
                
                # Check if child already exists
                child = next((c for c in current_node["children"] if c["name"] == part), None)
                
                if not child:
                    child = {
                        "name": part,
                        "type": "file" if is_file else "directory",
                        "children": [] if not is_file else None
                    }
                    current_node["children"].append(child)
                
                if not is_file:
                    add_to_tree(path_parts[1:], child)

            for file_path in files:
                # Use relative path from repo_path
                rel_path = os.path.relpath(file_path, self.repo_path)
                parts = rel_path.split(os.sep)
                add_to_tree(parts, root)
                
            return {
                "repo_id": self.repo_id,
                "tree": root
            }
        except Exception as e:
            return {"error": str(e)}

    def build_architecture_map(self) -> Dict[str, Any]:
        try:
            files = self._collect_repo_files()
            chunks = self._list_repo_chunks(limit=12000)

            module_file_counts: Dict[str, int] = defaultdict(int)
            for path in files:
                module_file_counts[self._module_name(path)] += 1

            module_symbol_counts: Dict[str, Counter] = defaultdict(Counter)
            symbol_locations: Dict[str, Dict[str, Any]] = {}
            for chunk in chunks:
                file_path = self._normalize_path(chunk.get("file_path", ""))
                if not file_path:
                    continue
                module_name = self._module_name(file_path)
                symbol_name = (chunk.get("symbol_name") or "").strip()
                if not symbol_name or symbol_name.lower() in {"global", "module"}:
                    continue
                module_symbol_counts[module_name][symbol_name] += 1
                symbol_locations.setdefault(symbol_name, {
                    "file_path": file_path,
                    "line_start": chunk.get("start_line", 0),
                })

            all_modules = sorted(set(module_file_counts.keys()) | set(module_symbol_counts.keys()))
            modules: List[Dict[str, Any]] = []
            for module_name in all_modules:
                top_symbols = [name for name, _ in module_symbol_counts[module_name].most_common(5)]
                modules.append({
                    "name": module_name,
                    "file_count": module_file_counts.get(module_name, 0),
                    "symbol_count": sum(module_symbol_counts[module_name].values()),
                    "top_symbols": top_symbols,
                })

            modules.sort(key=lambda item: (-item["file_count"], item["name"]))

            dependencies = self._build_module_dependencies()
            entry_points = self._find_entry_points(symbol_locations)

            return {
                "repo_id": self.repo_id,
                "overview": {
                    "files_indexed": len(files),
                    "modules": len(modules),
                    "graph_nodes": self.graph.graph.number_of_nodes(),
                    "graph_edges": self.graph.graph.number_of_edges(),
                },
                "modules": modules,
                "dependencies": dependencies,
                "entry_points": entry_points,
            }
        except Exception as e:
            return {
                "repo_id": self.repo_id,
                "overview": {"files_indexed": 0, "modules": 0, "graph_nodes": 0, "graph_edges": 0, "error": str(e)},
                "modules": [],
                "dependencies": [],
                "entry_points": []
            }

    def generate_mermaid_diagram(self) -> Dict[str, str]:
        """Generates a highly robust, minimal flowchart for Mermaid."""
        try:
            files = self._collect_repo_files()
            if not files:
                return {
                    "repo_id": self.repo_id,
                    "mermaid_code": "flowchart LR\n  Empty(\"No files found\")"
                }

            # Build a tree structure from paths
            tree = {}
            for f in files:
                parts = f.split('/')
                curr = tree
                for part in parts:
                    if part not in curr:
                        curr[part] = {}
                    curr = curr[part]

            mermaid_lines = ["flowchart LR"]
            node_idx = 0
            max_depth = 3
            max_nodes = 100
            nodes_count = 0
            truncated = False

            import re
            def clean_label(text):
                # Only allow alphanumeric and spaces
                return re.sub(r'[^a-zA-Z0-9 ]', '', text)

            def process_tree(curr_tree, parent_id, depth):
                nonlocal node_idx, nodes_count, truncated
                
                if depth > max_depth or nodes_count > max_nodes:
                    truncated = True
                    return

                items = sorted(curr_tree.items(), key=lambda x: (len(x[1]) == 0, x[0]))
                
                for name, children in items:
                    if nodes_count > max_nodes:
                        truncated = True
                        break
                        
                    label = clean_label(name)
                    node_id = f"v{node_idx}"
                    node_idx += 1
                    nodes_count += 1
                    
                    prefix = "Folder " if children else "File "
                    mermaid_lines.append(f"  {node_id}(\"{prefix}{label}\")")
                    if parent_id:
                        mermaid_lines.append(f"  {parent_id} --> {node_id}")
                    
                    if children:
                        process_tree(children, node_id, depth + 1)

            root_id = "vroot"
            mermaid_lines.append(f"  {root_id}(\"Project Root\")")
            
            process_tree(tree, root_id, 1)

            if truncated:
                mermaid_lines.append("  Trunc(\"Diagram Truncated\")")
                mermaid_lines.append(f"  {root_id} --> Trunc")

            return {
                "repo_id": self.repo_id,
                "mermaid_code": "\n".join(mermaid_lines)
            }
        except Exception as e:
            return {
                "repo_id": self.repo_id,
                "mermaid_code": f"flowchart TD\n  Error(\"Error: {str(e)}\")"
            }

    def generate_plantuml_diagram(self) -> Dict[str, str]:
        """Generates a PlantUML representation and its image URL."""
        try:
            architecture = self.build_architecture_map()
            modules = architecture.get("modules", [])
            dependencies = architecture.get("dependencies", [])
            layers = self._categorize_layers(modules)

            puml = ["@startuml", "skinparam backgroundColor #1e1e2e", "skinparam handwritten false", "skinparam defaultFontColor #cdd6f4", "skinparam linetype ortho"]
            puml.append("skinparam rectangle {")
            puml.append("  BackgroundColor #24273a")
            puml.append("  BorderColor #8aadf4")
            puml.append("  FontColor #cad3f5")
            puml.append("}")

            for layer_name, layer_mods in layers.items():
                if not layer_mods: continue
                puml.append(f"package \"{layer_name}\" <<Rectangle>> #313244 {{")
                for mod in layer_mods:
                    name = mod["name"].replace("/", "_").replace(".", "_").replace("(", "").replace(")", "")
                    puml.append(f"  rectangle \"{mod['name']}\\n({mod['file_count']} files)\" as {name}")
                puml.append("}")

            for dep in dependencies:
                f = dep["from_module"].replace("/", "_").replace(".", "_").replace("(", "").replace(")", "")
                t = dep["to_module"].replace("/", "_").replace(".", "_").replace("(", "").replace(")", "")
                puml.append(f"{f} --> {t} : {dep['weight']} calls")

            puml.append("@enduml")
            puml_code = "\n".join(puml)
            
            return {
                "repo_id": self.repo_id,
                "puml_code": puml_code
            }
        except Exception as e:
            return {
                "repo_id": self.repo_id,
                "puml_code": f"@startuml\nrectangle \"Error generating diagram: {str(e)}\"\n@enduml"
            }

    def generate_graph_json(self) -> Dict[str, Any]:
        """Generates JSON structure for Cytoscape.js with compound nodes (layers/modules)."""
        try:
            architecture = self.build_architecture_map()
            modules = architecture.get("modules", [])
            layers = self._categorize_layers(modules)
            
            nodes = []
            edges = []
            
            # 1. Add Layers as parent nodes
            for layer_name, layer_mods in layers.items():
                if not layer_mods:
                    continue
                
                layer_id = layer_name.replace(" ", "_").replace("&", "And")
                nodes.append({
                    "data": {
                        "id": layer_id,
                        "label": layer_name,
                        "type": "layer"
                    }
                })
                
                # 2. Add Modules as children of layers
                for mod in layer_mods:
                    mod_id = mod["name"]
                    nodes.append({
                        "data": {
                            "id": mod_id,
                            "parent": layer_id,
                            "label": mod["name"],
                            "type": "module",
                            "file_count": mod["file_count"]
                        }
                    })
                    
                    # 3. Add Top Symbols as children of modules
                    for symbol in mod.get("top_symbols", []):
                        symbol_id = f"{mod_id}::{symbol}"
                        nodes.append({
                            "data": {
                                "id": symbol_id,
                                "parent": mod_id,
                                "label": symbol,
                                "type": "symbol"
                            }
                        })

            # 4. Add Edges between modules (for simplicity in architecture view)
            for dep in architecture.get("dependencies", []):
                edges.append({
                    "data": {
                        "source": dep["from_module"],
                        "target": dep["to_module"],
                        "weight": dep["weight"],
                        "label": f"{dep['weight']} calls"
                    }
                })
                
            return {
                "nodes": nodes,
                "edges": edges
            }
        except Exception as e:
            return {
                "nodes": [{"data": {"id": "err", "label": f"Error: {str(e)}"}}],
                "edges": []
            }

    def _categorize_layers(self, modules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        layers = {
            "Frontend": [],
            "API & Backend": [],
            "Intelligence Engine": [],
            "Storage Layer": [],
            "Other Modules": []
        }
        for mod in modules:
            name = mod["name"].lower()
            if any(x in name for x in ["frontend", "ui", "web", "client"]):
                layers["Frontend"].append(mod)
            elif any(x in name for x in ["api", "main", "server", "backend", "routes"]):
                layers["API & Backend"].append(mod)
            elif any(x in name for x in ["intelligence", "agent", "retrieval", "embeddings", "chunking", "parsing", "graph"]):
                layers["Intelligence Engine"].append(mod)
            elif any(x in name for x in ["storage", "database", "db", "models"]):
                layers["Storage Layer"].append(mod)
            else:
                layers["Other Modules"].append(mod)
        return layers

    def build_onboarding_guide(self) -> Dict[str, Any]:
        architecture = self.build_architecture_map()
        readme_text = self._read_readme()

        quickstart = self._extract_quickstart_steps(readme_text)
        top_modules = [module["name"] for module in architecture["modules"][:5]]
        recommended_files = self._suggest_files_from_modules(architecture["modules"])
        readme_files = self._extract_file_mentions(readme_text)
        for file_name in readme_files:
            if file_name not in recommended_files:
                recommended_files.append(file_name)
            if len(recommended_files) >= 8:
                break

        summary_lines = [
            f"This repository has {architecture['overview']['files_indexed']} indexed source files",
            f"organized across {architecture['overview']['modules']} top-level modules.",
        ]
        if top_modules:
            summary_lines.append(f"Primary modules: {', '.join(top_modules[:4])}.")
        if architecture["entry_points"]:
            entry_labels = [f"{item['symbol']} ({item['file_path']})" for item in architecture["entry_points"][:3]]
            summary_lines.append(f"Likely entry points: {', '.join(entry_labels)}.")

        key_concepts = []
        for module in architecture["modules"][:5]:
            symbols = ", ".join(module["top_symbols"][:3]) or "general utilities"
            key_concepts.append(
                f"{module['name']}: {module['file_count']} files, key symbols include {symbols}."
            )

        first_questions = [
            "Which module handles request entry and orchestration?",
            "Which symbols are reused across multiple modules?",
            "What dependencies are highest-risk for changes?",
        ]

        return {
            "repo_id": self.repo_id,
            "summary": " ".join(summary_lines),
            "quickstart": quickstart,
            "key_concepts": key_concepts,
            "recommended_files": recommended_files[:8],
            "first_questions": first_questions,
            "architecture_snapshot": architecture["overview"],
        }

    def get_memory_snapshot(self) -> Dict[str, Any]:
        glossary = self._list_glossary_terms(limit=200)
        notes = self._list_project_notes(limit=50)
        return {"glossary": glossary, "notes": notes}

    def get_analytics_data(self) -> Dict[str, Any]:
        """Calculates deep analytics for the repository dashboard."""
        files = self._collect_repo_files()
        chunks = self._list_repo_chunks(limit=10000)
        
        # 1. Complexity Score (Symbol density)
        module_complexity: Dict[str, float] = defaultdict(float)
        module_symbol_count: Dict[str, int] = defaultdict(int)
        
        # Use file-level if only one module (root)
        use_file_level = False
        potential_modules = set()
        for chunk in chunks:
            path = self._normalize_path(chunk.get("file_path", ""))
            mod = self._module_name(path)
            potential_modules.add(mod)
        
        if len(potential_modules) <= 1:
            use_file_level = True

        for chunk in chunks:
            path = self._normalize_path(chunk.get("file_path", ""))
            if use_file_level:
                key = os.path.basename(path)
            else:
                key = self._module_name(path)
            module_symbol_count[key] += 1
            
        for key, count in module_symbol_count.items():
            module_complexity[key] = round(count * 1.5, 2)

        # 2. Top "Impact" (Connections/fan-in)
        impact_scores: Dict[str, int] = defaultdict(int)
        for src, dst in self.graph.graph.edges():
            src_path = self._node_to_file(src)
            dst_path = self._node_to_file(dst)
            
            if use_file_level:
                src_key = os.path.basename(src_path)
                dst_key = os.path.basename(dst_path)
            else:
                src_key = self._module_name(src_path)
                dst_key = self._module_name(dst_path)
                
            if src_key != dst_key:
                impact_scores[dst_key] += 1

        # Fallback for small repos: just use symbol count as impact if no edges
        if not impact_scores and module_symbol_count:
            for k, v in module_symbol_count.items():
                impact_scores[k] = v // 2

        top_entities = sorted(
            [{"name": k, "score": v} for k, v in impact_scores.items()],
            key=lambda x: x["score"], reverse=True
        )[:8]

        # 3. Dependency Heatmap Data
        deps = self._build_module_dependencies()
        heatmap = []
        for d in deps[:30]:
            heatmap.append({
                "from": d["from_module"],
                "to": d["to_module"],
                "weight": d["weight"]
            })

        # Final check: if still empty, return some placeholder for the WOW factor
        if not top_entities and not module_complexity:
             return {
                "repo_id": self.repo_id,
                "complexity_over_time": {"labels": ["Indexing..."], "values": [0]},
                "top_contributors": {"labels": ["Scanning..."], "values": [0]},
                "dependency_heatmap": []
            }

        return {
            "repo_id": self.repo_id,
            "complexity_over_time": {
                "labels": sorted(module_complexity.keys(), key=lambda x: module_complexity[x], reverse=True)[:10],
                "values": sorted(module_complexity.values(), reverse=True)[:10]
            },
            "top_contributors": {
                "labels": [m["name"] for m in top_entities],
                "values": [m["score"] for m in top_entities]
            },
            "dependency_heatmap": heatmap
        }

    def build_memory_context(self, glossary: List[Dict[str, Any]], notes: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        if glossary:
            lines.append("Project glossary:")
            for item in glossary[:20]:
                term = (item.get("term") or "").strip()
                definition = (item.get("definition") or "").strip()
                if term and definition:
                    lines.append(f"- {term}: {definition}")

        if notes:
            if lines:
                lines.append("")
            lines.append("Project memory notes:")
            for item in notes[:10]:
                note = (item.get("note") or "").strip()
                if note:
                    lines.append(f"- {note}")

        return "\n".join(lines).strip()

    def _collect_repo_files(self) -> List[str]:
        if not os.path.exists(self.repo_path):
            return []

        collected: List[str] = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            for filename in files:
                _, ext = os.path.splitext(filename)
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, filename)
                relative = os.path.relpath(full_path, self.repo_path).replace("\\", "/")
                collected.append(relative)
        return sorted(collected)

    def _build_module_dependencies(self) -> List[Dict[str, Any]]:
        bucket: Dict[str, Dict[str, Any]] = {}

        for src, dst, edge_data in self.graph.graph.edges(data=True):
            src_file = self._node_to_file(src)
            dst_file = self._node_to_file(dst)
            if not src_file or not dst_file:
                continue

            src_module = self._module_name(src_file)
            dst_module = self._module_name(dst_file)
            if src_module == dst_module:
                continue

            key = f"{src_module}->{dst_module}"
            if key not in bucket:
                bucket[key] = {
                    "from_module": src_module,
                    "to_module": dst_module,
                    "weight": 0,
                    "relation_counts": Counter(),
                }
            bucket[key]["weight"] += 1
            relation = edge_data.get("relation", "unknown")
            bucket[key]["relation_counts"][relation] += 1

        dependencies: List[Dict[str, Any]] = []
        for item in bucket.values():
            dependencies.append({
                "from_module": item["from_module"],
                "to_module": item["to_module"],
                "weight": item["weight"],
                "top_relations": [
                    {"relation": rel, "count": count}
                    for rel, count in item["relation_counts"].most_common(3)
                ],
            })

        dependencies.sort(key=lambda value: (-value["weight"], value["from_module"], value["to_module"]))
        return dependencies[:40]

    def _find_entry_points(self, symbol_locations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for node_id, attrs in self.graph.graph.nodes(data=True):
            if attrs.get("type") not in {"function", "class"}:
                continue

            in_degree = self.graph.graph.in_degree(node_id)
            out_degree = self.graph.graph.out_degree(node_id)
            if out_degree <= 0 or in_degree > 1:
                continue

            file_path = attrs.get("file_path") or self._node_to_file(node_id)
            symbol_name = attrs.get("name") or node_id.split("::")[-1]
            if not file_path:
                continue

            lines = symbol_locations.get(symbol_name, {})
            entries.append({
                "symbol": symbol_name,
                "file_path": file_path,
                "line_start": lines.get("line_start", 0),
                "fan_out": out_degree,
                "fan_in": in_degree,
            })

        entries.sort(key=lambda item: (-item["fan_out"], item["fan_in"], item["symbol"]))
        return entries[:8]

    def _extract_quickstart_steps(self, readme_text: str) -> List[str]:
        if not readme_text:
            return [
                "Read the architecture map to understand module boundaries.",
                "Start with the listed entry points and follow dependencies.",
                "Use glossary terms to align on project language.",
            ]

        steps: List[str] = []
        lines = readme_text.splitlines()
        capture = False
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("##"):
                capture = "getting started" in lower or "installation" in lower or "quickstart" in lower
                continue

            if not capture:
                continue

            match = re.match(r"^(\d+[\).\s]+|- )(.+)$", stripped)
            if match:
                steps.append(match.group(2).strip())
            elif stripped and len(steps) < 5:
                steps.append(stripped)

            if len(steps) >= 8:
                break

        if steps:
            return steps[:8]

        return [
            "Open README and run setup commands from the installation section.",
            "Index the repository in the dashboard.",
            "Ask onboarding questions in Beginner mode for guided context.",
        ]

    def _suggest_files_from_modules(self, modules: List[Dict[str, Any]]) -> List[str]:
        suggestions: List[str] = []
        for module in modules[:6]:
            name = module["name"]
            if name == "(root)":
                for candidate in ["README.md", "run.py", "main.py"]:
                    if candidate not in suggestions:
                        suggestions.append(candidate)
                continue
            suggestions.append(f"{name}/")
        return suggestions

    def _extract_file_mentions(self, readme_text: str) -> List[str]:
        if not readme_text:
            return []
        matches = re.findall(r"(?:^|[\s`])([A-Za-z0-9_\-./]+(?:\.[A-Za-z0-9]+))", readme_text)
        unique: List[str] = []
        for path in matches:
            cleaned = path.strip().strip("`")
            if "/" not in cleaned and "." not in cleaned:
                continue
            if cleaned not in unique:
                unique.append(cleaned)
        return unique[:20]

    def _read_readme(self) -> str:
        for name in ("README.md", "readme.md", "README.txt"):
            path = os.path.join(self.repo_path, name)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                        return handle.read()
                except Exception:
                    return ""
        return ""

    def _list_repo_chunks(self, limit: int) -> List[Dict[str, Any]]:
        if not hasattr(self.store, "list_repo_chunks"):
            return []
        try:
            return self.store.list_repo_chunks(self.repo_id, limit=limit)
        except Exception:
            return []

    def _list_glossary_terms(self, limit: int) -> List[Dict[str, Any]]:
        if not hasattr(self.store, "list_glossary_terms"):
            return []
        try:
            return self.store.list_glossary_terms(self.repo_id, limit=limit)
        except Exception:
            return []

    def _list_project_notes(self, limit: int) -> List[Dict[str, Any]]:
        if not hasattr(self.store, "list_project_notes"):
            return []
        try:
            return self.store.list_project_notes(self.repo_id, limit=limit)
        except Exception:
            return []

    def _node_to_file(self, node_id: str) -> str:
        attrs = self.graph.graph.nodes.get(node_id, {})
        direct_file = attrs.get("file_path")
        if direct_file:
            return self._normalize_path(direct_file)
        return self._normalize_path(node_id.split("::", 1)[0])

    def _module_name(self, file_path: str) -> str:
        normalized = self._normalize_path(file_path)
        if not normalized:
            return "(unknown)"
        if "/" not in normalized:
            return "(root)"
        return normalized.split("/", 1)[0]

    def _normalize_path(self, path: str) -> str:
        return (path or "").replace("\\", "/").strip("/")
