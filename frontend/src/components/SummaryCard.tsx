import React from "react";
import ReactMarkdown from "react-markdown";
import { PlaySquare, Calendar } from "lucide-react";
import type { HistoryItem } from "../types";

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

      <hr className="border-slate-100" />

      <div className="px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 mb-3">
          Summary
        </p>
        <div className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none [&_ul]:space-y-1 [&_li]:flex [&_li]:items-start [&_li]:gap-2 [&_li::marker]:hidden [&_li]:list-none [&_li]:before:content-['•'] [&_li]:before:text-indigo-500 [&_li]:before:font-bold [&_li]:before:flex-shrink-0">
          <ReactMarkdown>{summary.summary}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
};
