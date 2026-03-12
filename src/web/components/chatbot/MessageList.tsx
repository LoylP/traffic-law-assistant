import { useEffect, useRef } from "react";
import { Compass, Lightbulb } from "lucide-react";

import { Message } from "@/types/chat";

import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

type MessageListProps = {
  messages: Message[];
  isTyping: boolean;
};

export function MessageList({ messages, isTyping }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    containerRef.current?.scrollTo({
      top: containerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="relative z-10 min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4 sm:px-6"
    >
      {messages.length === 0 && !isTyping && (
        <div className="animate-message-in rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-600">
          <p className="mb-2 inline-flex items-center gap-1.5 font-semibold text-slate-700">
            <Compass size={16} />
            Sẵn sàng tra cứu luật giao thông
          </p>
          <p className="inline-flex items-center gap-1.5">
            <Lightbulb size={14} />
            Bắt đầu bằng một câu hỏi như: &quot;Mức phạt vượt đèn đỏ là bao nhiêu?&quot;
            hoặc chọn gợi ý phía dưới.
          </p>
        </div>
      )}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isTyping && <TypingIndicator />}
    </div>
  );
}
