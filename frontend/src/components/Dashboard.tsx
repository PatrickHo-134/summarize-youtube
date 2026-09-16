import React, { useState } from "react";
import { ArrowUpDown } from "lucide-react";
import type { HistoryItem } from "../types";
import { SummaryCard } from "./SummaryCard";

interface DashboardProps {
  summaries: HistoryItem[];
}

type SortOrder = "newest" | "oldest";

export const Dashboard: React.FC<DashboardProps> = ({ summaries }) => {
  const [sort, setSort] = useState<SortOrder>("newest");

  const sorted = [...summaries].sort((a, b) => {
    const diff =
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    return sort === "newest" ? diff : -diff;
  });

  const toggleSort = () =>
    setSort((s) => (s === "newest" ? "oldest" : "newest"));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 mb-1">
            Your library
          </p>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-gray-900">
            Saved Summaries
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {summaries.length} {summaries.length === 1 ? "video" : "videos"}{" "}
            saved for later
          </p>
        </div>

        <button
          onClick={toggleSort}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm hover:bg-slate-50 transition cursor-pointer flex-shrink-0"
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
          {sort === "newest" ? "Newest first" : "Oldest first"}
        </button>
      </div>

      {sorted.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center text-sm text-gray-400">
          No summaries saved yet. Summarize a video to get started.
        </div>
      ) : (
        <div className="space-y-4">
          {sorted.map((s) => (
            <SummaryCard key={s.videoId} summary={s} />
          ))}
        </div>
      )}
    </div>
  );
};
