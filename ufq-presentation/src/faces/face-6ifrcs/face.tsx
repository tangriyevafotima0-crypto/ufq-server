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

export default function ImageOverlayCoverFace() {
  const darken = (controls.imageDarken?.value ?? 35) / 100;
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-foreground font-body"
    >
      {/* Full-bleed duotone background image */}
      <motion.img
        src={blocks.heroImage.src}
        alt=""
        initial={{ scale: 1.08, opacity: 0 }}
        animate={inView ? { scale: 1, opacity: 1 } : {}}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        className="absolute inset-0 w-full h-full object-cover"
        style={{ filter: "grayscale(1) contrast(1.15) brightness(0.9)" }}
      />
      {/* Darkening overlay (opacity from controls.imageDarken) */}
      <div className="absolute inset-0 bg-foreground" style={{ opacity: darken }} />
      {/* Brand duotone wash */}
      <div className="absolute inset-0 bg-brand/20 mix-blend-multiply" />
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />
      <Rivets />

      {/* Company name top-left */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="absolute top-8 left-6 @xl:top-14 @xl:left-16 z-10"
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

      {/* Tagline top-left */}
      <motion.div
        initial={{ opacity: 0, y: 20, filter: "blur(12px)" }}
        animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
        transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        className="absolute top-20 left-6 @xl:top-32 @xl:left-16 z-10"
      >
        <TextContent
          content={blocks.taglineLine1.content}
          className="font-display font-semibold uppercase leading-[1.0] text-paper text-4xl @xl:text-[96px]"
          data-content-keys={["taglineLine1"]}
          style={{
            letterSpacing: "-0.005em",
          }}
        />
        <div className="mt-4 @xl:mt-7 h-1.5 @xl:h-2 w-24 @xl:w-40 bg-accent" />
      </motion.div>

      {/* Subtitle bottom-left */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 1, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="absolute bottom-8 left-6 @xl:bottom-14 @xl:left-16 pr-6 z-10"
      >
        <TextContent
          content={blocks.subtitle.content}
          className="text-paper/85 text-sm @xl:text-2xl font-normal leading-snug"
          data-content-keys={["subtitle"]}
        />
      </motion.div>
    </div>
  );
}
