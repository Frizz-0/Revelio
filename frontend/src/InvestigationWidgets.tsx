import { useState } from "react";
import type { ReactNode } from "react";
import { Check, X } from "lucide-react";

export type ActivityItem = {
  id: number;
  label: string;
  detail?: string;
  state: "active" | "done" | "error";
  time: string;
};

export function ActivityRow({ item, expanded = false }: { item: ActivityItem; expanded?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <button onClick={() => item.detail && setOpen((value) => !value)} className={`flex w-full items-start gap-3 px-5 py-3 text-left transition ${item.detail ? "hover:bg-white/[0.025]" : "cursor-default"}`}>
      <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${item.state === "active" ? "border-indigo-300/30 text-indigo-200" : item.state === "error" ? "border-red-300/30 text-red-300" : "border-white/10 text-emerald-300/70"}`}>
        {item.state === "active" ? <span className="size-1.5 rounded-full bg-indigo-200 animate-pulse" /> : item.state === "error" ? <X size={10} /> : <Check size={10} />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-2"><span className="text-xs text-zinc-300">{item.label}</span><time className="shrink-0 text-[10px] text-zinc-700">{item.time}</time></span>
        {(open || expanded) && item.detail && <span className="mt-1.5 block break-words text-[11px] leading-4 text-zinc-500">{item.detail}</span>}
      </span>
    </button>
  );
}

export function Readout({ icon, label, value, detail, tone }: { icon: ReactNode; label: string; value: string | number; detail: string; tone: "cyan" | "blue" | "amber" | "violet" }) {
  return <div className={`readout-card hud-panel tone-${tone}`}><div className="flex items-center justify-between"><span className="readout-label">{label}</span><span className="readout-icon">{icon}</span></div><div className="readout-value">{value}</div><div className="readout-detail">{detail}</div></div>;
}

export function TelemetryLine({ label, value }: { label: string; value: string }) {
  return <div className="telemetry-line"><span>{label}</span><span className="telemetry-value">{value}</span></div>;
}

export function FindingBadge({ status }: { status: string }) {
  const style = status === "supported" ? "border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-200" : status === "contradicted" ? "border-rose-300/20 bg-rose-300/[0.07] text-rose-200" : "border-amber-300/20 bg-amber-300/[0.07] text-amber-200";
  return <span className={`rounded-full border px-2.5 py-1 text-[9px] font-medium capitalize ${style}`}>{status}</span>;
}
