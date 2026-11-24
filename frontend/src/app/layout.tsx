import type { Metadata } from "next";
import "../styles/globals.css";
import AuroraBackground from "../components/ui/AuroraBackground";

export const metadata: Metadata = {
  title: "Swarm Intelligence GraphRAG",
  description: "Decentralized multi-hop reasoning over dynamic knowledge graphs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuroraBackground />
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
