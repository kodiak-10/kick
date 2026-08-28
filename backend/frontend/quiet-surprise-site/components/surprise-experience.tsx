"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRef, useState } from "react";
import { EasterEggStar } from "@/components/easter-egg-star";
import { FloatingBackdrop } from "@/components/floating-backdrop";
import { InteractiveCard } from "@/components/interactive-card";
import { cardDecks, footerEcho } from "@/lib/content";

const transition = {
  duration: 0.7,
  ease: [0.22, 1, 0.36, 1] as const
};

const heroNotes = [
  {
    label: "收件方式",
    value: "网页，不是那种随手转发的模板。"
  },
  {
    label: "气氛",
    value: "安静地偏心一下，不会太用力。"
  },
  {
    label: "备注",
    value: "不需要立刻回应，看完就已经足够。"
  }
];

export function SurpriseExperience() {
  const revealRef = useRef<HTMLElement | null>(null);
  const [isOpened, setIsOpened] = useState(false);
  const [hasFinished, setHasFinished] = useState(false);
  const [replaySeed, setReplaySeed] = useState(0);

  const scrollToReveal = () => {
    window.setTimeout(() => {
      revealRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    }, 260);
  };

  const handleOpen = () => {
    if (isOpened) {
      scrollToReveal();
      return;
    }

    setIsOpened(true);
    setHasFinished(false);
    scrollToReveal();
  };

  const handleReplay = () => {
    setIsOpened(false);
    setHasFinished(false);
    setReplaySeed((value) => value + 1);
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  };

  return (
    <div className="relative isolate overflow-hidden">
      <FloatingBackdrop />
      <EasterEggStar key={`egg-${replaySeed}`} />

      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 pb-16 pt-5 sm:px-6 sm:pb-20 lg:px-8">
        <section className="flex min-h-[94vh] items-center py-10 sm:py-16">
          <div className="grid w-full gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-end">
            <motion.div
              key={`hero-${replaySeed}`}
              initial={{ opacity: 0, y: 30, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={transition}
              className="glass-panel soft-outline relative overflow-hidden px-6 py-8 sm:px-8 sm:py-10 lg:px-10"
            >
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.12),_transparent_46%)]" />
              <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.05))] lg:block" />

              <div className="relative">
                <p className="section-label">私人数字小礼物</p>
                <h1 className="balanced-title mt-6 max-w-3xl text-[2.5rem] leading-[1.06] text-zinc-100 sm:text-[3.4rem] lg:text-[4.4rem]">
                  别紧张，这不是一个很严肃的网站。
                </h1>
                <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-300 sm:text-lg sm:leading-8">
                  只是觉得，普通消息有点配不上这次想给你的小惊喜。
                </p>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <motion.button
                    type="button"
                    onClick={handleOpen}
                    whileTap={{ scale: 0.98 }}
                    whileHover={{ y: -1 }}
                    className="primary-button w-full sm:w-auto"
                  >
                    {isOpened ? "已经点开了，继续往下看" : "那我点开看看"}
                  </motion.button>
                  <p className="text-sm leading-6 text-zinc-500">
                    不会跳出很夸张的东西，只是认真一点。
                  </p>
                </div>
              </div>
            </motion.div>

            <motion.aside
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transition, delay: 0.12 }}
              className="glass-panel soft-outline px-5 py-5 sm:px-6"
            >
              <p className="text-[11px] tracking-[0.28em] text-zinc-500">页面说明</p>
              <div className="mt-4 space-y-4">
                {heroNotes.map((note) => (
                  <div
                    key={note.label}
                    className="border-b border-white/[0.08] pb-4 last:border-b-0 last:pb-0"
                  >
                    <p className="text-sm text-zinc-500">{note.label}</p>
                    <p className="mt-1 text-sm leading-6 text-zinc-200">{note.value}</p>
                  </div>
                ))}
              </div>
            </motion.aside>
          </div>
        </section>

        <AnimatePresence mode="wait">
          {isOpened ? (
            <motion.div
              key={`opened-${replaySeed}`}
              initial={{ opacity: 0, y: 34 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 14 }}
              transition={transition}
              className="space-y-6 sm:space-y-8"
            >
              <motion.section
                ref={revealRef}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...transition, delay: 0.08 }}
                className="glass-panel soft-outline relative overflow-hidden px-6 py-7 sm:px-8 sm:py-8"
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.1),_transparent_48%)]" />

                <div className="relative">
                  <p className="section-label">惊喜揭晓</p>
                  <motion.h2
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...transition, delay: 0.14 }}
                    className="balanced-title mt-5 text-3xl leading-tight text-zinc-100 sm:text-4xl"
                  >
                    你已触发今日限定彩蛋。
                  </motion.h2>
                  <motion.p
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...transition, delay: 0.22 }}
                    className="mt-4 max-w-2xl text-base leading-7 text-zinc-300 sm:text-lg sm:leading-8"
                  >
                    而且，这个页面确实不是随手发出去的那种。
                  </motion.p>
                </div>
              </motion.section>

              <section className="space-y-5">
                <motion.div
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...transition, delay: 0.18 }}
                  className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
                >
                  <div>
                    <p className="section-label">互动卡片</p>
                    <h3 className="mt-4 text-2xl font-medium tracking-[-0.03em] text-zinc-100 sm:text-3xl">
                      下面这三张卡，各有一点偏心。
                    </h3>
                  </div>
                  <p className="max-w-md text-sm leading-6 text-zinc-500">
                    轻点一下会展开，再点一次会换一句。页面很安静，但不是没有反应。
                  </p>
                </motion.div>

                <div className="grid gap-4 md:grid-cols-3">
                  {cardDecks.map((deck, index) => (
                    <InteractiveCard
                      key={`${deck.title}-${replaySeed}`}
                      deck={deck}
                      index={index}
                    />
                  ))}
                </div>
              </section>

              <motion.section
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...transition, delay: 0.24 }}
                className="glass-panel soft-outline relative overflow-hidden px-6 py-7 sm:px-8 sm:py-8"
              >
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_32%,transparent)]" />

                <div className="relative">
                  <p className="section-label">结尾</p>
                  <p className="mt-5 max-w-3xl text-base leading-8 text-zinc-200 sm:text-lg">
                    做这个，没有什么标准答案。只是觉得，普通的消息，有点配不上这次想给你的感觉。
                  </p>

                  <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                    <motion.button
                      type="button"
                      onClick={() => setHasFinished(true)}
                      whileTap={{ scale: 0.98 }}
                      className="primary-button w-full sm:w-auto"
                    >
                      我看完了
                    </motion.button>
                    <motion.button
                      type="button"
                      onClick={handleReplay}
                      whileTap={{ scale: 0.98 }}
                      className="secondary-button w-full sm:w-auto"
                    >
                      再看一遍
                    </motion.button>
                  </div>

                  <AnimatePresence>
                    {hasFinished ? (
                      <motion.p
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 8 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="mt-5 max-w-2xl text-sm leading-7 text-zinc-400"
                      >
                        {footerEcho}
                      </motion.p>
                    ) : null}
                  </AnimatePresence>
                </div>
              </motion.section>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
