"""Import and clean research papers from CSV exports."""

import argparse
import csv
import json
import re
import unicodedata

from collections import Counter
from datetime import date
from pathlib import Path

from app.corpus import DATA_DIR


COUNTRY_ALIASES = {
    "usa": "United States",
    "u.s.": "United States",
    "us": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "south korea": "South Korea",
}

COUNTRY_CODES = {
    "United States": "us",
    "China": "cn",
    "India": "in",
    "Germany": "de",
    "United Kingdom": "gb",
    "Japan": "jp",
    "France": "fr",
    "Italy": "it",
    "Canada": "ca",
    "Australia": "au",
    "South Korea": "kr",
    "Spain": "es",
    "Netherlands": "nl",
    "Brazil": "br",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_title(title):
    """Ignore case, punctuation and whitespace differences."""
    text = unicodedata.normalize("NFKC", clean(title)).casefold()
    return "".join(char for char in text if char.isalnum())


def normalize_doi(doi):
    """Make DOI URLs and plain DOI strings comparable."""
    value = clean(doi).casefold()

    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if value.startswith(prefix):
            value = value[len(prefix):]

    return value.strip().rstrip("/")


def split_values(value):
    """Split semicolon- or pipe-separated values."""
    value = clean(value)

    if not value:
        return []

    return [
        item.strip()
        for item in re.split(r"[;|]", value)
        if item.strip()
    ]


def parse_topics(value):
    """Support JSON arrays as well as ordinary separated values."""
    value = clean(value)

    if not value:
        return []

    try:
        parsed = json.loads(value)

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]
    except json.JSONDecodeError:
        pass

    return split_values(value)


def normalize_country(value):
    country = clean(value)

    if not country:
        return ""

    alias = COUNTRY_ALIASES.get(country.casefold())

    if alias:
        return alias

    for known in COUNTRY_CODES:
        if known.casefold() == country.casefold():
            return known

    return country


def load_taxonomy():
    path = DATA_DIR / "taxonomy.json"
    taxonomy = json.loads(path.read_text(encoding="utf-8"))

    countries = {
        item["name"] for item in taxonomy["countries"]
    }

    topics = {
        topic
        for domain in taxonomy["domains"]
        for topic in domain["topics"]
    }

    return countries, topics


def build_paper(row, paper_id, known_topics):
    title = clean(row.get("title"))
    abstract = clean(row.get("abstract"))

    raw_year = clean(row.get("year"))
    raw_date = clean(row.get("date"))

    publication_year = None
    publication_date = raw_date or None

    if raw_year:
        try:
            publication_year = int(raw_year)
        except ValueError:
            pass

    if publication_year is None and raw_date:
        try:
            publication_year = date.fromisoformat(
                raw_date[:10]
            ).year
        except ValueError:
            pass

    if publication_date is None and publication_year:
        publication_date = f"{publication_year}-01-01"

    country = normalize_country(
        row.get("affiliation_country")
    )

    organizations = split_values(
        row.get("institutions")
    )

    all_topics = parse_topics(row.get("topics"))

    recognized_topics = [
        topic for topic in all_topics
        if topic in known_topics
    ]

    other_topics = [
        topic for topic in all_topics
        if topic not in known_topics
    ]

    methods = split_values(row.get("methods"))

    keywords = list(dict.fromkeys(
        [topic.casefold() for topic in all_topics]
        + [method.casefold() for method in methods]
    ))

    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": [],
        "publication_date": publication_date,
        "publication_year": publication_year,
        "journal": None,
        "conference": None,
        "publisher": None,
        "doi": clean(row.get("doi")) or None,
        "source_url": None,
        "open_access_url": None,
        "country": country,
        "organizations": organizations,
        "citation_count": None,
        "reference_count": None,
        "research_type": None,
        "derived": {
            "topics": recognized_topics,
            "subtopics": [],
            "missions": [],
            "spacecraft": [],
            "technologies": [],
            "methods": methods,
            "entities": [],
            "keywords": keywords,
            "embedding_reference": None,
            "other_topics": other_topics,
        },
        "is_synthetic": False,
    }


def ingest(csv_path, dry_run=False, output=None):
    csv_path = Path(csv_path)

    if not csv_path.exists():
        sample_path = Path(__file__).resolve().parents[1].parent / "sample_export.csv"
        if csv_path.name == "sample_export.csv" and sample_path.exists():
            csv_path = sample_path
        else:
            raise FileNotFoundError(
                f"CSV file not found: {csv_path}"
            )

    known_countries, known_topics = load_taxonomy()

    rows_in = 0
    skipped = Counter()
    countries_without_iso = Counter()
    topics_outside_taxonomy = Counter()

    papers = []
    seen_titles = set()
    seen_dois = set()

    columns_used = {}

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames or []

        column_mapping = {
            "paper_id": "id",
            "title": "title",
            "abstract": "abstract",
            "country": "affiliation_country",
            "institutions": "institutions",
            "topics": "topics",
            "methods": "methods",
            "doi": "doi",
            "year": "year",
            "date": "date",
        }

        for field, column in column_mapping.items():
            if column in columns:
                columns_used[field] = column

        for row in reader:
            rows_in += 1

            abstract = clean(row.get("abstract"))

            if not abstract:
                skipped["no abstract"] += 1
                continue

            title = clean(row.get("title"))

            if not title:
                skipped["no title"] += 1
                continue

            doi = normalize_doi(row.get("doi"))
            normalized_title = normalize_title(title)

            if (
                normalized_title in seen_titles
                or (doi and doi in seen_dois)
            ):
                continue

            seen_titles.add(normalized_title)

            if doi:
                seen_dois.add(doi)

            country = normalize_country(
                row.get("affiliation_country")
            )

            if country and country not in known_countries:
                countries_without_iso[country] += 1

            for topic in parse_topics(row.get("topics")):
                if topic not in known_topics:
                    topics_outside_taxonomy[topic] += 1

            paper_id = (
                clean(row.get("id"))
                or f"import-{len(papers) + 1:05d}"
            )

            papers.append(
                build_paper(row, paper_id, known_topics)
            )

    duplicates_removed = (
        rows_in
        - len(papers)
        - sum(skipped.values())
    )

    report = {
        "rows_in": rows_in,
        "papers_out": len(papers),
        "skipped": dict(skipped),
        "duplicates_removed": duplicates_removed,
        "columns_used": columns_used,
        "countries_without_iso_code": dict(
            countries_without_iso
        ),
        "topics_outside_taxonomy": dict(
            topics_outside_taxonomy
        ),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if dry_run:
        print("\nDry run: nothing written.")
        return

    output = Path(
        output or DATA_DIR / "imported_papers.json"
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(papers, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nImported papers written to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean and import research papers from CSV."
    )

    parser.add_argument("csv_file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate a report without writing files.",
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path.",
    )

    args = parser.parse_args()

    ingest(
        args.csv_file,
        dry_run=args.dry_run,
        output=args.output,
    )


if __name__ == "__main__":
    main()