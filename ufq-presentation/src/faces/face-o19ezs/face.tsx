import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { blocks } from "./face.content.json";
import { controls } from "./face.controls.json";
import { TextContent } from "@/components/ui/text-content";

const EASE = [0.22, 1, 0.36, 1] as const;

export default function ProcessListFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.2 });
  const showDescriptions = controls.showDescriptions?.value ?? true;

  const rows = blocks.rows.rows;

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      <div className="relative flex-1 min-h-0 flex flex-col px-6 pt-9 pb-7 @xl:px-20 @xl:pt-16 @xl:pb-14">
        {/* Label */}
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="shrink-0 flex items-center gap-2 @xl:gap-3"
        >
          <span className="h-2 w-2 @xl:h-3 @xl:w-3 bg-brand border-2 border-foreground shrink-0" />
          <TextContent
            content={blocks.label.content}
            className="font-display text-foreground/60 text-xs @xl:text-xl font-medium uppercase tracking-[0.28em]"
            data-content-keys={["label"]}
          />
          <span className="h-px flex-1 bg-foreground/30" />
          <span className="font-display text-foreground/50 text-[9px] @xl:text-base uppercase tracking-[0.3em] select-none">
            Spec 07-A
          </span>
        </motion.div>

        {/* Rows */}
        <div className="mt-5 @xl:mt-10 flex-1 min-h-0 flex flex-col border-t-2 border-line">
          {rows.map((row, index) => (
            <motion.div
              key={row.id}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.15 + index * 0.1, ease: EASE }}
              className="flex-1 min-h-0 flex items-center gap-4 @xl:gap-10 border-b-2 border-line"
            >
              {/* Number */}
              <TextContent
                content={row.number}
                className="shrink-0 w-8 @xl:w-24 font-display font-semibold text-steel-dark text-lg @xl:text-4xl tabular-nums"
                data-content-keys={[`rows.rows.${index}.number`]}
              />

              {/* Name */}
              <TextContent
                content={row.name}
                className="flex-1 min-w-0 text-foreground font-display font-semibold uppercase text-3xl @xl:text-7xl leading-[1.25] break-words"
                data-content-keys={[`rows.rows.${index}.name`]}
                style={{ letterSpacing: "-0.005em" }}
              />

              {/* Description */}
              {showDescriptions && (
                <TextContent
                  content={row.description}
                  className="hidden @xl:block shrink-0 w-[30%] text-muted text-lg @xl:text-xl font-normal leading-snug"
                  data-content-keys={[`rows.rows.${index}.description`]}
                />
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
