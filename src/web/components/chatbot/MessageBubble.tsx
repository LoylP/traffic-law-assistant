import { Bot, Clock3, UserRound } from "lucide-react";

import { Message } from "@/types/chat";

type MessageBubbleProps = {
  message: Message;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`animate-message-in flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[88%] items-start gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
        <div
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
            isUser ? "bg-slate-200 text-slate-700" : "bg-sky-100 text-sky-700"
          }`}
        >
          {isUser ? <UserRound size={14} /> : <Bot size={14} />}
        </div>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
          isUser
            ? "rounded-br-md bg-slate-900 text-white"
            : "rounded-bl-md border border-slate-300 bg-white text-slate-800"
        }`}
        >
          <p>{message.content}</p>
          <p
            className={`mt-2 inline-flex items-center gap-1 text-[11px] ${
              isUser ? "text-slate-300" : "text-slate-500"
            }`}
          >
            <Clock3 size={12} />
            {message.timestamp}
          </p>
        </div>
      </div>
    </div>
  );
}
