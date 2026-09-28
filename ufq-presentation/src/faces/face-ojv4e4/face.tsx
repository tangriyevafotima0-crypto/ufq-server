import "./face.css";
import React, { useRef, useState, useEffect } from "react";
import { motion, useInView } from "motion/react";
import { ChevronRight, ChevronDown } from "lucide-react";
import { blocks } from "./face.content.json";
import { controls } from "./face.controls.json";
import { TextContent } from "@/components/ui/text-content";
import { getComponentPointerPoint } from "@/components/ui/pointer-events";

export default function TimelineFace() {
  const ref = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });

  const colWidth = controls.columnWidth?.value ?? 460;

  const rows = blocks.milestones.rows;

  // Detect portrait (mobile) orientation from the slide container itself.
  const [isVertical, setIsVertical] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setIsVertical(el.clientHeight > el.clientWidth);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Edge fade visibility
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const updateEdges = () => {
    const el = scrollRef.current;
    if (!el) return;
    if (isVertical) {
      setAtStart(el.scrollTop <= 4);
      setAtEnd(el.scrollTop >= el.scrollHeight - el.clientHeight - 4);
    } else {
      setAtStart(el.scrollLeft <= 4);
      setAtEnd(el.scrollLeft >= el.scrollWidth - el.clientWidth - 4);
    }
  };

  useEffect(() => {
    updateEdges();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVertical]);

  // Drag-to-scroll for mouse/pen
  const drag = useRef<{ start: number; startScroll: number } | null>(null);
  const handlePointerDown = (e: React.PointerEvent) => {
    const el = scrollRef.current;
    if (!el) return;
    const p = getComponentPointerPoint({ event: e });
    drag.current = {
      start: isVertical ? p.y : p.x,
      startScroll: isVertical ? el.scrollTop : el.scrollLeft,
    };
    el.setPointerCapture(e.pointerId);
  };
  const handlePointerMove = (e: React.PointerEvent) => {
    if (!drag.current || !scrollRef.current) return;
    const p = getComponentPointerPoint({ event: e });
    const now = isVertical ? p.y : p.x;
    if (isVertical) {
      scrollRef.current.scrollTop = drag.current.startScroll - (now - drag.current.start);
    } else {
      scrollRef.current.scrollLeft = drag.current.startScroll - (now - drag.current.start);
    }
  };
  const handlePointerUp = () => {
    drag.current = null;
  };

  const scrollToEnd = () => {
    const el = scrollRef.current;
    if (!el) return;
    if (isVertical) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else {
      el.scrollTo({ left: el.scrollWidth, behavior: "smooth" });
    }
  };

  return (
    <div ref={ref} className="relative w-full h-full overflow-hidden bg-background font-body">
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-40" />
      <div className="ind-noise pointer-events-none absolute inset-0 z-40" />

      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: 16, filter: "blur(10px)" }}
        animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="absolute top-2 left-0 right-0 @xl:right-auto z-30 px-6 pt-6 pb-4 @xl:top-20 @xl:left-16 @xl:px-0 @xl:pt-0 @xl:pb-0 @xl:pr-6 bg-background @xl:bg-transparent"
      >
        <TextContent
          content={blocks.title.content}
          className="text-foreground font-display font-semibold uppercase leading-[0.98] text-4xl @xl:text-8xl"
          data-content-keys={["title"]}
          style={{ letterSpacing: "-0.005em" }}
        />
        <div className="mt-3 @xl:mt-5 h-1.5 @xl:h-2 w-20 @xl:w-32 bg-accent" />
      </motion.div>

      {/* Scroll track */}
      <div
        ref={scrollRef}
        onScroll={updateEdges}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className={`absolute inset-x-0 bottom-0 top-2 @xl:top-3 no-scrollbar cursor-grab active:cursor-grabbing ${
          isVertical
            ? "overflow-y-auto overflow-x-hidden touch-pan-y"
            : "overflow-x-auto overflow-y-hidden touch-pan-x"
        }`}
      >
        {isVertical ? (
          /* ===== Vertical (mobile) layout ===== */
          <div className="relative flex flex-col pt-32 px-6 pb-10">
            {/* Vertical spine */}
            <div className="pointer-events-none absolute left-6 top-32 bottom-10 w-0.5 bg-foreground/30" />
            {rows.map((row, i) => (
              <motion.div
                key={row.id}
                initial={{ opacity: 0, y: 28 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{
                  duration: 0.55,
                  delay: 0.15 + i * 0.1,
                  ease: "easeOut",
                }}
                className="relative pl-6 pb-9"
              >
                {/* Node on the spine */}
                <div className="absolute left-0 top-1.5 -translate-x-1/2 w-2.5 h-2.5 bg-brand border-2 border-foreground ring-4 ring-background" />
                <TextContent
                  content={row.date}
                  className="text-foreground/60 font-display uppercase tracking-[0.14em] text-xs @xl:text-base font-medium"
                  data-content-keys={[`milestones.rows.${i}.date`]}
                />
                <div className="mt-1.5">
                  <span className="ind-stamp inline-block bg-brand px-2.5 py-1 text-foreground font-display uppercase tracking-[0.14em] text-[11px] @xl:text-[15px] font-medium">
                    <TextContent
                      content={row.label}
                      data-content-keys={[`milestones.rows.${i}.label`]}
                    />
                  </span>
                </div>
                <TextContent
                  content={row.body1}
                  className="mt-3 text-muted text-sm @xl:text-lg font-normal leading-snug"
                  data-content-keys={[`milestones.rows.${i}.body1`]}
                />
                <TextContent
                  content={row.body2}
                  className="mt-2 text-muted text-sm @xl:text-lg font-normal leading-snug"
                  data-content-keys={[`milestones.rows.${i}.body2`]}
                />
              </motion.div>
            ))}
          </div>
        ) : (
          /* ===== Horizontal (desktop) layout ===== */
          <div
            className="relative flex h-full items-stretch pt-44 @xl:pt-60 pb-6 @xl:pb-9 pl-6 @xl:pl-16"
            style={{ width: "max-content" }}
          >
            <div
              className="pointer-events-none absolute bottom-0 left-6 @xl:left-16 right-0 h-4 @xl:h-6"
              style={{
                backgroundImage: `repeating-linear-gradient(to right, var(--foreground) 0, var(--foreground) 2px, transparent 2px, transparent ${colWidth / 10}px)`,
                opacity: 0.35,
              }}
            />
            {rows.map((row, i) => (
              <motion.div
                key={row.id}
                initial={{ opacity: 0, y: 28 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{
                  duration: 0.55,
                  delay: 0.15 + i * 0.12,
                  ease: "easeOut",
                }}
                className="relative h-full flex flex-col pl-5 @xl:pl-8 pr-8 @xl:pr-16 pb-8 @xl:pb-14"
                style={{ width: colWidth }}
              >
                <div className="absolute left-0 top-0 bottom-8 @xl:bottom-14 w-0.5 bg-foreground/30" />

                <div>
                  <span className="ind-stamp inline-block bg-brand px-2.5 py-1 @xl:px-3 @xl:py-1.5 text-foreground font-display uppercase tracking-[0.14em] text-[11px] @xl:text-base font-medium">
                    <TextContent
                      content={row.label}
                      data-content-keys={[`milestones.rows.${i}.label`]}
                    />
                  </span>
                  <TextContent
                    content={row.body1}
                    className="mt-4 @xl:mt-6 text-muted text-sm @xl:text-2xl font-normal leading-snug"
                    data-content-keys={[`milestones.rows.${i}.body1`]}
                  />
                  <TextContent
                    content={row.body2}
                    className="mt-3 @xl:mt-5 text-muted text-sm @xl:text-2xl font-normal leading-snug"
                    data-content-keys={[`milestones.rows.${i}.body2`]}
                  />
                </div>

                <div className="mt-auto">
                  <TextContent
                    content={row.date}
                    className="text-foreground font-display font-semibold uppercase text-lg @xl:text-4xl"
                    data-content-keys={[`milestones.rows.${i}.date`]}
                    style={{ letterSpacing: "-0.005em" }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Edge gradient fades */}
      {isVertical ? (
        <>
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-24 z-20 transition-opacity duration-300"
            style={{
              opacity: atEnd ? 0 : 1,
              background:
                "linear-gradient(to top, var(--background), var(--background) 30%, transparent)",
            }}
          />
        </>
      ) : (
        <>
          <div
            className="pointer-events-none absolute inset-y-0 left-0 w-40 @xl:w-80 z-20 transition-opacity duration-300"
            style={{
              opacity: atStart ? 0 : 1,
              background:
                "linear-gradient(to right, var(--background), var(--background) 40%, transparent)",
            }}
          />
          <div
            className="pointer-events-none absolute inset-y-0 right-0 w-40 @xl:w-80 z-20 transition-opacity duration-300"
            style={{
              opacity: atEnd ? 0 : 1,
              background:
                "linear-gradient(to left, var(--background), var(--background) 40%, transparent)",
            }}
          />
        </>
      )}

      {/* "More" cue — click to jump to the last item */}
      <motion.button
        type="button"
        onClick={scrollToEnd}
        aria-label="Scroll to last milestone"
        className={`ind-stamp absolute z-30 flex items-center justify-center bg-brand hover:bg-accent p-2 @xl:p-3 transition-opacity duration-300 ${
          isVertical
            ? "bottom-4 left-1/2 -translate-x-1/2"
            : "top-1/2 right-6 @xl:right-12 -translate-y-1/2"
        }`}
        style={{ opacity: atEnd ? 0 : 1, pointerEvents: atEnd ? "none" : "auto" }}
        animate={inView ? (isVertical ? { y: [0, 8, 0] } : { x: [0, 10, 0] }) : {}}
        transition={{ duration: 1.6, ease: "easeInOut", repeat: Infinity }}
      >
        {isVertical ? (
          <ChevronDown className="text-foreground w-6 h-6" />
        ) : (
          <ChevronRight className="text-foreground w-6 h-6 @xl:w-10 @xl:h-10" />
        )}
      </motion.button>
    </div>
  );
}
