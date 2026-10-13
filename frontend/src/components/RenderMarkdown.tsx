import React from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";

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
    <p className="text-sm text-gray-700 leading-relaxed mb-3 break-words">{children}</p>
  ),
  ul: ({ children }) => <ul className="space-y-1.5 mb-3">{children}</ul>,
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-1.5 mb-3 text-sm text-gray-700 break-words">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="flex items-start gap-2 text-sm text-gray-700">
      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0" />
      <span className="break-words min-w-0">{children}</span>
    </li>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  pre: ({ children }) => (
    <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-lg p-3 sm:p-4 mb-3 overflow-x-auto">
      {children}
    </pre>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = /language-/.test(className ?? "");
    if (isBlock) {
      return (
        <code className={`${className ?? ""} font-mono whitespace-pre`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="bg-slate-100 text-indigo-600 rounded px-1.5 py-0.5 text-xs sm:text-sm font-mono break-words"
        {...props}
      >
        {children}
      </code>
    );
  },
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3 -mx-1 px-1">
      <table className="min-w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-slate-200 bg-slate-50 px-3 py-2 text-left font-semibold text-slate-900 whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-slate-200 px-3 py-2 text-slate-700 align-top break-words">
      {children}
    </td>
  ),
};

interface SharedMarkdownProps {
  content: string;
}

export const RenderMarkdown: React.FC<SharedMarkdownProps> = ({ content }) => {
  const normalized = content.replace(/\\n/g, "\n");
  return <ReactMarkdown components={mdComponents}>{normalized}</ReactMarkdown>;
};
