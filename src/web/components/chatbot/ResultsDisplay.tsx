import { SearchResult } from "@/lib/chat-api";

type ResultsDisplayProps = {
  results: SearchResult[];
};

function formatCurrency(value?: number) {
  if (typeof value !== "number") return "Không rõ";
  return value.toLocaleString("vi-VN") + "đ";
}

export function ResultsDisplay({ results }: ResultsDisplayProps) {
  if (!results || results.length === 0) {
    return <p className="text-slate-500">Không có kết quả.</p>;
  }

  const renderText = (value: unknown, fallback = "-") => {
    if (typeof value === "string") return value;
    if (typeof value === "number") return value.toString();
    return fallback;
  };

  return (
    <div className="space-y-4">
      {results.map((result, index) => {
        const node = result.raw_node as Record<string, unknown>;

        const score =
          typeof result.score === "number"
            ? result.score
            : typeof result.scores?.hybrid === "number"
            ? result.scores.hybrid
            : typeof result.scores?.embedding === "number"
            ? result.scores.embedding
            : typeof result.scores?.bm25 === "number"
            ? result.scores.bm25
            : undefined;

        return (
          <div
            key={index}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <div className="mb-3 flex items-start justify-between">
              <span className="text-sm font-medium text-blue-600">
                Kết quả #{index + 1}
              </span>
              <span className="text-xs text-slate-500">
                Điểm: {typeof score === "number" ? score.toFixed(3) : "-"}
              </span>
            </div>

            <div className="space-y-2 text-sm text-slate-700">
              <p>
                <span className="font-semibold">ID:</span>{" "}
                {renderText(node.violation_id ?? result.violation_id)}
              </p>

              <p>
                <span className="font-semibold">Hành vi:</span>{" "}
                {renderText(node.normalized_violation)}
              </p>

              <p>
                <span className="font-semibold">Phương tiện:</span>{" "}
                {renderText(node.vehicle_type)}
              </p>

              <p>
                <span className="font-semibold">Mức phạt:</span>{" "}
                {formatCurrency(node.fine_min as number)} - {formatCurrency(node.fine_max as number)}
              </p>

              <p>
                <span className="font-semibold">Trích dẫn:</span>{" "}
                {renderText(node.legal_basis)}
              </p>

              <p>
                <span className="font-semibold">Hình thức bổ sung:</span>{" "}
                {renderText(node.additional_sanctions)?.trim()
                  ? renderText(node.additional_sanctions)
                  : "Không có"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}