# Revelio V1

Revelio is an investigation system. Its agent controls a bounded loop: choose
an action, execute a capability, inspect the observation, then choose again.

## V1 path

- **Search** retrieves source titles, URLs, and snippets from SearXNG.
- **Research** analyzes the collected evidence and checks extracted claims
  against that evidence.
- **Calculator** evaluates arithmetic in Python. Standalone arithmetic goals
  are routed directly to it without an LLM call. In mixed tasks, the agent is
  required to observe a calculator result before it can answer a calculation.
- **Synthesis** returns the agent's response to the user.

The agent loop and investigation capabilities are separate seams: later work
can replace or extend the investigation workflow without embedding search or
verification logic in the loop. The older `investigator/` pipeline remains
separate and is not called by the V1 command-line entry point.

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

## V1 boundaries

One agent, one investigation state (actions and observations), and three
capabilities. No agent swarm, vector database, voice, vision, or production
API layer. Keep the existing investigator pipeline isolated until a specific
V1 behavior needs to reuse it.
