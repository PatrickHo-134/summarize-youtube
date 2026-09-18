import React from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { Database, Cpu } from "lucide-react";

interface SummaryViewerProps {
  summary: string;
  source: "cache" | "llm" | null;
}

const mdComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-xl font-bold text-slate-900 mt-5 mb-2">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold text-slate-900 mt-4 mb-2">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold text-slate-900 mt-3 mb-1">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="text-sm text-gray-700 leading-relaxed mb-3">{children}</p>
  ),
  ul: ({ children }) => <ul className="space-y-1.5 mb-3">{children}</ul>,
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-1.5 mb-3 text-sm text-gray-700">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="flex items-start gap-2 text-sm text-gray-700">
      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0" />
      <span>{children}</span>
    </li>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
};

export const SummaryViewer: React.FC<SummaryViewerProps> = ({
  summary,
  source,
}) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
        <h2 className="text-base font-semibold text-slate-900">
          Video Insights
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

      <ReactMarkdown components={mdComponents}>{summary}</ReactMarkdown>
    </div>
  );
};
