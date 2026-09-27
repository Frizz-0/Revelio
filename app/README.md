# Revelio V2 prototype

Revelio is an investigation system. Its agent controls a bounded loop: choose
an action, execute a capability, inspect the observation, then choose again.

## V1 path

- **Search** retrieves source titles, URLs, and snippets from SearXNG.
- **Research** fetches and parses up to two search-result pages, extracts
  exact quoted evidence with URLs, and evaluates findings as supported,
  contradicted, or insufficient using those passages.
- **Calculator** evaluates arithmetic in Python. Standalone arithmetic goals
  are routed directly to it without an LLM call. In mixed tasks, the agent is
  required to observe a calculator result before it can answer a calculation.
- **Synthesis** returns the agent's response to the user.

The agent loop and investigation capabilities remain separate seams. V2 reuses
the investigator's source extractor and evidence verifier inside the agent's
research capability; the old `investigator.investigate()` planner/query loop
is not used as a second orchestrator.

The active agent code is kept in two modules: `agent.py` contains the loop,
state, action model, decision prompt, and guardrails; `capabilities.py` contains
the capability registry and the default search/research/calculator wiring.

## Run

From the repository root, set `GROQ_API_KEY` and `SEARXNG_URL` in `.env`, then:

```powershell
python -m app.main "Calculate 3847 * 29"
python -m app.main --debug "Search for NVIDIA AI GPU market share in 2024"
```

With no goal argument, Revelio prompts for one. Pure arithmetic uses the local
calculator directly. Research needs Groq and a reachable SearXNG instance.
Each run prints the selected action and tool success/error. Pass `--debug` to
also print the complete state with action history and observations.

Search results and research findings are held in the run's in-memory
observations. PDF support covers text-based PDFs; scanned PDFs need OCR.
Verification checks what collected passages support and flags disagreement. It
does not independently establish publisher trustworthiness or prove a claim
true outside the supplied sources.

## Local UI

The Vite prototype in `frontend/` connects to the local FastAPI event stream.
Run the API and UI in separate terminals from the repository root:

```powershell
python -m uvicorn app.api.server:app --reload --port 8000
cd frontend
npm run dev
```

The UI sends an investigation to `POST /api/investigate` and displays streamed
agent/tool events plus the final state, verified finding, source links, and
quoted evidence. The API also exposes `GET /api/health`.

## V2 boundaries

One agent, one investigation state (actions and observations), and three
capabilities. No agent swarm, vector database, voice, vision, or production
API layer. The local API exists only to connect the prototype UI. There is no
standalone final-answer proofreader in the current investigator code; V2
grounds synthesis in verified findings and source URLs.
