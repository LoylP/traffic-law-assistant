import { KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";
import { MessageSquareText, SendHorizontal } from "lucide-react";

type ChatInputProps = {
  onSend: (content: string) => void;
  accessory?: ReactNode;
};

export function ChatInput({ onSend, accessory }: ChatInputProps) {
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const resizeTextarea = (textarea: HTMLTextAreaElement) => {
    textarea.style.height = "auto";

    const style = window.getComputedStyle(textarea);
    const lineHeight = Number.parseFloat(style.lineHeight) || 20;
    const paddingY =
      Number.parseFloat(style.paddingTop) + Number.parseFloat(style.paddingBottom);
    const borderY =
      Number.parseFloat(style.borderTopWidth) +
      Number.parseFloat(style.borderBottomWidth);
    const maxHeight = lineHeight * 10 + paddingY + borderY;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);

    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  };

  useEffect(() => {
    if (!textareaRef.current) {
      return;
    }

    resizeTextarea(textareaRef.current);
  }, [content]);

  const submitMessage = () => {
    const value = content.trim();
    if (!value) {
      return;
    }

    onSend(value);
    setContent("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    if (event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    submitMessage();
  };

  const canSend = content.trim().length > 0;

  return (
    <div className="p-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi của bạn..."
            rows={1}
            className="min-h-12 w-full resize-none rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 pr-14 text-sm text-slate-900 outline-none ring-0 transition placeholder:text-slate-500 focus:border-slate-900"
          />
          <button
            type="button"
            onClick={submitMessage}
            disabled={!canSend}
            className="absolute top-1 right-1.5 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white transition enabled:hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            aria-label="Gửi tin nhắn"
          >
            <SendHorizontal size={16} />
          </button>
        </div>
        {accessory ? (
          <div className="shrink-0">{accessory}</div>
        ) : (
          <span className="hidden items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-[11px] text-slate-500 md:inline-flex">
            <MessageSquareText size={13} />
            Enter để gửi
          </span>
        )}
      </div>
    </div>
  );
}
