# SaaS Pain-Point Engine

A small research tool that scans Reddit communities for real user frustrations and turns them into actionable micro-SaaS ideas.

It combines:

- **[Bright Data MCP](https://www.npmjs.com/package/@brightdata/mcp)** for web search and scraping
- **[NVIDIA NIM](https://build.nvidia.com/)** for LLM analysis
- **Streamlit** for a simple UI

Enter a subreddit like `saas` or `startups`, and the app returns structured pain points with suggested product ideas and a market-readiness score.

## How it works

```text
Subreddit input
    │
    ▼
Bright Data MCP
    ├─ search_engine  → Google search for Reddit frustration posts
    └─ scrape_as_markdown → scrape the subreddit feed
    │
    ▼
NVIDIA NIM (OpenAI-compatible API)
    └─ extract 3–4 complaints + micro-SaaS ideas as JSON
    │
    ▼
Streamlit UI / CLI output
```

For each community, the engine:

1. Searches Google for posts matching frustration-style queries on the target subreddit
2. Scrapes the subreddit homepage as markdown
3. Sends the combined context to an NVIDIA NIM model
4. Returns a JSON report with user frustrations, triggers, SaaS ideas, and scores

## Example output

```json
{
  "community": "saas",
  "extracted_problems": [
    {
      "user_frustration": "Founders struggle to track churn reasons across support tickets and product feedback.",
      "context_or_trigger": "Pricing changes and onboarding drop-offs are hard to connect to user complaints.",
      "potential_saas_solution": "A lightweight churn-intelligence dashboard that clusters Reddit, support, and NPS feedback.",
      "market_readiness_score": 8
    }
  ]
}
```

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js + `npx` (required to launch the Bright Data MCP server)
- API keys:
  - [Bright Data API token](https://brightdata.com/)
  - [NVIDIA API key](https://build.nvidia.com/)

## Setup

1. Clone or open this project directory.

2. Install dependencies:

```bash
uv sync
```

3. Create a `.env` file:

```env
BRIGHTDATA_API_KEY=your_brightdata_api_key
API_TOKEN=your_brightdata_api_key
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_NIM_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

Notes:

- Bright Data MCP expects `API_TOKEN`. The app also accepts `BRIGHTDATA_API_KEY` or `BRIGHT_DATA_API_KEY`.
- `NVIDIA_NIM_MODEL` defaults to `meta/llama-3.3-70b-instruct` if omitted.

## Run the Streamlit app

```bash
uv run streamlit run app.py
```

Then:

1. Enter a subreddit name in the sidebar (without `r/`)
2. Click **Analyze community**
3. Review the generated ideas or download the JSON report

Analysis usually takes 1–2 minutes because it starts the Bright Data MCP server, performs search/scrape calls, then runs the NVIDIA model.

## Run from the CLI

```bash
uv run python main.py
```

By default this analyzes `r/saas`. To analyze another community, change the argument in `main.py` or import and call:

```python
from main import run_pain_point_engine_sync

result = run_pain_point_engine_sync("startups")
print(result["parsed_report"])
```

## Project structure

```text
saas-painpoint-engine/
├── app.py          # Streamlit UI
├── main.py         # Core engine (Bright Data MCP + NVIDIA NIM)
├── pyproject.toml
├── uv.lock
└── .env            # Local secrets (not committed)
```

## Troubleshooting

### `Cannot run MCP server without API_TOKEN env`

Bright Data MCP requires `API_TOKEN`. Either:

- add it to `.env`, or
- run the app via `uv run streamlit run app.py` / `uv run python main.py`, which injects it automatically from `BRIGHTDATA_API_KEY`

If testing MCP manually:

```bash
set -a && source .env && set +a
npx -y @brightdata/mcp
```

### `404` when installing `brightdata-mcp`

The correct npm package is:

```bash
npx -y @brightdata/mcp
```

There is no package named `brightdata-mcp`.

### Analysis returns empty or weak results

Try:

- a more active subreddit (`saas`, `startups`, `entrepreneur`, `smallbusiness`)
- a different NVIDIA model via `NVIDIA_NIM_MODEL`
- checking the **Source context** expander in the UI to confirm Bright Data returned search/scrape content

## License

Use and modify freely within your own projects.
