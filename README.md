# Codebase Knowledge AI

A production-grade, enterprise-ready Code Intelligence System that indexes repositories, understands complex code relationships, and provides deep architectural insights via a neural reasoning engine.

## Core Capabilities

- **Neural Ingestion:** Automated AST decomposition using Tree-sitter for high-fidelity extraction of symbols, imports, and cross-file dependencies.
- **Relationship Synthesis:** Multi-dimensional dependency mapping using NetworkX to discover logical flows and impact areas.
- **Hybrid Retrieval:** Combined semantic vector search (FAISS + BGE-small) with high-speed keyword indexing (SQLite FTS5).
- **Agentic Reasoning:** Advanced intelligence engine powered by Gemini/OpenAI that traverses the codebase to answer complex engineering queries.
- **Premium Interface:** High-fidelity, dark-mode glassmorphism dashboard designed for professional oversight and deep technical analysis.

## Professional Tech Stack

- **Backend Architecture:** FastAPI High-Performance Framework.
- **Intelligence Layer:** LangChain Agentic Orchestration.
- **Vector Engine:** FAISS (Facebook AI Similarity Search).
- **Relational Data:** SQLite (with Full-Text Search 5).
- **Semantic Models:** BGE-small-v1.5 Embeddings.
- **Structural Analysis:** Tree-sitter & NetworkX.
- **Frontend Design:** Vanilla HTML5/CSS3 (Glassmorphism / Premium Dark Mode).

## Operational Deployment

### Prerequisites

- Python 3.10+ or Docker
- Google Gemini API Key (or compatible OpenAI provider)

### Quick Start

1. **Clone the Infrastructure:**
   ```powershell
   git clone https://github.com/your-org/codebase-knowledge-ai.git
   cd codebase-knowledge-ai
   ```

2. **Configure Neural Parameters:**
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_gemini_key_here
   LLM_PROVIDER=google
   ```

3. **Initialize the Backend:**
   ```powershell
   python run.py
   ```

4. **Establish Connection:**
   Open `http://localhost:8081` (or your configured port) to access the Codebase Knowledge AI Neural Interface.

## Protocol Documentation (API)

- **POST /api/repos:** Initialize new repository ingestion.
- **GET /api/repos:** List all synchronized knowledge clusters.
- **GET /api/repos/{repo_id}/graph:** Retrieve the structural relationship map.
- **POST /api/repos/{repo_id}/query:** Transmit a natural language query to the reasoning engine.

## License

Enterprise Licensed / MIT.
