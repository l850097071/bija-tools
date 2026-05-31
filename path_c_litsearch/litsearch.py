"""
litsearch — Academic literature deep search
Input research question → Semantic Scholar API → structured review
用法: python litsearch.py "CO2 reduction on Cu catalysts" --years 2022-2026
"""

import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


@dataclass
class Paper:
    title: str
    authors: list[str]
    year: int
    venue: str
    citations: int
    paper_id: str
    abstract: str = ""
    url: str = ""


def search_papers(query: str, limit: int = 20, year_range: str = None) -> list[Paper]:
    """Search Semantic Scholar API."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,citationCount,paperId,abstract,url"
    }
    if year_range:
        # e.g. "2022-2026"
        parts = year_range.split("-")
        if len(parts) == 2:
            params["year"] = f"{parts[0]}-{parts[1]}"

    url = f"{SEMANTIC_SCHOLAR_API}/paper/search?{urllib.parse.urlencode(params)}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "litsearch/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = (attempt + 1) * 5
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                return [Paper(title=f"HTTP {e.code}: rate limited. Retry later or use API key.",
                              authors=[], year=0, venue="", citations=0, paper_id="")]
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return [Paper(title=f"API Error: {e}", authors=[], year=0,
                              venue="", citations=0, paper_id="")]

    papers = []
    for p in data.get("data", []):
        authors = [a.get("name", "?") for a in (p.get("authors") or [])]
        papers.append(Paper(
            title=p.get("title", "Untitled"),
            authors=authors,
            year=p.get("year", 0) or 0,
            venue=p.get("venue", "") or "",
            citations=p.get("citationCount", 0) or 0,
            paper_id=p.get("paperId", ""),
            abstract=p.get("abstract", "") or "",
            url=p.get("url", "") or f"https://api.semanticscholar.org/{p.get('paperId','')}"
        ))
    return papers


def group_by_theme(papers: list[Paper]) -> dict:
    """Simple keyword-based theme clustering."""
    themes = {}
    keywords = {
        "DFT": ["dft", "density functional", "first-principles", "vasp", "ab initio"],
        "Machine Learning": ["machine learning", "neural network", "deep learning", "ml", "ai"],
        "Catalysis": ["catalysis", "catalyst", "catalytic", "reaction mechanism"],
        "CO2 Reduction": ["co2", "carbon dioxide", "co2rr", "electroreduction"],
        "Experiment": ["experimental", "synthesis", "characterization", "xrd", "tem", "xps"],
        "Review": ["review", "perspective", "roadmap", "progress"],
    }
    for paper in papers:
        text = (paper.title + " " + paper.abstract).lower()
        matched = False
        for theme, kws in keywords.items():
            if any(kw in text for kw in kws):
                themes.setdefault(theme, []).append(paper)
                matched = True
        if not matched:
            themes.setdefault("Other", []).append(paper)
    return themes


def generate_report(query: str, papers: list[Paper], themes: dict) -> str:
    """Generate structured literature review."""
    lines = [
        f"Literature Search Report",
        f"{'='*60}",
        f"Query: {query}",
        f"Date: {time.strftime('%Y-%m-%d')}",
        f"Papers found: {len(papers)}",
        f"",
    ]

    # Summary stats
    years = [p.year for p in papers if p.year > 0]
    if years:
        lines.append(f"Year range: {min(years)}-{max(years)}")
    total_cites = sum(p.citations for p in papers)
    top_venue = max(set(p.venue for p in papers if p.venue), key=lambda v: sum(1 for p in papers if p.venue == v), default="N/A")
    lines.append(f"Total citations: {total_cites}")
    lines.append(f"Top venue: {top_venue}")
    lines.append("")

    # Thematic breakdown
    lines.append("## Thematic Breakdown")
    for theme, ps in sorted(themes.items(), key=lambda x: -len(x[1])):
        lines.append(f"  {theme}: {len(ps)} papers ({len(ps)*100//len(papers)}%)")
    lines.append("")

    # Top papers
    lines.append("## Top Cited Papers")
    for i, p in enumerate(sorted(papers, key=lambda x: -x.citations)[:10], 1):
        authors_short = p.authors[0].split()[-1] if p.authors else "?"
        if len(p.authors) > 2:
            authors_short += f" et al."
        elif len(p.authors) == 2:
            authors_short += f", {p.authors[1].split()[-1]}"
        lines.append(f"  {i}. [{p.citations}] {p.title}")
        lines.append(f"     {authors_short} ({p.year}) — {p.venue}")
        if p.abstract:
            lines.append(f"     {p.abstract[:200]}...")
        lines.append("")

    # Research gap analysis (placeholder)
    lines.append("## Research Gaps (AI-assisted analysis)")
    lines.append("  * Consider: Compare findings across DFT and experimental papers for contradictory results.")
    lines.append("  * Consider: Track whether ML papers use consistent benchmarks for fair comparison.")
    lines.append("  * Consider: Check if review papers identify the same gaps as recent primary research.")
    lines.append("  * Action: Pick top 3 most-cited papers + top 3 most recent papers for deep read.")
    lines.append("")

    # Reading list
    lines.append("## Priority Reading List")
    recent = sorted([p for p in papers if p.year >= 2024], key=lambda x: -x.citations)
    for i, p in enumerate(recent[:5], 1):
        lines.append(f"  {i}. {p.title} ({p.year}, {p.citations} cites)")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Academic literature deep search")
    parser.add_argument("query", help="Research question or keywords")
    parser.add_argument("--years", help="Year range (e.g. 2022-2026)", default="2022-2026")
    parser.add_argument("--limit", type=int, default=20, help="Max papers")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    print(f"Searching: {args.query}")
    papers = search_papers(args.query, args.limit, args.years)

    if not papers:
        print("No results.")
        return

    themes = group_by_theme(papers)
    report = generate_report(args.query, papers, themes)

    if args.json:
        output = {
            "query": args.query,
            "total": len(papers),
            "themes": {k: len(v) for k, v in themes.items()},
            "papers": [asdict(p) for p in papers]
        }
        if args.output:
            Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False))
            print(f"JSON saved to {args.output}")
        else:
            print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if args.output:
            Path(args.output).write_text(report)
            print(f"Report saved to {args.output}")
        print(report)


if __name__ == "__main__":
    main()
