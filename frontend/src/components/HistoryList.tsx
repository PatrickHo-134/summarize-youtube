import React, { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import {
  Calendar,
  ArrowUpDown,
  Play,
  ExternalLink,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { type HistoryItem } from "../types";

interface HistoryListProps {
  items: HistoryItem[];
  isLoading?: boolean;
  isLoadingMore?: boolean;
  nextToken?: string | null;
  onLoadMore?: () => void;
  error?: string | null;
}

export const HistoryList: React.FC<HistoryListProps> = ({
  items = [],
  isLoading = false,
  isLoadingMore = false,
  nextToken = null,
  onLoadMore,
  error = null,
}) => {
  const [sortBy, setSortBy] = useState<"newest" | "oldest">("newest");

  const safeItems = Array.isArray(items) ? items : [];

  // Sort items dynamically based on date created
  const sortedItems = useMemo(() => {
    return [...safeItems].sort((a, b) => {
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();
      return sortBy === "newest" ? dateB - dateA : dateA - dateB;
    });
  }, [safeItems, sortBy]);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  if (error) {
    return (
      <div className="text-center py-16 bg-white rounded-2xl border border-red-100 p-8">
        <p className="text-sm font-medium text-red-600">{error}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        <div className="h-8 w-32 bg-slate-200 rounded-md animate-pulse mb-6" />
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className="h-44 bg-white rounded-2xl border border-slate-200/80 p-6 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <section className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-2">
        <div className="space-y-1">
          <p className="text-xs font-semibold text-indigo-600 tracking-wide uppercase">
            Your library
          </p>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Saved Summaries
          </h1>
          <p className="text-slate-500 text-sm">
            {items.length} {items.length === 1 ? "video" : "videos"} saved for
            later
          </p>
        </div>

        {items.length > 0 && (
          <div className="relative inline-flex items-center self-start sm:self-auto bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-2xs">
            <ArrowUpDown className="w-4 h-4 text-slate-400 mr-2 shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "newest" | "oldest")}
              className="bg-transparent text-sm font-medium text-slate-700 pr-6 focus:outline-none cursor-pointer appearance-none"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
            <ChevronDown className="w-4 h-4 text-slate-400 pointer-events-none absolute right-2.5" />
          </div>
        )}
      </div>

      {sortedItems.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 p-8 shadow-2xs">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-3">
            <Play className="w-5 h-5 fill-current" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">
            No saved summaries yet
          </h3>
          <p className="text-slate-500 text-sm mt-1 max-w-sm mx-auto">
            Paste a YouTube URL on the main tab to generate your first summary
            and store it in your library.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedItems.map((item) => (
            <article
              key={`${item.videoId}-${item.createdAt}`}
              className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-2xs hover:shadow-xs transition-shadow space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0 mt-0.5">
                    <Play className="w-4 h-4 fill-current" />
                  </div>
                  <div className="space-y-0.5">
                    <a
                      href={item.videoUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 text-xs sm:text-sm font-medium hover:underline inline-flex items-center gap-1 group"
                    >
                      {item.videoUrl.replace(/^https?:\/\/(www\.)?/, "")}
                      <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                    <h2 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                      {item.title || `Video Summary (${item.videoId})`}
                    </h2>
                  </div>
                </div>

                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-50 border border-slate-200/60 text-slate-500 text-xs font-medium shrink-0 self-start sm:self-auto">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>{formatDate(item.createdAt)}</span>
                </div>
              </div>

              <hr className="border-slate-100" />

              <div
                className="prose prose-slate max-w-none text-sm leading-relaxed text-slate-600
                  prose-headings:font-bold prose-headings:text-slate-900 prose-headings:text-base prose-headings:mt-3 prose-headings:mb-1.5
                  prose-p:my-1.5
                  prose-ul:my-2 prose-ul:pl-4 prose-li:my-1 prose-li:marker:text-indigo-500"
              >
                <ReactMarkdown>{item.summary}</ReactMarkdown>
              </div>
            </article>
          ))}

          {nextToken && (
            <div className="flex justify-center pt-2">
              <button
                onClick={onLoadMore}
                disabled={isLoadingMore}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm font-medium text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading…
                  </>
                ) : (
                  'Load More'
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
