import { cn } from "../../lib/utils";
import React from "react";

export function GlassCard({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("glass-card p-4", className)} {...rest}>
      {children}
    </div>
  );
}
