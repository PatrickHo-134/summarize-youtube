Here is a structured strategy to transition your app into a React component-driven architecture.

1\. Project Setup & Tooling
---------------------------

-   **Initialize with Vite:** Bootstrap the project using Vite for fast bundling: `npm create vite@latest frontend -- --template react-ts`.

-   **Install Core Dependencies:** Add `react-markdown` for rendering Markdown responses, `lucide-react` for modern action icons, and `tailwindcss` for styling.

2\. Component Architecture & Type Definitions
---------------------------------------------

-   **`types.ts`:** Define TypeScript interfaces for requests and API responses (`SummaryResponse`, `ApiError`, `StatusState`).

-   **`UrlForm.tsx`:** Encapsulates the YouTube URL state, input validation, and submission triggers.

-   **`SummaryViewer.tsx`:** Accepts raw Markdown content and renders standard HTML elements styled with Tailwind typography classes.

-   **`ActionControls.tsx`:** Houses interactive buttons like "Email Summary" and "Retry Request", toggled according to the response state.

3\. State Management & API Hook
-------------------------------

-   **Model App States:** Use an explicit status union state (`'idle' | 'loading' | 'success' | 'error'`) to manage application state transitions deterministically.

-   **Custom Fetch Hook (`useSummarize`):** Extract API Gateway calls into a custom React hook to keep UI components presentation-focused.

-   **Retry Handling:** Expose a `refetch()` trigger from your custom hook directly to the "Retry Request" button to simplify re-attempting failed API calls.

4\. Build Pipeline & CloudFront Deployment
------------------------------------------

-   **Compile Production Assets:** Execute `npm run build` to generate optimized static output files in the `dist/` directory.

-   **S3 Bucket Sync:** Update your deployment pipeline to sync the `dist/` directory to your S3 bucket (`aws s3 sync dist/ s3://your-s3-bucket-name`).

-   **Invalidate CDN Cache:** Create a CloudFront invalidation (`aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"`) so users receive the updated React app immediately.