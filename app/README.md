# Active code map

## Runtime flow

- main.py starts a run and routes plain arithmetic directly to Python.
- agent/agent.py owns the action loop, run state, and response guardrails.
- agent/capabilities.py registers search, research, calculator, and image analysis when images are attached.
- services/search_service.py calls SearXNG.
- services/document_service.py fetches web pages and linked PDFs.
- services/document_parser.py parses fetched pages and uploaded PDF, DOCX, TXT, Markdown, and HTML files.
- investigator/evidence_extractor.py extracts exact source passages; investigator/verifier.py evaluates them.
- services/llm.py calls Groq and maintains the local response cache.
- Model calls stream provider token counts and latency to the UI; local cache hits are marked separately and do not claim token usage.
- api/server.py provides JSON and multipart investigation routes plus streamed events.
- frontend/src contains the local React investigation UI.

Uploaded documents are parsed in memory, passed into the existing agent state, then reviewed by the same research/extraction/verification flow used for web sources. They are not stored by Revelio. To control model cost, only the first 24,000 extracted characters per file are reviewed; Revelio adds a caveat when a file is longer.

Uploaded PNG, JPEG, and WebP images are passed in memory to Groq's `qwen/qwen3.8-27b` vision model before the agent chooses follow-up steps. The model returns visible text, visual findings, uncertainties, and a suggested route. These are AI visual observations, not verified quotations. The model has a Groq free-plan quota (currently listed as 30 requests/minute and 1,000/day); actual quotas can vary by account. Image bytes are sent to Groq for analysis and are not written to the local LLM cache. The prototype uses the VLM itself for visual Q&A, OCR-like reading, and charts; it does not add a separate CNN, ViT, or local OCR stack.

## Intentionally removed

The old planner/query-generator/investigator orchestration, standalone analyzer and verifier wrappers, unused result model, and no-op model router were not referenced by the active runtime. Their responsibilities either remain in the single active agent flow or were never connected. The active quote extractor and evidence verifier remain.

Generated LLM response cache and Python bytecode are runtime artifacts, not source modules; they are left in place. They can be cleared when the app is stopped if you want a cold cache.

## Design rule for future work

For every feature or version, compare Revelio with a general chat app: does the feature improve investigations, traceable evidence, or visibility into the process? Revelio should remain investigation-first. Image analysis adds visible, uncertainty-labeled visual observations and lets the agent choose whether web research is needed; a general chat app may describe the image without that auditable route. Prefer a small change to the current path over a new subsystem unless the feature needs it.
