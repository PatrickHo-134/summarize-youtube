import React from "react";
import { Database, Cpu } from "lucide-react";
import { RenderMarkdown } from "./RenderMarkdown";

interface SummaryViewerProps {
  summary: string;
  source: "cache" | "llm" | null;
  title?: string | null;
}

export const SummaryViewer: React.FC<SummaryViewerProps> = ({
  summary,
  source,
  title,
}) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
        <h2 className="text-base font-semibold text-slate-900">
          {title || "Video Insights"}
        </h2>
        {source && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
            {source === "cache" ? (
              <>
                <Database className="w-3.5 h-3.5 text-blue-500" /> Cached
              </>
            ) : (
              <>
                <Cpu className="w-3.5 h-3.5 text-purple-500" /> Generated via
                GPT-4o-mini
              </>
            )}
          </span>
        )}
      </div>

      <RenderMarkdown content={summary} />
    </div>
  );
};
