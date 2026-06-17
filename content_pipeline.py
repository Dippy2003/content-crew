"""
Multi-agent content pipeline using CrewAI.
Flow: Researcher -> Writer -> Editor

Setup:
    pip install crewai crewai-tools ddgs python-dotenv litellm
    Add GROQ_API_KEY=your_key_here to a .env file

Run (single topic, prompts you interactively):
    python content_pipeline.py

Run (batch mode, one run per line in topics.txt):
    python content_pipeline.py --batch topics.txt
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

# Windows' default console codepage (cp1252) can't render the emoji crewai
# uses in its progress UI; force UTF-8 so those don't crash/warn.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from ddgs import DDGS

load_dotenv()

# Workaround: crewai's prompt-cache breakpoint marker is only stripped by the
# native Anthropic provider. Non-native providers routed through litellm
# (e.g. Groq) receive the raw "cache_breakpoint" key and reject the request.
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda message: message


# ---- Tool: simple web search (no API key needed) ----
@tool("Web Search")
def web_search(query: str) -> str:
    """Search the web for a query and return a few summarized results with sources."""
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


# ---- LLM config ----
# Using Groq's free tier (Llama 3.3 70B) instead of a paid Anthropic key.
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY"),
)


# ---- Agents ----
researcher = Agent(
    role="Senior Research Analyst",
    goal="Find accurate, current, well-sourced information on {topic}",
    backstory=(
        "You are a meticulous researcher who cross-checks multiple sources "
        "and clearly flags anything uncertain or unverified."
    ),
    tools=[web_search],
    llm=llm,
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Turn research into a clear, engaging draft on {topic}",
    backstory=(
        "You write in a direct, conversational style, avoid filler and "
        "buzzwords, and structure pieces so they're easy to follow."
    ),
    llm=llm,
    verbose=True,
)

editor = Agent(
    role="Senior Editor",
    goal="Polish the draft for clarity, accuracy, and tone, and tighten any bloated sections",
    backstory=(
        "You have a sharp eye for awkward phrasing, unsupported claims, "
        "and unnecessary length. You verify the draft against the research "
        "before approving it."
    ),
    llm=llm,
    verbose=True,
)


# ---- Tasks ----
research_task = Task(
    description=(
        "Research {topic}. Gather key facts, recent developments, and at "
        "least 3 credible sources."
    ),
    expected_output="A structured summary of findings with bullet points and source links.",
    agent=researcher,
)

writing_task = Task(
    description="Using the research, write a roughly 600-word article on {topic} for a general audience.",
    expected_output="A complete draft article in markdown.",
    agent=writer,
    context=[research_task],
)

editing_task = Task(
    description=(
        "Review and polish the draft. Fix unclear sentences, verify claims "
        "against the research, and tighten the length."
    ),
    expected_output="The final, publication-ready article in markdown.",
    agent=editor,
    context=[writing_task],
)


# ---- Crew ----
content_crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, writing_task, editing_task],
    process=Process.sequential,
    verbose=True,
)


# ---- Helpers ----
def run_with_retries(topic: str, max_attempts: int = 3, base_delay: float = 5.0):
    """Run the crew on a topic, retrying with exponential backoff on failure."""
    for attempt in range(1, max_attempts + 1):
        try:
            return content_crew.kickoff(inputs={"topic": topic})
        except Exception as e:
            if attempt == max_attempts:
                print(f"\nFailed after {max_attempts} attempts on topic '{topic}': {e}")
                return None
            delay = base_delay * (2 ** (attempt - 1))
            print(
                f"\nAttempt {attempt} failed for topic '{topic}': {e}\n"
                f"Retrying in {delay:.0f}s..."
            )
            time.sleep(delay)
    return None


def save_article(topic: str, content: str) -> str:
    """Save the final article to /outputs/<topic>_<timestamp>.md and return the path."""
    outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "untitled"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{slug}_{timestamp}.md"
    path = os.path.join(outputs_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(content))

    return path


def run_topic(topic: str) -> None:
    print(f"\n{'=' * 60}\nRunning pipeline for topic: {topic}\n{'=' * 60}")
    result = run_with_retries(topic)
    if result is None:
        print(f"Skipping '{topic}' — no output produced.")
        return
    path = save_article(topic, result)
    print(f"\nSaved article to: {path}")


# ---- Run ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CrewAI content pipeline.")
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Path to a text file with one topic per line; runs the pipeline for each.",
    )
    args = parser.parse_args()

    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            topics = [line.strip() for line in f if line.strip()]
        if not topics:
            print(f"No topics found in {args.batch}")
        for topic in topics:
            run_topic(topic)
    else:
        topic = input("What topic should the crew write about? ")
        run_topic(topic)
