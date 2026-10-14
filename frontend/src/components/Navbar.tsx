import type { AppView } from "../types";

interface NavbarProps {
  view: AppView;
  onViewChange: (view: AppView) => void;
  userEmail?: string | null;
  onSignOut?: () => void;
  onLogin?: () => void;
}

export function Navbar({ view, onViewChange, userEmail, onSignOut, onLogin }: NavbarProps) {
  return (
    <nav className="w-full bg-white border-b border-gray-200 px-3 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-between gap-y-2 py-2 sm:h-14 sm:py-0">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
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
          <span className="text-sm sm:text-base font-semibold text-gray-900 truncate">
            YT Summarizer
          </span>
        </div>

        <div className="flex items-center flex-wrap justify-end gap-0.5 sm:gap-1">
          <button
            onClick={() => onViewChange("new")}
            className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md transition cursor-pointer whitespace-nowrap ${
              view === "new"
                ? "text-indigo-700"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            New Summary
          </button>
          <button
            onClick={() => onViewChange("dashboard")}
            className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-full transition cursor-pointer whitespace-nowrap ${
              view === "dashboard"
                ? "bg-indigo-50 text-indigo-700"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            History
          </button>

          {userEmail && onSignOut ? (
            <div className="flex items-center gap-2 ml-1 sm:ml-2 pl-1 sm:pl-2 border-l border-gray-200">
              <button
                onClick={onSignOut}
                className="px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md text-red-600 hover:bg-red-50 transition cursor-pointer whitespace-nowrap"
              >
                Sign Out
              </button>
            </div>
          ) : onLogin ? (
            <div className="ml-1 sm:ml-2 pl-1 sm:pl-2 border-l border-gray-200">
              <button
                onClick={onLogin}
                className="px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 transition cursor-pointer whitespace-nowrap"
              >
                Login
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </nav>
  );
}
