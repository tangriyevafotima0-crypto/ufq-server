import "./face.css";
import React, { useRef, useState } from "react";
import { motion, useInView, AnimatePresence } from "motion/react";
import { Check } from "lucide-react";
import { blocks } from "./face.content.json";
import { TextContent } from "@/components/ui/text-content";
import { useFormPlugin } from "@/plugins/form";

type Fields = {
  fullName: string;
  email: string;
  company: string;
  role: string;
};

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

export default function RegistrationFace() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const form = useFormPlugin("registration");

  const [values, setValues] = useState<Fields>({
    fullName: "",
    email: "",
    company: "",
    role: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const update = (key: keyof Fields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || done) return;
    setSubmitting(true);
    try {
      await form.submit({ values });
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  };

  const inputCls =
    "w-full bg-transparent border-b border-line focus:border-accent outline-none text-foreground text-base @xl:text-2xl font-normal py-1 @xl:py-3 transition-colors placeholder:text-foreground/30";

  const fieldDefs: {
    key: keyof Fields;
    label: string;
    placeholder: string;
    type: string;
    contentKey: string;
  }[] = [
    { key: "fullName", label: blocks.nameLabel.content, placeholder: blocks.namePlaceholder.content, type: "text", contentKey: "nameLabel" },
    { key: "email", label: blocks.emailLabel.content, placeholder: blocks.emailPlaceholder.content, type: "email", contentKey: "emailLabel" },
    { key: "company", label: blocks.companyLabel.content, placeholder: blocks.companyPlaceholder.content, type: "text", contentKey: "companyLabel" },
    { key: "role", label: blocks.roleLabel.content, placeholder: blocks.rolePlaceholder.content, type: "text", contentKey: "roleLabel" },
  ];

  return (
    <div ref={ref} className="relative w-full h-full overflow-y-auto @xl:overflow-hidden bg-background font-body flex flex-col @xl:flex-row">
      <div className="ind-noise pointer-events-none absolute inset-0 z-40" />
      <div className="ind-hazard pointer-events-none absolute inset-x-0 top-0 h-2 @xl:h-3 z-30" />

      {/* Background image (fills canvas on mobile) */}
      <div className="absolute inset-0 shrink-0 @xl:relative @xl:w-[35%]">
        <ImageBg />
        <LeftContent inView={inView} desktop={false} />
      </div>

      {/* Hazard tape divider */}
      <div className="ind-hazard hidden @xl:block w-3 shrink-0 z-20" />

      {/* Form sheet */}
      <div className="relative flex-1 flex flex-col justify-end @xl:justify-center">
        <motion.div
          initial={{ y: "100%" }}
          animate={inView ? { y: 0 } : {}}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="relative bg-surface rounded-t-2xl @xl:rounded-none shadow-[0_-20px_40px_rgba(0,0,0,0.1)] @xl:shadow-none px-6 py-3 @xl:px-16 @xl:py-14 min-h-[65%] @xl:min-h-0 @xl:h-full reg-sheet flex items-center justify-center"
        >
          <Rivets />
          <div className="w-full max-w-[640px]">
            <AnimatePresence mode="wait">
              {done ? (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                  className="flex flex-col items-start text-center @xl:text-left items-center @xl:items-start"
                >
                  <div className="ind-stamp flex items-center justify-center w-12 h-12 @xl:w-16 @xl:h-16 bg-accent text-paper mb-5 @xl:mb-8">
                    <Check className="w-6 h-6 @xl:w-9 @xl:h-9" strokeWidth={2.5} />
                  </div>
                  <TextContent
                    content={blocks.successTitle.content}
                    className="font-display font-semibold uppercase text-foreground text-4xl @xl:text-7xl leading-[1.02]"
                    data-content-keys={["successTitle"]}
                    style={{ letterSpacing: "-0.005em" }}
                  />
                  <TextContent
                    content={blocks.successText.content}
                    className="mt-4 text-muted text-base @xl:text-2xl font-normal leading-snug"
                    data-content-keys={["successText"]}
                  />
                </motion.div>
              ) : (
                <motion.form
                  key="form"
                  onSubmit={handleSubmit}
                  initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
                  animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
                  transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                >
                  <TextContent
                    content={blocks.formHeading.content}
                    className="font-display font-semibold uppercase text-foreground text-2xl @xl:text-4xl mb-3 @xl:mb-10"
                    data-content-keys={["formHeading"]}
                    style={{ letterSpacing: "-0.005em" }}
                  />

                  <div className="flex flex-col gap-1 @xl:gap-7">
                    {fieldDefs.map((f) => (
                      <label key={f.key} className="block">
                        <TextContent
                          content={f.label}
                          className="font-display uppercase tracking-[0.18em] text-muted text-xs @xl:text-base font-medium block mb-1 @xl:mb-2"
                          data-content-keys={[f.contentKey]}
                        />
                        <input
                          type={f.type}
                          value={values[f.key]}
                          onChange={update(f.key)}
                          placeholder={f.placeholder}
                          required
                          className={inputCls}
                        />
                      </label>
                    ))}
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="ind-stamp mt-2 @xl:mt-12 w-full bg-foreground text-paper font-display uppercase tracking-[0.14em] text-base @xl:text-2xl font-medium py-3 @xl:py-5 transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    <TextContent
                      content={submitting ? "Submitting..." : blocks.submitText.content}
                      data-content-keys={["submitText"]}
                    />
                  </button>
                </motion.form>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function ImageBg() {
  return (
    <>
      <img
        src={blocks.bgImage.src}
        alt=""
        className="w-full h-full object-cover"
        style={{ filter: "grayscale(1) contrast(1.15) brightness(0.9)" }}
      />
      <div className="absolute inset-0 bg-foreground/55" />
      <div className="absolute inset-0 bg-brand/20 mix-blend-multiply" />
    </>
  );
}

function LeftContent({ inView, desktop }: { inView: boolean; desktop?: boolean }) {
  return (
    <div className="absolute inset-0 flex flex-col justify-start gap-6 @xl:gap-8 px-6 py-6 @xl:px-16 @xl:py-14">
      <Rivets />
      <motion.div
        initial={{ opacity: 0, y: 24, filter: "blur(12px)" }}
        animate={inView ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
        transition={{ duration: 1, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
      >
        <TextContent
          content={blocks.titleLine1.content}
          className="font-display font-semibold uppercase leading-[1.0] text-paper text-4xl @xl:text-8xl"
          data-content-keys={["titleLine1"]}
          style={{ letterSpacing: "-0.005em" }}
        />
        <TextContent
          content={blocks.titleLine2.content}
          className="font-display font-semibold uppercase leading-[1.0] text-paper text-4xl @xl:text-8xl"
          data-content-keys={["titleLine2"]}
          style={{ letterSpacing: "-0.005em" }}
        />
        {desktop && (
          <TextContent
            content={blocks.subtitle.content}
            className="mt-6 max-w-[440px] text-paper/70 text-base @xl:text-2xl font-normal leading-snug"
            data-content-keys={["subtitle"]}
          />
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ duration: 1, delay: 0.45 }}
      >
        <div className="inline-flex items-center gap-2">
          <span className="h-2 w-2 @xl:h-3 @xl:w-3 bg-brand border-2 border-paper shrink-0" />
          <TextContent
            content={blocks.footnote.content}
            className="font-display uppercase tracking-[0.28em] text-brand text-xs @xl:text-lg font-normal"
            data-content-keys={["footnote"]}
          />
        </div>
      </motion.div>
    </div>
  );
}
