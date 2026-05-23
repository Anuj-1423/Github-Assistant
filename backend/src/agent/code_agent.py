try:
    from langchain.agents import create_tool_calling_agent, AgentExecutor
except ImportError:
    try:
        from langchain.agents import create_agent
        create_tool_calling_agent = None
        AgentExecutor = None
    except ImportError:
        create_tool_calling_agent = None
        create_agent = None
        AgentExecutor = None

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from src.agent.tools import CodeIntelligenceTools
from src.agent.system_tools import SystemControlTools
from src.retrieval.hybrid_retriever import HybridRetriever
from src.graph.graph_builder import CodeGraph
from typing import Dict, Any, List
import logging
import os
import threading

logger = logging.getLogger(__name__)

# Load env for non-FastAPI entrypoints (demo scripts/tests).
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env"), override=True)


class CodeAgent:
    # Shared across all instances — ensures strict round-robin across every request
    _request_counter: int = 0
    _counter_lock: threading.Lock = threading.Lock()

    @classmethod
    def _next_provider(cls) -> str:
        """Returns 'groq' or 'nvidia' alternating on every call."""
        with cls._counter_lock:
            provider = "groq" if cls._request_counter % 2 == 0 else "nvidia"
            cls._request_counter += 1
            return provider

    def __init__(self, repo_id: str, retriever: HybridRetriever, graph: CodeGraph, repo_path: str, audience_mode: str = "pro", memory_context: str = "", settings: Dict[str, Any] = None):
        self.repo_id = repo_id
        self.retriever = retriever
        self.graph = graph
        self.repo_path = repo_path
        self.audience_mode = audience_mode
        self.memory_context = memory_context
        self.tools_handler = CodeIntelligenceTools(repo_id, retriever, graph, repo_path)
        self.system_handler = SystemControlTools()
        
        # Combine codebase tools with system tools
        self.tools = self.tools_handler.get_tools() + self.system_handler.get_tools()
        self.executor = None
        self.init_error = None
        self.llm = None
        self.fallback_llm = None
        self.llm_groq = None       # Always initialized if GROQ_API_KEY is set
        self.llm_nvidia = None     # Always initialized if NVIDIA_API_KEY is set
        self.using_compiled_agent = False
        
        # Resolve settings: Argument > Database > Environment
        if not settings:
            try:
                from src.storage.storage_factory import get_storage
                store = get_storage()
                if hasattr(store, "get_system_settings"):
                    settings = store.get_system_settings()
            except Exception:
                pass
        
        settings = settings or {}

        # Env vars ALWAYS take strict priority over DB settings.
        # Strip whitespace to avoid falsy empty strings from .env files.
        env_provider = (os.getenv("LLM_PROVIDER") or "").strip()
        env_model    = (os.getenv("LLM_MODEL")    or "").strip()

        provider   = env_provider or settings.get("ai_provider") or "openai"
        provider   = provider.lower()
        model_name = env_model    or settings.get("model_name") or None
        temperature = settings.get("temperature", 0)
        max_tokens  = settings.get("max_tokens")

        if provider in ["google", "gemini"]:
            api_key = settings.get("api_key") or os.getenv("GOOGLE_API_KEY", "missing")
            if api_key != "missing":
                try:
                    if not model_name: model_name = "gemini-1.5-flash"
                    model = self._normalize_google_model(model_name)
                    self.llm = ChatGoogleGenerativeAI(
                        model=model,
                        google_api_key=api_key,
                        temperature=temperature,
                        max_retries=3,
                        max_output_tokens=max_tokens
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (Google/Gemini): {str(e)}"
                    self.llm = None
        elif provider == "anthropic":
            api_key = settings.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "missing")
            if api_key != "missing":
                try:
                    from langchain_anthropic import ChatAnthropic
                    self.llm = ChatAnthropic(
                        model=model_name or "claude-3-5-sonnet-latest",
                        temperature=temperature,
                        api_key=api_key,
                        max_tokens=max_tokens or 4096
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (Anthropic): {str(e)}"
                    self.llm = None
        elif provider == "cohere":
            api_key = settings.get("api_key") or os.getenv("COHERE_API_KEY", "missing")
            if api_key != "missing":
                try:
                    from langchain_cohere import ChatCohere
                    self.llm = ChatCohere(
                        model=model_name or "command-r-plus-08-2024",
                        temperature=temperature,
                        cohere_api_key=api_key
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (Cohere): {str(e)}"
                    self.llm = None
        elif provider == "groq" and ChatGroq is not None:
            api_key = os.getenv("GROQ_API_KEY") or settings.get("api_key") or "missing"
            if api_key != "missing":
                try:
                    # llama-3.1-8b-instant has 30 RPM on the free tier — enough for real usage.
                    # The 70B tool-use model has a much lower limit and causes repeated 429s.
                    default_groq_model = "llama-3.1-8b-instant"
                    self.llm = ChatGroq(
                        model=model_name or default_groq_model,
                        temperature=temperature,
                        groq_api_key=api_key,
                        max_tokens=max_tokens or 4096
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (Groq): {str(e)}"
                    self.llm = None
        elif provider in ["nvidia", "nim"]:
            api_key = os.getenv("NVIDIA_API_KEY") or settings.get("api_key") or "missing"
            if api_key != "missing":
                try:
                    # NVIDIA NIM is OpenAI-compatible — same client, different base URL and key.
                    self.llm = ChatOpenAI(
                        model=model_name or "meta/llama-3.1-8b-instruct",
                        temperature=temperature,
                        openai_api_key=api_key,
                        openai_api_base="https://integrate.api.nvidia.com/v1",
                        max_tokens=max_tokens or 4096
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (NVIDIA): {str(e)}"
                    self.llm = None
        else: # Default to OpenAI
            api_key = os.getenv("OPENAI_API_KEY") or settings.get("api_key") or "missing"
            base_url = os.getenv("OPENAI_API_BASE", None)
            if api_key != "missing":
                try:
                    self.llm = ChatOpenAI(
                        model=model_name or "gpt-4o",
                        temperature=temperature,
                        openai_api_key=api_key,
                        openai_api_base=base_url,
                        max_tokens=max_tokens
                    )
                except Exception as e:
                    self.init_error = f"LLM Init Error (OpenAI): {str(e)} | api_key_var='{api_key}' | env='{os.getenv('OPENAI_API_KEY')}'"
                    self.llm = None
            else:
                self.init_error = f"API Key missing. api_key_var='{api_key}' | env='{os.getenv('OPENAI_API_KEY')}'"
                self.llm = None

        # --- Always initialize BOTH Groq and NVIDIA for round-robin load balancing ---
        # Groq LLM
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key and ChatGroq is not None:
            try:
                self.llm_groq = ChatGroq(
                    model="llama-3.1-8b-instant",
                    temperature=0,
                    groq_api_key=groq_key,
                    max_tokens=4096
                )
            except Exception:
                self.llm_groq = None

        # NVIDIA NIM LLM
        nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
        if nvidia_key and nvidia_key != "your_nvidia_api_key_here":
            try:
                self.llm_nvidia = ChatOpenAI(
                    model="meta/llama-3.1-8b-instruct",
                    temperature=0,
                    openai_api_key=nvidia_key,
                    openai_api_base="https://integrate.api.nvidia.com/v1",
                    max_tokens=4096
                )
            except Exception:
                self.llm_nvidia = None

        # Pick primary LLM using round-robin if both are available.
        # IMPORTANT: NVIDIA NIM doesn't support LangChain tool-calling schema —
        # it handles direct LLM calls fine but throws 500s with the agent tool schema.
        # So: Groq gets the tool-calling agent, NVIDIA gets direct LLM calls.
        if self.llm_groq and self.llm_nvidia:
            chosen = CodeAgent._next_provider()
            self._active_provider = chosen
            self.llm = self.llm_groq if chosen == "groq" else self.llm_nvidia
            self.fallback_llm = self.llm_nvidia if chosen == "groq" else self.llm_groq
            logger.info(f"Round-robin: routing this request to [{chosen.upper()}]")
        elif self.llm_groq:
            self._active_provider = "groq"
            self.llm = self.llm_groq
        elif self.llm_nvidia:
            self._active_provider = "nvidia"
            self.llm = self.llm_nvidia
        else:
            self._active_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        # else: self.llm already set by the main provider block above

        if self.llm:
            system_prompt = f"""
            You are Codebase Knowledge AI — an expert code intelligence assistant built for engineers.

            Repository: {self.repo_id}
            User Level: {self.audience_mode}
            Project Memory: {self.memory_context}

            How to respond:
            - Lead with the answer. Don't open with "Great question!" or any warm-up. Get straight to it.
            - Write like a senior engineer explaining something to a capable colleague — clear, direct, and technically precise.
            - Use Markdown only where it genuinely helps: code blocks for code, bold for key terms, headers only when the response is long enough to need navigation.
            - When referencing code, always include the exact file path and line numbers.
            - If something could go wrong or needs a caveat, say it plainly — don't bury it in bullet points.
            - End when you're done. No filler closing lines like "I hope this helps!"
            - Tool calls: provide ONLY the exact tool name (e.g. 'search_code'). Never include JSON or curly braces in the tool name field.
            """
            
            if create_tool_calling_agent:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])
                try:
                    agent = create_tool_calling_agent(self.llm, self.tools, prompt)
                    self.executor = AgentExecutor(
                        agent=agent,
                        tools=self.tools,
                        verbose=True,
                        max_iterations=5,        # Stops runaway tool loops (each loop = 1 API call)
                        max_execution_time=60,   # Hard 60s wall-clock limit per query
                        early_stopping_method="generate",
                        handle_parsing_errors=True,
                    )
                except Exception as e:
                    self.init_error = f"Agent Creation Error: {str(e)}"
                    self.executor = None
            elif 'create_agent' in globals() and create_agent:
                # Use the new API found in this environment
                try:
                    self.executor = create_agent(
                        model=self.llm,
                        tools=self.tools,
                        system_prompt=system_prompt
                    )
                    self.using_compiled_agent = True
                except Exception as e:
                    self.init_error = f"create_agent Error: {str(e)}"
                    self.executor = None
            else:
                self.init_error = "No supported agent creation function found in langchain.agents"

    async def answer(self, query: str) -> Dict[str, Any]:
        if not self.llm:
            provider = os.getenv("LLM_PROVIDER", "openai").upper()
            reason = f"LLM provider not available ({provider}). {self.init_error or ''}".strip()
            return self._fallback_answer(query, reason)

        # NVIDIA NIM doesn't handle LangChain's tool-calling schema well (returns 500).
        # Route NVIDIA turns directly to _direct_llm_answer — it's fast and reliable.
        if getattr(self, "_active_provider", "") == "nvidia":
            logger.info("NVIDIA turn — using direct LLM (no tool schema).")
            return await self._direct_llm_answer(query)

        if not self.executor:
            reason = f"Agent executor unavailable. {self.init_error or ''}".strip()
            return self._fallback_answer(query, reason)
        
        try:
            if self.using_compiled_agent:
                response = await self.executor.ainvoke({
                    "messages": [{"role": "user", "content": query}]
                })
            elif hasattr(self.executor, 'ainvoke'):
                response = await self.executor.ainvoke({"input": query})
            else:
                response = await self.executor.invoke({"input": query})
            
            # Extract output based on response format
            answer = ""
            if isinstance(response, dict):
                answer = response.get("output") or response.get("answer") or self._extract_message_text(response)
                if not answer:
                    answer = str(response)
            else:
                answer = str(response)

            # If the agent returned a blank, hallucinated XML tags, or explicit error strings,
            # fall through to the direct RAG path which always produces a grounded response.
            ans_lower = answer.strip().lower()
            is_error = "error:" in ans_lower or "generation exceeded" in ans_lower or "max tokens" in ans_lower
            is_hallucinated_tag = answer.strip().startswith("<") and answer.strip().endswith(">")

            if not answer or len(answer.strip()) < 50 or is_error or is_hallucinated_tag:
                logger.warning(f"Agent returned invalid output (len={len(answer)}) — falling back to direct RAG answer.")
                return await self._direct_llm_answer(query)

            return {
                "answer": answer,
                "flow": [],
                "citations": [],
                "confidence": "high"
            }
        except Exception as e:
            error_msg = str(e)
            # Rate limit OR server error on primary — cross-over to the other provider
            is_rate_limit = "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate_limit" in error_msg.lower()
            is_server_error = "500" in error_msg or "Internal Server Error" in error_msg or "502" in error_msg
            if is_rate_limit or is_server_error:
                if self.fallback_llm:
                    reason = "rate-limited" if is_rate_limit else "server error"
                    logger.warning(f"Primary LLM {reason}. Switching to fallback provider.")
                    original_llm = self.llm
                    self.llm = self.fallback_llm
                    result = await self._direct_llm_answer(query)
                    self.llm = original_llm
                    return result
                return self._fallback_answer(query, "Primary provider failed. Add a second API key to .env to enable automatic failover.")
            # Decommissioned or tool-call failure — retry without tools
            if "model_decommissioned" in error_msg or "decommissioned" in error_msg:
                return await self._direct_llm_answer(query)
            if "tool_use_failed" in error_msg or "tool call validation" in error_msg or "Failed to call a function" in error_msg:
                return await self._direct_llm_answer(query)
            return self._fallback_answer(query, f"Agent execution error: {error_msg}")

    async def answer_stream(self, query: str):
        """
        Streaming version of answer for real-time feedback and voice orchestration.
        """
        if not self.llm or not self.executor:
            res = self._fallback_answer(query)
            yield {"type": "answer", "content": res["answer"]}
            return

        try:
            # Using astream_events for granular feedback (thoughts, tool usage, and text chunks)
            async for event in self.executor.astream_events(
                {"input": query},
                version="v1"
            ):
                kind = event["event"]
                
                # Model is thinking or using a tool
                if kind == "on_tool_start":
                    tool_name = event["name"]
                    yield {"type": "thought", "content": f"Initializing {tool_name}..."}
                
                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    yield {"type": "thought", "content": f"{tool_name} processing complete."}

                # Model is streaming tokens
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {"type": "chunk", "content": content}

                # Agent final output
                elif kind == "on_chain_end" and event["name"] == "AgentExecutor":
                    # We usually get the final answer via chunks, but this confirms completion
                    yield {"type": "done", "content": ""}

        except Exception as e:
            yield {"type": "error", "content": f"System anomaly detected: {str(e)}"}

    async def _direct_llm_answer(self, query: str) -> Dict[str, Any]:
        """
        Direct LLM answer with rich code context.
        Used for NVIDIA turns and as fallback when the tool agent fails.
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            # Retrieve up to 12 chunks for broader coverage
            chunks = self.retriever.retrieve(query, limit=12)
            context_parts = []
            citations = []
            seen_files = set()

            for chunk in chunks:
                file_path = chunk.get("file_path", "")
                seen_files.add(file_path)
                snippet = (chunk.get("content") or "")[:800].strip()
                symbol = chunk.get("symbol_name", "")
                start = chunk.get("start_line", 0)
                end = chunk.get("end_line", 0)

                label = f"{file_path}"
                if symbol and symbol.lower() not in {"global", "module", ""}:
                    label += f" → {symbol}"
                label += f" (lines {start}–{end})"

                context_parts.append(f"**{label}**\n```\n{snippet}\n```")
                citations.append({
                    "file_path": file_path,
                    "start_line": start,
                    "end_line": end,
                })

            # Build a file listing from what we've seen
            file_list = "\n".join(f"  - {f}" for f in sorted(seen_files)) if seen_files else "  (no files retrieved)"

            # Repo identity
            repo_name = self.repo_id

            if context_parts:
                context_block = "\n\n".join(context_parts)
                context_section = f"Files seen in this repo:\n{file_list}\n\nRelevant code snippets:\n\n{context_block}"
            else:
                context_section = (
                    f"No code chunks were retrieved for this query. "
                    f"The repo ID is '{repo_name}'. "
                    f"Answer based on general knowledge of what this type of project likely does, "
                    f"but be clear you're inferring from the repo name/context rather than reading the code."
                )

            system_msg = (
                "You are Codebase Knowledge AI — an expert code analyst. "
                "You are given actual source code and file names from a real repository. "
                "Your job is to answer the user's question based on this code.\n\n"
                "Rules:\n"
                "- Read the file names and code snippets carefully before answering.\n"
                "- For questions like 'what does this project do', read the files and describe "
                "exactly what it does — mention the language, framework, key files, and purpose.\n"
                "- Answer directly and concisely — no warm-up phrases.\n"
                "- Mention specific file names and function names from the code snippets.\n"
                "- Use Markdown formatting: bold for key terms, code blocks for code, bullet lists for steps.\n"
                "- If you can identify the project purpose from filenames and code, state it plainly.\n"
                "- If the code is sparse, infer confidently from what IS there.\n"
                "- Never return a blank answer. Never say 'I cannot determine' — always give your best reading.\n"
                "- Never say 'Based on the provided context' — just answer."
            )

            human_msg = (
                f"Repository: {repo_name}\n\n"
                f"{context_section}\n\n"
                f"Question: {query}"
            )

            lc_messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=human_msg),
            ]

            response = await self.llm.ainvoke(lc_messages)
            answer_text = self._stringify_content(response.content) if hasattr(response, "content") else str(response)
            logger.info(f"_direct_llm_answer: LLM returned {len(answer_text.strip())} chars via provider [{getattr(self, '_active_provider', 'unknown')}]")

            # If the LLM returned blank or near-blank, try the fallback provider
            if not answer_text or len(answer_text.strip()) < 20:
                if self.fallback_llm:
                    logger.warning("Primary LLM returned blank answer — retrying on fallback provider.")
                    original_llm = self.llm
                    self.llm = self.fallback_llm
                    result = await self._direct_llm_answer(query)
                    self.llm = original_llm
                    return result
                return self._fallback_answer(query, "LLM returned an empty response.")

            return {
                "answer": answer_text,
                "flow": [],
                "citations": citations,
                "confidence": "high" if chunks else "medium",
            }
        except Exception as e:
            return self._fallback_answer(query, f"Direct LLM answer failed: {str(e)}")

    def _normalize_google_model(self, model_name: str) -> str:
        """
        Normalize model names to valid Gemini identifiers.
        """
        model_name = (model_name or "").lower()
        
        # Only map the placeholder "Gemini 3 Flash" to a known target.
        # Otherwise, respect the user's .env configuration.
        aliases = {
            "gemini-3-flash": "gemini-2.5-flash",
            "gemini-3": "gemini-2.5-pro",
            "gemini-3.1": "gemini-2.5-pro",
            "gemini-flash-latest": "gemini-2.5-flash",
            "gemini-1.5-flash": "gemini-2.5-flash", 
        }
        
        return aliases.get(model_name, model_name)

    def _extract_message_text(self, response: Dict[str, Any]) -> str:
        messages = response.get("messages")
        if not messages:
            return ""

        # LangGraph often returns a list of message objects; prefer the latest AI output.
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            msg_type = getattr(msg, "type", "")
            if content and msg_type in {"ai", "assistant"}:
                return self._stringify_content(content)

            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content")
                if content and role in {"assistant", "ai"}:
                    return self._stringify_content(content)

        # Fallback: first content-like field
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content:
                return self._stringify_content(content)
            if isinstance(msg, dict) and msg.get("content"):
                return self._stringify_content(msg["content"])

        return ""

    def _stringify_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content["text"]
            return str(content)

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                else:
                    text = getattr(item, "text", None)
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "\n".join(parts)
            return str(content)

        return str(content)

    def _fallback_answer(self, query: str, reason: str = "") -> Dict[str, Any]:
        """
        Retrieval-only fallback so chat stays functional without external LLM access.
        """
        relevant_chunks = self.retriever.retrieve(query)
        if not relevant_chunks:
            return {
                "answer": f"I couldn't find relevant code for your query. {reason}".strip(),
                "flow": [],
                "citations": [],
                "confidence": "low"
            }

        best_chunk = relevant_chunks[0]
        flow = [{
            "node": best_chunk["symbol_name"],
            "file_path": best_chunk["file_path"],
            "line_start": best_chunk["start_line"],
            "line_end": best_chunk["end_line"]
        }]

        symbol_id = f"{best_chunk['file_path']}::{best_chunk['symbol_name']}"
        neighbors = self.graph.get_neighbors(symbol_id)
        for edge in neighbors.get("outgoing", [])[:3]:
            node_id = edge["id"]
            parts = node_id.split("::", 1)
            flow.append({
                "node": parts[1] if len(parts) > 1 else node_id,
                "file_path": parts[0] if len(parts) > 1 else best_chunk["file_path"],
                "line_start": 0,
                "line_end": 0
            })

        reason_note = f"**Note:** {reason}\n\n" if reason else ""
        return {
            "answer": (
                f"{reason_note}"
                f"Here's the most relevant code I found — `{best_chunk['file_path']}` "
                f"(lines {best_chunk['start_line']}–{best_chunk['end_line']}):\n\n"
                f"{best_chunk['content'][:800]}"
            ),
            "flow": flow,
            "citations": [{
                "file_path": c["file_path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"]
            } for c in relevant_chunks[:5]],
            "confidence": "medium"
        }
