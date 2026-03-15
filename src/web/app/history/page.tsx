"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, History } from "lucide-react";

type HistoryItem = {
  id: number;
  api_type: string;
  original_query: string;
  processed_query?: string;
  top_k: number;
  timestamp: string;
  results: unknown[];
};

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'hybrid' | 'llm_hybrid'>('all');

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const endpoint =
          filter === "all"
            ? "/history"
            : `/history/${filter === "hybrid" ? "hybrid" : "llm"}`;
        const response = await fetch(`${baseUrl}${endpoint}`);
        const data = await response.json();
        setHistory(data.items || []);
      } catch (error) {
        console.error("Failed to fetch history:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [filter, baseUrl]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                <ArrowLeft className="h-4 w-4" />
                Quay lại
              </Link>
              <h1 className="text-xl font-semibold text-slate-900">Lịch sử tìm kiếm</h1>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setFilter('all')}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  filter === 'all' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Tất cả
              </button>
              <button
                onClick={() => setFilter('hybrid')}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  filter === 'hybrid' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Retrieval
              </button>
              <button
                onClick={() => setFilter('llm_hybrid')}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  filter === 'llm_hybrid' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                LLM
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-slate-500">Đang tải...</div>
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-12">
            <History className="mx-auto h-12 w-12 text-slate-400" />
            <h3 className="mt-4 text-lg font-medium text-slate-900">Không có lịch sử</h3>
            <p className="mt-2 text-slate-500">Chưa có truy vấn nào được lưu.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        item.api_type === 'hybrid' ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {item.api_type === 'hybrid' ? 'Retrieval' : 'LLM'}
                      </span>
                      <span className="text-sm text-slate-500">
                        {new Date(item.timestamp).toLocaleString('vi-VN')}
                      </span>
                    </div>
                    <h3 className="font-medium text-slate-900 mb-1">
                      Truy vấn: {item.original_query}
                    </h3>
                    {item.processed_query && (
                      <p className="text-sm text-slate-600 mb-2">
                        Đã xử lý: {item.processed_query}
                      </p>
                    )}
                    <p className="text-sm text-slate-500">
                      Số kết quả: {item.top_k}
                    </p>
                  </div>
                </div>
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-800">
                    Xem kết quả ({item.results.length} mục)
                  </summary>
                  <pre className="mt-2 max-h-60 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-700">
                    {JSON.stringify(item.results, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}