import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { blocks } from "./face.content.json";
import { controls } from "./face.controls.json";
import { TextContent } from "@/components/ui/text-content";

function Rivets() {
  return (
    <>
      <span className="ind-rivet absolute top-3 left-3 z-20" />
      <span className="ind-rivet absolute top-3 right-3 z-20" />
      <span className="ind-rivet absolute bottom-3 left-3 z-20" />
      <span className="ind-rivet absolute bottom-3 right-3 z-20" />
    </>
  );
}

export default function AgendaFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  const showNumbers = controls.showNumbers?.value ?? true;
  const items = blocks.items.rows.slice(0, 5);

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background text-foreground font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />
      <Rivets />

      <div className="relative flex-1 min-h-0 flex flex-col px-6 pt-9 pb-7 @xl:px-16 @xl:pt-20 @xl:pb-14">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="shrink-0"
        >
          <div className="flex items-center gap-2 @xl:gap-3">
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
            <span className="h-px flex-1 bg-foreground/30" />
            <span className="font-display text-foreground/50 text-[9px] @xl:text-base uppercase tracking-[0.3em] select-none">
              Spec 07-A
            </span>
          </div>
          <TextContent
            content={blocks.title.content}
            className="mt-4 @xl:mt-7 font-display font-semibold uppercase leading-[1.02] text-foreground text-4xl @xl:text-7xl"
            data-content-keys={["title"]}
            style={{ letterSpacing: "-0.005em" }}
          />
          <motion.div
            className="mt-4 @xl:mt-6 h-1.5 @xl:h-2 w-20 @xl:w-32 bg-accent origin-left"
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          />
        </motion.div>

        {/* Items */}
        <div className="mt-8 @xl:mt-12 flex-1 min-h-0 flex flex-col">
          {items.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.2 + index * 0.09, ease: "easeOut" }}
              className="flex-1 min-h-0 flex flex-col justify-center @xl:flex-row @xl:items-center gap-1 @xl:gap-10 border-t-2 border-line py-4 @xl:py-0"
            >
              <div className="flex items-baseline gap-4 @xl:gap-8 min-w-0">
                {showNumbers && (
                  <span className="shrink-0 w-9 @xl:w-16 font-display font-semibold text-foreground/40 text-lg @xl:text-3xl tabular-nums">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                )}
                <TextContent
                  content={item.title}
                  className="text-foreground font-display font-medium uppercase text-xl @xl:text-4xl leading-tight tracking-tight"
                  data-content-keys={[`items.rows.${index}.title`]}
                />
              </div>
              <TextContent
                content={item.note}
                className={[
                  "text-muted text-xs @xl:text-lg font-normal leading-snug @xl:ml-auto @xl:text-right @xl:max-w-[32ch]",
                  showNumbers ? "pl-[52px] @xl:pl-0" : "",
                ].join(" ")}
                data-content-keys={[`items.rows.${index}.note`]}
              />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
