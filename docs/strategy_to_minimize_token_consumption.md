# Key strategies to minimize token consumption while maintaining agent performance

### 1\. Optimize Project Context Files

-   **Keep `CLAUDE.md` Lean:** Maintain `CLAUDE.md` as a lightweight reference card for high-frequency CLI commands, architecture guidelines, and syntax constraints. Remove outdated troubleshooting logs, full API schemas, or verbose documentation that can be stored in separate docs files and referenced only when needed.

-   **Configure `.claudeignore`:** Create a `.claudeignore` file in your root folder (works like `.gitignore`) to block Claude Code from searching or ingesting non-code assets, detailed coverage reports, build artifacts, lockfiles (`package-lock.json`), or massive log files.

### 2\. Session & History Management

-   **Start Fresh Sessions for Independent Tasks:** Since every prompt re-sends the entire conversation history, do not reuse a single session for unrelated tasks. Once a bug fix or feature implementation is complete, run `/clear` or exit and launch a new session.

-   **Use `/compact` Regularly:** In long-running sessions, run the `/compact` command to summarize the conversation history, pruning unnecessary file read outputs while retaining key context.

### 3\. Scope Requests and File Paths Explicitly

-   **Specify Target Files:** Avoid broad requests like *"Fix the auth flow"* which force Claude to scan the codebase using regex/file searches and read multiple files. Specify target files directly: *"Fix the token extraction in `backend/summarize/src/lambda_function.py`"*.

-   **Direct File Edits:** If you already know what needs to change, tell Claude Code exact line ranges or function names to inspect rather than letting it inspect entire folders.

### 4\. Control Terminal & Test Outputs

-   **Run Targeted Test Commands:** Avoid running full test suites or verbose build scripts inside the Claude session. Tell Claude to execute narrow tests (e.g., `pytest path/to/test.py::test_name`) rather than logging hundreds of passing test outputs into the prompt history.

-   **Limit Output Verbosity:** If a command produces long logs, pipe or filter the output before handing control back to Claude, or specify flag parameters that reduce verbosity (e.g., `npm test -- --silent`).