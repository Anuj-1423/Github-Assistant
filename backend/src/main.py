import os
import sys
import json
import logging
import shutil
import tempfile
import time
import csv
import io
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load .env file from the project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"), override=True)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
from starlette.background import BackgroundTask

# Add the project root to sys.path so that 'src' is discoverable
# This fixes common "ModuleNotFoundError" and IDE unresolved reference errors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.jobs.indexing_job import IndexingJob
    from src.retrieval.hybrid_retriever import HybridRetriever
    from src.storage.storage_factory import get_storage
    from src.graph.graph_builder import CodeGraph
    from src.agent.code_agent import CodeAgent
    from src.intelligence.repo_features import RepoFeatureService
except ImportError as e:
    # Fallback for different execution contexts
    from jobs.indexing_job import IndexingJob
    from retrieval.hybrid_retriever import HybridRetriever
    from storage.storage_factory import get_storage
    from graph.graph_builder import CodeGraph
    from agent.code_agent import CodeAgent
    from intelligence.repo_features import RepoFeatureService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

app = FastAPI(title="Codebase Knowledge AI API", version="1.0.0")
print("\n" + "="*50)
print(" CODEBASE KNOWLEDGE AI BACKEND LOADED ")
print("="*50 + "\n")

@app.get("/api/health")
async def health_check():
    return {"status": "online", "version": "1.0.1", "timestamp": time.time()}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store for active jobs
jobs = {}

