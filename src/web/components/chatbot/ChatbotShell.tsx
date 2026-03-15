"use client";

import { useCallback, useState } from "react";
import { BadgeCheck, Sparkles } from "lucide-react";

import { sendMessage as sendMessageApi } from "@/lib/chat-api";
import { Message } from "@/types/chat";

import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

function formatTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function generateId(prefix = 'id') {
  const browserCrypto = typeof crypto !== 'undefined' ? crypto : undefined;
  const randomUUID = (browserCrypto as unknown as { randomUUID?: () => string })?.randomUUID;

  if (typeof randomUUID === 'function') {
    return `${prefix}_${randomUUID()}`;
  }

  // Fallback for environments where crypto.randomUUID is unavailable
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

export function ChatbotShell() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [searchMode, setSearchMode] = useState<'retrieval' | 'llm'>('retrieval');
  const [topK, setTopK] = useState(3);
  const [alpha, setAlpha] = useState(0.5);
  const hasConversation = messages.length > 0 || isTyping;


  const refreshConversation = useCallback(() => {
    setMessages([]);
    setIsTyping(false);
  }, []);

  const sendMessage = useCallback((content: string) => {
    const optimisticUserMessage: Message = {
      id: generateId('tmp'),
      role: "user",
      content,
      timestamp: formatTime(new Date().toISOString()),
    };

    setMessages((current) => [...current, optimisticUserMessage]);
    setIsTyping(true);

    void (async () => {
      try {
        const response = await sendMessageApi(content, searchMode, topK, alpha);
        const assistantMessage: Message = {
          id: generateId('assistant'),
          role: "assistant",
          content: JSON.stringify(
            response.api_type === "llm" && response.best_result
              ? [response.best_result]
              : response.results,
            null,
            2
          ),
          timestamp: formatTime(new Date().toISOString()),
        };

        setMessages((current) => [...current, assistantMessage]);
      } catch (error) {
        console.error("Send message failed", error);
        const message = error instanceof Error ? error.message : String(error);
        window.alert(`Không thể gửi tin nhắn: ${message}`);
      } finally {
        setIsTyping(false);
      }
    })();
  }, [searchMode, topK, alpha]);

  return (
    <div className="flex h-screen w-full flex-col">
      <ChatHeader
        title="Trợ lý giao thông"
        onRefresh={refreshConversation}
        searchMode={searchMode}
        onSelectMode={setSearchMode}
        topK={topK}
        onTopKChange={setTopK}
        alpha={alpha}
        onAlphaChange={setAlpha}
      />

      <section className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-slate-50">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <span className="chat-blob left-10 top-8 h-44 w-44 bg-sky-200/30" />
          <span className="chat-blob delay-1200 right-8 top-20 h-36 w-36 bg-indigo-200/25" />
        </div>
        <div className="relative z-10 flex min-h-0 flex-1 flex-col justify-end px-3 py-3 sm:px-4 sm:py-4">
          <div
            className={`mx-auto w-full max-w-4xl transition-[opacity,transform] duration-500 ease-out will-change-transform ${
              hasConversation
                ? "animate-chat-frame-in pointer-events-auto mb-3 flex min-h-0 flex-1 translate-y-0 opacity-100"
                : "pointer-events-none h-0 min-h-0 -translate-y-4 opacity-0"
            }`}
          >
            <MessageList messages={messages} isTyping={isTyping} />
          </div>

          <div className="mx-auto w-full max-w-4xl">
            <div
              className={`overflow-hidden px-2 text-center transition-[max-height,margin,opacity,transform] duration-500 ease-out ${
                hasConversation
                  ? "mb-0 max-h-0 -translate-y-2 opacity-0"
                  : "animate-hero-in mb-5 max-h-40 translate-y-0 opacity-100"
              }`}
            >
                <p className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-100/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-sky-800">
                  <Sparkles size={13} />
                  Trợ lý pháp lý giao thông
                </p>
                <h2 className="mt-3 text-2xl font-semibold text-slate-900 sm:text-3xl">
                  Hỏi nhanh, hiểu rõ mức phạt và quy định
                </h2>
                <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-slate-600">
                  <BadgeCheck size={14} className="text-emerald-600" />
                  Tư vấn bằng tiếng Việt, ngắn gọn, dễ áp dụng khi lái xe.
                </p>
            </div>

            <div
              className={`space-y-3 rounded-2xl border bg-white/90 p-3 shadow-[0_16px_50px_-28px_rgba(15,23,42,0.45)] sm:p-4 ${
                hasConversation ? "border-slate-200" : "border-slate-200/80"
              }`}
            >
              <ChatInput
              onSend={sendMessage}
              accessory={
                !hasConversation ? (
                  <span className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600">
                    {searchMode === 'retrieval' ? 'Retrieval' : 'LLM'}
                  </span>
                ) : undefined
              }
            />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
