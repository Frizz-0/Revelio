# Active code map

## Runtime flow

- main.py starts a run and routes plain arithmetic directly to Python.
- agent/agent.py owns the action loop, run state, and response guardrails.
- agent/capabilities.py registers search, research, and calculator.
- services/search_service.py calls SearXNG.
- services/document_service.py fetches web pages and linked PDFs.
- services/document_parser.py parses fetched pages and uploaded PDF, DOCX, TXT, Markdown, and HTML files.
- investigator/evidence_extractor.py extracts exact source passages; investigator/verifier.py evaluates them.
- services/llm.py calls Groq and maintains the local response cache.
- api/server.py provides JSON and multipart investigation routes plus streamed events.
- frontend/src contains the local React investigation UI.

Uploaded files are parsed in memory, passed into the existing agent state, then reviewed by the same research/extraction/verification flow used for web sources. They are not stored as files by Revelio. To control model cost, only the first 24,000 extracted characters per file are reviewed; Revelio adds a caveat when a file is longer.

## Intentionally removed

The old planner/query-generator/investigator orchestration, standalone analyzer and verifier wrappers, unused result model, and no-op model router were not referenced by the active runtime. Their responsibilities either remain in the single active agent flow or were never connected. The active quote extractor and evidence verifier remain.

Generated LLM response cache and Python bytecode are runtime artifacts, not source modules; they are left in place. They can be cleared when the app is stopped if you want a cold cache.

## Design rule for future work

For every feature or version, compare Revelio with a general chat app: does the feature improve investigations, traceable evidence, or visibility into the process? Revelio should remain investigation-first. Prefer a small change to the current path over a new subsystem unless the feature needs it.
