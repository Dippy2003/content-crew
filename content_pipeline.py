"""
Multi-agent content pipeline using CrewAI.
Flow: Researcher -> Writer -> Editor

Setup:
    pip install crewai crewai-tools duckduckgo-search
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python content_pipeline.py
"""

import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from duckduckgo_search import DDGS


# ---- Tool: simple web search (no API key needed) ----
@tool("Web Search")
def web_search(query: str) -> str:
    """Search the web for a query and return a few summarized results with sources."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{r['title']}: {r['body']} (source: {r['href']})" for r in results
    )


# ---- LLM config ----
# Swap "model" for whichever Claude model you have access to.
llm = LLM(
    model="anthropic/claude-sonnet-4-5",
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
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


# ---- Run ----
if __name__ == "__main__":
    topic = input("What topic should the crew write about? ")
    result = content_crew.kickoff(inputs={"topic": topic})
    print("\n\n=== FINAL ARTICLE ===\n")
    print(result)
