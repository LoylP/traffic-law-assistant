import Image from "next/image";
import { RotateCcw, Sparkles } from "lucide-react";
import { ModelSettings } from "./ModelSettings";

type ChatHeaderProps = {
  title: string;
  onRefresh: () => void;
  expanded: boolean;
  selectedModel: string;
  onSelectModel: (model: string) => void;
};

export function ChatHeader({
  title,
  onRefresh,
  expanded,
  selectedModel,
  onSelectModel,
}: ChatHeaderProps) {
  return (
    <header
      className={`relative z-[120] border-b bg-white transition-[max-height,opacity,transform,border-color] duration-500 ease-out ${
        expanded
          ? "max-h-40 translate-y-0 overflow-visible border-slate-200 opacity-100"
          : "pointer-events-none max-h-0 -translate-y-2 overflow-hidden border-transparent opacity-0"
      }`}
    >
      <div className="flex items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div
            className={`relative overflow-hidden rounded-xl border border-slate-200 bg-white transition-[width,height] duration-500 ease-out ${
              expanded ? "h-16 w-16" : "h-10 w-10"
            }`}
          >
            <Image
              src="/logo.png"
              alt="Logo chatbot giao thông"
              fill
              className="object-cover"
              sizes="80px"
              priority
            />
          </div>
          <div>
            <p
              className={`inline-flex items-center gap-1 overflow-hidden text-xs font-medium uppercase tracking-[0.16em] text-slate-500 transition-[max-height,opacity,transform] duration-500 ease-out ${
                expanded ? "max-h-8 translate-y-0 opacity-100" : "max-h-0 -translate-y-1 opacity-0"
              }`}
            >
              <Sparkles size={14} />
              Phiên hiện tại
            </p>
            <h1
              className={`font-semibold text-slate-900 transition-[margin-top,font-size] duration-500 ease-out ${
                expanded ? "mt-1 text-lg" : "mt-0 text-base"
              }`}
            >
              {title}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ModelSettings
            selectedModel={selectedModel}
            onSelectModel={onSelectModel}
            variant="full"
            placement="bottom-end"
          />
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
          >
            <RotateCcw size={14} />
            <span
              className={`overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-500 ease-out ${
                expanded ? "max-w-48 opacity-100" : "max-w-0 opacity-0"
              }`}
            >
              Làm mới cuộc trò chuyện
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
