import Image from "next/image";
import Link from "next/link";
import { RotateCcw, Sparkles, History } from "lucide-react";
import { SearchSettings } from "./SearchSettings";

type ChatHeaderProps = {
  title: string;
  onRefresh: () => void;
  searchMode: 'retrieval' | 'llm';
  onSelectMode: (mode: 'retrieval' | 'llm') => void;
  topK: number;
  onTopKChange: (topK: number) => void;
  alpha: number;
  onAlphaChange: (alpha: number) => void;
};

export function ChatHeader({
  title,
  onRefresh,
  searchMode,
  onSelectMode,
  topK,
  onTopKChange,
  alpha,
  onAlphaChange,
}: ChatHeaderProps) {
  return (
    <header className="relative z-[120] border-b bg-white">
      <div className="flex items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white h-14 w-14">
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
            <p className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              <Sparkles size={14} />
              Phiên hiện tại
            </p>
            <h1 className="mt-1 text-lg font-semibold text-slate-900">{title}</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/history"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <History className="h-4 w-4" />
            Lịch sử
          </Link>
          <SearchSettings
            searchMode={searchMode}
            onSelectMode={onSelectMode}
            topK={topK}
            onTopKChange={onTopKChange}
            alpha={alpha}
            onAlphaChange={onAlphaChange}
            variant="full"
            placement="bottom-end"
          />
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
          >
            <RotateCcw size={14} />
            <span className="overflow-hidden whitespace-nowrap text-sm">
              Làm mới cuộc trò chuyện
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
