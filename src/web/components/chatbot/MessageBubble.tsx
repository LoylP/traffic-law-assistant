import { Bot, Clock3, UserRound } from "lucide-react";

import { Message } from "@/types/chat";
import { SearchResult } from "@/lib/chat-api";
import { ResultsDisplay } from "./ResultsDisplay";

type MessageBubbleProps = {
  message: Message;
};

function parseResults(content: string): SearchResult[] | null {
  try {
    const parsed: unknown = JSON.parse(content);
    if (!Array.isArray(parsed) || parsed.length === 0) return null;

    const first = parsed[0];
    if (
      typeof first === "object" &&
      first !== null &&
      "raw_node" in first
    ) {
      return parsed as SearchResult[];
    }

    return null;
  } catch {
    return null;
  }
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const parsedResults = parseResults(message.content);

  const content = parsedResults ? (
    <ResultsDisplay results={parsedResults} />
  ) : (
    <p>{message.content}</p>
  );

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
          {content}
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