class RepoCreate(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"

class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = "flow"
    audience_mode: Optional[str] = "pro"

class FlowStep(BaseModel):
    node: str
    file_path: str
    line_start: int
    line_end: int

class QueryResponse(BaseModel):
    answer: str
    flow: List[FlowStep]
    citations: List[dict]
    confidence: str

class GlossaryUpsertRequest(BaseModel):
    term: str
    definition: str

class NoteCreateRequest(BaseModel):
    note: str
    source_query: Optional[str] = None

# Serve Static Files
# Note: Ensure the 'frontend' folder exists at the root of the workspace
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

def resolve_repo_path(repo_id: str) -> str:
    if repo_id in jobs and jobs[repo_id].get("repo_path"):
        return jobs[repo_id]["repo_path"]
    return os.path.abspath(os.path.join(ROOT_DIR, "storage", "repos", repo_id))

def ensure_repo_exists(repo_id: str):
    store = get_storage()
    repo = store.get_repo(repo_id)
    if not repo and repo_id not in jobs:
        logger.error(f"Repository not found in DB or jobs: '{repo_id}'")
        # List all repos for debugging
        all_repos = store.list_repos()
        logger.info(f"Available repo IDs: {[r['id'] for r in all_repos]}")
        raise HTTPException(status_code=404, detail=f"Repo '{repo_id}' not found")

def _safe_delete_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.warning("Failed to delete temporary file: %s", path)

def _to_safe_filename(value: str) -> str:
    if not value:
        return "repository"
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "repository"

@app.get("/")
async def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{page}.html")
async def serve_page(page: str):
    path = os.path.join(FRONTEND_DIR, f"{page}.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Page not found")

@app.get("/style.css")
async def serve_css():
    # Explicit route for style.css since many pages link to it at root
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"), media_type="text/css")

@app.post("/api/repos")
async def create_repo(repo: RepoCreate, background_tasks: BackgroundTasks):
    store = get_storage()
    repo_name = repo.repo_url.split('/')[-1] if '/' in repo.repo_url else repo.repo_url
    
    try:
        job = IndexingJob(repo.repo_url, repo.branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize indexing job: {str(e)}")

    jobs[job.repo_id] = {"status": "PENDING", "job": job}
    
    # Initialize in DB as PENDING so it shows up in dashboard immediately
    if hasattr(store, "upsert_repo"):
        store.upsert_repo(job.repo_id, repo_name, repo.repo_url, repo.branch, status="PENDING")

    async def run_job():
        # Re-fetch store in the thread to be safe
        thread_store = get_storage()
        try:
            result = await job.run()
            jobs[job.repo_id].update(result)
            # Persist the READY status to DB
            if hasattr(thread_store, "upsert_repo"):
                thread_store.upsert_repo(job.repo_id, repo_name, repo.repo_url, repo.branch, status="READY")
        except Exception as e:
            jobs[job.repo_id].update({
                "status": "FAILED",
                "error": str(e),
            })
            # Persist the FAILED status to DB
            if hasattr(thread_store, "upsert_repo"):
                thread_store.upsert_repo(job.repo_id, repo_name, repo.repo_url, repo.branch, status="FAILED")
        
    background_tasks.add_task(run_job)
    return {"repo_id": job.repo_id, "status": "PENDING"}

@app.get("/api/repos")
async def list_repositories():
    store = get_storage()
    if hasattr(store, "list_repos"):
        return store.list_repos()
    return []

@app.delete("/api/repos/{repo_id}")
async def delete_repository(repo_id: str):
    store = get_storage()
    # 1. Clear DB Metadata
    if hasattr(store, "delete_repo"):
        store.delete_repo(repo_id)
    
    # 2. Delete Vector Store (FAISS)
    vector_dir = os.path.abspath("./storage/vectors")
    index_file = os.path.join(vector_dir, f"{repo_id}.index")
    pkl_file = os.path.join(vector_dir, f"{repo_id}_ids.pkl")
    
    if os.path.exists(index_file):
        os.remove(index_file)
    if os.path.exists(pkl_file):
        os.remove(pkl_file)
    
    # 3. Delete Graph Storage
    graph_path = os.path.abspath(f"./storage/graphs/{repo_id}.json")
    if os.path.exists(graph_path):
        os.remove(graph_path)

    # 4. Delete Chroma collection if exists
    try:
        from src.storage.chroma_store import ChromaStore
        chroma = ChromaStore()
        chroma.delete_collection(repo_id)
    except Exception:
        pass

    # 5. Delete Cloned Source Code
    repo_path = resolve_repo_path(repo_id)
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)
        
    return {"status": "DELETED", "repo_id": repo_id}

@app.get("/api/repos/{repo_id}/status")
async def get_repo_status(repo_id: str):
    if repo_id not in jobs:
        store = get_storage()
        repo = store.get_repo(repo_id)
        if repo:
            return {"repo_id": repo_id, "status": "READY"}
        raise HTTPException(status_code=404, detail="Repo not found")
    
    status_data = jobs[repo_id]
    return {
        "repo_id": repo_id,
        "status": status_data.get("status", "UNKNOWN"),
        "files_indexed": status_data.get("files_indexed", 0),
        "chunks_created": status_data.get("chunks_created", 0),
        "graph_nodes": status_data.get("graph_nodes", 0),
        "graph_edges": status_data.get("graph_edges", 0),
        "error": status_data.get("error"),
    }

@app.get("/api/repos/{repo_id}/graph")
async def get_repo_graph(repo_id: str):
    graph = CodeGraph(repo_id)
    if not os.path.exists(graph.storage_path):
        raise HTTPException(status_code=404, detail="Graph not found")
    
    with open(graph.storage_path, 'r') as f:
        return json.load(f)

@app.get("/api/repos/{repo_id}/download")
async def download_repo_zip(repo_id: str):
    ensure_repo_exists(repo_id)

    if repo_id in jobs:
        current_status = jobs[repo_id].get("status")
        if current_status != "READY":
            raise HTTPException(status_code=409, detail="Repository is not ready for download yet.")

    repo_path = resolve_repo_path(repo_id)
    repo_abs_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_abs_path):
        raise HTTPException(status_code=404, detail="Indexed repository files not found.")

    store = get_storage()
    repo = store.get_repo(repo_id) if hasattr(store, "get_repo") else None
    repo_name = _to_safe_filename((repo or {}).get("name") or repo_id)

    export_dir = os.path.join(tempfile.gettempdir(), "code_intel_repo_exports")
    os.makedirs(export_dir, exist_ok=True)
    archive_base = os.path.join(export_dir, f"{repo_id}_{int(time.time())}")
    archive_path = shutil.make_archive(archive_base, "zip", root_dir=repo_abs_path)

    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=f"{repo_name}.zip",
        background=BackgroundTask(_safe_delete_file, archive_path),
    )

