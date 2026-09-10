import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Database, Cpu } from 'lucide-react';

interface SummaryViewerProps {
  summary: string;
  source: 'cache' | 'llm' | null;
}

export const SummaryViewer: React.FC<SummaryViewerProps> = ({ summary, source }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 pb-4 mb-6">
        <h2 className="text-xl font-bold text-gray-900">Video Insights</h2>
        {source && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {source === 'cache' ? (
              <>
                <Database className="w-3.5 h-3.5 text-blue-500" /> Cached
              </>
            ) : (
              <>
                <Cpu className="w-3.5 h-3.5 text-purple-500" /> Generated via GPT-4o-mini
              </>
            )}
          </span>
        )}
      </div>

      <div className="summary-content leading-relaxed">
        <ReactMarkdown>{summary}</ReactMarkdown>
      </div>
    </div>
  );
};