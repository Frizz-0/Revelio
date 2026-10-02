# Revelio

Revelio is a local investigation prototype. It searches the web or reads uploaded documents, extracts source passages, checks what those passages support, and presents an answer with evidence and caveats.

## Run locally

1. Set GROQ_API_KEY and SEARXNG_URL in .env.
2. Start SearXNG with docker compose up -d.
3. From the repository root, start the API:

       python -m uvicorn app.api.server:app --reload --port 8000

4. In another terminal, start the UI:

       cd frontend
       npm run dev

5. Open http://localhost:5173.

For command-line use, from the repository root:

    python -m app.main "Is NVIDIA's dominance in AI GPUs sustainable?"
    python -m app.main "Calculate 3847 * 29"

## What V2 includes

- A bounded investigation agent with a single run state and visible action/tool events.
- Web search through SearXNG, source-page reading, exact-quote extraction, and evidence review.
- Uploads of up to 3 PDF, DOCX, TXT, Markdown, or HTML documents per investigation. Each file is limited to 10 MB and the combined upload to 25 MB. Files are parsed in memory and are not saved by Revelio. Revelio reviews up to the first 24,000 extracted characters per file and shows a caveat when a file is longer.
- A deterministic Python calculator for arithmetic.
- A local React UI and FastAPI event stream for investigating and inspecting evidence.

## How Revelio differs from a general chat app

A general chat app is designed for broad conversation and may answer from model knowledge. Revelio is narrower: it treats a question as an investigation, shows which sources it read, preserves exact quotations, checks claims against those quotations, and exposes uncertainty. Arithmetic is evaluated in Python rather than entrusted to the language model.

When considering a feature or version, first ask whether it improves investigation quality, evidence traceability, or user visibility. If it only adds general chat behavior, it likely does not belong in Revelio.

## Limits

Evidence review checks the collected passages; it does not prove a publisher is trustworthy or that a source is true. Websites can block fetching. Scanned PDFs need OCR, which is not included. Investigation data is held in memory for the run; there is no history database, vision, agent swarm, or production deployment layer.

See app/README.md for the active code map and investigation flow.