@app.get("/api/repos/{repo_id}/architecture-map")
async def get_architecture_map(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.build_architecture_map()

@app.get("/api/repos/{repo_id}/architecture-mermaid")
async def get_repo_architecture_mermaid(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.generate_mermaid_diagram()

@app.get("/api/repos/{repo_id}/architecture-puml")
async def get_repo_architecture_puml(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.generate_plantuml_diagram()

@app.get("/api/repos/{repo_id}/architecture-graph")
async def get_repo_architecture_graph(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.generate_graph_json()

@app.get("/api/repos/{repo_id}/structure")
async def get_repo_structure(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.generate_repo_tree()

@app.get("/api/repos/{repo_id}/onboarding")
async def get_onboarding_guide(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.build_onboarding_guide()

@app.get("/api/repos/{repo_id}/memory")
async def get_repo_memory(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.get_memory_snapshot()

@app.get("/api/repos/{repo_id}/analytics")
async def get_repo_analytics(repo_id: str):
    ensure_repo_exists(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)
    service = RepoFeatureService(repo_id, repo_path, graph, store)
    return service.get_analytics_data()

@app.post("/api/repos/{repo_id}/memory/glossary")
async def upsert_repo_glossary(repo_id: str, request: GlossaryUpsertRequest):
    ensure_repo_exists(repo_id)
    term = request.term.strip()
    definition = request.definition.strip()
    if not term or not definition:
        raise HTTPException(status_code=400, detail="Both term and definition are required.")

    store = get_storage()
    if not hasattr(store, "upsert_glossary_term"):
        raise HTTPException(status_code=501, detail="Glossary is not supported by current storage backend.")

    store.upsert_glossary_term(repo_id, term, definition)
    return {"status": "ok", "term": term}

@app.delete("/api/repos/{repo_id}/memory/glossary")
async def delete_repo_glossary(repo_id: str, term: str = Query(..., min_length=1)):
    ensure_repo_exists(repo_id)
    store = get_storage()
    if not hasattr(store, "delete_glossary_term"):
        raise HTTPException(status_code=501, detail="Glossary is not supported by current storage backend.")

    store.delete_glossary_term(repo_id, term.strip())
    return {"status": "ok", "term": term.strip()}

@app.post("/api/repos/{repo_id}/memory/notes")
async def add_repo_note(repo_id: str, request: NoteCreateRequest):
    ensure_repo_exists(repo_id)
    note = request.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Note cannot be empty.")

    store = get_storage()
    if not hasattr(store, "add_project_note"):
        raise HTTPException(status_code=501, detail="Project notes are not supported by current storage backend.")

    source_query = request.source_query.strip() if request.source_query else None
    store.add_project_note(repo_id, note, source_query)
    return {"status": "ok"}

@app.post("/api/repos/{repo_id}/query", response_model=QueryResponse)
async def query_repo(repo_id: str, request: QueryRequest):
    ensure_repo_exists(repo_id)

    retriever = HybridRetriever(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    
    # Resolve path for local tools
    repo_path = resolve_repo_path(repo_id)

    feature_service = RepoFeatureService(repo_id, repo_path, graph, store)
    memory = feature_service.get_memory_snapshot()
    memory_context = feature_service.build_memory_context(memory.get("glossary", []), memory.get("notes", []))

    if hasattr(store, "log_query"):
        store.log_query(repo_id=repo_id, query=request.query, user_id="default_user")
    
    agent = CodeAgent(
        repo_id,
        retriever,
        graph,
        repo_path,
        audience_mode=request.audience_mode or "pro",
        memory_context=memory_context,
    )
    result = await agent.answer(request.query)
    
    # Handle flow visualization if result is empty
    if not result.get("flow") and request.mode == "flow":
        relevant_chunks = retriever.retrieve(request.query, limit=1)
        if relevant_chunks:
            chunk = relevant_chunks[0]
            symbol_id = f"{chunk['file_path']}::{chunk['symbol_name']}"
            result["flow"] = [{
                "node": chunk['symbol_name'],
                "file_path": chunk['file_path'],
                "line_start": chunk['start_line'],
                "line_end": chunk['end_line']
            }]
            neighbors = graph.get_neighbors(symbol_id)
            for out in neighbors.get("outgoing", [])[:3]:
                result["flow"].append({
                    "node": out['id'].split("::")[-1],
                    "file_path": out['id'].split("::")[0],
                    "line_start": 0,
                    "line_end": 0
                })
    return {
        "answer": result.get("answer", "No answer generated."),
        "flow": result.get("flow", []),
        "citations": result.get("citations", []),
        "confidence": result.get("confidence", "medium")
    }

@app.get("/api/repos/{repo_id}/query-logs")
async def get_repo_query_logs(repo_id: str, limit: int = Query(default=50, ge=1, le=500)):
    ensure_repo_exists(repo_id)
    store = get_storage()
    if hasattr(store, "list_query_logs_for_repo"):
        return {"logs": store.list_query_logs_for_repo(repo_id, limit=limit)}
    return {"logs": []}

@app.post("/api/repos/{repo_id}/search")
async def deep_code_search(repo_id: str, request: QueryRequest):
    ensure_repo_exists(repo_id)
    store = get_storage()
    # Log the search as a query
    if hasattr(store, "log_query"):
        store.log_query(repo_id=repo_id, query=request.query, user_id="default_user")
    
    # Use keyword_search from the store
    if hasattr(store, "keyword_search"):
        results = store.keyword_search(repo_id, request.query, top_k=10)
        return {"results": results}
    return {"results": []}

@app.post("/api/repos/{repo_id}/query/stream")
async def query_repo_stream(repo_id: str, request: QueryRequest):
    ensure_repo_exists(repo_id)
    
    retriever = HybridRetriever(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    store = get_storage()
    repo_path = resolve_repo_path(repo_id)

    feature_service = RepoFeatureService(repo_id, repo_path, graph, store)
    memory = feature_service.get_memory_snapshot()
    memory_context = feature_service.build_memory_context(memory.get("glossary", []), memory.get("notes", []))

    if hasattr(store, "log_query"):
        store.log_query(repo_id=repo_id, query=request.query, user_id="default_user")
    
    agent = CodeAgent(
        repo_id,
        retriever,
        graph,
        repo_path,
        audience_mode=request.audience_mode or "pro",
        memory_context=memory_context,
    )

    async def event_generator():
        async for chunk in agent.answer_stream(request.query):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/api/admin/overview")
async def get_admin_overview():
    store = get_storage()
    if hasattr(store, "get_admin_overview"):
        return store.get_admin_overview()

    repos = store.list_repos() if hasattr(store, "list_repos") else []
    total_users = 1 if hasattr(store, "get_user_profile") and store.get_user_profile() else 0
    return {
        "total_users": total_users,
        "global_docs": len(repos),
        "personal_docs": len([r for r in repos if (r.get("status") or "").upper() == "READY"]),
        "total_queries": 0,
        "total_chunks": 0,
        "repo_status": {
            "ready": len([r for r in repos if (r.get("status") or "").upper() == "READY"]),
            "pending": len([r for r in repos if (r.get("status") or "").upper() not in ("READY", "FAILED")]),
            "failed": len([r for r in repos if (r.get("status") or "").upper() == "FAILED"]),
        },
        "recent_queries": []
    }

@app.get("/api/admin/users")
async def get_admin_users(limit: int = Query(default=200, ge=1, le=1000)):
    store = get_storage()
    if hasattr(store, "list_users_with_query_counts"):
        users = store.list_users_with_query_counts(limit=limit)
    elif hasattr(store, "list_users"):
        users = store.list_users(limit=limit)
    else:
        users = []

    return {"users": users}

@app.get("/api/admin/query-logs")
async def get_admin_query_logs(limit: int = Query(default=50, ge=1, le=500)):
    store = get_storage()
    if hasattr(store, "list_query_logs"):
        return {"logs": store.list_query_logs(limit=limit)}
    return {"logs": []}

@app.get("/api/admin/users/export.csv")
async def export_admin_users_csv():
    store = get_storage()
    rows = []
    if hasattr(store, "list_users_with_query_counts"):
        rows = store.list_users_with_query_counts(limit=10000)
    elif hasattr(store, "list_users"):
        rows = store.list_users(limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "username", "full_name", "email", "role", "total_queries", "last_query_at", "updated_at"])
    for row in rows:
        writer.writerow([
            row.get("id", ""),
            row.get("username", ""),
            row.get("full_name", ""),
            row.get("email", ""),
            row.get("role", ""),
            row.get("total_queries", 0),
            row.get("last_query_at", ""),
            row.get("updated_at", "")
        ])
    output.seek(0)
    filename = f"admin_users_{int(time.time())}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)

@app.get("/api/user/profile")
async def get_profile():
    store = get_storage()
    if hasattr(store, "get_user_profile"):
        return store.get_user_profile()
    return {}

@app.post("/api/user/profile")
async def update_profile(profile: dict):
    store = get_storage()
    if hasattr(store, "update_user_profile"):
        store.update_user_profile('default_user', profile)
        return {"status": "success"}
    return {"status": "error"}

@app.get("/api/system/settings")
async def get_system_settings():
    store = get_storage()
    if hasattr(store, "get_system_settings"):
        return store.get_system_settings()
    return {}

@app.post("/api/system/settings")
async def update_system_settings(settings: dict):
    store = get_storage()
    if hasattr(store, "update_system_settings"):
        store.update_system_settings(settings)
        return {"status": "success"}
    return {"status": "error"}
