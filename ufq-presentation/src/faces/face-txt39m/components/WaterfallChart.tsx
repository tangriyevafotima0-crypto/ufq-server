import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const COLORS = {
  start: "#F7C600",
  total: "#F7C600",
  increase: "#1E1F1D",
  decrease: "#D9531E",
};

type Row = { label: string; value: string; type: string };

export function buildWaterfall(rows: Row[]) {
  let running = 0;
  return rows.map((r) => {
    const v = Number(r.value) || 0;
    const type = (r.type || "increase").toLowerCase();
    let base = 0;
    let bar = 0;
    if (type === "start") {
      base = 0;
      bar = v;
      running = v;
    } else if (type === "total") {
      base = 0;
      bar = v;
      running = v;
    } else if (type === "decrease") {
      base = running - v;
      bar = v;
      running = running - v;
    } else {
      base = running;
      bar = v;
      running = running + v;
    }
    return {
      label: r.label,
      base,
      bar,
      total: running,
      type,
      color: COLORS[type as keyof typeof COLORS] ?? COLORS.increase,
    };
  });
}

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const isStep = d.type === "increase" || d.type === "decrease";
  return (
    <div
      className="bg-foreground px-4 py-3 rounded-none"
      style={{ borderLeft: "5px solid var(--brand)", boxShadow: "4px 4px 0 rgba(30,31,29,0.25)" }}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 border border-background"
          style={{ background: d.color }}
        />
        <span className="font-display text-[#F4F4F0] text-sm @xl:text-lg uppercase tracking-[0.1em]">
          {d.label}
        </span>
      </div>
      {isStep && (
        <div className="mt-1 font-body text-line text-xs @xl:text-base tracking-[0.06em]">
          {d.type === "decrease" ? "−" : "+"}
          {d.bar.toLocaleString()}
        </div>
      )}
      <div className="mt-1 font-display text-brand text-lg font-medium">
        {d.total.toLocaleString()}
      </div>
    </div>
  );
}

export default function WaterfallChart({ rows }: { rows: Row[] }) {
  const data = buildWaterfall(rows);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
        barCategoryGap="24%"
      >
        <CartesianGrid vertical={false} stroke="#B9B9B2" strokeDasharray="6 4" />
        <XAxis
          dataKey="label"
          tickLine={{ stroke: "#1E1F1D", strokeWidth: 2 }}
          tickSize={7}
          axisLine={{ stroke: "#1E1F1D", strokeWidth: 2 }}
          tick={{ fill: "#1E1F1D", fontSize: 9, fontFamily: "Oswald" }}
          className="@xl:text-[17px] text-[9px]"
          dy={8}
          interval={0}
        />
        <YAxis
          tickLine={{ stroke: "#1E1F1D", strokeWidth: 2 }}
          tickSize={7}
          axisLine={{ stroke: "#1E1F1D", strokeWidth: 2 }}
          tick={{ fill: "#3A3B38", fontSize: 8, fontFamily: "Roboto Condensed" }}
          className="@xl:text-[16px] text-[8px]"
          tickFormatter={(v: number) => (v >= 1000 ? `${v / 1000}k` : `${v}`)}
          width={40}
        />
        <Tooltip cursor={{ fill: "#1E1F1D", opacity: 0.08 }} content={<ChartTooltip />} />
        <Bar dataKey="base" stackId="a" fill="transparent" isAnimationActive={false} />
        <Bar
          dataKey="bar"
          stackId="a"
          stroke="#1E1F1D"
          strokeWidth={1.5}
          animationDuration={700}
          animationEasing="ease-out"
        >
          {data.map((d, i) => (
            <Cell key={i} fill={d.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

