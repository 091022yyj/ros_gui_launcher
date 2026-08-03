import { motion } from "framer-motion";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  strong?: boolean;
}

/** 液态玻璃卡片 */
export function GlassCard({ children, className = "", strong = false }: GlassCardProps) {
  return (
    <motion.div
      className={`${strong ? "glass-strong" : "glass glass-hover"} p-6 ${className}`}
      whileHover={{ y: -3, scale: 1.005 }}
      whileTap={{ scale: 0.995 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      {children}
    </motion.div>
  );
}
