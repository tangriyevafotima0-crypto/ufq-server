import "./face.css";
import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
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

export default function SplitIndustrialFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      {/* Top: stamped editorial plate */}
      <div className="relative w-full flex-1 bg-surface px-6 pt-9 pb-6 @xl:px-16 @xl:pt-20 @xl:pb-12">
        <Rivets />
        <div className="flex h-full flex-col">
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
          </motion.div>

          <div className="mt-4 @xl:mt-8 flex flex-col @xl:flex-row flex-1 items-start justify-between gap-4 @xl:gap-6">
            <motion.div
              initial={{ opacity: 0, scale: 1.03 }}
              animate={inView ? { opacity: 1, scale: 1 } : {}}
              transition={{ duration: 0.45, delay: 0.12, ease: "easeOut" }}
            >
              <TextContent
                content={blocks.title.content}
                className="block font-display font-semibold uppercase leading-[1.02] text-foreground text-4xl @xl:text-8xl break-words"
                data-content-keys={["title"]}
                style={{ letterSpacing: "-0.005em" }}
              />
              <motion.div
                className="mt-4 @xl:mt-7 h-1.5 @xl:h-2 w-24 @xl:w-40 bg-accent origin-left"
                initial={{ scaleX: 0 }}
                animate={inView ? { scaleX: 1 } : {}}
                transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : {}}
              transition={{ duration: 0.6, delay: 0.35 }}
              className="shrink-0 @xl:text-right"
            >
              <TextContent
                content={blocks.aside.content}
                className="block text-muted text-sm @xl:text-2xl font-normal leading-snug"
                data-content-keys={["aside"]}
              />
              <div className="mt-3 @xl:mt-5 flex items-center justify-end gap-2">
                <span className="h-px w-10 @xl:w-16 bg-foreground/30" />
                <span className="font-display text-foreground/50 text-[9px] @xl:text-base uppercase tracking-[0.3em] select-none">
                  Spec 07-A
                </span>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Hazard tape divider */}
      <div className="ind-hazard h-2 @xl:h-3 shrink-0 z-10" />

      {/* Bottom: duotone image plate */}
      <motion.div
        initial={{ opacity: 0, y: 26 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.55, delay: 0.35, ease: "easeOut" }}
        className="relative w-full flex-1 overflow-hidden"
      >
        <img
          src={blocks.bgImage.src}
          alt=""
          className="w-full h-full object-cover"
          style={{ filter: "grayscale(1) contrast(1.15) brightness(0.9)" }}
        />
        <div className="absolute inset-0 bg-foreground/25" />
        <div className="absolute inset-0 bg-brand/20 mix-blend-multiply" />
        <Rivets />
      </motion.div>
    </div>
  );
}
