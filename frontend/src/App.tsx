import { useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  Activity,
  ArrowUp,
  Check,
  Circle,
  ExternalLink,
  FileSearch,
  FileText,
  Menu,
  Paperclip,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type EventData = { event: string; [key: string]: any };
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
type ActivityItem = {
  id: number;
  label: string;
  detail?: string;
  state: "active" | "done" | "error";
  time: string;
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
  const [liveSources, setLiveSources] = useState<LiveSource[]>([]);
  const [liveEvidenceCount, setLiveEvidenceCount] = useState(0);

  function reset() {
    setGoal("");
    setDocuments([]);
    setAnswer("");
    setState(null);
    setActivity([]);
    setPhase(-1);
    setCurrentMessage("Ask a question to start an investigation.");
    setIsThinking(false);
    setActiveReason("");
    setResultCount(0);
    setLiveSources([]);
    setLiveEvidenceCount(0);
    setStatus("Ready");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = prompt.trim();
    const attached = [...documents];
    if (!question || busy) return;
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
    setLiveSources([]);
    setLiveEvidenceCount(0);
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
          actionDescription(item.action?.tool ?? item.action?.action_type),
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
        }
        addActivity(`${capitalize(item.tool)} started`, "active", summarizeArguments(item.arguments));
        break;
      case "tool_finished":
        setIsThinking(false);
        if (item.tool === "search" && item.success) setCurrentMessage(`${item.output?.length ?? 0} candidate results found. Now selecting pages to inspect.`);
        if (item.tool === "research" && item.success) setCurrentMessage("Source review is complete. Bringing the verified finding together.");
        if (item.tool === "search" && Array.isArray(item.output)) {
          setResultCount(item.output.length);
        }
        addActivity(`${capitalize(item.tool)} ${item.success ? "completed" : "failed"}`, item.success ? "done" : "error", item.error || toolSummary(item), `${capitalize(item.tool)} started`);
        break;
      case "search_finished":
        setResultCount(item.result_count ?? 0);
        addActivity("Search results collected", "done", `${item.result_count ?? 0} results for “${item.query}”`);
        break;
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
  const finding: Finding | undefined = research?.finding;
  const evidence: Evidence[] = research?.evidence ?? [];
  const visibleAnswer = answerForDisplay(answer);
  const progress = !goal ? 0 : status === "Completed" ? 100 : Math.max(8, ((phase + 1) / stages.length) * 100);

  return (
    <div className="min-h-screen bg-[#08090c] text-zinc-100 selection:bg-indigo-400/30">
      {sidebarOpen && <button aria-label="Close navigation overlay" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-40 bg-black/70 lg:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[252px] flex-col border-r border-white/[0.07] bg-[#0a0b0f] transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-3"><div className="grid size-8 place-items-center rounded-lg border border-indigo-300/25 bg-indigo-400/10 text-sm font-bold text-indigo-200">R</div><span className="text-xs font-semibold tracking-[0.2em]">REVELIO</span></div>
          <button aria-label="Close navigation" onClick={() => setSidebarOpen(false)} className="text-zinc-500 lg:hidden"><X size={17} /></button>
        </div>
        <div className="px-3"><button onClick={reset} className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]"><Plus size={15} />New investigation</button></div>
        <div className="mt-8 px-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-600">Current session</div>
        {goal && <div className="mx-3 mt-3 rounded-lg border border-indigo-300/10 bg-indigo-300/[0.06] px-3 py-3 text-xs leading-5 text-zinc-300">{goal}</div>}
        <div className="mt-auto border-t border-white/[0.07] p-4"><div className="flex items-center gap-2 text-[10px] text-zinc-600"><span className={`size-1.5 rounded-full ${busy ? "bg-emerald-400 animate-pulse" : "bg-zinc-700"}`} />Local research workspace</div></div>
      </aside>

      <main className="lg:ml-[252px]">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.07] bg-[#08090c]/85 px-5 backdrop-blur-xl lg:px-8">
          <div className="flex min-w-0 items-center gap-3"><button aria-label="Open navigation" onClick={() => setSidebarOpen(true)} className="text-zinc-500 lg:hidden"><Menu size={18} /></button><span className="hidden shrink-0 text-xs text-zinc-600 sm:block">Revelio /</span><span className="truncate text-xs font-medium text-zinc-300">{goal || "New investigation"}</span></div>
          <div className="flex shrink-0 items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-[10px] text-zinc-400"><span className={`size-1.5 rounded-full ${busy ? "bg-indigo-300 animate-pulse" : status === "Failed" ? "bg-red-400" : status === "Completed" ? "bg-emerald-400" : "bg-zinc-600"}`} />{status}</div>
        </header>

        <div className="mx-auto max-w-[1240px] px-5 py-7 sm:px-7 lg:px-10 lg:py-9">
          <section className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0d0f15] px-6 py-7 sm:px-8 sm:py-9">
            <div className="hero-glow pointer-events-none absolute -right-20 -top-32 size-[360px] rounded-full bg-indigo-500/[0.13] blur-[90px]" />
            <div className="relative flex flex-col justify-between gap-7 md:flex-row md:items-center">
              <div className="max-w-3xl">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-indigo-300"><Sparkles size={13} />Research workspace</div>
                <h1 className="mt-3 text-2xl font-semibold leading-tight tracking-tight text-white sm:text-3xl">{goal || "Make complex questions easier to answer."}</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">{goal ? currentMessage : "Revelio searches sources, checks quotations, and shows what supports—or limits—its answer."}</p>
                {goal && <div className="mt-5 flex flex-wrap gap-2 text-[10px] text-zinc-400"><StatChip icon={<Search size={12} />} label={`${resultCount} search results`} /><StatChip icon={<FileText size={12} />} label={`${liveSources.length || sources.length} sources opened`} /><StatChip icon={<ShieldCheck size={12} />} label={`${liveEvidenceCount || evidence.length} evidence items`} /></div>}
              </div>
              <div className={`relative mx-auto grid size-28 shrink-0 place-items-center md:mr-5 ${busy ? "" : "opacity-75"}`} aria-hidden="true">
                {busy && <><span className="absolute inset-0 rounded-full border border-indigo-300/20 animate-orbit"/><span className="absolute inset-3 rounded-full border border-cyan-300/15 animate-orbit-reverse"/></>}
                <div className={`grid size-[72px] place-items-center rounded-full border border-indigo-200/20 bg-gradient-to-br from-indigo-400/20 to-cyan-300/[0.06] text-indigo-200 shadow-[0_0_45px_rgba(129,140,248,0.12)] ${busy ? "animate-breathe" : ""}`}><Activity size={27} strokeWidth={1.4} /></div>
                {busy && <span className="absolute right-1 top-5 size-2 rounded-full bg-cyan-200 shadow-[0_0_14px_rgba(103,232,249,.9)] animate-pulse"/>}
              </div>
            </div>
            {goal && <div className="relative mt-7">
              <div className="mb-3 flex items-center justify-between text-[10px]"><span className="font-medium text-zinc-400">Investigation progress</span><span className="text-zinc-600">{status === "Completed" ? "Complete" : `${Math.min(phase + 1, stages.length)} of ${stages.length} stages`}</span></div>
              <div className="h-1 overflow-hidden rounded-full bg-white/[0.07]"><div className={`h-full rounded-full bg-gradient-to-r from-indigo-400 to-cyan-300 transition-all duration-700 ${busy ? "progress-shimmer" : ""}`} style={{ width: `${progress}%` }}/></div>
              <div className="mt-4 grid grid-cols-5 gap-1 sm:gap-3">{stages.map((stage, index) => {
                const complete = status === "Completed" || index < phase;
                const active = busy && index === phase;
                return <div key={stage} className="flex min-w-0 items-center gap-1.5 sm:gap-2"><span className={`grid size-5 shrink-0 place-items-center rounded-full border ${complete ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200" : active ? "border-indigo-300/50 bg-indigo-300/10 text-indigo-200" : "border-white/10 text-zinc-700"}`}>{complete ? <Check size={11}/> : active ? <span className="size-1.5 rounded-full bg-indigo-200 animate-pulse"/> : <Circle size={8}/>}</span><span className={`truncate text-[9px] sm:text-[10px] ${complete || active ? "text-zinc-300" : "text-zinc-600"}`}>{stage}</span></div>;
              })}</div>
            </div>}
          </section>

          {goal && <section className={`live-now relative mt-5 overflow-hidden rounded-2xl border ${busy ? "border-indigo-300/20" : "border-white/[0.08]"} bg-[#0d0f16]`}>
            <div className="live-now-wash pointer-events-none absolute inset-0" />
            <div className="relative flex flex-col gap-5 px-5 py-5 sm:flex-row sm:items-center sm:gap-7 sm:px-7 sm:py-6">
              <div className={`live-orbit relative mx-auto grid size-28 shrink-0 place-items-center sm:mx-0 ${busy ? "is-active" : "is-idle"}`} aria-hidden="true">
                <span className="orbit-ring orbit-ring-one"/><span className="orbit-ring orbit-ring-two"/><span className="orbit-ring orbit-ring-three"/>
                <span className="orbit-core grid size-16 place-items-center rounded-full border border-indigo-200/25 bg-[#111522] text-indigo-100"><Sparkles size={24} strokeWidth={1.4}/></span>
                {busy && <span className="orbit-dot orbit-dot-one"/>}{busy && <span className="orbit-dot orbit-dot-two"/>}
              </div>
              <div className="min-w-0 flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] sm:justify-start"><span className={`relative flex size-2 ${busy ? "" : "hidden"}`}><span className="absolute inline-flex size-full rounded-full bg-cyan-300 opacity-60 animate-ping"/><span className="relative inline-flex size-2 rounded-full bg-cyan-200"/></span><span className={busy ? "text-cyan-200" : "text-zinc-500"}>{busy ? isThinking ? "Revelio is thinking" : "Revelio is working" : status === "Completed" ? "Investigation complete" : status}</span></div>
                <h2 className="mt-2 text-lg font-medium tracking-tight text-white sm:text-xl">{busy ? isThinking ? "Thinking through the next step" : stageLabel(phase) : status === "Completed" ? "Here’s what the investigation found" : "Investigation status"}</h2>
                <p className="mx-auto mt-2 max-w-2xl text-xs leading-5 text-zinc-400 sm:mx-0 sm:text-sm">{currentMessage}</p>
                {activeReason && busy && <div className="mx-auto mt-3 max-w-2xl rounded-lg border border-white/[0.06] bg-black/20 px-3 py-2 text-left sm:mx-0"><div className="text-[9px] font-semibold uppercase tracking-[0.16em] text-indigo-200/70">Why this step</div><p className="mt-1 text-[11px] leading-4 text-zinc-400">{activeReason}</p></div>}
              </div>
              <div className="hidden w-32 shrink-0 sm:block"><div className="flex h-10 items-end justify-center gap-1.5">{[15, 24, 12, 31, 19, 27, 13, 22].map((height, index) => <span key={index} className={`signal-bar ${busy ? "signal-bar-active" : ""}`} style={{ height: busy ? `${height}px` : "4px", animationDelay: `${index * 90}ms` }}/>)}</div><div className="mt-2 text-center text-[9px] uppercase tracking-[0.15em] text-zinc-600">{busy ? `Step ${Math.max(1, phase + 1)} / ${stages.length}` : status === "Completed" ? "Complete" : "Idle"}</div></div>
            </div>
            {busy && <div className="live-progress-track"><span/></div>}
          </section>}

          {!goal && <section className="mt-6 grid gap-3 sm:grid-cols-3">{examples.map((example) => <button key={example} onClick={() => setPrompt(example)} className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4 text-left text-xs leading-5 text-zinc-400 transition hover:border-indigo-300/20 hover:bg-indigo-300/[0.04] hover:text-zinc-200"><span className="mb-2 block text-indigo-300"><Sparkles size={14}/></span>{example}</button>)}</section>}

          {goal && <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_350px]">
            <div className="space-y-4">
              <section className="overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
                <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-4"><div><div className="text-xs font-semibold text-zinc-200">Answer</div><div className="mt-1 text-[10px] text-zinc-600">{busy ? "Drafting from collected evidence" : status}</div></div>{finding?.status && <FindingBadge status={finding.status}/>}</div>
                <div className="min-h-28 whitespace-pre-wrap px-5 py-5 text-sm leading-7 text-zinc-300">{visibleAnswer || (busy ? <span className="flex items-center gap-2 text-zinc-500"><span className="flex gap-1"><i className="thinking-dot"/><i className="thinking-dot delay-1"/><i className="thinking-dot delay-2"/></span>{currentMessage}</span> : <span className="text-zinc-600">Your answer will appear here.</span>)}</div>
                {finding?.caveats?.length ? <div className="border-t border-white/[0.07] bg-amber-300/[0.025] px-5 py-4"><div className="text-[10px] font-medium uppercase tracking-wider text-amber-200/70">Limits to keep in mind</div><ul className="mt-2 space-y-1.5">{finding.caveats.map((caveat, index) => <li key={index} className="flex gap-2 text-xs leading-5 text-zinc-500"><span className="text-amber-200/60">•</span>{caveat}</li>)}</ul></div> : null}
              </section>

              <section className="overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
                <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-4"><div><div className="text-xs font-semibold text-zinc-200">Sources & evidence</div><div className="mt-1 text-[10px] text-zinc-600">Search results are candidates; opened sources and quotes are tracked separately.</div></div><span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] text-zinc-500">{sources.length || searchResults.length} sources</span></div>
                {(sources.length ? sources : searchResults).length ? <div className="divide-y divide-white/[0.06]">{(sources.length ? sources : searchResults).map((source, index) => {
                  const live = liveSources.find((item) => item.url === source.url);
                  const researched = sources.some((item) => item.url === source.url);
                  const uploaded = source.url.startsWith("upload://");
                  return <a key={`${source.url}-${index}`} href={uploaded ? undefined : source.url} target={uploaded ? undefined : "_blank"} rel={uploaded ? undefined : "noreferrer"} className="group flex items-start justify-between gap-4 px-5 py-3.5 transition hover:bg-white/[0.025]"><span className="flex min-w-0 gap-3"><span className="mt-0.5 text-zinc-600"><FileSearch size={15}/></span><span className="min-w-0"><span className="block truncate text-xs font-medium text-zinc-300 group-hover:text-white">{source.title || source.url}</span><span className="mt-1 block truncate text-[10px] text-zinc-600">{domainOf(source.url)}</span></span></span><span className="flex shrink-0 items-center gap-2 text-[9px] text-zinc-500">{uploaded ? "Uploaded" : live?.state === "unavailable" ? "Unavailable" : live?.state === "opening" ? "Opening…" : researched ? "Read" : "Candidate"}{!uploaded && <ExternalLink size={12}/>}</span></a>;
                })}</div> : <div className="px-5 py-8 text-center text-xs text-zinc-600">Sources will appear here as soon as search finishes.</div>}
                {evidence.length > 0 && <div className="border-t border-white/[0.07] px-5 py-4"><div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500"><ShieldCheck size={13}/>Quoted evidence · {evidence.length}</div><div className="space-y-3">{evidence.map((item, index) => <blockquote key={index} className="rounded-lg border border-white/[0.06] bg-black/20 p-3 text-xs leading-5 text-zinc-400"><span className="text-indigo-200/90">“{item.supporting_text}”</span>{item.claim && <div className="mt-2 text-[10px] text-zinc-500">Claim: {item.claim}</div>}<a href={item.url?.startsWith("upload://") ? undefined : item.url} target={item.url?.startsWith("upload://") ? undefined : "_blank"} rel={item.url?.startsWith("upload://") ? undefined : "noreferrer"} className="mt-2 block truncate text-[10px] text-zinc-600 hover:text-indigo-200">{item.url?.startsWith("upload://") ? `Uploaded file: ${item.url.slice(9)}` : item.url}</a></blockquote>)}</div></div>}
              </section>
            </div>

            <aside className="h-fit overflow-hidden rounded-xl border border-white/[0.08] bg-[#0c0e12]">
              <details>
                <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-4"><span><span className="block text-xs font-semibold text-zinc-200">Detailed activity</span><span className="mt-1 block text-[10px] text-zinc-600">{activity.length} observable events · expand for the event log</span></span><span className={`rounded-full border px-2.5 py-1 text-[9px] uppercase tracking-wider ${busy ? "border-cyan-200/20 text-cyan-200" : "border-white/10 text-zinc-500"}`}>{busy ? "Live" : "Log"}</span></summary>
                <div className="max-h-[440px] divide-y divide-white/[0.045] overflow-auto border-t border-white/[0.06]">{activity.length ? activity.map((item) => <ActivityRow key={item.id} item={item}/>) : <div className="px-5 py-7 text-center text-xs text-zinc-600">Progress appears here while Revelio works.</div>}</div>
              </details>
            </aside>
          </div>}

          <form onSubmit={submit} className={`mx-auto max-w-[820px] ${goal ? "mt-6" : "mt-7"}`}>
            {documents.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{documents.map((file, index) => <span key={`${file.name}-${file.size}-${index}`} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-[#0c0e12] px-3 py-2 text-[10px] text-zinc-300"><FileText size={12} className="text-indigo-200"/><span className="max-w-56 truncate">{file.name}</span><button type="button" aria-label={`Remove ${file.name}`} onClick={() => setDocuments((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-zinc-500 hover:text-white"><X size={12}/></button></span>)}</div>}
            <div className="flex items-end gap-2 rounded-xl border border-white/10 bg-[#0c0e12] p-2 shadow-2xl shadow-black/20 transition focus-within:border-indigo-300/30">
              <input ref={uploadRef} className="hidden" type="file" multiple accept=".pdf,.docx,.txt,.md,.html,.htm" onChange={(event) => { const selected = Array.from(event.target.files ?? []); setDocuments((current) => [...current, ...selected].slice(0, 3)); event.currentTarget.value = ""; }}/>
              <button type="button" aria-label="Attach documents" title="Attach PDF, DOCX, TXT, Markdown, or HTML" disabled={busy || documents.length >= 5} onClick={() => uploadRef.current?.click()} className="grid size-9 shrink-0 place-items-center rounded-lg text-zinc-500 transition hover:bg-white/[0.06] hover:text-indigo-200 disabled:opacity-40"><Paperclip size={16}/></button>
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask Revelio to investigate something…" rows={1} className="min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-xs text-zinc-200 outline-none placeholder:text-zinc-600"/>
              <button type="submit" disabled={!prompt.trim() || busy} className="grid size-9 place-items-center rounded-lg bg-indigo-100 text-zinc-900 transition hover:bg-white disabled:bg-white/[0.06] disabled:text-zinc-700"><ArrowUp size={16}/></button>
            </div>
            <div className="mt-2 text-center text-[9px] text-zinc-700">Search · Open sources · Extract evidence · Verify · Answer · Optional PDF, DOCX, TXT, MD, or HTML</div>
          </form>
        </div>
      </main>
    </div>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const [open, setOpen] = useState(false);
  return <button onClick={() => item.detail && setOpen((value) => !value)} className={`flex w-full items-start gap-3 px-5 py-3 text-left transition ${item.detail ? "hover:bg-white/[0.025]" : "cursor-default"}`}>
    <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${item.state === "active" ? "border-indigo-300/30 text-indigo-200" : item.state === "error" ? "border-red-300/30 text-red-300" : "border-white/10 text-emerald-300/70"}`}>{item.state === "active" ? <span className="size-1.5 rounded-full bg-indigo-200 animate-pulse"/> : item.state === "error" ? <X size={10}/> : <Check size={10}/>}</span>
    <span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-2"><span className="text-xs text-zinc-300">{item.label}</span><time className="shrink-0 text-[10px] text-zinc-700">{item.time}</time></span>{open && item.detail && <span className="mt-1.5 block break-words text-[11px] leading-4 text-zinc-500">{item.detail}</span>}</span>
  </button>;
}

function StatChip({ icon, label }: { icon: ReactNode; label: string }) {
  return <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-black/20 px-2.5 py-1.5">{icon}{label}</span>;
}

function FindingBadge({ status }: { status: string }) {
  const style = status === "supported" ? "border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-200" : status === "contradicted" ? "border-rose-300/20 bg-rose-300/[0.07] text-rose-200" : "border-amber-300/20 bg-amber-300/[0.07] text-amber-200";
  return <span className={`rounded-full border px-2.5 py-1 text-[9px] font-medium capitalize ${style}`}>{status}</span>;
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
