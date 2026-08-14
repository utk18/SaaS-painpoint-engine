import os
import json
import asyncio
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

JSON_STRUCTURE_PROMPT = """
You must output your analysis strictly as a valid JSON object matching this schema layout:
{
  "community": "string",
  "extracted_problems": [
    {
      "user_frustration": "Detailed explanation of the core bug, block, or tool limitation",
      "context_or_trigger": "What triggered this issue? (e.g. pricing increase, complex UI)",
      "potential_saas_solution": "Actionable micro-SaaS application idea that resolves it",
      "market_readiness_score": 8
    }
  ]
}
Do not wrap your output in markdown formatting wrappers like ```json. Return ONLY the raw JSON text string.
"""


def get_brightdata_api_token():
    return (
        os.getenv("API_TOKEN")
        or os.getenv("BRIGHTDATA_API_KEY")
        or os.getenv("BRIGHT_DATA_API_KEY")
        or ""
    ).strip()


def get_nim_client():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("Set NVIDIA_API_KEY in your .env file.")
    return OpenAI(
        base_url=os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=api_key,
    )


def get_brightdata_mcp_url():
    api_token = get_brightdata_api_token()
    if not api_token:
        raise ValueError("Set BRIGHTDATA_API_KEY (or API_TOKEN) in your .env file.")

    base_url = os.getenv("BRIGHTDATA_MCP_URL", "https://mcp.brightdata.com/mcp").rstrip("/")
    if "token=" in base_url:
        return base_url

    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={api_token}"


def extract_tool_text(response):
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if hasattr(content, "text"):
        return content.text
    return str(content)


def parse_model_output(raw_output: str):
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)


async def run_pain_point_engine(niche_topic: str):
    clean_subreddit = niche_topic.replace(" ", "").lower().removeprefix("r/").removeprefix("/")
    if not clean_subreddit:
        raise ValueError("Enter a subreddit name.")

    target_model = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")
    nim_client = get_nim_client()
    mcp_url = get_brightdata_mcp_url()

    async with streamable_http_client(mcp_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            search_query = (
                f'site:reddit.com/r/{clean_subreddit} '
                f'"is anyone else frustrated with" OR "is there a tool for"'
            )
            search_response = await session.call_tool(
                "search_engine",
                arguments={"query": search_query},
            )
            search_text = extract_tool_text(search_response)

            target_url = f"https://www.reddit.com/r/{clean_subreddit}/"
            scrape_response = await session.call_tool(
                "scrape_as_markdown",
                arguments={"url": target_url},
            )
            raw_markdown = extract_tool_text(scrape_response)

            combined_context = f"SEARCH SNIPPETS:\n{search_text}\n\nRAW FEED CONTENT:\n{raw_markdown}"

            completion = nim_client.chat.completions.create(
                model=target_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a pragmatic venture capitalist and SaaS product builder. "
                            "Read raw web dumps of developer/founder discussions. "
                            "Find genuine complaints or software gaps. "
                            f"{JSON_STRUCTURE_PROMPT}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analyze this compiled web scrape context from the /r/{clean_subreddit} "
                            f"community. Extract 3-4 specific user complaints.\n\n"
                            f"Context:\n{combined_context[:15000]}"
                        ),
                    },
                ],
                temperature=0.2,
            )

            raw_output = completion.choices[0].message.content.strip()
            parsed_report = None
            parse_error = None
            try:
                parsed_report = parse_model_output(raw_output)
            except json.JSONDecodeError as exc:
                parse_error = str(exc)

            return {
                "subreddit": clean_subreddit,
                "model": target_model,
                "search_query": search_query,
                "target_url": target_url,
                "search_text": search_text,
                "raw_markdown": raw_markdown,
                "parsed_report": parsed_report,
                "raw_output": raw_output,
                "parse_error": parse_error,
            }


def run_pain_point_engine_sync(niche_topic: str):
    return asyncio.run(run_pain_point_engine(niche_topic))


if __name__ == "__main__":
    result = run_pain_point_engine_sync("saas")
    if result["parsed_report"]:
        print(f"\n📊 === FOUNDER COMPLAINT REPORT FOR /r/{result['subreddit']} ===")
        print(json.dumps(result["parsed_report"], indent=2))
    else:
        print("\n⚠️ Failed to parse raw text directly as JSON. Printing raw output instead:")
        print(result["raw_output"])
