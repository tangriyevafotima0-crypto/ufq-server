import "./face.css";
import React, { useRef, useState } from "react";
import { motion, useInView } from "motion/react";
import { Plus } from "lucide-react";
import { blocks } from "./face.content.json";
import { TextContent } from "@/components/ui/text-content";

const EASE = [0.22, 1, 0.36, 1] as const;

export default function FaqGridFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqs = blocks.faqs.rows.slice(0, 5);
  const cells = [{ kind: "title" as const }, ...faqs.map((f) => ({ kind: "faq" as const, faq: f }))];

  // Fill up to 6 cells for a consistent 3x2 grid on desktop
  const displayCells = [...cells];
  while (displayCells.length < 6) {
    displayCells.push({ kind: "empty" as const });
  }

  const toggleFaq = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div
      ref={ref}
      className="faq-grid-container relative w-full h-full overflow-y-auto @xl:overflow-hidden bg-background font-body flex flex-col @xl:grid @xl:grid-cols-3 @xl:grid-rows-2"
    >
      <div className="ind-noise pointer-events-none absolute inset-0 z-30" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-30" />

      {displayCells.map((cell, i) => {
        const col = i % 3;
        const row = Math.floor(i / 3);
        const faqIndex = i - 1;
        const isOpen = openIndex === i;

        if (cell.kind === "empty") {
          return (
            <div
              key={i}
              className={[
                "hidden @xl:block border-line",
                col > 0 ? "@xl:border-l-2" : "",
                row > 0 ? "@xl:border-t-2" : "",
              ].join(" ")}
            />
          );
        }

        return (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 0.7, delay: i * 0.08, ease: EASE }}
            onClick={() => cell.kind === "faq" && toggleFaq(i)}
            className={[
              "relative flex flex-col px-4 py-3 @xl:px-12 @xl:py-10 border-line transition-colors duration-300",
              cell.kind === "faq" ? "cursor-pointer @xl:cursor-default" : "mb-auto @xl:mb-0",
              // mobile: single column, divider above every cell except the first
              i > 0 && cell.kind !== "title" ? "border-t-2" : "",
              // desktop: reset mobile borders, then apply grid dividers
              "@xl:border-t-0 @xl:mb-0",
              col > 0 ? "@xl:border-l-2" : "",
              row > 0 ? "@xl:border-t-2" : "",
            ].join(" ")}
          >
            {cell.kind === "title" ? (
              <>
                <TextContent
                  content={blocks.title.content}
                  className="font-display font-semibold uppercase text-4xl @xl:text-7xl text-foreground tracking-tight"
                  data-content-keys={["title"]}
                />
                <span className="mt-4 @xl:mt-6 h-1.5 @xl:h-2 w-16 @xl:w-24 bg-accent" />
              </>
            ) : (
              <>
                <div className="flex items-center justify-between gap-4">
                  <TextContent
                    content={cell.faq!.question}
                    className="font-display font-medium uppercase text-base @xl:text-4xl text-foreground leading-tight tracking-tight"
                    data-content-keys={[`faqs.rows.${faqIndex}.question`]}
                  />
                  <div
                    className={[
                      "shrink-0 @xl:hidden transition-transform duration-300",
                      isOpen ? "rotate-45" : "rotate-0",
                    ].join(" ")}
                  >
                    <Plus size={20} className="text-muted" />
                  </div>
                </div>

                <div
                  className={[
                    "faq-answer-enter",
                    isOpen ? "faq-answer-active" : "",
                  ].join(" ")}
                >
                  <div className="faq-answer-inner">
                    <TextContent
                      content={cell.faq!.answer}
                      className="mt-3 @xl:mt-auto text-sm @xl:text-xl font-light text-muted leading-snug pt-4 @xl:pt-8"
                      data-content-keys={[`faqs.rows.${faqIndex}.answer`]}
                    />
                  </div>
                </div>
              </>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
