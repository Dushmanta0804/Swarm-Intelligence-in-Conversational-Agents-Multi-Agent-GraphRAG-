"use client";
import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../lib/types";
import { MessageList } from "./MessageList";
import { QueryInput } from "./QueryInput";

export function ChatContainer({
  messages, loading, onAsk, onFocusNode,
}: {
  messages: ChatMessage[];
  loading: boolean;
  onAsk: (q: string) => void;
  onFocusNode: (n: string | null) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length]);
  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex-1 min-h-0">
        <MessageList messages={messages} onFocusNode={onFocusNode} />
      </div>
      <div ref={bottomRef} />
      <QueryInput onAsk={onAsk} loading={loading} />
    </div>
  );
}
