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

export default function CoverIndustrialFace() {
  const imageWidth = controls.imageWidth?.value ?? 45;
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col @xl:flex-row"
      style={{ ["--image-width" as string]: `${imageWidth}%` }}
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-20" />

      {/* Text side — stamped plate */}
      <div className="relative flex flex-1 min-w-0 flex-col bg-surface px-6 pt-9 pb-7 @xl:px-16 @xl:pt-20 @xl:pb-14">
        <Rivets />
        <div className="grid grid-cols-1 @xl:grid-cols-2 gap-6 @xl:gap-12 flex-1 min-h-0">
          {/* Column 1 */}
          <motion.div
            initial={{ opacity: 0, y: 22 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <TextContent
              content={blocks.headingLeft.content}
              className="font-display font-semibold uppercase leading-[1.05] text-foreground text-2xl @xl:text-5xl"
              data-content-keys={["headingLeft"]}
              style={{ letterSpacing: "-0.005em" }}
            />
            <motion.div
              className="mt-3 @xl:mt-5 h-1.5 @xl:h-2 w-16 @xl:w-24 bg-accent origin-left"
              initial={{ scaleX: 0 }}
              animate={inView ? { scaleX: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
            />
            <TextContent
              content={blocks.bodyLeft.content}
              className="mt-4 @xl:mt-7 text-muted text-xs @xl:text-lg font-normal leading-relaxed"
              data-content-keys={["bodyLeft"]}
            />
          </motion.div>

          {/* Column 2 */}
          <motion.div
            initial={{ opacity: 0, y: 22 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.12, ease: "easeOut" }}
          >
            <TextContent
              content={blocks.headingRight.content}
              className="font-display font-semibold uppercase leading-[1.05] text-foreground text-2xl @xl:text-5xl"
              data-content-keys={["headingRight"]}
              style={{ letterSpacing: "-0.005em" }}
            />
            <motion.div
              className="mt-3 @xl:mt-5 h-1.5 @xl:h-2 w-16 @xl:w-24 bg-accent origin-left"
              initial={{ scaleX: 0 }}
              animate={inView ? { scaleX: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.42, ease: "easeOut" }}
            />
            <TextContent
              content={blocks.bodyRight.content}
              className="mt-4 @xl:mt-7 text-muted text-xs @xl:text-lg font-normal leading-relaxed"
              data-content-keys={["bodyRight"]}
            />
          </motion.div>
        </div>

        {/* Footer — spec strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-6 @xl:mt-10"
        >
          <div className="flex items-center gap-2 @xl:gap-3">
            <span className="font-display text-foreground/60 text-[10px] @xl:text-lg font-semibold leading-none select-none">
              [
            </span>
            <TextContent
              content={blocks.footer.content}
              className="font-display text-foreground/60 text-[10px] @xl:text-lg font-medium uppercase tracking-[0.28em] leading-none whitespace-nowrap"
              data-content-keys={["footer"]}
            />
            <span className="font-display text-foreground/60 text-[10px] @xl:text-lg font-semibold leading-none select-none">
              ]
            </span>
            <span className="h-px flex-1 bg-foreground/30" />
            <span className="font-display text-foreground/50 text-[9px] @xl:text-base uppercase tracking-[0.3em] select-none">
              Spec 07-A
            </span>
          </div>
        </motion.div>
      </div>

      {/* Hazard tape divider */}
      <div className="ind-hazard h-2 @xl:h-auto @xl:w-3 shrink-0" />

      {/* Image side — duotone plate */}
      <motion.div
        initial={{ opacity: 0, y: 26 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.55, delay: 0.35, ease: "easeOut" }}
        className="ind-cover-image relative w-full h-48 @xl:h-full shrink-0 overflow-hidden"
      >
        <img
          src={blocks.image.src}
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

