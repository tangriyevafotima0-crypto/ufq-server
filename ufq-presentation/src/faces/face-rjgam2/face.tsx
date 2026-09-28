import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { ArrowRight } from "lucide-react";
import { blocks } from "./face.content.json";
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

export default function ProblemSolutionFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background text-foreground font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      <div className="relative flex-1 min-h-0 flex flex-col @xl:flex-row">
        {/* Problem */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="relative flex-1 min-w-0 flex flex-col justify-center items-center text-center bg-background px-6 pt-9 pb-8 @xl:px-16 @xl:py-14"
        >
          <Rivets />
          <div className="flex items-center justify-center gap-2 @xl:gap-3">
            <span className="font-display text-foreground/60 text-xs @xl:text-base font-semibold leading-none select-none">
              [
            </span>
            <TextContent
              content={blocks.problemLabel.content}
              className="font-display text-foreground/60 text-xs @xl:text-base font-medium uppercase tracking-[0.28em] leading-none"
              data-content-keys={["problemLabel"]}
            />
            <span className="font-display text-foreground/60 text-xs @xl:text-base font-semibold leading-none select-none">
              ]
            </span>
          </div>
          <TextContent
            content={blocks.problemTitle.content}
            className="mt-3 @xl:mt-6 font-display font-semibold uppercase leading-[1.05] text-foreground text-3xl @xl:text-6xl"
            data-content-keys={["problemTitle"]}
            style={{ letterSpacing: "-0.005em" }}
          />
          <TextContent
            content={blocks.problemBody.content}
            className="mt-4 @xl:mt-8 text-muted text-sm @xl:text-xl font-normal leading-relaxed max-w-[40ch]"
            data-content-keys={["problemBody"]}
          />
        </motion.div>

        {/* Hazard divider with arrow chip */}
        <div className="ind-hazard relative shrink-0 z-10 flex items-center justify-center h-2 @xl:h-auto @xl:w-3">
          <motion.div
            initial={{ opacity: 0, scale: 0.6 }}
            animate={inView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.35, ease: "easeOut" }}
            className="ind-stamp relative z-10 flex items-center justify-center size-10 @xl:size-14 bg-brand"
          >
            <ArrowRight className="size-4 @xl:size-6 text-foreground rotate-90 @xl:rotate-0" strokeWidth={2} />
          </motion.div>
        </div>

        {/* Solution */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
          className="relative flex-1 min-w-0 flex flex-col justify-center items-center text-center bg-surface px-6 py-8 @xl:px-16 @xl:py-14"
        >
          <Rivets />
          <div className="ind-stamp inline-flex items-center gap-2 bg-brand px-2.5 py-1 @xl:px-4 @xl:py-1.5">
            <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
              [
            </span>
            <TextContent
              content={blocks.solutionLabel.content}
              className="font-display text-foreground text-xs @xl:text-base font-medium uppercase tracking-[0.28em] leading-none"
              data-content-keys={["solutionLabel"]}
            />
            <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
              ]
            </span>
          </div>
          <TextContent
            content={blocks.solutionTitle.content}
            className="mt-3 @xl:mt-6 font-display font-semibold uppercase leading-[1.05] text-foreground text-3xl @xl:text-6xl"
            data-content-keys={["solutionTitle"]}
            style={{ letterSpacing: "-0.005em" }}
          />
          <TextContent
            content={blocks.solutionBody.content}
            className="mt-4 @xl:mt-8 text-foreground text-sm @xl:text-xl font-normal leading-relaxed max-w-[40ch]"
            data-content-keys={["solutionBody"]}
          />
        </motion.div>
      </div>
    </div>
  );
}
