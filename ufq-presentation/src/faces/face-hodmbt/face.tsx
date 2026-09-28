import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { blocks } from "./face.content.json";
import { TextContent } from "@/components/ui/text-content";

const EASE = [0.22, 1, 0.36, 1] as const;

export default function FeatureCardsFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      <div className="relative flex-1 min-h-0 flex flex-col px-6 pt-9 pb-8 @xl:px-16 @xl:pt-16 @xl:pb-14">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="shrink-0"
        >
          <div className="flex items-center gap-2 @xl:gap-3">
            <span className="h-2 w-2 @xl:h-3 @xl:w-3 bg-brand border-2 border-foreground shrink-0" />
            <TextContent
              content={blocks.label.content}
              className="font-display text-foreground/60 text-xs @xl:text-base font-medium uppercase tracking-[0.28em]"
              data-content-keys={["label"]}
            />
          </div>
          <TextContent
            content={blocks.title.content}
            className="mt-3 @xl:mt-5 font-display font-semibold uppercase leading-[1.02] text-foreground text-4xl @xl:text-7xl"
            data-content-keys={["title"]}
            style={{ letterSpacing: "-0.005em" }}
          />
          <motion.div
            className="mt-3 @xl:mt-5 h-1.5 @xl:h-2 w-16 @xl:w-24 bg-accent origin-left"
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          />
        </motion.div>

        {/* Cards */}
        <div className="mt-8 @xl:mt-12 flex-1 min-h-0 grid grid-cols-1 @xl:grid-cols-4 gap-[2px] bg-line border-2 border-line">
          {blocks.cards.rows.map((card, index) => (
            <motion.div
              key={card.id}
              initial={{ opacity: 0, y: 28 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.1, ease: EASE }}
              className="relative bg-surface p-5 @xl:p-8 flex flex-col justify-between"
            >
              <span className="font-display font-semibold text-steel-dark text-2xl @xl:text-4xl tabular-nums">
                {card.index}
              </span>
              <div>
                <TextContent
                  content={card.title}
                  className="text-foreground font-display font-medium uppercase text-lg @xl:text-3xl"
                  data-content-keys={[`cards.rows.${index}.title`]}
                />
                <TextContent
                  content={card.description}
                  className="mt-2 @xl:mt-4 text-muted text-xs @xl:text-lg font-normal leading-relaxed"
                  data-content-keys={[`cards.rows.${index}.description`]}
                />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
