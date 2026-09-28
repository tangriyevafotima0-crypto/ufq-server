import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { ArrowRight } from "lucide-react";
import { blocks } from "./face.content.json";
import { TextContent } from "@/components/ui/text-content";

const EASE = [0.22, 1, 0.36, 1] as const;

export default function ProcessStepsFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  const steps = blocks.steps.rows;

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      <div className="relative flex-1 min-h-0 flex flex-col px-6 pt-9 pb-8 @xl:px-16 @xl:pt-16 @xl:pb-14">
        {/* Eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex items-center gap-2 @xl:gap-3"
        >
          <span className="h-2 w-2 @xl:h-3 @xl:w-3 bg-brand border-2 border-foreground shrink-0" />
          <TextContent
            content={blocks.eyebrow.content}
            className="font-display text-foreground/60 text-xs @xl:text-base font-medium uppercase tracking-[0.28em]"
            data-content-keys={["eyebrow"]}
          />
        </motion.div>

        {/* Statement */}
        <motion.div
          initial={{ opacity: 0, scale: 1.03 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.45, delay: 0.12, ease: "easeOut" }}
          className="mt-4 @xl:mt-8"
        >
          <TextContent
            content={blocks.statement.content}
            className="text-foreground font-display font-semibold uppercase leading-[1.12] text-2xl @xl:text-6xl max-w-6xl"
            data-content-keys={["statement"]}
            style={{ letterSpacing: "-0.005em" }}
          />
          <motion.div
            className="mt-4 @xl:mt-6 h-1.5 @xl:h-2 w-24 @xl:w-36 bg-accent origin-left"
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
          />
        </motion.div>

        {/* Steps */}
        <div className="mt-auto pt-8 @xl:pt-12 border-t-2 border-line">
          <div className="flex flex-col @xl:flex-row items-start @xl:justify-start gap-4 @xl:gap-0">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.6, delay: 0.4 + index * 0.12, ease: EASE }}
                  className="flex flex-col"
                >
                  <TextContent
                    content={step.number}
                    className="text-foreground font-display font-semibold text-4xl @xl:text-7xl leading-none tabular-nums"
                    data-content-keys={[`steps.rows.${index}.number`]}
                  />
                  <TextContent
                    content={step.label}
                    className="mt-3 @xl:mt-6 font-display text-muted text-[10px] @xl:text-base font-medium uppercase tracking-[0.18em]"
                    data-content-keys={[`steps.rows.${index}.label`]}
                  />
                </motion.div>

                {index < steps.length - 1 && (
                  <motion.div
                    initial={{ opacity: 0, scaleX: 0 }}
                    animate={inView ? { opacity: 1, scaleX: 1 } : {}}
                    transition={{ duration: 0.5, delay: 0.5 + index * 0.12, ease: EASE }}
                    style={{ transformOrigin: "left" }}
                    className="flex items-center justify-center px-0 @xl:px-12 mt-0 @xl:mt-8"
                  >
                    <ArrowRight
                      className="text-accent w-5 h-5 @xl:w-10 @xl:h-10 rotate-90 @xl:rotate-0"
                      strokeWidth={2}
                    />
                  </motion.div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
