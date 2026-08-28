"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

const transition = {
  duration: 0.36,
  ease: [0.22, 1, 0.36, 1] as const
};

export function EasterEggStar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed right-4 top-4 z-30 sm:right-6 sm:top-6">
      <motion.button
        type="button"
        aria-label="打开隐藏彩蛋"
        onClick={() => setIsOpen((value) => !value)}
        whileTap={{ scale: 0.96 }}
        className="glass-panel soft-outline flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.12] bg-white/[0.05] text-zinc-100"
      >
        <motion.span
          animate={{
            opacity: [0.5, 1, 0.5],
            scale: [1, 1.08, 1],
            rotate: [0, 5, -4, 0]
          }}
          transition={{
            duration: 3.6,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut"
          }}
        >
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4 fill-current"
            aria-hidden="true"
          >
            <path d="M12 2.8l1.87 5.14 5.47.44-4.22 3.53 1.35 5.3L12 14.14l-4.47 2.07 1.35-5.3-4.22-3.53 5.47-.44L12 2.8z" />
          </svg>
        </motion.span>
      </motion.button>

      <AnimatePresence>
        {isOpen ? (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 10, scale: 1 }}
            exit={{ opacity: 0, y: 0, scale: 0.98 }}
            transition={transition}
            className="glass-panel soft-outline absolute right-0 mt-2 w-64 rounded-[24px] px-4 py-4 text-sm leading-6 text-zinc-300"
          >
            隐藏彩蛋：
            <br />
            会点开这个角落的人，通常也会留意那些不怎么大声的细节。于是这颗小星星，算给细节控的额外奖励。
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
