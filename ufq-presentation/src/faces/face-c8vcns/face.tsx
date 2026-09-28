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

export default function CoverImageFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col items-center"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />
      <Rivets />

      {/* Company name */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="mt-8 @xl:mt-16 text-center"
      >
        <div className="ind-stamp inline-flex items-center gap-2 bg-brand px-2.5 py-1 @xl:px-4 @xl:py-1.5">
          <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
            [
          </span>
          <TextContent
            content={blocks.company.content}
            className="font-display text-foreground text-xs @xl:text-base font-medium uppercase tracking-[0.28em] leading-none"
            data-content-keys={["company"]}
          />
          <span className="font-display text-foreground text-xs @xl:text-base font-semibold leading-none select-none">
            ]
          </span>
        </div>
      </motion.div>

      {/* Tagline */}
      <motion.div
        initial={{ opacity: 0, y: 20, filter: "blur(12px)" }}
        animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
        transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        className="mt-3 @xl:mt-6 text-center px-6"
      >
        <TextContent
          content={blocks.tagline.content}
          className="leading-[1.02] text-foreground font-display font-semibold uppercase text-5xl @xl:text-[110px]"
          data-content-keys={["tagline"]}
          style={{ letterSpacing: "-0.005em" }}
        />
      </motion.div>

      {/* Accent bar */}
      <motion.div
        className="mt-4 @xl:mt-8 h-1.5 @xl:h-2 w-24 @xl:w-40 bg-accent"
        initial={{ scaleX: 0 }}
        animate={inView ? { scaleX: 1 } : {}}
        transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
      />

      {/* Hero image peeking from bottom — duotone plate */}
      <motion.div
        initial={{ opacity: 0, y: 60 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 1.1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="relative mt-6 @xl:mt-14 w-[88%] @xl:w-[78%] flex-1 min-h-0 overflow-hidden bg-foreground border-2 border-b-0 border-foreground"
      >
        <img
          src={blocks.heroImage.src}
          alt=""
          className="w-full h-full object-cover object-top"
          style={{ filter: "grayscale(1) contrast(1.15) brightness(0.9)" }}
        />
        <div className="absolute inset-0 bg-foreground/25" />
        <div className="absolute inset-0 bg-brand/20 mix-blend-multiply" />
        <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3" />
      </motion.div>
    </div>
  );
}
