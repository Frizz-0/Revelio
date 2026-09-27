import { useState } from "react";
import type { FormEvent } from "react";
import { Activity, ArrowUp, Check, ExternalLink, FileText, Menu, Plus, ShieldCheck, Sparkles, X } from "lucide-react";

type StreamEvent = { event: string;[key: string]: any };
type AgentState = {
  goal: string;
  status: string;
  final_answer?: string | null;
  observations?: Array<{ tool: string; success: boolean; output?: any; error?: string }>;
};
type ActivityItem = { id: number; label: string; state: "active" | "done" | "error" };

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState("");
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [state, setState] = useState<AgentState | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = prompt.trim();
    if (!question || busy) return;
    setGoal(question);
    setPrompt("");
    setAnswer("");
    setState(null);
    setActivity([]);
    setStatus("Connecting");
    setBusy(true);
    try {
      const response = await fetch("/api/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ goal: question }),
      });
      if (!response.ok || !response.body) throw new Error(`API returned ${response.status}`);
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
          if (!line) continue;
          const item = JSON.parse(line.slice(6)) as StreamEvent;
          consume(item);
        }
        if (done) break;
      }
    } catch (error) {
      setStatus("Connection failed");
      setActivity((items) => [...items, { id: Date.now(), label: String(error), state: "error" }]);
    } finally {
      setBusy(false);
    }
  }

  function consume(item: StreamEvent) {
    const add = (label: string, state: ActivityItem["state"] = "done") =>
      setActivity((items) => [...items, { id: Date.now() + Math.random(), label, state }]);
    switch (item.event) {
      case "started": setStatus("Investigating"); add("Investigation started", "active"); break;
      case "decision_started": add(`Choosing next action · step ${item.step}`, "active"); break;
      case "action_selected": add(`Agent chose ${item.action?.tool ?? item.action?.action_type}`, "done"); break;
      case "action_rejected": add(`Action rejected: ${item.error}`, "error"); break;
      case "tool_started": add(`${item.tool} started${item.arguments?.query ? ` · ${item.arguments.query}` : ""}`, "active"); break;
      case "tool_finished": add(`${item.tool} ${item.success ? "succeeded" : "failed"}${item.error ? ` · ${item.error}` : ""}`, item.success ? "done" : "error"); break;
      case "search_finished": add(`Search returned ${item.result_count} results`); break;
      case "research_source_started": add(`Fetching ${item.title || item.url}`, "active"); break;
      case "research_source_finished": add(`${item.success ? "Fetched" : "Could not read"} ${item.title || item.url}`, item.success ? "done" : "error"); break;
      case "evidence_extraction_started": add(`Extracting evidence · ${item.title}`); break;
      case "verification_started": add(`Verifying ${item.evidence_count} evidence items across ${item.source_count} sources`, "active"); break;
      case "verification_finished": add(`Verification: ${item.status} · ${item.evidence_count} evidence items`); break;
      case "completed": setStatus("Completed"); if (item.state) setState(item.state); break;
      case "failed": setStatus("Failed"); add(item.error || "Investigation failed", "error"); if (item.state) setState(item.state); break;
      case "result": setState(item.state); setAnswer(item.state?.final_answer || ""); break;
      case "finished": setStatus(item.status === "completed" ? "Completed" : "Failed"); break;
    }
  }

  const observations = state?.observations ?? [];
  const searchResults = observations.filter((item) => item.tool === "search" && item.success).flatMap((item) => Array.isArray(item.output) ? item.output : []);
  const research = [...observations].reverse().find((item) => item.tool === "research" && item.success)?.output;
  const sources = research?.sources ?? searchResults.map((item: any) => ({ title: item.title, url: item.url }));
  const finding = research?.finding;
  const evidence = research?.evidence ?? [];

  return (
    <div className="min-h-screen bg-[#090a0c] text-zinc-100">
      {sidebarOpen && <button aria-label="Close navigation overlay" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-40 bg-black/60 lg:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-[#20242b] bg-[#0b0c0f] transition-transform duration-200 ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="flex items-center justify-between px-5 py-5"><div className="flex items-center gap-3"><div className="grid size-8 place-items-center rounded-lg border border-[#343944] bg-[#14171d] text-sm font-bold text-indigo-300">R</div><span className="text-sm font-semibold tracking-[0.15em]">REVELIO</span></div><button onClick={() => setSidebarOpen(false)} className="p-1.5 text-zinc-500 lg:hidden"><X size={17} /></button></div>
        <div className="px-3"><button onClick={() => { setGoal(""); setAnswer(""); setState(null); setActivity([]); setStatus("Ready"); }} className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#292e37] bg-[#14171c] px-3 py-2.5 text-xs text-zinc-200"><Plus size={15} />New investigation</button></div>
        <div className="mt-8 px-5 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600">Current session</div>
        {goal && <div className="mx-3 mt-3 rounded-lg bg-[#15181d] px-3 py-3 text-xs text-zinc-300">{goal}</div>}
        <div className="mt-auto border-t border-[#20242b] p-4 text-[10px] text-zinc-600">Local prototype · API {busy ? "connected" : "idle"}</div>
      </aside>

      <main className="lg:ml-[260px]">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[#20242b] bg-[#090a0c]/90 px-5 backdrop-blur-xl lg:px-8"><div className="flex items-center gap-3"><button onClick={() => setSidebarOpen(true)} className="p-2 text-zinc-500 lg:hidden"><Menu size={18} /></button><span className="hidden text-xs text-zinc-600 sm:block">Investigation /</span><span className="max-w-[55vw] truncate text-sm font-medium">{goal || "New investigation"}</span></div><div className="rounded-full border border-[#252b35] px-3 py-1.5 text-[10px] text-zinc-400">{status}</div></header>
        <div className="mx-auto max-w-[1180px] px-5 py-8 lg:px-10 lg:py-10">
          <section><div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600">Investigation</div><h1 className="mt-2 max-w-4xl text-2xl font-semibold tracking-tight text-zinc-100 sm:text-3xl">{goal || "What should Revelio investigate?"}</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500">Live tool calls, source processing, verification, and answer from the local agent.</p></section>
          <section className="mt-8 grid gap-4 xl:grid-cols-[1fr_340px]">
            <div className="overflow-hidden rounded-xl border border-[#20242b] bg-[#0f1115]"><div className="border-b border-[#20242b] px-5 py-4"><div className="text-xs font-semibold">Answer</div><div className="mt-1 text-[10px] text-zinc-600">{busy ? "Agent is working…" : status}</div></div><div className="p-5 text-sm leading-7 text-zinc-300">{answer || (busy ? <span className="text-zinc-600">Waiting for the agent to finish…</span> : <span className="text-zinc-700">Your result will appear here.</span>)}</div>{finding && <div className="border-t border-[#20242b] px-5 py-4 text-xs text-zinc-500">Finding status: <span className="text-zinc-300">{finding.status}</span>{finding.caveats?.length > 0 && <ul className="mt-2 list-disc pl-5">{finding.caveats.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul>}</div>}</div>
            <div className="overflow-hidden rounded-xl border border-[#20242b] bg-[#0f1115]"><div className="flex items-center justify-between border-b border-[#20242b] px-5 py-4"><div className="text-xs font-semibold">Agent activity</div><span className="text-[9px] font-bold tracking-[0.15em] text-indigo-300">{busy ? "LIVE" : "LOG"}</span></div><div className="max-h-[380px] space-y-4 overflow-auto p-5">{activity.length ? activity.map((item) => <div key={item.id} className="flex items-start gap-3"><div className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${item.state === "active" ? "border-indigo-400/30 text-indigo-300" : item.state === "error" ? "border-red-400/30 text-red-300" : "border-[#292e36] text-zinc-600"}`}>{item.state === "active" ? <Activity size={11} /> : item.state === "error" ? <X size={11} /> : <Check size={11} />}</div><span className="break-words text-xs text-zinc-400">{item.label}</span></div>) : <p className="text-xs text-zinc-700">Tool and model activity will appear here.</p>}</div></div>
          </section>
          {finding && <section className="mt-4 overflow-hidden rounded-xl border border-[#20242b] bg-[#0f1115]"><div className="border-b border-[#20242b] px-5 py-4"><div className="text-xs font-semibold">Verified finding</div></div><div className="flex gap-3 p-5"><ShieldCheck size={17} className="mt-1 shrink-0 text-indigo-300" /><div><div className="text-sm font-medium text-zinc-200">{finding.conclusion}</div>{finding.caveats?.map((item: string, index: number) => <p key={index} className="mt-2 text-xs text-zinc-500">{item}</p>)}</div></div></section>}
          <section className="mt-4 overflow-hidden rounded-xl border border-[#20242b] bg-[#0f1115]"><div className="border-b border-[#20242b] px-5 py-4"><div className="text-xs font-semibold">Sources and evidence</div><div className="mt-1 text-[10px] text-zinc-600">{sources.length} source(s) · {evidence.length} extracted evidence item(s)</div></div>{sources.length ? <div className="divide-y divide-[#20242b]">{sources.map((source: any, index: number) => <a key={`${source.url}-${index}`} href={source.url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-white/[0.02]"><span className="flex min-w-0 items-center gap-3"><FileText size={15} className="shrink-0 text-zinc-600" /><span className="truncate text-xs text-zinc-300">{source.title || source.url}</span></span><ExternalLink size={14} className="shrink-0 text-zinc-600" /></a>)}</div> : <div className="px-5 py-5 text-xs text-zinc-700">Sources will appear when search runs.</div>}{evidence.length > 0 && <div className="border-t border-[#20242b] p-5">{evidence.map((item: any, index: number) => <blockquote key={index} className="mb-3 border-l-2 border-indigo-400/40 pl-3 text-xs leading-5 text-zinc-400">“{item.supporting_text}”<div className="mt-1 text-[10px] text-zinc-600">{item.url}</div></blockquote>)}</div>}</section>
          <form onSubmit={submit} className="mx-auto mt-7 max-w-[820px]"><div className="flex items-end gap-2 rounded-xl border border-[#2a2f38] bg-[#0e1014] p-2 shadow-2xl shadow-black/20 focus-within:border-[#3b4250]"><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask Revelio to investigate something…" rows={1} className="min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-xs text-zinc-200 outline-none placeholder:text-zinc-700" /><button type="submit" disabled={!prompt.trim() || busy} className="grid size-9 place-items-center rounded-lg border border-transparent bg-indigo-100 text-zinc-900 disabled:border-[#292e37] disabled:bg-[#171a20] disabled:text-zinc-700"><ArrowUp size={16} /></button></div><div className="mt-2 flex items-center justify-center gap-1 text-[9px] text-zinc-700"><Sparkles size={10} />Search · Analyze · Verify · Synthesize</div></form>
        </div>
      </main>
    </div>
  );
}

export default App;
