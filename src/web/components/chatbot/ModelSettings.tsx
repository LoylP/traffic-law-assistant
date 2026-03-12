"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Check, Plus, Settings2 } from "lucide-react";

import { PRESET_MODELS } from "@/lib/models";

type ModelSettingsProps = {
  selectedModel: string;
  onSelectModel: (model: string) => void;
  variant?: "icon" | "full";
  placement?: "bottom-end" | "top-end";
};

export function ModelSettings({
  selectedModel,
  onSelectModel,
  variant = "full",
  placement = "bottom-end",
}: ModelSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [customModel, setCustomModel] = useState("");
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const groupedModels = useMemo(() => {
    const groups = new Map<string, typeof PRESET_MODELS>();
    for (const model of PRESET_MODELS) {
      const existing = groups.get(model.provider) ?? [];
      groups.set(model.provider, [...existing, model]);
    }
    return Array.from(groups.entries());
  }, []);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!wrapperRef.current) {
        return;
      }
      if (!wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    window.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const submitCustomModel = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextModel = customModel.trim();
    if (!nextModel) {
      return;
    }
    onSelectModel(nextModel);
    setCustomModel("");
    setIsOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className={`text-center rounded-xl border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 ${
          variant === "icon" ? "h-12 w-12 justify-center px-0" : "inline-flex items-center py-1.5 gap-2"
        }`}
        aria-label="Chọn model"
      >
        <Settings2 size={20} />
        {variant === "full" && (
          <span className="max-w-40 truncate">{selectedModel}</span>
        )}
      </button>

      {isOpen && (
        <div
          className={`absolute right-0 z-[80] w-[min(22rem,calc(100vw-1rem))] rounded-2xl border border-slate-200 bg-white p-3 shadow-xl ${
            placement === "top-end"
              ? "bottom-full mb-2 origin-bottom-right"
              : "top-full mt-2 origin-top-right"
          }`}
        >
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Chọn model
          </p>

          <div className="max-h-[65vh] space-y-3 overflow-y-auto pr-1">
            {groupedModels.map(([provider, models]) => (
              <div key={provider}>
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                  {provider}
                </p>
                <div className="space-y-1">
                  {models.map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        onSelectModel(model.id);
                        setIsOpen(false);
                      }}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm transition ${
                        selectedModel === model.id
                          ? "bg-slate-900 text-white"
                          : "text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      <span>{model.label}</span>
                      {selectedModel === model.id && <Check size={14} />}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <form onSubmit={submitCustomModel} className="space-y-1.5 border-t border-slate-200 pt-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                Tự nhập model
              </p>
              <div className="flex items-center gap-2">
                <input
                  value={customModel}
                  onChange={(event) => setCustomModel(event.target.value)}
                  placeholder="vd: gemini-2.5-pro"
                  className="w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm text-slate-800 outline-none transition focus:border-slate-900"
                />
                <button
                  type="submit"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white transition hover:bg-slate-800"
                  aria-label="Áp dụng model"
                >
                  <Plus size={14} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
