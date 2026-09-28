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

export default function ImageStatementFace() {
  const darken = (controls.overlayDarkness?.value ?? 55) / 100;
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-foreground font-body"
    >
      {/* Background image — duotone plate */}
      <img
        src={blocks.heroImage.src}
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
        style={{ filter: "grayscale(1) contrast(1.15) brightness(0.9)" }}
      />
      <div className="absolute inset-0 bg-brand/20 mix-blend-multiply" />

      {/* Darkening gradient for legibility */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(180deg, color-mix(in srgb, var(--foreground) ${darken * 20}%, transparent) 0%, color-mix(in srgb, var(--foreground) ${darken * 50}%, transparent) 55%, color-mix(in srgb, var(--foreground) ${darken * 100}%, transparent) 100%)`,
        }}
      />

      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />
      <Rivets />

      {/* Content bottom-left */}
      <div className="absolute inset-0 flex flex-col justify-end px-6 py-7 @xl:px-16 @xl:py-14">
        <motion.div
          initial={{ opacity: 0, y: 24, filter: "blur(12px)" }}
          animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="mb-3 @xl:mb-6 flex items-center gap-2 @xl:gap-3">
            <span className="h-2 w-2 @xl:h-3 @xl:w-3 bg-brand border-2 border-paper shrink-0" />
            <span className="h-1.5 @xl:h-2 w-16 @xl:w-32 bg-accent shrink-0" />
          </div>
          <TextContent
            content={blocks.title.content}
            className="[&_a]:underline [&_em]:italic [&_strong]:font-bold leading-[1.0] text-paper font-display font-semibold uppercase text-4xl @xl:text-8xl"
            data-content-keys={["title"]}
            style={{ letterSpacing: "-0.005em" }}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="mt-5 @xl:mt-9 max-w-[340px] @xl:max-w-5xl"
        >
          <TextContent
            content={blocks.subtitle.content}
            className="text-paper/85 text-sm @xl:text-2xl font-normal leading-snug"
            data-content-keys={["subtitle"]}
          />
        </motion.div>
      </div>
    </div>
  );
}
