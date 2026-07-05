# CLAUDE.md

## Tech Stack
* **SSG:** Hugo Extended (v0.148.0)
* **Theme:** PaperMod (Defaulting to default Dark mode / ProfileMode landing)
* **Automation:** Python 3.11+
* **AI Integration:** Google Gemini API (`google-generativeai` SDK, using `gemini-3.5-flash`)
* **CI/CD & Hosting:** GitHub Actions & GitHub Pages (`.github/workflows/auto_blogger.yml`)

## Build & Development Commands
* **Start local Hugo preview server:** `./hugo server`
* **Build static site locally:** `./hugo`
* **Build with draft/future posts:** `./hugo -D -F`
* **Run Auto Blogger script manually:** `python auto_blogger.py` (ensure `GEMINI_API_KEY` is set)
* **Initialize virtual environment:** `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## Code Style & Architecture
* **Python Style:** Clean, modular structure using `main()` entrypoint. Keep prompt constants isolated from logic flow. Explicit error handling for API and Git tasks.
* **Hugo Layouts:** Override theme behavior using standard Go Templates in the local `layouts/` directory (e.g. [list.html](file:///home/bot/automated-niche-blog/layouts/_default/list.html)).
* **Frontend JavaScript:** Vanilla ES6+ without frameworks. DOM manipulation relies on HTML5 `data-*` attributes for instant client-side sorting and filtering.
* **Styling:** Vanilla CSS embedded cleanly inside layout files or partials.
* **Git Commits:** Conventional Commits prefixes: `Feat:`, `Fix:`, `Refactor:`, `Test:`, `Chore:`.

## Testing Guidelines
* **Hugo Builds:** Validate changes locally by running `./hugo` to verify no template compilation or syntax errors occur.
* **Output Inspection:** Inspect generated HTML outputs in `public/posts/` and check JSON files like `public/index.json` to verify search index compilation and content accuracy.
* **API Validation:** Execute `auto_blogger.py` with mock topics to verify key loading, safety filtering warnings, and affiliate link formatting under the Gemini quota limit.
