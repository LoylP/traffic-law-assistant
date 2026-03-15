"use client";

import { FormEvent, useRef, useState } from "react";
import { Settings, Check } from "lucide-react";

type SearchSettingsProps = {
  searchMode: 'retrieval' | 'llm';
  onSelectMode: (mode: 'retrieval' | 'llm') => void;
  topK: number;
  onTopKChange: (topK: number) => void;
  alpha: number;
  onAlphaChange: (alpha: number) => void;
  variant?: "icon" | "full";
  placement?: "bottom-end" | "top-end";
};

export function SearchSettings({
  searchMode,
  onSelectMode,
  topK,
  onTopKChange,
  alpha,
  onAlphaChange,
  variant = "full",
  placement = "bottom-end",
}: SearchSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-slate-100 ${
          variant === "icon" ? "p-2" : ""
        }`}
        title="Cài đặt tìm kiếm"
      >
        <Settings className="h-4 w-4" />
        {variant === "full" && <span>Cài đặt tìm kiếm</span>}
      </button>

      {isOpen && (
        <div
          className={`absolute z-50 mt-2 w-80 rounded-lg border border-slate-200 bg-white p-4 shadow-lg ${
            placement === "bottom-end" ? "right-0" : "left-0"
          }`}
        >
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  Chế độ tìm kiếm
                </label>
                <div className="mt-2 flex gap-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="mode"
                      value="retrieval"
                      checked={searchMode === 'retrieval'}
                      onChange={() => onSelectMode('retrieval')}
                      className="mr-2"
                    />
                    Retrieval
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="mode"
                      value="llm"
                      checked={searchMode === 'llm'}
                      onChange={() => onSelectMode('llm')}
                      className="mr-2"
                    />
                    LLM
                  </label>
                </div>
              </div>

              {searchMode === 'retrieval' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">
                      Số lượng kết quả (top_k)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={topK}
                      onChange={(e) => onTopKChange(Number(e.target.value))}
                      className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">
                      Ngưỡng khớp (alpha)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.1"
                      value={alpha}
                      onChange={(e) => onAlphaChange(Number(e.target.value))}
                      className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Check className="h-4 w-4" />
                Áp dụng
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}