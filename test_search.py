"""Temporary standalone test for the web_search tool logic (not wired to any agent)."""

import sys
from ddgs import DDGS


def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{r['title']}: {r['body']} (source: {r['href']})" for r in results
    )


def safe_print(text: str) -> None:
    print(text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))


if __name__ == "__main__":
    print("--- Query: 'latest AI agent frameworks' ---")
    safe_print(web_search("latest AI agent frameworks"))

    print("\n--- Query designed to return no/zero results ---")
    safe_print(web_search("asdkjhqwlekjhasdlkjhqwoiuerlkjhasdkjfh39458xyzunlikely"))

    print("\n--- Query designed to error (empty string, ddgs requires a query) ---")
    safe_print(web_search(""))
