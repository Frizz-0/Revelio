import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  Activity,
  ArrowUp,
  Check,
  ExternalLink,
  FileSearch,
  FileText,
  Image as ImageIcon,
  Menu,
  Paperclip,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { ActivityRow, FindingBadge, Readout, TelemetryLine } from "./InvestigationWidgets";
import type { ActivityItem } from "./InvestigationWidgets";

type EventData = { event: string;[key: string]: any };
type Finding = {
  conclusion?: string;
  status?: string;
  caveats?: string[];
};
type Source = { title?: string; url: string; snippet?: string; truncated?: boolean };
type Evidence = { claim?: string; supporting_text?: string; url?: string };
type AgentState = {
  goal: string;
  status: string;
  final_answer?: string | null;
  observations?: Array<{ tool: string; success: boolean; output?: any; error?: string }>;
};
type LiveSource = Source & { state: "opening" | "read" | "unavailable" };

const stages = ["Find sources", "Open sources", "Extract evidence", "Verify", "Answer"];
const examples = [
  "Is NVIDIA's dominance in AI GPUs sustainable?",
  "What are the main causes of bee population decline?",
  "Compare heat pumps and gas boilers for a UK home",
];

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [documents, setDocuments] = useState<File[]>([]);
  const [investigationImages, setInvestigationImages] = useState<Array<{ name: string; url: string }>>([]);
  const uploadRef = useRef<HTMLInputElement>(null);
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState("");
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [state, setState] = useState<AgentState | null>(null);
  const [phase, setPhase] = useState(-1);
  const [currentMessage, setCurrentMessage] = useState("Ask a question to start an investigation.");
  const [isThinking, setIsThinking] = useState(false);
  const [activeReason, setActiveReason] = useState("");
  const [resultCount, setResultCount] = useState(0);
  const [leadSources, setLeadSources] = useState<Source[]>([]);
  const [liveSources, setLiveSources] = useState<LiveSource[]>([]);
  const [liveEvidenceCount, setLiveEvidenceCount] = useState(0);
  const [usageTotals, setUsageTotals] = useState({ input: 0, output: 0, calls: 0, cacheHits: 0 });

  useEffect(() => () => investigationImages.forEach((image) => URL.revokeObjectURL(image.url)), [investigationImages]);

  function reset() {
    setGoal("");
    setDocuments([]);
    setInvestigationImages([]);
    setAnswer("");
    setState(null);
    setActivity([]);
    setPhase(-1);
    setCurrentMessage("Ask a question to start an investigation.");
    setIsThinking(false);
    setActiveReason("");
    setResultCount(0);
    setLeadSources([]);
    setLiveSources([]);
    setLiveEvidenceCount(0);
    setUsageTotals({ input: 0, output: 0, calls: 0, cacheHits: 0 });
    setStatus("Ready");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = prompt.trim();
    const attached = [...documents];
    if (!question || busy) return;
    setInvestigationImages(attached.filter((file) => file.type.startsWith("image/")).map((file) => ({ name: file.name, url: URL.createObjectURL(file) })));
    setGoal(question);
    setPrompt("");
    setDocuments([]);
    setAnswer("");
    setState(null);
    setActivity([]);
    setPhase(0);
    setCurrentMessage("Connecting to the investigation service…");
    setIsThinking(false);
    setActiveReason("");
    setResultCount(0);
    setLeadSources([]);
    setLiveSources([]);
    setLiveEvidenceCount(0);
    setUsageTotals({ input: 0, output: 0, calls: 0, cacheHits: 0 });
    setStatus("Starting");
    setBusy(true);

    try {
      const form = new FormData();
      form.append("goal", question);
      attached.forEach((file) => form.append("files", file));
      const response = await fetch(attached.length ? "/api/investigate-with-documents" : "/api/investigate", {
        method: "POST",
        headers: attached.length ? { Accept: "text/event-stream" } : { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: attached.length ? form : JSON.stringify({ goal: question }),
      });
      if (!response.ok || !response.body) {
        let detail = "";
        try { detail = (await response.json()).detail || ""; } catch { /* keep fallback */ }
        throw new Error(detail || `API returned ${response.status}. Is the FastAPI server running on port 8000?`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          const line = block.split("\n").find((part) => part.startsWith("data: "));
          if (line) consume(JSON.parse(line.slice(6)) as EventData);
        }
        if (done) break;
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus("Connection issue");
      setCurrentMessage(message);
      addActivity(message, "error");
    } finally {
      setBusy(false);
    }
  }

  function addActivity(label: string, itemState: ActivityItem["state"] = "done", detail?: string, resolveLabel?: string) {
    setActivity((items) => {
      let resolved = false;
      const updated = items.map((item) => {
        if (!resolved && item.state === "active" && item.label === resolveLabel) {
          resolved = true;
          return { ...item, state: itemState === "error" ? "error" as const : "done" as const };
        }
        return item;
      });
      return [
        { id: Date.now() + Math.random(), label, detail, state: itemState, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) },
        ...updated,
      ];
    });
  }

  function consume(item: EventData) {
    switch (item.event) {
      case "started":
        setStatus("Investigating");
        setCurrentMessage("Setting up the investigation…");
        addActivity("Investigation started", "active", item.goal);
        break;
      case "documents_loaded":
        setPhase(0);
        setCurrentMessage(`Reading ${item.documents?.length ?? 0} uploaded document${item.documents?.length === 1 ? "" : "s"}.`);
        {
          const loaded: Source[] = item.documents ?? [];
          const limited = loaded.filter((source) => source.truncated);
          const names = loaded.map((source) => source.title).join(", ");
          const detail = limited.length
            ? `${names}. Only the first 24,000 extracted characters will be reviewed for ${limited.map((source) => source.title).join(", ")}.`
            : names;
          setLiveSources((sources) => (item.documents ?? []).reduce(
            (current: LiveSource[], source: Source) => upsertSource(current, { ...source, state: "read" }),
            sources,
          ));
          addActivity("Documents added to investigation", "done", detail);
        }
        break;
      case "images_loaded":
        setCurrentMessage(`Ready to inspect ${item.images?.length ?? 0} uploaded image${item.images?.length === 1 ? "" : "s"}.`);
        addActivity("Images ready for visual analysis", "done", (item.images ?? []).map((image: any) => image.title).join(", "));
        break;
      case "decision_started":
        setIsThinking(true);
        setCurrentMessage("Reviewing the information collected so far and choosing the next step.");
        setActiveReason("");
        addActivity("Choosing the next action", "active", `Step ${item.step}`);
        break;
      case "action_selected":
        setIsThinking(false);
        setActiveReason(item.action?.reason || actionDescription(item.action?.tool ?? item.action?.action_type));
        addActivity(
          `Next action: ${capitalize(item.action?.tool ?? item.action?.action_type)}`,
          "done",
          item.action?.reason || actionDescription(item.action?.tool ?? item.action?.action_type),
          "Choosing the next action",
        );
        break;
      case "action_rejected":
        addActivity("Action needs correction", "error", item.error);
        break;
      case "tool_started":
        setIsThinking(false);
        if (item.tool === "search") {
          setPhase(0);
          setCurrentMessage("Searching the web for relevant sources.");
        } else if (item.tool === "research") {
          setPhase(1);
          setCurrentMessage("Opening readable sources and checking their contents.");
        } else if (item.tool === "calculator") {
          setPhase(0);
          setCurrentMessage("Calculating with the deterministic calculator.");
        } else if (item.tool === "analyze_image") {
          setPhase(1);
          setCurrentMessage("Inspecting the uploaded image and identifying visible details.");
        }
        addActivity(`${capitalize(item.tool)} started`, "active", summarizeArguments(item.arguments));
        break;
      case "tool_finished":
        setIsThinking(false);
        if (item.tool === "search" && item.success) setCurrentMessage(`${item.output?.length ?? 0} candidate results found. Now selecting pages to inspect.`);
        if (item.tool === "research" && item.success) setCurrentMessage("Source review is complete. Bringing the verified finding together.");
        if (item.tool === "analyze_image" && item.success) setCurrentMessage("Visual observations are ready. Deciding whether outside research is needed.");
        if (item.tool === "search" && Array.isArray(item.output)) {
          setResultCount(item.output.length);
          setLeadSources(item.output);
        }
        addActivity(`${capitalize(item.tool)} ${item.success ? "completed" : "failed"}`, item.success ? "done" : "error", item.error || toolSummary(item), `${capitalize(item.tool)} started`);
        break;
      case "search_finished":
        setResultCount(item.result_count ?? 0);
        addActivity("Search results collected", "done", `${item.result_count ?? 0} results for “${item.query}”`);
        break;
      case "vision_analysis_started":
        setCurrentMessage(`Vision model is inspecting ${item.title || "the uploaded image"}.`);
        addActivity("Analyzing image", "active", item.task || item.title);
        break;
      case "vision_analysis_finished":
        addActivity(item.success ? "Visual analysis ready" : "Image analysis failed", item.success ? "done" : "error", item.suggested_route ? `Suggested route: ${item.suggested_route}` : item.error, "Analyzing image");
        break;
      case "model_usage": {
        const stage = String(item.stage || "Model call").replace(/_/g, " ");
        if (item.cache_hit) {
          setUsageTotals((totals) => ({ ...totals, cacheHits: totals.cacheHits + 1 }));
          addActivity(`${capitalize(stage)} · cache hit`, "done", "Served from Revelio's local cache; no new provider tokens used.");
        } else {
          const input = Number(item.prompt_tokens) || 0;
          const output = Number(item.completion_tokens) || 0;
          setUsageTotals((totals) => ({ ...totals, input: totals.input + input, output: totals.output + output, calls: totals.calls + 1 }));
          const usageDetail = item.failed
            ? `Provider call failed after ${item.latency_seconds ?? "?"}s; token usage unavailable.`
            : `${input.toLocaleString()} input · ${output.toLocaleString()} output · ${item.latency_seconds ?? "?"}s · ${item.model || "model"}`;
          addActivity(`${capitalize(stage)} ${item.failed ? "failed" : "usage"}`, item.failed ? "error" : "done", usageDetail);
        }
        break;
      }
      case "research_source_started":
        setIsThinking(false);
        setPhase(1);
        setCurrentMessage(`Opening ${item.title || "a source"} to inspect its contents.`);
        setLiveSources((sources) => upsertSource(sources, { title: item.title, url: item.url, state: "opening" }));
        addActivity("Opening source", "active", item.title || item.url);
        break;
      case "research_source_finished":
        setLiveSources((sources) => upsertSource(sources, {
          title: item.title,
          url: item.url,
          state: item.success ? "read" : "unavailable",
        }));
        addActivity(item.success ? "Source readable" : "Source unavailable", item.success ? "done" : "error", item.title || item.error || item.url, "Opening source");
        break;
      case "evidence_extraction_started":
        setIsThinking(false);
        setPhase(2);
        setCurrentMessage(`Looking for direct quotations related to the question in ${item.title || "the source"}.`);
        addActivity("Extracting evidence", "active", item.title);
        break;
      case "evidence_extraction_finished":
        if (item.success) setLiveEvidenceCount((count) => count + (item.count ?? 0));
        addActivity(item.success ? "Evidence extraction finished" : "Could not extract evidence", item.success ? "done" : "error", item.success ? `${item.count ?? 0} candidate quotations` : item.error, "Extracting evidence");
        break;
      case "verification_started":
        setIsThinking(false);
        setPhase(3);
        setLiveEvidenceCount(item.evidence_count ?? 0);
        setCurrentMessage(`Checking ${item.evidence_count ?? 0} quoted claims across ${item.source_count ?? 0} readable sources.`);
        addActivity("Checking evidence", "active", `${item.evidence_count ?? 0} items · ${item.source_count ?? 0} sources`);
        break;
      case "verification_finished":
        setCurrentMessage(`Evidence review is ${item.status}. Checking how strongly the sources support an answer.`);
        addActivity(`Evidence review: ${item.status}`, item.status === "supported" ? "done" : item.status === "contradicted" ? "error" : "done", `${item.evidence_count ?? 0} evidence items · ${item.source_count ?? 0} independent sources`, "Checking evidence");
        break;
      case "synthesis_guarded":
        setIsThinking(false);
        setCurrentMessage("Evidence is limited or conflicting, so Revelio is preparing a cautious answer.");
        addActivity("Answer limited to verified evidence", "done", "The finding is insufficient; unsupported conclusions are withheld.");
        break;
      case "completed":
        setIsThinking(false);
        setActivity((items) => items.map((entry) => entry.state === "active" ? { ...entry, state: "done" } : entry));
        setStatus("Completed");
        setPhase(4);
        setCurrentMessage("Investigation complete.");
        if (item.state) setState(item.state);
        break;
      case "failed":
        setIsThinking(false);
        setActivity((items) => items.map((entry) => entry.state === "active" ? { ...entry, state: "error" } : entry));
        setStatus("Failed");
        setCurrentMessage(item.error || "The investigation stopped before completion.");
        addActivity("Investigation stopped", "error", item.error);
        if (item.state) setState(item.state);
        break;
      case "result":
        setState(item.state);
        setAnswer(item.state?.final_answer || "");
        break;
      case "finished":
        setStatus(item.status === "completed" ? "Completed" : "Failed");
        if (item.status === "completed") setPhase(4);
        break;
    }
  }

  const observations = state?.observations ?? [];
  const searchResults: Source[] = observations
    .filter((observation) => observation.tool === "search" && observation.success)
    .flatMap((observation) => Array.isArray(observation.output) ? observation.output : []);
  const uploadedDocuments: Source[] = observations
    .filter((observation) => observation.tool === "document" && observation.success)
    .flatMap((observation) => Array.isArray(observation.output) ? observation.output : []);
  const research = [...observations].reverse().find((observation) => observation.tool === "research" && observation.success)?.output;
  const sources: Source[] = research?.sources ?? [...uploadedDocuments, ...searchResults];
  const boardSources = [...new Map([...leadSources, ...liveSources, ...sources].map((source) => [source.url, source])).values()];
  const finding: Finding | undefined = research?.finding;
  const evidence: Evidence[] = research?.evidence ?? [];
  const visualAnalyses = observations.filter((observation) => observation.tool === "analyze_image" && observation.success).map((observation) => observation.output);
  const visibleAnswer = answerForDisplay(answer);
  const progress = !goal ? 0 : status === "Completed" ? 100 : Math.max(8, ((phase + 1) / stages.length) * 100);

  return (
    <div className="console-shell min-h-screen bg-[#08090c] text-zinc-100 selection:bg-cyan-300/30">
      {sidebarOpen && <button aria-label="Close navigation overlay" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-40 bg-black/70 lg:hidden" />}
      <aside className={`console-sidebar fixed inset-y-0 left-0 z-50 flex w-[252px] flex-col border-r border-white/[0.07] bg-[#0a0b0f] transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-3"><div className="grid size-8 place-items-center rounded-lg border border-indigo-300/25 bg-indigo-400/10 text-sm font-bold text-indigo-200">R</div><span className="text-xs font-semibold tracking-[0.2em]">REVELIO</span></div>
          <button aria-label="Close navigation" onClick={() => setSidebarOpen(false)} className="text-zinc-500 lg:hidden"><X size={17} /></button>
        </div>
        <div className="px-3"><button onClick={reset} className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]"><Plus size={15} />New investigation</button></div>
        <div className="mt-8 px-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-600">Current session</div>
        {goal && <div className="mx-3 mt-3 rounded-lg border border-indigo-300/10 bg-indigo-300/[0.06] px-3 py-3 text-xs leading-5 text-zinc-300">{goal}</div>}
        <div className="mt-auto border-t border-white/[0.07] p-4"><div className="flex items-center gap-2 text-[10px] text-zinc-600"><span className={`size-1.5 rounded-full ${busy ? "bg-emerald-400 animate-pulse" : "bg-zinc-700"}`} />Local research workspace</div></div>
      </aside>

      <main className="console-main lg:ml-[252px]">
        <header className="console-topbar sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.07] bg-[#08090c]/85 px-5 backdrop-blur-xl lg:px-8">
          <div className="flex min-w-0 items-center gap-3"><button aria-label="Open navigation" onClick={() => setSidebarOpen(true)} className="text-zinc-500 lg:hidden"><Menu size={18} /></button><span className="hidden shrink-0 font-mono text-[10px] tracking-[0.2em] text-cyan-300/60 sm:block">REVELIO / CONSOLE</span><span className="hidden text-cyan-900 sm:block">//</span><span className="truncate text-xs font-medium text-zinc-300">{goal || "Awaiting investigation input"}</span></div>
          <div className="flex shrink-0 items-center gap-3"><span className="hidden font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600 sm:block">Local runtime · event stream</span><div className="hud-status flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-[10px] text-zinc-400"><span className={`size-1.5 rounded-full ${busy ? "bg-cyan-300 animate-pulse" : status === "Failed" ? "bg-red-400" : status === "Completed" ? "bg-emerald-400" : "bg-zinc-600"}`} />{status}</div></div>
        </header>

        <div className="console-content mx-auto max-w-[1560px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <section className="mission-panel hud-panel relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0d0f15] px-5 py-6 sm:px-7 sm:py-7">
            <div className="hero-glow pointer-events-none absolute -right-20 -top-32 size-[360px] rounded-full bg-indigo-500/[0.13] blur-[90px]" />
            <div className="relative flex flex-col justify-between gap-7 md:flex-row md:items-center">
              <div className="max-w-3xl">
                <div className="hud-eyebrow flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300"><span className={`hud-live-dot ${busy ? "is-live" : ""}`} />{goal ? "Active investigation" : "Research console · ready"}<span className="mx-1 text-cyan-900">/</span><span className="text-zinc-500">{goal ? `Run ${String(state?.iteration ?? 0).padStart(2, "0")}` : "Input required"}</span></div>
                <h1 className="mt-3 max-w-4xl text-2xl font-semibold leading-tight tracking-tight text-white sm:text-3xl">{goal || "What should Revelio investigate?"}</h1>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">{goal ? currentMessage : "Search, inspect, extract, verify, and synthesize. Follow the investigation as it runs."}</p>
              </div>
              <div className={`relative mx-auto grid size-28 shrink-0 place-items-center md:mr-5 ${busy ? "" : "opacity-75"}`} aria-hidden="true">
                {busy && <><span className="absolute inset-0 rounded-full border border-indigo-300/20 animate-orbit" /><span className="absolute inset-3 rounded-full border border-cyan-300/15 animate-orbit-reverse" /></>}
                <div className={`grid size-[72px] place-items-center rounded-full border border-indigo-200/20 bg-gradient-to-br from-indigo-400/20 to-cyan-300/[0.06] text-indigo-200 shadow-[0_0_45px_rgba(129,140,248,0.12)] ${busy ? "animate-breathe" : ""}`}><Activity size={27} strokeWidth={1.4} /></div>
                {busy && <span className="absolute right-1 top-5 size-2 rounded-full bg-cyan-200 shadow-[0_0_14px_rgba(103,232,249,.9)] animate-pulse" />}
              </div>
            </div>
            <div className="relative mt-6">
              <div className="mb-3 flex items-center justify-between text-[10px]"><span className="font-medium uppercase tracking-[0.16em] text-zinc-400">Investigation sequence</span><span className="font-mono text-cyan-200/70">{status === "Completed" ? "ALL STAGES COMPLETE" : goal ? `${Math.min(phase + 1, stages.length)} / ${stages.length} ACTIVE` : "STANDBY"}</span></div>
              <div className="h-[2px] overflow-hidden rounded-full bg-white/[0.07]"><div className={`h-full rounded-full bg-gradient-to-r from-cyan-500 to-sky-200 transition-all duration-700 ${busy ? "progress-shimmer" : ""}`} style={{ width: `${progress}%` }} /></div>
              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5 sm:gap-3">{stages.map((stage, index) => {
                const complete = status === "Completed" || index < phase;
                const active = busy && index === phase;
                return <div key={stage} className={`phase-node ${complete ? "phase-complete" : active ? "phase-active" : ""}`}><span className="phase-node-index">{complete ? <Check size={11} /> : active ? <span className="size-1.5 rounded-full bg-cyan-200 animate-pulse" /> : String(index + 1).padStart(2, "0")}</span><span className="min-w-0"><span className="phase-node-name">{stage}</span><span className="phase-node-state">{complete ? "Complete" : active ? "In progress" : "Queued"}</span></span></div>;
              })}</div>
            </div>
          </section>

          <section className={`live-now hud-panel relative mt-4 overflow-hidden rounded-2xl border ${busy ? "border-cyan-300/25" : "border-white/[0.08]"} bg-[#0d0f16]`}>
            <div className="live-now-wash pointer-events-none absolute inset-0" />
            <div className="relative flex flex-col gap-5 px-5 py-5 sm:flex-row sm:items-center sm:gap-7 sm:px-7 sm:py-6">
              <div className={`revelio-core relative mx-auto grid size-36 shrink-0 place-items-center sm:mx-0 ${busy ? isThinking ? "core-thinking" : "core-active" : status === "Completed" ? "core-complete" : "core-idle"}`} aria-hidden="true">
                <span className="core-grid" />
                <span className="core-ring core-ring-outer" /><span className="core-ring core-ring-mid" /><span className="core-ring core-ring-inner" />
                <span className="core-ticks" />
                <span className="core-lens"><span className="core-iris" /><span className="core-pupil" /><span className="core-glint" /></span>
                <span className="core-scanline" />
                <span className="core-label core-label-top">R / V · 03</span>
                <span className="core-label core-label-bottom">{busy ? isThinking ? "REASONING" : "PROCESSING" : status === "Completed" ? "COMPLETE" : "STANDBY"}</span>
                <span className="core-signal core-signal-left" /><span className="core-signal core-signal-right" />
              </div>
              <div className="min-w-0 flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] sm:justify-start"><span className={`relative flex size-2 ${busy ? "" : "hidden"}`}><span className="absolute inline-flex size-full rounded-full bg-cyan-300 opacity-60 animate-ping" /><span className="relative inline-flex size-2 rounded-full bg-cyan-200" /></span><span className={busy ? "text-cyan-200" : "text-zinc-500"}>01 · CURRENT STEP</span><span className={`live-step-status ${busy ? "is-running" : ""}`}>{busy ? "LIVE" : status.toUpperCase()}</span></div>
                <h2 className="mt-2 text-lg font-medium tracking-tight text-white sm:text-xl">{busy ? isThinking ? "Thinking through the next step" : stageLabel(phase) : status === "Completed" ? "Here’s what the investigation found" : goal ? "Investigation status" : "Standing by for your question"}</h2>
                <p className="mx-auto mt-2 max-w-2xl text-xs leading-5 text-zinc-400 sm:mx-0 sm:text-sm">{currentMessage}</p>
                {activeReason && busy && <div className="mx-auto mt-3 max-w-2xl rounded-lg border border-white/[0.06] bg-black/20 px-3 py-2 text-left sm:mx-0"><div className="text-[9px] font-semibold uppercase tracking-[0.16em] text-indigo-200/70">Why this step</div><p className="mt-1 text-[11px] leading-4 text-zinc-400">{activeReason}</p></div>}
              </div>
              <div className="hidden w-32 shrink-0 sm:block"><div className="flex h-10 items-end justify-center gap-1.5">{[15, 24, 12, 31, 19, 27, 13, 22].map((height, index) => <span key={index} className={`signal-bar ${busy ? "signal-bar-active" : ""}`} style={{ height: busy ? `${height}px` : "4px", animationDelay: `${index * 90}ms` }} />)}</div><div className="mt-2 text-center text-[9px] uppercase tracking-[0.15em] text-zinc-600">{busy ? `Step ${Math.max(1, phase + 1)} / ${stages.length}` : status === "Completed" ? "Complete" : "Idle"}</div></div>
            </div>
            {busy && <div className="live-progress-track"><span /></div>}
          </section>

          <section className="readout-grid mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4" aria-label="Investigation telemetry">
            <Readout icon={<Search size={14} />} label="Search results" value={resultCount} detail={busy ? "Candidates returned" : goal ? "Search complete" : "Waiting for query"} tone="cyan" />
            <Readout icon={<FileSearch size={14} />} label="Sources opened" value={liveSources.length || sources.length} detail={`${liveSources.filter((source) => source.state === "read").length || sources.length} readable`} tone="blue" />
            <Readout icon={<ShieldCheck size={14} />} label="Evidence items" value={liveEvidenceCount || evidence.length} detail={finding?.status ? `Review: ${finding.status}` : "Quoted passages"} tone="amber" />
            <Readout icon={<Sparkles size={14} />} label="Model activity" value={`${(usageTotals.input + usageTotals.output).toLocaleString()} tokens`} detail={`${usageTotals.calls} calls · ${usageTotals.cacheHits} cache hits`} tone="violet" />
          </section>

          {!goal && <section className="suggested-grid mt-4 grid gap-2 sm:grid-cols-3">{examples.map((example, index) => <button key={example} onClick={() => setPrompt(example)} className="suggested-query hud-panel p-4 text-left text-xs leading-5 text-zinc-400 transition"><span className="mb-3 flex items-center justify-between text-[9px] font-mono uppercase tracking-[0.16em] text-cyan-300/60"><span>Suggested scan</span><span>0{index + 1}</span></span><span className="block text-zinc-300">{example}</span></button>)}</section>}

          <div className="console-dashboard mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_370px]">
            <div className="space-y-4">
              <section className="hud-panel answer-panel overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
                <div className="hud-panel-heading flex items-center justify-between border-b border-white/[0.07] px-5 py-4"><div><div className="flex items-center gap-2 text-xs font-semibold text-zinc-200"><Activity size={14} className="text-cyan-300" />05 · Final answer</div><div className="mt-1 pl-5 text-[10px] text-zinc-600">{busy ? "Composing from collected observations" : `Run state · ${status}`}</div></div>{finding?.status && <FindingBadge status={finding.status} />}</div>
                <div className="min-h-28 whitespace-pre-wrap px-5 py-5 text-sm leading-7 text-zinc-300">{visibleAnswer || (busy ? <span className="flex items-center gap-2 text-zinc-500"><span className="flex gap-1"><i className="thinking-dot" /><i className="thinking-dot delay-1" /><i className="thinking-dot delay-2" /></span>{currentMessage}</span> : <span className="text-zinc-600">Your answer will appear here.</span>)}</div>
                {finding?.caveats?.length ? <div className="border-t border-white/[0.07] bg-amber-300/[0.025] px-5 py-4"><div className="text-[10px] font-medium uppercase tracking-wider text-amber-200/70">Limits to keep in mind</div><ul className="mt-2 space-y-1.5">{finding.caveats.map((caveat, index) => <li key={index} className="flex gap-2 text-xs leading-5 text-zinc-500"><span className="text-amber-200/60">•</span>{caveat}</li>)}</ul></div> : null}
              </section>

              {visualAnalyses.length > 0 && <section className="hud-panel overflow-hidden rounded-xl border border-indigo-300/15 bg-[#0c0e12]">
                <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-4"><div><div className="flex items-center gap-2 text-xs font-semibold text-zinc-200"><ImageIcon size={14} className="text-indigo-200" />Visual analysis</div><div className="mt-1 text-[10px] text-zinc-600">AI observations from the uploaded image · not independently verified</div></div><span className="rounded-full border border-indigo-200/15 px-2.5 py-1 text-[10px] text-indigo-200">{visualAnalyses.length} image{visualAnalyses.length === 1 ? "" : "s"}</span></div>
                <div className="space-y-4 px-5 py-4">{visualAnalyses.map((analysis: any, index: number) => <div key={`${analysis.image_index}-${index}`} className="space-y-3"><div className="text-xs font-medium text-zinc-300">{analysis.title}</div>{analysis.summary && <p className="text-xs leading-5 text-zinc-400">{analysis.summary}</p>}{analysis.visible_text?.length > 0 && <div><div className="text-[10px] uppercase tracking-wider text-zinc-600">Visible text</div><ul className="mt-1 space-y-1">{analysis.visible_text.map((text: string, i: number) => <li key={i} className="text-xs text-zinc-400">{text}</li>)}</ul></div>}{analysis.visual_findings?.length > 0 && <div><div className="text-[10px] uppercase tracking-wider text-zinc-600">Findings</div><ul className="mt-1 space-y-1">{analysis.visual_findings.map((text: string, i: number) => <li key={i} className="text-xs text-zinc-400">{text}</li>)}</ul></div>}{analysis.uncertainties?.length > 0 && <div className="text-[11px] leading-5 text-amber-200/70">Uncertain: {analysis.uncertainties.join(" · ")}</div>}</div>)}</div>
              </section>}

              <section className="hud-panel source-panel overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
                <div className="hud-panel-heading board-heading"><div><div className="flex items-center gap-2 text-xs font-semibold"><FileSearch size={14} />02 · Evidence board <span className="board-stamp">FIELD NOTES</span></div><div className="board-subtitle">Start with the question, follow source leads, then check the evidence.</div></div><span className="board-count">{boardSources.length} LEADS</span></div>
                <div className="board-question"><span className="board-pin" /><span className="board-question-label">THE QUESTION</span><strong>{goal || "A new investigation begins here"}</strong><small>{busy ? currentMessage : status === "Completed" ? `Finding: ${finding?.status || "review complete"}` : "Search results are leads; evidence must still be checked."}</small></div>
                {investigationImages.length > 0 && <div className="board-photos" aria-label="Uploaded photographs used in this investigation">{investigationImages.map((image, index) => {
                  const analysis = visualAnalyses.find((item: any) => item.image_index === index);
                  return <figure className={`board-photo board-photo-${index % 3}`} key={`${image.name}-${index}`}><span className="photo-pin" /><img src={image.url} alt={`Uploaded evidence: ${image.name}`} /><figcaption><strong>{image.name}</strong><span>{analysis ? "VISION INSPECTED" : busy ? "QUEUED FOR INSPECTION" : "UPLOADED EVIDENCE"}</span>{analysis?.summary && <small>{analysis.summary}</small>}</figcaption></figure>;
                })}</div>}
                {boardSources.length ? <div className="divide-y board-leads">{boardSources.map((source, index) => {
                  const live = liveSources.find((item) => item.url === source.url);
                  const researched = sources.some((item) => item.url === source.url);
                  const uploaded = source.url.startsWith("upload://");
                  return <a key={`${source.url}-${index}`} href={uploaded ? undefined : source.url} target={uploaded ? undefined : "_blank"} rel={uploaded ? undefined : "noreferrer"} className={`group flex items-start justify-between gap-4 px-5 py-3.5 board-lead board-lead-${index % 5}`}><span className="flex min-w-0 gap-3"><span className="board-lead-number">{String(index + 1).padStart(2, "0")}</span><span className="min-w-0"><span className="block board-lead-title">{source.title || source.url}</span><span className="mt-1 block truncate board-lead-domain">{domainOf(source.url)}</span>{source.snippet && <span className="board-lead-snippet">{source.snippet}</span>}</span></span><span className="board-lead-state">{uploaded ? "FILE" : live?.state === "unavailable" ? "UNREADABLE" : live?.state === "opening" ? "OPENING" : researched ? "CHECKED" : "LEAD"}{!uploaded && <ExternalLink size={12} />}</span></a>;
                })}</div> : <div className="empty-board"><span className="empty-stamp"><Search size={17} /></span><strong>{busy ? "Listening for the first leads" : "The board is ready"}</strong><span>{busy ? currentMessage : "Start an investigation and source cards will land here as they are found."}</span></div>}
                {evidence.length > 0 && <section className="quoted-evidence"><div className="quoted-evidence-heading"><ShieldCheck size={16} /><span><strong>Quoted evidence</strong><small>Passages extracted for checking · {evidence.length} items</small></span></div><div className="quoted-evidence-list">{evidence.map((item, index) => <blockquote className="quote-card" key={index}><span className="quote-index">E{String(index + 1).padStart(2, "0")}</span><p>“{item.supporting_text}”</p>{item.claim && <div className="quote-claim"><strong>Claim being checked</strong><span>{item.claim}</span></div>}<a href={item.url?.startsWith("upload://") ? undefined : item.url} target={item.url?.startsWith("upload://") ? undefined : "_blank"} rel={item.url?.startsWith("upload://") ? undefined : "noreferrer"}>{item.url?.startsWith("upload://") ? `Uploaded file: ${item.url.slice(9)}` : item.url || "Source unavailable"}{item.url && !item.url.startsWith("upload://") && <ExternalLink size={12} />}</a></blockquote>)}</div></section>}
              </section>
            </div>

            <aside className="telemetry-rail h-fit overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
              <section className="journal-panel agent-journal">
                <div className="journal-heading"><span className="journal-icon"><Activity size={15} /></span><div><span>03 · AGENT REASONING</span><h2>Why it chose each step</h2></div><span className={`journal-live ${busy ? "on" : ""}`}>{busy ? "LIVE" : "LOG"}</span></div>
                <p className="journal-intro">The agent’s stated reasons for its actions, recorded as the investigation unfolds.</p>
                <div className="journal-entries">{activity.filter((item) => item.label.startsWith("Next action:") || item.label === "Choosing the next action" || item.state === "error").slice(0, 4).map((item) => <ActivityRow key={item.id} item={item} expanded />)}{!activity.length && <p className="journal-empty">The investigator’s next-step notes will appear here.</p>}</div>
              </section>
              <section className="journal-panel insight-journal">
                <div className="journal-heading"><span className="journal-icon"><Sparkles size={15} /></span><div><span>04 · WORKING SUMMARY</span><h2>Key insights so far</h2></div></div>
                {finding?.conclusion ? <div className="insight-slip"><span className="slip-pin" /><p>{finding.conclusion}</p><small>Evidence review · {finding.status || "pending"}</small></div> : <div className="insight-slip muted"><span className="slip-pin" /><p>{evidence.length ? `${evidence.length} quoted passages are being checked.` : busy ? currentMessage : "Verified insights will appear here as evidence is reviewed."}</p><small>{evidence.length} evidence slips · {liveSources.filter((source) => source.state === "read").length} sources read</small></div>}
                {evidence.slice(0, 3).map((item, index) => <div className="pencil-insight" key={index}><span>✎</span><p>{item.claim || item.supporting_text}</p></div>)}
              </section>
              <section className="hud-panel activity-panel overflow-hidden">
                <div className="hud-panel-heading flex items-center justify-between px-4 py-4"><span><span className="flex items-center gap-2 text-xs font-semibold text-zinc-200"><Activity size={14} className="text-cyan-300" />Live event stream</span><span className="mt-1 block pl-5 font-mono text-[9px] uppercase tracking-[0.14em] text-zinc-600">{activity.length} recorded events</span></span><span className={`flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider ${busy ? "text-cyan-200" : "text-zinc-500"}`}><span className={`size-1.5 rounded-full ${busy ? "bg-cyan-300 animate-pulse" : "bg-zinc-600"}`} />{busy ? "Live" : "Idle"}</span></div>
                <div className="max-h-[540px] divide-y divide-white/[0.045] overflow-auto border-t border-white/[0.06]">{activity.length ? activity.map((item) => <ActivityRow key={item.id} item={item} />) : <div className="px-5 py-7 text-center text-xs text-zinc-600">Live tool calls and evidence steps appear here.</div>}</div>
              </section>
              <section className="system-readout border-t border-cyan-300/10 px-4 py-4">
                <div className="mb-3 flex items-center justify-between"><span className="font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-500">Run telemetry</span><span className="text-[9px] text-zinc-700">observed values</span></div>
                <div className="space-y-2 font-mono text-[10px]"><TelemetryLine label="PHASE" value={busy ? `${Math.max(1, phase + 1)} / ${stages.length} · ${stageLabel(phase)}` : status.toUpperCase()} /><TelemetryLine label="MODEL CALLS" value={`${usageTotals.calls} live · ${usageTotals.cacheHits} cached`} /><TelemetryLine label="TOKENS IN / OUT" value={`${usageTotals.input.toLocaleString()} / ${usageTotals.output.toLocaleString()}`} /><TelemetryLine label="SOURCES / QUOTES" value={`${sources.length || searchResults.length} / ${liveEvidenceCount || evidence.length}`} /></div>
              </section>
            </aside>
          </div>

          <form onSubmit={submit} className={`console-input mx-px max-w-[1100px] ${goal ? "mt-4" : "mt-5"}`}>
            {documents.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{documents.map((file, index) => <span key={`${file.name}-${file.size}-${index}`} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-[#0c0e12] px-3 py-2 text-[10px] text-zinc-300">{file.type.startsWith("image/") ? <ImageIcon size={12} className="text-cyan-200" /> : <FileText size={12} className="text-indigo-200" />}<span className="max-w-56 truncate">{file.name}</span><button type="button" aria-label={`Remove ${file.name}`} onClick={() => setDocuments((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-zinc-500 hover:text-white"><X size={12} /></button></span>)}</div>}
            <div className="input-frame hud-panel flex items-end gap-2 rounded-xl border border-white/10 bg-[#0c0e12] p-2 shadow-2xl shadow-black/20 transition focus-within:border-cyan-300/40">
              <input ref={uploadRef} className="hidden" type="file" multiple accept=".pdf,.docx,.txt,.md,.html,.htm,.png,.jpg,.jpeg,.webp" onChange={(event) => { const selected = Array.from(event.target.files ?? []); setDocuments((current) => [...current, ...selected].slice(0, 3)); event.currentTarget.value = ""; }} />
              <button type="button" aria-label="Attach documents or images" title="Attach a PDF, DOCX, TXT, Markdown, HTML, PNG, JPEG, or WebP file" disabled={busy || documents.length >= 3} onClick={() => uploadRef.current?.click()} className="grid size-9 shrink-0 place-items-center rounded-lg text-zinc-500 transition hover:bg-white/[0.06] hover:text-indigo-200 disabled:opacity-40"><Paperclip size={16} /></button>
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask Revelio to investigate something…" rows={1} className="min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-xs text-zinc-200 outline-none placeholder:text-zinc-600" />
              <button type="submit" disabled={!prompt.trim() || busy} className="grid size-9 place-items-center rounded-lg bg-indigo-100 text-zinc-900 transition hover:bg-white disabled:bg-white/[0.06] disabled:text-zinc-700"><ArrowUp size={16} /></button>
            </div>
            <div className="mt-2 flex items-center justify-between px-1 font-mono text-[8px] uppercase tracking-[0.12em] text-zinc-700"><span>Command input · natural language</span><span>Attach up to 3 documents or images</span></div>
          </form>
        </div>
      </main>
    </div>
  );
}

function stageLabel(phase: number) {
  return ["Searching the web", "Opening sources", "Extracting evidence", "Verifying claims", "Preparing answer"][phase] ?? "Working";
}

function summarizeArguments(args: Record<string, unknown> | undefined) {
  if (args?.query) return String(args.query);
  if (args?.expression) return String(args.expression);
  return undefined;
}

function toolSummary(item: EventData) {
  if (item.tool === "search" && Array.isArray(item.output)) return `${item.output.length} candidate sources found`;
  if (item.tool === "research" && item.output?.finding) return `Finding status: ${item.output.finding.status}`;
  return undefined;
}

function actionDescription(action: string | undefined) {
  switch (action) {
    case "search": return "Looking for candidate sources relevant to the question.";
    case "research": return "Opening source pages, extracting quotations, and checking evidence.";
    case "calculator": return "Evaluating the requested arithmetic deterministically.";
    case "analyze_image": return "Inspecting the uploaded image with the vision model.";
    case "respond": return "Preparing a concise answer from the available findings.";
    default: return "Selecting the next step in the investigation.";
  }
}

function upsertSource(sources: LiveSource[], next: LiveSource): LiveSource[] {
  const existing = sources.findIndex((source) => source.url === next.url);
  if (existing < 0) return [...sources, next];
  return sources.map((source, index) => index === existing ? { ...source, ...next } : source);
}

function capitalize(value: string | undefined) {
  if (!value) return "Tool";
  return value[0].toUpperCase() + value.slice(1);
}

function domainOf(url: string) {
  if (url.startsWith("upload://")) return "Uploaded for this investigation";
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

function answerForDisplay(text: string) {
  return text
    .replace(/\n\nCaveats:\s*[\s\S]*?(?=\n\nSources fetched for review:|$)/i, "")
    .replace(/\n\nSources fetched for review:\s*[\s\S]*$/i, "")
    .trim();
}

export default App;
