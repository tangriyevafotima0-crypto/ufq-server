import React, { useRef } from "react";
import { motion, useInView } from "motion/react";
import { blocks } from "./face.content.json";
import { controls } from "./face.controls.json";
import { TextContent } from "@/components/ui/text-content";
import MasonryColumn from "./components/MasonryColumn";
import "./face.css";

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

export default function OverviewSplitFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });
  const speed = controls.scrollSpeed?.value ?? 26;

  const images = blocks.gallery.rows.map((r) => r.image).filter((img) => img?.src);
  // Split images across two columns moving in opposite directions.
  // With few images, cycle them (offset per column) so both tracks stay full
  // and a column never stacks the same image back-to-back.
  const MIN_PER_COL = 4;
  let colA: typeof images = [];
  let colB: typeof images = [];
  if (images.length >= MIN_PER_COL * 2) {
    colA = images.filter((_, i) => i % 2 === 0);
    colB = images.filter((_, i) => i % 2 === 1);
  } else if (images.length > 0) {
    const offset = Math.max(1, Math.floor(images.length / 2));
    colA = Array.from({ length: MIN_PER_COL }, (_, i) => images[i % images.length]);
    colB = Array.from({ length: MIN_PER_COL }, (_, i) => images[(i + offset) % images.length]);
  }

  return (
    <div
      ref={ref}
      className="relative w-full h-full overflow-hidden bg-background font-body flex flex-col @xl:flex-row"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-40" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-30" />

      {/* Left: text column */}
      <div className="relative flex w-full @xl:w-1/2 flex-col justify-between bg-surface px-6 py-8 @xl:px-16 @xl:py-16 order-2 @xl:order-1">
        <Rivets />
        {/* Company name */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="inline-flex items-center gap-2">
            <span className="font-display text-foreground/60 text-xs @xl:text-base font-semibold leading-none select-none">
              [
            </span>
            <TextContent
              content={blocks.company.content}
              className="font-display text-foreground/60 text-xs @xl:text-base font-medium uppercase tracking-[0.28em] leading-none"
              data-content-keys={["company"]}
            />
            <span className="font-display text-foreground/60 text-xs @xl:text-base font-semibold leading-none select-none">
              ]
            </span>
          </div>
        </motion.div>

        {/* Title + Body grouped together */}
        <div className="mt-6 @xl:mt-0">
          {/* Title */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            <TextContent
              content={blocks.titleLine1.content}
              className="font-display font-semibold uppercase leading-[1.0] text-foreground text-4xl @xl:text-8xl"
              data-content-keys={["titleLine1"]}
              style={{ letterSpacing: "-0.005em" }}
            />
            <TextContent
              content={blocks.titleLine2.content}
              className="font-display font-semibold uppercase leading-[1.0] text-steel-dark text-4xl @xl:text-8xl"
              data-content-keys={["titleLine2"]}
              style={{ letterSpacing: "-0.005em" }}
            />
            <motion.div
              className="mt-4 @xl:mt-6 h-1.5 @xl:h-2 w-24 @xl:w-40 bg-accent origin-left"
              initial={{ scaleX: 0 }}
              animate={inView ? { scaleX: 1 } : {}}
              transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
            />
          </motion.div>

          {/* Body */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 1, delay: 0.45 }}
            className="mt-5 @xl:mt-8 max-w-md @xl:max-w-xl"
          >
            <TextContent
              content={blocks.body.content}
              className="text-muted text-sm @xl:text-2xl font-normal leading-relaxed"
              data-content-keys={["body"]}
            />
          </motion.div>
        </div>
      </div>

      {/* Right: infinite masonry */}
      <motion.div
        initial={{ opacity: 0, filter: "blur(12px)" }}
        animate={inView ? { opacity: 1, filter: "blur(0px)" } : {}}
        transition={{ duration: 1, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
        className="relative w-full @xl:w-1/2 h-1/2 @xl:h-full p-6 @xl:p-16 order-1 @xl:order-2"
      >
        {images.length > 0 ? (
          <>
            <div className="masonry-mask ind-photo flex h-full gap-4 @xl:gap-6">
              <MasonryColumn
                images={colA}
                direction="up"
                duration={speed}
              />
              <MasonryColumn
                images={colB}
                direction="down"
                duration={speed * 1.25}
              />
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center bg-surface">
            <span className="text-muted text-sm @xl:text-base">Add images to the gallery</span>
          </div>
        )}
      </motion.div>
    </div>
  );
}
