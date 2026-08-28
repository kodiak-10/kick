"use client";

import { motion } from "framer-motion";

const halos = [
  {
    className:
      "left-[-12%] top-[4%] h-[20rem] w-[20rem] bg-[rgba(132,150,176,0.15)] blur-[120px]",
    duration: 18,
    shiftX: 18,
    shiftY: 26,
    scale: 1.08
  },
  {
    className:
      "right-[-8%] top-[22%] h-[18rem] w-[18rem] bg-[rgba(199,181,151,0.12)] blur-[120px]",
    duration: 22,
    shiftX: -20,
    shiftY: 18,
    scale: 1.12
  },
  {
    className:
      "left-1/2 top-[66%] h-[22rem] w-[22rem] -translate-x-1/2 bg-[rgba(160,165,175,0.08)] blur-[140px]",
    duration: 25,
    shiftX: 0,
    shiftY: -24,
    scale: 1.1
  }
];

const particles = [
  { top: "14%", left: "12%", size: 4, duration: 10, delay: 0 },
  { top: "18%", left: "80%", size: 3, duration: 12, delay: 1.4 },
  { top: "28%", left: "58%", size: 2, duration: 9, delay: 0.8 },
  { top: "35%", left: "18%", size: 3, duration: 11, delay: 2.2 },
  { top: "44%", left: "88%", size: 4, duration: 13, delay: 0.4 },
  { top: "52%", left: "42%", size: 3, duration: 8, delay: 1.6 },
  { top: "60%", left: "72%", size: 2, duration: 10, delay: 0.2 },
  { top: "68%", left: "16%", size: 4, duration: 14, delay: 1.1 },
  { top: "74%", left: "54%", size: 3, duration: 9, delay: 1.9 },
  { top: "82%", left: "84%", size: 2, duration: 11, delay: 0.6 }
];

export function FloatingBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      {halos.map((halo) => (
        <motion.div
          key={halo.className}
          animate={{
            x: [0, halo.shiftX, 0],
            y: [0, halo.shiftY, 0],
            scale: [1, halo.scale, 1]
          }}
          transition={{
            duration: halo.duration,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut"
          }}
          className={`absolute rounded-full ${halo.className}`}
        />
      ))}

      {particles.map((particle) => (
        <motion.span
          key={`${particle.left}-${particle.top}`}
          style={{
            left: particle.left,
            top: particle.top,
            width: particle.size,
            height: particle.size
          }}
          className="absolute rounded-full bg-white/70 shadow-[0_0_14px_rgba(255,255,255,0.5)]"
          animate={{
            y: [0, -18, 0],
            x: [0, 6, 0],
            opacity: [0.12, 0.48, 0.14],
            scale: [1, 1.2, 1]
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut"
          }}
        />
      ))}

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_40%)]" />
      <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(rgba(255,255,255,0.55)_0.45px,transparent_0.45px)] [background-size:22px_22px] [mask-image:linear-gradient(180deg,white,transparent_82%)]" />
    </div>
  );
}
