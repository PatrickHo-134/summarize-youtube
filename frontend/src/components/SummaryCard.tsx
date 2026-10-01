import React from "react";
import { PlaySquare, Calendar } from "lucide-react";
import type { HistoryItem } from "../types";
import { SummaryViewer } from "./SummaryViewer";

interface SummaryCardProps {
  summary: HistoryItem;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function shortUrl(url: string): string {
  try {
    const u = new URL(url);
    return u.host + u.pathname + u.search;
  } catch {
    return url;
  }
}

export const SummaryCard: React.FC<SummaryCardProps> = ({ summary }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div className="flex items-start justify-between gap-3 px-5 py-4">
        <div className="flex items-start gap-3 min-w-0">
          <PlaySquare className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <a
              href={summary.videoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-indigo-600 hover:underline truncate block"
            >
              {shortUrl(summary.videoUrl)}
            </a>
            <p className="text-sm font-semibold text-gray-900 mt-0.5 leading-snug">
              {summary.title}
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 text-slate-600 text-xs px-2.5 py-1 flex-shrink-0 whitespace-nowrap">
          <Calendar className="w-3 h-3" />
          {formatDate(summary.createdAt)}
        </span>
      </div>

      <div className="px-5 pt-0 pb-2">
        <SummaryViewer summary={summary.summary} source={null} title={summary.title} />
      </div>
    </div>
  );
};
