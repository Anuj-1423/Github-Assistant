"use client";

import { useCallback, useEffect, useState } from "react";

import GraphView from "@/components/GraphView";

const API_BASE = "http://localhost:8000";

type ViewMode = "search" | "graph" | "architecture" | "onboarding" | "memory";
type AudienceMode = "beginner" | "pro";

interface ArchitectureOverview {
  files_indexed: number;
  modules: number;
  graph_nodes: number;
  graph_edges: number;
}

interface ArchitectureModule {
  name: string;
  file_count: number;
  symbol_count: number;
  top_symbols: string[];
}

interface ArchitectureDependency {
  from_module: string;
  to_module: string;
  weight: number;
  top_relations: { relation: string; count: number }[];
}

interface ArchitectureEntryPoint {
  symbol: string;
  file_path: string;
  line_start: number;
  fan_out: number;
  fan_in: number;
}

interface ArchitectureMapData {
  overview: ArchitectureOverview;
  modules: ArchitectureModule[];
  dependencies: ArchitectureDependency[];
  entry_points: ArchitectureEntryPoint[];
}

interface OnboardingData {
  summary: string;
  quickstart: string[];
  key_concepts: string[];
  recommended_files: string[];
  first_questions: string[];
  architecture_snapshot: ArchitectureOverview;
}

interface GlossaryItem {
  term: string;
  definition: string;
  updated_at: string;
}

interface NoteItem {
  id: number;
  note: string;
  source_query: string | null;
  created_at: string;
}

interface MemoryData {
  glossary: GlossaryItem[];
  notes: NoteItem[];
}

interface QueryFlowStep {
  node: string;
  file_path: string;
  line_start: number;
  line_end: number;
}

interface CitationData {
  file_path: string;
  start_line: number;
  end_line: number;
}

interface QueryAnswerData {
  answer: string;
  flow: QueryFlowStep[];
  citations: CitationData[];
  confidence: string;
}

interface RepoStatusData {
  status: string;
  files_indexed?: number;
  chunks_created?: number;
  graph_nodes?: number;
  graph_edges?: number;
}

