import { cn } from "../../lib/utils";
import React from "react";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" };

export function GlassButton({ variant = "primary", className, children, ...rest }: Props) {
  return (
    <button
      className={cn(
        "rounded-xl px-4 py-2 text-sm font-medium transition-all duration-200 border",
        variant === "primary"
          ? "bg-cyan-400/10 border-cyan-400/40 text-cyan-100 hover:bg-cyan-400/20 hover:shadow-aurora-glow"
          : "bg-white/5 border-white/10 text-slate-200 hover:border-cyan-500/30",
        "disabled:opacity-40 disabled:pointer-events-none",
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
