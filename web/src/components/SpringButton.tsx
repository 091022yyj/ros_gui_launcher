import { motion } from "framer-motion";
import { ReactNode } from "react";

interface SpringButtonProps {
  children: ReactNode;
  variant?: "primary" | "secondary" | "danger";
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

/** 弹簧按钮(自适应帧率) */
export function SpringButton({
  children,
  variant = "primary",
  onClick,
  disabled = false,
  className = "",
}: SpringButtonProps) {
  const variants = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    danger: "btn-danger",
  };

  return (
    <motion.button
      className={`${variants[variant]} ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}
      whileHover={disabled ? {} : { scale: 1.05 }}
      whileTap={disabled ? {} : { scale: 0.95 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </motion.button>
  );
}