interface RepoListItemData {
  id: string;
  repo_id?: string;
  name: string;
  status: string;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [audienceMode, setAudienceMode] = useState<AudienceMode>("pro");
  const [isIndexing, setIsIndexing] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);
  const [repos, setRepos] = useState<RepoListItemData[]>([]);
  const [answer, setAnswer] = useState<QueryAnswerData | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<RepoStatusData | null>(null);
  const [activeView, setActiveView] = useState<ViewMode>("search");
  const [viewLoading, setViewLoading] = useState(false);

  const [architecture, setArchitecture] = useState<ArchitectureMapData | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingData | null>(null);
  const [memory, setMemory] = useState<MemoryData>({ glossary: [], notes: [] });

  const [newTerm, setNewTerm] = useState("");
  const [newDefinition, setNewDefinition] = useState("");
  const [newNote, setNewNote] = useState("");
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [downloadingRepo, setDownloadingRepo] = useState(false);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (activeRepoId && status?.status !== "READY" && status?.status !== "FAILED") {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/repos/${activeRepoId}/status`);
          const data = await res.json();
          setStatus(data);
          if (data.status === "READY") {
            clearInterval(interval);
          }
        } catch {
          console.error("Status check failed");
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [activeRepoId, status]);

  const handleIndex = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, branch }),
      });
      const data = await res.json();
      setActiveRepoId(data.repo_id);
      setIsIndexing(false);
      setStatus({ status: "PENDING" });
      setRepos([...repos, { id: data.repo_id, name: repoUrl.split("/").pop(), status: "PENDING" }]);
      setAnswer(null);
      setArchitecture(null);
      setOnboarding(null);
      setMemory({ glossary: [], notes: [] });
    } catch {
      alert("Failed to start indexing");
    }
  };

  const handleQuery = async () => {
    if (!activeRepoId || !query) return;
    setLoading(true);
    setActiveView("search");
    try {
      const res = await fetch(`${API_BASE}/api/repos/${activeRepoId}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, audience_mode: audienceMode }),
      });
      const data = await res.json();
      setAnswer(data);
    } catch {
      alert("Query failed");
    } finally {
      setLoading(false);
    }
  };

  const loadArchitecture = useCallback(async (repoIdOverride?: string) => {
    const repoId = repoIdOverride || activeRepoId;
    if (!repoId) return;
    setViewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/architecture-map`);
      const data = await res.json();
      setArchitecture(data);
    } catch {
      alert("Failed to load architecture map");
    } finally {
      setViewLoading(false);
    }
  }, [activeRepoId]);

  const loadRepoStatus = useCallback(async (repoId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/status`);
      if (!res.ok) return;
      const data: RepoStatusData = await res.json();
      setStatus(data);
    } catch {
      console.error("Failed to refresh repository status");
    }
  }, []);

  const loadOnboarding = useCallback(async (repoIdOverride?: string) => {
    const repoId = repoIdOverride || activeRepoId;
    if (!repoId) return;
    setViewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/onboarding`);
      const data = await res.json();
      setOnboarding(data);
    } catch {
      alert("Failed to load onboarding guide");
    } finally {
      setViewLoading(false);
    }
  }, [activeRepoId]);

  const loadMemory = useCallback(async (repoIdOverride?: string) => {
    const repoId = repoIdOverride || activeRepoId;
    if (!repoId) return;
    setViewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/memory`);
      const data = await res.json();
      setMemory({
        glossary: data.glossary || [],
        notes: data.notes || [],
      });
    } catch {
      alert("Failed to load project memory");
    } finally {
      setViewLoading(false);
    }
  }, [activeRepoId]);

  const handleGlossarySave = async () => {
    if (!activeRepoId || !newTerm.trim() || !newDefinition.trim()) return;
    setMemoryBusy(true);
    try {
      await fetch(`${API_BASE}/api/repos/${activeRepoId}/memory/glossary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          term: newTerm.trim(),
          definition: newDefinition.trim(),
        }),
      });
      setNewTerm("");
      setNewDefinition("");
      await loadMemory();
    } catch {
      alert("Failed to save glossary term");
    } finally {
      setMemoryBusy(false);
    }
  };

  const handleGlossaryDelete = async (term: string) => {
    if (!activeRepoId) return;
    setMemoryBusy(true);
    try {
      await fetch(`${API_BASE}/api/repos/${activeRepoId}/memory/glossary?term=${encodeURIComponent(term)}`, {
        method: "DELETE",
      });
      await loadMemory();
    } catch {
      alert("Failed to delete glossary term");
    } finally {
      setMemoryBusy(false);
    }
  };

  const handleNoteSave = async () => {
    if (!activeRepoId || !newNote.trim()) return;
    setMemoryBusy(true);
    try {
      await fetch(`${API_BASE}/api/repos/${activeRepoId}/memory/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: newNote.trim(), source_query: query || null }),
      });
      setNewNote("");
      await loadMemory();
    } catch {
      alert("Failed to save note");
    } finally {
      setMemoryBusy(false);
    }
  };

  const handleDownloadRepo = async () => {
    if (!activeRepoId || status?.status !== "READY") return;

    setDownloadingRepo(true);
    try {
      const res = await fetch(`${API_BASE}/api/repos/${activeRepoId}/download`);
      if (!res.ok) {
        throw new Error("download_failed");
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("content-disposition") || "";
      const filenameMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
      const filename = filenameMatch?.[1] || `${activeRepoId}.zip`;

      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      alert("Failed to download ZIP. Please ensure indexing is completed.");
    } finally {
      setDownloadingRepo(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-canvas overflow-hidden text-text-main">
      <aside className="w-72 border-r border-border-subtle bg-surface flex flex-col z-20 shadow-xl">
        <div className="p-6 border-b border-border-subtle flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-brand rounded-technical flex items-center justify-center text-canvas font-bold shadow-lg shadow-primary-brand/20">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/></svg>
          </div>
          <div>
            <h1 className="font-bold tracking-tight text-gradient text-lg">Code Intel</h1>
            <p className="text-[10px] text-text-muted font-bold uppercase tracking-wider">Production System</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="pb-4 px-3">
            <button
              onClick={() => setIsIndexing(true)}
              className="w-full bg-surface-raised border border-border-subtle hover:border-primary-brand text-xs font-bold py-2.5 rounded-technical transition-all flex items-center justify-center gap-2 group"
            >
              <span className="text-primary-brand group-hover:scale-110 transition-transform">+</span> New Repository
            </button>
          </div>

          <NavItem active={activeView === "search"} label="Semantic Search" icon={<SearchIcon />} onClick={() => setActiveView("search")} />
          <NavItem active={activeView === "graph"} label="Dependency Graph" icon={<GraphIcon />} onClick={() => setActiveView("graph")} />
          <NavItem
            active={activeView === "architecture"}
            label="Architecture Map"
            icon={<LayersIcon />}
            onClick={() => {
              setActiveView("architecture");
              void loadArchitecture();
            }}
          />
          <NavItem
            active={activeView === "onboarding"}
            label="Onboarding Guide"
            icon={<BookIcon />}
            onClick={() => {
              setActiveView("onboarding");
              void loadOnboarding();
            }}
          />
          <NavItem
            active={activeView === "memory"}
            label="Glossary & Memory"
            icon={<MemoryIcon />}
            onClick={() => {
              setActiveView("memory");
              void loadMemory();
            }}
          />

          <div className="pt-8 pb-2 px-4 text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center justify-between">
            <span>Repositories</span>
            <span className="w-1.5 h-1.5 rounded-full bg-secondary-brand shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
          </div>

          <div className="space-y-1">
            {repos.map((repo) => (
              <RepoItem
                key={repo.id}
                name={repo.name}
                status={repo.id === activeRepoId ? (status?.status || repo.status) : repo.status}
                active={repo.id === activeRepoId}
                onClick={() => {
                  const nextRepoId = repo.repo_id || repo.id;
                  setActiveRepoId(nextRepoId);
                  void loadRepoStatus(nextRepoId);
                  if (activeView === "architecture") {
                    void loadArchitecture(nextRepoId);
                  }
                  if (activeView === "onboarding") {
                    void loadOnboarding(nextRepoId);
                  }
                  if (activeView === "memory") {
                    void loadMemory(nextRepoId);
                  }
                }}
              />
            ))}
            {repos.length === 0 && (
              <div className="px-4 py-8 text-center space-y-2">
                <div className="text-text-muted opacity-20 flex justify-center"><FileIcon size={32} /></div>
                <p className="text-[10px] text-text-muted font-medium">No repositories indexed yet.</p>
              </div>
            )}
          </div>
        </div>

        <div className="p-5 border-t border-border-subtle bg-surface/50 backdrop-blur-sm">
          <div className="flex items-center gap-3 p-2 rounded-panel border border-transparent hover:border-border-subtle hover:bg-surface-raised transition-all cursor-pointer">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-brand to-secondary-brand flex items-center justify-center text-xs font-bold text-canvas shadow-lg">IS</div>
            <div className="flex flex-col">
              <span className="text-xs font-bold tracking-tight">Ishaan</span>
              <span className="text-[10px] text-secondary-brand font-medium">Online</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 bg-canvas relative">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary-brand/5 blur-[120px] rounded-full -mr-64 -mt-64 pointer-events-none"></div>

        <header className="h-16 border-b border-border-subtle bg-surface/80 backdrop-blur-md flex items-center justify-between px-8 z-10 gap-6">
          <div className="flex-1 max-w-3xl">
            <div className="relative group">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                placeholder="Ask intelligence: 'How does the payment flow work?'"
                className="w-full bg-canvas/50 border border-border-subtle rounded-technical py-2 px-5 pl-12 text-sm font-medium text-text-main focus:outline-none focus:border-primary-brand focus:ring-4 focus:ring-primary-brand/10 transition-all placeholder:text-text-muted"
              />
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary-brand transition-colors">
                <SearchIcon size={18} />
              </div>
              <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
                {loading && <div className="w-4 h-4 border-2 border-primary-brand border-t-transparent rounded-full animate-spin"></div>}
                <div className="text-[10px] font-bold text-text-muted border border-border-subtle px-2 py-0.5 rounded bg-surface-raised shadow-sm">
                  ENTER
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <AudienceToggle mode={audienceMode} onChange={setAudienceMode} />
            <button className="text-text-secondary hover:text-text-main transition-colors">
              <SettingsIcon size={20} />
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col bg-canvas/50 overflow-y-auto custom-scrollbar">
            {activeView === "graph" && activeRepoId ? (
              <GraphView repoId={activeRepoId} apiBase={API_BASE} />
            ) : null}

            {activeView === "architecture" && (
              <ArchitecturePanel loading={viewLoading} data={architecture} />
            )}

            {activeView === "onboarding" && (
              <OnboardingPanel loading={viewLoading} data={onboarding} />
            )}

            {activeView === "memory" && (
              <MemoryPanel
                loading={viewLoading}
                memory={memory}
                newTerm={newTerm}
                setNewTerm={setNewTerm}
                newDefinition={newDefinition}
                setNewDefinition={setNewDefinition}
                newNote={newNote}
                setNewNote={setNewNote}
                onSaveTerm={handleGlossarySave}
                onDeleteTerm={handleGlossaryDelete}
                onSaveNote={handleNoteSave}
                busy={memoryBusy}
              />
            )}

            {activeView === "search" && (
              <>
                {!answer && (
                  <div className="flex-1 flex flex-col items-center justify-center p-12 text-center space-y-8 animate-fade-in">
                    <div className="relative">
                      <div className="w-24 h-24 bg-primary-brand/10 rounded-3xl flex items-center justify-center text-primary-brand relative z-10 border border-primary-brand/20 shadow-2xl">
                        <GraphIcon size={48} />
                      </div>
                      <div className="absolute -inset-4 bg-primary-brand/5 blur-2xl rounded-full"></div>
                    </div>
                    <div className="max-w-md space-y-4">
                      <h2 className="text-2xl font-bold tracking-tight">Ready to explore <span className="text-gradient">your codebase</span>?</h2>
                      <p className="text-sm text-text-secondary leading-relaxed">
                        Select a repository or index a new one to begin. Switch between Beginner and Pro mode for the response depth you need.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 w-full max-w-lg">
                      <div className="p-4 border border-border-subtle rounded-panel bg-surface/50 hover:border-primary-brand/50 transition-all cursor-pointer group">
                        <h4 className="text-xs font-bold text-primary-brand mb-1">Architecture Map</h4>
                        <p className="text-[10px] text-text-muted">Understand modules, edges, and likely entry points.</p>
                      </div>
                      <div className="p-4 border border-border-subtle rounded-panel bg-surface/50 hover:border-secondary-brand/50 transition-all cursor-pointer group">
                        <h4 className="text-xs font-bold text-secondary-brand mb-1">Onboarding Assistant</h4>
                        <p className="text-[10px] text-text-muted">Get quickstart guidance for new team members.</p>
                      </div>
                    </div>
                  </div>
                )}

                {answer && (
                  <div className="p-10 space-y-12 animate-fade-in">
                    <div className="space-y-6">
                      <div className="flex items-center gap-3">
                        <div className="px-3 py-1 bg-primary-brand/10 text-primary-brand text-[10px] font-bold rounded uppercase tracking-widest border border-primary-brand/20">Answer</div>
                        <div className="h-[1px] flex-1 bg-border-subtle"></div>
                      </div>
                      <div className="prose prose-invert max-w-none">
                        <p className="text-lg leading-relaxed text-text-main font-medium whitespace-pre-wrap">
                          {answer.answer}
                        </p>
                      </div>
                    </div>

                    {answer.flow && answer.flow.length > 0 && (
                      <div className="space-y-6">
                        <div className="flex items-center gap-3">
                          <div className="px-3 py-1 bg-secondary-brand/10 text-secondary-brand text-[10px] font-bold rounded uppercase tracking-widest border border-secondary-brand/20">Logic Flow</div>
                          <div className="h-[1px] flex-1 bg-border-subtle"></div>
                        </div>
                        <div className="flex flex-wrap gap-4">
                          {answer.flow.map((step: QueryFlowStep, i: number) => (
                            <div key={i} className="flex items-center gap-4">
                              <div className="p-4 bg-surface rounded-panel border border-border-subtle shadow-lg hover:border-primary-brand/50 transition-all group min-w-[200px]">
                                <div className="text-[10px] text-text-muted font-bold mb-1 uppercase tracking-tighter">Step {i + 1}</div>
                                <div className="text-xs font-bold text-text-main group-hover:text-primary-brand transition-colors">{step.node}</div>
                                <div className="text-[10px] text-text-muted mt-2 font-mono truncate">{step.file_path}</div>
                              </div>
                              {i < answer.flow.length - 1 && (
                                <div className="text-text-muted">
                                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <aside className="w-[380px] border-l border-border-subtle bg-surface flex flex-col z-10">
            <div className="p-6 border-b border-border-subtle flex items-center justify-between">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-widest">Metadata Context</h3>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${status?.status === "READY" ? "bg-secondary-brand shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-warning-brand animate-pulse"}`}></span>
                <span className="text-[10px] font-bold text-text-main">{status?.status || "IDLE"}</span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Index Statistics</h4>
                <div className="grid grid-cols-2 gap-3">
                  <StatBox label="Files" value={status?.files_indexed || architecture?.overview?.files_indexed || 0} />
                  <StatBox label="Chunks" value={status?.chunks_created || 0} />
                  <StatBox label="Nodes" value={status?.graph_nodes || architecture?.overview?.graph_nodes || 0} />
                  <StatBox label="Edges" value={status?.graph_edges || architecture?.overview?.graph_edges || 0} />
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Assistant Mode</h4>
                <div className="p-3 border border-border-subtle rounded-panel bg-canvas">
                  <div className="text-xs font-bold text-primary-brand uppercase">{audienceMode}</div>
                  <div className="text-[11px] text-text-muted mt-2">
                    {audienceMode === "beginner"
                      ? "Explains concepts in plain language and guided steps."
                      : "Returns concise technical answers and trade-offs."}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Repository Export</h4>
                <button
                  onClick={handleDownloadRepo}
                  disabled={!activeRepoId || status?.status !== "READY" || downloadingRepo}
                  className={`w-full text-xs font-bold py-3 rounded-technical border transition-all ${
                    !activeRepoId || status?.status !== "READY" || downloadingRepo
                      ? "border-border-subtle text-text-muted bg-canvas cursor-not-allowed"
                      : "border-primary-brand text-primary-brand bg-primary-brand/10 hover:bg-primary-brand/20"
                  }`}
                >
                  {downloadingRepo ? "Preparing ZIP..." : "Download Indexed Repo (ZIP)"}
                </button>
                <p className="text-[10px] text-text-muted">
                  Available once the selected repository is fully mapped.
                </p>
              </div>

              {answer && answer.citations?.length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Sources & Evidence</h4>
                  <div className="space-y-2">
                    {answer.citations?.map((cit: CitationData, i: number) => (
                      <CitationItem key={i} file={cit.file_path} lines={`${cit.start_line}-${cit.end_line}`} confidence={answer.confidence} />
                    ))}
                  </div>
                </div>
              )}

              {activeView === "memory" && (
                <div className="space-y-4">
                  <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Memory Snapshot</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <StatBox label="Terms" value={memory.glossary.length} />
                    <StatBox label="Notes" value={memory.notes.length} />
                  </div>
                </div>
              )}
            </div>
          </aside>
        </div>
      </main>

      {isIndexing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/60 backdrop-blur-xl p-6 animate-fade-in">
          <div className="w-full max-w-xl glass-panel rounded-panel p-10 space-y-8 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-brand via-secondary-brand to-primary-brand bg-[length:200%_auto] animate-shimmer"></div>

            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-gradient">Index Codebase</h2>
                <p className="text-xs text-text-secondary mt-1">Provide a GitHub URL to start the intelligence engine.</p>
              </div>
              <button onClick={() => setIsIndexing(false)} className="w-8 h-8 rounded-full hover:bg-surface-raised flex items-center justify-center transition-colors">X</button>
            </div>

            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Repository URL</label>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/facebook/react"
                  className="w-full bg-surface border border-border-subtle rounded-technical p-4 text-sm font-medium focus:outline-none focus:border-primary-brand focus:ring-4 focus:ring-primary-brand/5 transition-all"
                />
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Branch</label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-surface border border-border-subtle rounded-technical p-4 text-sm font-medium focus:outline-none focus:border-primary-brand transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Mode</label>
                  <select className="w-full bg-surface border border-border-subtle rounded-technical p-4 text-sm font-medium focus:outline-none focus:border-primary-brand appearance-none">
                    <option>Standard Hybrid Index</option>
                    <option>Deep Semantic (Slower)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="pt-4 flex flex-col items-center gap-4">
              <button
                onClick={handleIndex}
                className="w-full bg-primary-brand hover:bg-primary-brand/90 text-canvas font-bold py-4 rounded-technical shadow-2xl shadow-primary-brand/20 transition-all btn-hover"
              >
                Start Ingestion Pipeline
              </button>
              <div className="flex items-center gap-6">
                <Badge label="Tree-sitter" />
                <Badge label="BGE-small" />
                <Badge label="FAISS" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ArchitecturePanel({ loading, data }: { loading: boolean; data: ArchitectureMapData | null }) {
  if (loading) {
    return <LoadingPanel label="Building architecture map..." />;
  }

  if (!data) {
    return <EmptyPanel label="Select a repository to view architecture map." />;
  }

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatBox label="Files Indexed" value={data.overview.files_indexed} />
        <StatBox label="Modules" value={data.overview.modules} />
        <StatBox label="Graph Nodes" value={data.overview.graph_nodes} />
        <StatBox label="Graph Edges" value={data.overview.graph_edges} />
      </div>

      <section className="space-y-4">
        <SectionTitle title="Modules" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.modules.slice(0, 12).map((module) => (
            <div key={module.name} className="p-4 border border-border-subtle rounded-panel bg-surface">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-primary-brand">{module.name}</h4>
                <span className="text-[10px] text-text-muted">{module.file_count} files</span>
              </div>
              <p className="text-[11px] text-text-muted mt-2">{module.symbol_count} symbols</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {module.top_symbols.slice(0, 4).map((symbol) => (
                  <span key={symbol} className="text-[10px] px-2 py-1 rounded border border-border-subtle bg-canvas">{symbol}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Dependency Paths" />
        <div className="space-y-2">
          {data.dependencies.slice(0, 12).map((dep, idx) => (
            <div key={`${dep.from_module}-${dep.to_module}-${idx}`} className="p-3 border border-border-subtle rounded-panel bg-surface flex items-center justify-between gap-4">
              <div className="text-xs font-medium">
                <span className="text-primary-brand">{dep.from_module}</span>
                <span className="text-text-muted mx-2">{"->"}</span>
                <span className="text-secondary-brand">{dep.to_module}</span>
              </div>
              <div className="text-[10px] text-text-muted">{dep.weight} edges</div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Likely Entry Points" />
        <div className="space-y-2">
          {data.entry_points.slice(0, 8).map((entry) => (
            <div key={`${entry.file_path}-${entry.symbol}`} className="p-3 border border-border-subtle rounded-panel bg-surface">
              <div className="text-xs font-bold text-text-main">{entry.symbol}</div>
              <div className="text-[10px] text-text-muted mt-1 font-mono">{entry.file_path}:{entry.line_start || 1}</div>
              <div className="text-[10px] text-text-muted mt-1">Fan-out {entry.fan_out} | Fan-in {entry.fan_in}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function OnboardingPanel({ loading, data }: { loading: boolean; data: OnboardingData | null }) {
  if (loading) {
    return <LoadingPanel label="Generating onboarding guide..." />;
  }
  if (!data) {
    return <EmptyPanel label="Select a repository to load onboarding." />;
  }

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      <section className="p-5 border border-border-subtle rounded-panel bg-surface">
        <SectionTitle title="Repository Summary" />
        <p className="text-sm text-text-main leading-relaxed mt-4">{data.summary}</p>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OnboardingCard title="Quickstart" items={data.quickstart} />
        <OnboardingCard title="Key Concepts" items={data.key_concepts} />
        <OnboardingCard title="Recommended Files" items={data.recommended_files} />
        <OnboardingCard title="First Questions" items={data.first_questions} />
      </section>
    </div>
  );
}

function MemoryPanel({
  loading,
  memory,
  newTerm,
  setNewTerm,
  newDefinition,
  setNewDefinition,
  newNote,
  setNewNote,
  onSaveTerm,
  onDeleteTerm,
  onSaveNote,
  busy,
}: {
  loading: boolean;
  memory: MemoryData;
  newTerm: string;
  setNewTerm: (value: string) => void;
  newDefinition: string;
  setNewDefinition: (value: string) => void;
  newNote: string;
  setNewNote: (value: string) => void;
  onSaveTerm: () => void;
  onDeleteTerm: (term: string) => void;
  onSaveNote: () => void;
  busy: boolean;
}) {
  if (loading) {
    return <LoadingPanel label="Loading glossary and project memory..." />;
  }

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 border border-border-subtle rounded-panel bg-surface space-y-3">
          <SectionTitle title="Add Glossary Term" />
          <input
            value={newTerm}
            onChange={(e) => setNewTerm(e.target.value)}
            placeholder="Term"
            className="w-full bg-canvas border border-border-subtle rounded-technical p-3 text-sm"
          />
          <textarea
            value={newDefinition}
            onChange={(e) => setNewDefinition(e.target.value)}
            placeholder="Definition"
            className="w-full bg-canvas border border-border-subtle rounded-technical p-3 text-sm min-h-24"
          />
          <button
            disabled={busy}
            onClick={onSaveTerm}
            className="bg-primary-brand text-canvas text-xs font-bold px-4 py-2 rounded-technical"
          >
            Save Term
          </button>
        </div>

        <div className="p-4 border border-border-subtle rounded-panel bg-surface space-y-3">
          <SectionTitle title="Add Project Note" />
          <textarea
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Example: Checkout flow depends on inventory pre-check."
            className="w-full bg-canvas border border-border-subtle rounded-technical p-3 text-sm min-h-32"
          />
          <button
            disabled={busy}
            onClick={onSaveNote}
            className="bg-secondary-brand text-canvas text-xs font-bold px-4 py-2 rounded-technical"
          >
            Save Note
          </button>
        </div>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Glossary Terms" />
        <div className="space-y-2">
          {memory.glossary.length === 0 && <p className="text-xs text-text-muted">No glossary terms saved yet.</p>}
          {memory.glossary.map((item) => (
            <div key={item.term} className="p-3 border border-border-subtle rounded-panel bg-surface flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-bold text-primary-brand">{item.term}</div>
                <div className="text-[11px] text-text-muted mt-1">{item.definition}</div>
              </div>
              <button onClick={() => onDeleteTerm(item.term)} className="text-[10px] border border-border-subtle rounded px-2 py-1 hover:border-warning-brand">
                Remove
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <SectionTitle title="Project Notes" />
        <div className="space-y-2">
          {memory.notes.length === 0 && <p className="text-xs text-text-muted">No notes saved yet.</p>}
          {memory.notes.map((item) => (
            <div key={item.id} className="p-3 border border-border-subtle rounded-panel bg-surface">
              <div className="text-xs text-text-main">{item.note}</div>
              {item.source_query && (
                <div className="text-[10px] text-text-muted mt-2">Source query: {item.source_query}</div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function AudienceToggle({ mode, onChange }: { mode: AudienceMode; onChange: (mode: AudienceMode) => void }) {
  return (
    <div className="flex items-center border border-border-subtle rounded-technical overflow-hidden bg-surface-raised">
      <button
        className={`px-3 py-2 text-[10px] font-bold uppercase tracking-wide ${mode === "beginner" ? "bg-primary-brand text-canvas" : "text-text-muted hover:text-text-main"}`}
        onClick={() => onChange("beginner")}
      >
        Beginner
      </button>
      <button
        className={`px-3 py-2 text-[10px] font-bold uppercase tracking-wide ${mode === "pro" ? "bg-secondary-brand text-canvas" : "text-text-muted hover:text-text-main"}`}
        onClick={() => onChange("pro")}
      >
        Pro
      </button>
    </div>
  );
}

function OnboardingCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="p-4 border border-border-subtle rounded-panel bg-surface space-y-3">
      <SectionTitle title={title} />
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div key={`${title}-${idx}`} className="text-xs text-text-secondary">{idx + 1}. {item}</div>
        ))}
      </div>
    </div>
  );
}

function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary-brand border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-text-muted uppercase tracking-widest">{label}</p>
      </div>
    </div>
  );
}

function EmptyPanel({ label }: { label: string }) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center">
        <p className="text-sm text-text-muted">{label}</p>
      </div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h3 className="text-[10px] font-bold text-text-muted uppercase tracking-widest">{title}</h3>;
}

function NavItem({ label, icon, active = false, onClick }: { label: string; icon: React.ReactNode; active?: boolean; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-technical cursor-pointer transition-all group ${active ? "bg-primary-brand/10 text-primary-brand" : "text-text-secondary hover:bg-surface-raised hover:text-text-main"}`}
    >
      <span className={`${active ? "text-primary-brand" : "text-text-muted group-hover:text-text-main"} transition-colors`}>{icon}</span>
      <span className="text-xs font-bold tracking-tight">{label}</span>
      {active && <div className="ml-auto w-1 h-4 bg-primary-brand rounded-full shadow-[0_0_8px_var(--color-primary-brand)]"></div>}
    </div>
  );
}

function RepoItem({ name, status, active, onClick }: { name: string; status: string; active: boolean; onClick: () => void }) {
  const isReady = status === "READY";
  return (
    <div
      onClick={onClick}
      className={`px-4 py-3 flex items-center justify-between group cursor-pointer rounded-technical border border-transparent transition-all ${active ? "bg-surface-raised border-border-subtle shadow-lg" : "hover:bg-surface-raised/50"}`}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        <span className={`text-sm ${active ? "text-primary-brand" : "text-text-muted group-hover:text-text-secondary"}`}>F</span>
        <span className={`text-xs font-bold truncate ${active ? "text-text-main" : "text-text-secondary group-hover:text-text-main"}`}>{name}</span>
      </div>
      <span className={`text-[8px] font-black tracking-tighter px-1.5 py-0.5 rounded border uppercase ${isReady ? "text-secondary-brand border-secondary-brand/20 bg-secondary-brand/5" : "text-warning-brand border-warning-brand/20 bg-warning-brand/5"}`}>
        {status}
      </span>
    </div>
  );
}

function CitationItem({ file, lines, confidence }: { file: string; lines: string; confidence: string }) {
  return (
    <div className="p-3 border border-border-subtle rounded-panel bg-canvas hover:border-primary-brand transition-all cursor-pointer group shadow-sm">
      <div className="flex justify-between items-center mb-2">
        <span className="text-[10px] font-mono font-bold text-primary-brand truncate max-w-[200px]">{file}</span>
        <span className={`text-[8px] font-black uppercase px-1 rounded border ${confidence === "high" ? "text-secondary-brand border-secondary-brand/20" : "text-warning-brand border-warning-brand/20"}`}>{confidence}</span>
      </div>
      <div className="text-[10px] text-text-muted font-medium">Lines {lines}</div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 rounded-technical bg-canvas border border-border-subtle flex flex-col gap-1">
      <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">{label}</span>
      <span className="text-sm font-bold text-text-main">{Number(value || 0).toLocaleString()}</span>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity">
      <div className="w-1 h-1 rounded-full bg-text-muted"></div>
      <span className="text-[9px] font-bold text-text-muted uppercase tracking-widest">{label}</span>
    </div>
  );
}

const SearchIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
);
const FileIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>
);
const GraphIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
);
const LayersIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-9 4.5 9 4.5 9-4.5L12 3Z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/></svg>
);
const BookIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>
);
const MemoryIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg>
);
const SettingsIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>
);
