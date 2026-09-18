import type { AppView } from "../types";

interface NavbarProps {
  view: AppView;
  onViewChange: (view: AppView) => void;
}

export function Navbar({ view, onViewChange }: NavbarProps) {
  return (
    <nav className="w-full bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto flex items-center justify-between h-14">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 rounded-lg flex-shrink-0">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="white"
              className="w-4 h-4"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <span className="text-base font-semibold text-gray-900 whitespace-nowrap">
            YT Summarizer
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onViewChange("new")}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition cursor-pointer ${
              view === "new"
                ? "text-indigo-700"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            New Summary
          </button>
          <button
            onClick={() => onViewChange("dashboard")}
            className={`px-3 py-1.5 text-sm font-medium rounded-full transition cursor-pointer ${
              view === "dashboard"
                ? "bg-indigo-50 text-indigo-700"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            Dashboard
          </button>
        </div>
      </div>
    </nav>
  );
}
