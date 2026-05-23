import os
import sys
import asyncio
import shutil

# Add backend to sys.path
sys.path.append(os.path.abspath("backend"))

from src.jobs.indexing_job import IndexingJob
from src.retrieval.hybrid_retriever import HybridRetriever
from src.graph.graph_builder import CodeGraph
from src.agent.code_agent import CodeAgent

async def run_demo():
    print("--- Starting Code Intelligence Demo ---")
    
    repo_path = os.path.abspath("demo_repo")
    repo_id = "demo_test_repo"
    
    # Cleanup previous storage if exists
    if os.path.exists("backend/storage"):
        print("Cleaning up previous storage...")
        # shutil.rmtree("backend/storage")
    
    print(f"1. Indexing repository at: {repo_path}")
    job = IndexingJob(repo_path)
    job.repo_id = repo_id # Force specific ID
    
    result = await job.run()
    print(f"Indexing Complete: {result['status']}")
    print(f"Stats: {result['files_indexed']} files, {result['chunks_created']} chunks")
    
    print("\n2. Initializing Agent...")
    retriever = HybridRetriever(repo_id)
    graph = CodeGraph(repo_id)
    graph.load()
    
    agent = CodeAgent(repo_id, retriever, graph, repo_path)
    
    # Test Question 1: Simple discovery
    query1 = "Where is the payment logic?"
    print(f"\nQUERY: {query1}")
    ans1 = await agent.answer(query1)
    print(f"ANSWER: {ans1['answer']}")
    
    # Test Question 2: Flow across services
    query2 = "Explain the flow for checkout."
    print(f"\nQUERY: {query2}")
    ans2 = await agent.answer(query2)
    print(f"ANSWER: {ans2['answer']}")
    
    if ans2.get('flow'):
        print("\nIDENTIFIED FLOW:")
        for step in ans2['flow']:
            print(f"  -> {step['node']} ({step['file_path']})")
            
    print("\n3. Testing Visuals (Mermaid Architecture)")
    try:
        from src.intelligence.repo_features import RepoFeatureService
        from src.storage.storage_factory import get_storage
        store = get_storage()
        service = RepoFeatureService(repo_id, repo_path, graph, store)
        mermaid_code = service.generate_mermaid_diagram().get('mermaid_code', '')
        print(f"Mermaid Code Generated Successfully ({len(mermaid_code)} chars)")
        print(f"Preview:\n{mermaid_code[:150]}...")
    except Exception as e:
        print(f"Error generating visuals: {e}")

if __name__ == "__main__":
    asyncio.run(run_demo())
