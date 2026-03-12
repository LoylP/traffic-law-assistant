import { BadgeAlert, BookOpenText, ClipboardCheck, LucideIcon, Scale } from "lucide-react";

import { QuickAction } from "@/types/chat";

type QuickActionsProps = {
  items: QuickAction[];
  onPick: (prompt: string) => void;
};

export function QuickActions({ items, onPick }: QuickActionsProps) {
  const iconByActionId: Record<string, LucideIcon> = {
    summary: BookOpenText,
    fine: BadgeAlert,
    checklist: ClipboardCheck,
    explain: Scale,
  };

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const Icon = iconByActionId[item.id] ?? BookOpenText;

        return (
        <button
          key={item.id}
          type="button"
          onClick={() => onPick(item.prompt)}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
        >
          <Icon size={14} />
          {item.label}
        </button>
        );
      })}
    </div>
  );
}
