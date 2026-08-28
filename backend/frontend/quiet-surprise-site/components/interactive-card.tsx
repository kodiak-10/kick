"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import type { CardDeck } from "@/lib/content";

type InteractiveCardProps = {
  deck: CardDeck;
  index: number;
};

const transition = {
  duration: 0.42,
  ease: [0.22, 1, 0.36, 1] as const
};

function pickNextIndex(total: number, current: number) {
  if (total <= 1) {
    return 0;
  }

  const next = Math.floor(Math.random() * total);

  if (current < 0) {
    return next;
  }

  return next === current ? (next + 1) % total : next;
}

export function InteractiveCard({ deck, index }: InteractiveCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const handleClick = () => {
    setIsOpen(true);
    setActiveIndex((current) => pickNextIndex(deck.items.length, isOpen ? current : -1));
  };

  return (
    <motion.button
      type="button"
      layout
      aria-expanded={isOpen}
      onClick={handleClick}
      whileTap={{ scale: 0.985 }}
      className={`glass-panel soft-outline group relative overflow-hidden p-5 text-left transition duration-300 sm:p-6 ${
        isOpen ? "bg-white/[0.075]" : "bg-white/[0.04]"
      }`}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.14),_transparent_56%)] opacity-0 transition duration-500 group-hover:opacity-100" />

      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] tracking-[0.28em] text-zinc-500">{deck.eyebrow}</p>
          <h3 className="mt-3 text-[1.35rem] font-medium tracking-[-0.03em] text-zinc-100">
            {deck.title}
          </h3>
        </div>
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.05] text-sm text-zinc-300">
          {isOpen ? "换" : `0${index + 1}`}
        </span>
      </div>

      <p className="relative mt-4 text-sm leading-6 text-zinc-400">{deck.hint}</p>

      <AnimatePresence mode="wait">
        {isOpen ? (
          <motion.div
            key={`${deck.title}-${activeIndex}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={transition}
            className="relative mt-5 border-t border-white/10 pt-5"
          >
            <p className="text-[15px] leading-7 text-zinc-100 sm:text-base">
              {deck.items[activeIndex]}
            </p>
            <p className="mt-4 text-[11px] tracking-[0.26em] text-zinc-500">
              再点一次，会换一句新的。
            </p>
          </motion.div>
        ) : (
          <motion.div
            key={`${deck.title}-placeholder`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={transition}
            className="relative mt-5 border-t border-white/10 pt-5"
          >
            <p className="text-[15px] leading-7 text-zinc-300/90 sm:text-base">
              这张卡现在还是合上的，轻点一下，它就会开口。
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.button>
  );
}
