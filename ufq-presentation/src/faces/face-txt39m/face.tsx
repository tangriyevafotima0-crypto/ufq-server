import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { blocks } from "./face.content.json";
import { controls } from "./face.controls.json";
import { TextContent } from "@/components/ui/text-content";
import WaterfallChart from "./components/WaterfallChart";

const LEGEND = [
  { key: "legendStart", color: "var(--brand)" },
  { key: "legendIncrease", color: "var(--foreground)" },
  { key: "legendDecrease", color: "var(--accent)" },
] as const;

function Rivets() {
  return (
    <>
      <span className="ind-rivet absolute top-3 left-3" />
      <span className="ind-rivet absolute top-3 right-3" />
      <span className="ind-rivet absolute bottom-3 left-3" />
      <span className="ind-rivet absolute bottom-3 right-3" />
    </>
  );
}

export default function ChartSplitFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const chartOnLeft = (controls.chartSide?.value ?? "Right") === "Left";

  const rows = blocks.chartData.rows;

  return (
    <div
      ref={ref}
      className={`relative w-full h-full overflow-hidden bg-background font-body flex flex-col ${
        chartOnLeft ? "@xl:flex-row-reverse" : "@xl:flex-row"
      }`}
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      {/* Text panel */}
      <div
        className="relative bg-surface px-6 pt-9 pb-7 @xl:px-16 @xl:pt-20 @xl:pb-16 flex flex-col @xl:basis-[36%]"
      >
        <Rivets />
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <div className="ind-stamp inline-flex items-center gap-2 bg-brand px-2.5 py-1 @xl:px-4 @xl:py-1.5">
            <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
              [
            </span>
            <TextContent
              content={blocks.label.content}
              className="font-display text-foreground text-xs @xl:text-base font-medium uppercase tracking-[0.28em] leading-none"
              data-content-keys={["label"]}
            />
            <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
              ]
            </span>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 1.03 }}
            animate={inView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.45, delay: 0.12, ease: "easeOut" }}
            className="mt-4 @xl:mt-7"
          >
            <TextContent
              content={blocks.headline.content}
              className="block font-display font-semibold uppercase leading-[1.02] text-foreground text-3xl @xl:text-7xl"
              data-content-keys={["headline"]}
              style={{ letterSpacing: "-0.005em" }}
            />
          </motion.div>

          <motion.div
            className="mt-4 @xl:mt-6 h-1.5 @xl:h-2 w-24 @xl:w-36 bg-accent origin-left"
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.35 }}
          className="mt-auto pt-6"
        >
          <div className="mb-4 flex items-center gap-2">
            <span className="h-px flex-1 bg-foreground/30" />
            <span className="font-display text-foreground/50 text-[9px] @xl:text-base uppercase tracking-[0.3em] select-none">
              Spec 07-A
            </span>
          </div>
          <TextContent
            content={blocks.body.content}
            className="text-muted text-sm @xl:text-xl font-normal leading-relaxed max-w-md"
            data-content-keys={["body"]}
          />
        </motion.div>
      </div>

      {/* Hazard tape divider */}
      <div className="ind-hazard h-2 @xl:h-auto @xl:w-3 shrink-0" />

      {/* Chart panel */}
      <div className="relative flex-1 bg-background px-6 pt-9 pb-7 @xl:px-14 @xl:pt-20 @xl:pb-14 flex flex-col min-h-0">
        <Rivets />
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        >
          <TextContent
            content={blocks.chartTitle.content}
            className="font-display text-foreground font-medium uppercase text-xl @xl:text-4xl leading-[1.1] max-w-2xl"
            data-content-keys={["chartTitle"]}
            style={{ letterSpacing: "0.01em" }}
          />
        </motion.div>

        {/* Legend */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="mt-5 @xl:mt-8 flex flex-wrap items-center gap-x-6 @xl:gap-x-8 gap-y-2"
        >
          {LEGEND.map((item) => (
            <div key={item.key} className="flex items-center gap-2 @xl:gap-2.5">
              <span
                className="h-2.5 w-2.5 @xl:h-3.5 @xl:w-3.5 rounded-none border-2 border-foreground shrink-0"
                style={{ background: item.color }}
              />
              <TextContent
                content={blocks[item.key].content}
                className="font-display text-foreground text-xs @xl:text-base font-normal uppercase tracking-[0.14em]"
                data-content-keys={[item.key]}
              />
            </div>
          ))}
        </motion.div>

        {/* Chart */}
        <motion.div
          initial={{ opacity: 0, y: 26 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.55, delay: 0.35, ease: "easeOut" }}
          className="flex-1 min-h-0 mt-4 @xl:mt-8"
        >
          <WaterfallChart rows={rows} />
        </motion.div>
      </div>
    </div>
  );
}

