#!/usr/bin/env python3
"""Look at a corpus before designing anything.

Reports what is actually in the text and proposes hierarchy regexes derived from
it, so the ontology conversation starts from evidence instead of from the
filename and a guess about the domain.

    python scripts/inspect_corpus.py --input ./book.pdf
    python scripts/inspect_corpus.py --input ./corpus --sample 40 --show-sample

No LLM, no network. Sampling only: Forge owns production extraction, and this
deliberately reads a slice rather than the whole corpus so inspection stays
fast and free.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".html"}

# Ordered: the first family that fires is usually the real structure.
HEADING_FAMILIES = [
    (
        "numbered_keyword",
        r"^\s*(?P<kw>CHAPTER|Chapter|CHAPITRE|Chapitre|PART|Part|PARTIE|TITRE|TITLE|Article|ARTICLE|Section|SECTION|BOOK|LIVRE|Annex|ANNEXE|Appendix)"
        r"\s+(?P<num>[IVXLCDM]+|\d+(?:\.\d+)*)\b",
        r"^\s*{kw}\s+([IVXLCDM]+|\d+(?:\.\d+)*)\s*[-–—:.]?\s*(.*)$",
    ),
    (
        "decimal",
        r"^\s*(?P<num>\d+(?:\.\d+){1,3})\s+(?P<title>[A-Z][^\n]{2,80})$",
        r"^\s*(\d+(?:\.\d+){1,3})\s+(.+)$",
    ),
    (
        "markdown",
        r"^(?P<hashes>#{1,4})\s+(?P<title>.+)$",
        r"^{hashes}\s+(.+)$",
    ),
    (
        "allcaps",
        r"^(?P<title>[A-Z][A-Z0-9'\-]{2,}(?:\s+[A-Z0-9'\-&]+){0,8})\s*$",
        r"^([A-Z][A-Z0-9'\-]{2,}(?:\s+[A-Z0-9'\-&]+){0,8})\s*$",
    ),
    (
        "titlecase_short",
        r"^(?P<title>(?:[A-Z][a-z''\-]+)(?:\s+(?:[A-Z][a-z''\-]+|of|the|and|for|in|a))" r"{1,7})\s*$",
        r"^((?:[A-Z][a-z''\-]+)(?:\s+(?:[A-Z][a-z''\-]+|of|the|and|for|in|a)){1,7})\s*$",
    ),
]

FRONT_MATTER = re.compile(
    r"^\s*(CONTENTS|TABLE OF CONTENTS|INDEX|ACKNOWLEDG|FOREWORD|PREFACE|BIBLIOGRAPHY|"
    r"GLOSSARY|ABOUT THE AUTHOR|COPYRIGHT|DEDICATION|SOMMAIRE|TABLE DES MATI)",
    re.IGNORECASE,
)


# ------------------------------------------------------------------ loading

def pdf_pages(path: Path, max_pages: int) -> tuple[list[str], dict]:
    info = {"pages": None, "text_layer": False}
    try:
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"^Pages:\s+(\d+)", out, re.MULTILINE)
        if m:
            info["pages"] = int(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    try:
        out = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True, timeout=60).stdout
        info["text_layer"] = len([l for l in out.splitlines()[2:] if l.strip()]) > 0
    except Exception:  # noqa: BLE001
        info["text_layer"] = True  # assume, and let the yield check catch it

    pages: list[str] = []
    try:
        res = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", "-l", str(max_pages), str(path), "-"],
            capture_output=True, text=True, timeout=300,
        )
        if res.returncode == 0:
            pages = [p for p in res.stdout.split("\f") if p.strip()]
    except Exception:  # noqa: BLE001
        pass
    if not pages:
        try:
            from pypdf import PdfReader

            r = PdfReader(str(path))
            info["pages"] = info["pages"] or len(r.pages)
            pages = [(p.extract_text() or "") for p in r.pages[:max_pages]]
            pages = [p for p in pages if p.strip()]
        except Exception as e:  # noqa: BLE001
            print(f"  could not read {path.name}: {e}", file=sys.stderr)
    return pages, info


def strip_running_lines(pages: list[str]) -> tuple[list[str], list[str]]:
    """Remove page furniture so it does not pollute the heading statistics."""
    if len(pages) < 2:
        return pages, []
    fp = Counter()
    for p in pages:
        lines = [l for l in p.splitlines() if l.strip()]
        for l in set(re.sub(r"\d+", "#", l).strip().lower() for l in lines[:3] + lines[-3:]):
            if l and len(l) > 3:
                fp[l] += 1
    threshold = max(2, int(len(pages) * 0.5))
    running = {k for k, v in fp.items() if v >= threshold}
    cleaned = []
    for p in pages:
        lines = p.splitlines()
        nonblank = [i for i, l in enumerate(lines) if l.strip()]
        edge = set(nonblank[:3]) | set(nonblank[-3:])
        cleaned.append(
            "\n".join(
                l for i, l in enumerate(lines)
                if not (i in edge and re.sub(r"\d+", "#", l).strip().lower() in running)
            )
        )
    return cleaned, sorted(running)


def load(input_path: Path, max_pages: int):
    docs = []
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(
            p for p in input_path.rglob("*")
            if p.suffix.lower() in TEXT_SUFFIXES | {".pdf"}
        )
    if not files:
        sys.exit(
            f"no readable files under {input_path}\n"
            f"supported: {', '.join(sorted(TEXT_SUFFIXES | {'.pdf'}))}\n"
            "For .docx or .epub, convert to text first."
        )

    for f in files:
        if f.suffix.lower() == ".pdf":
            pages, info = pdf_pages(f, max_pages)
            if not info["text_layer"] or not pages:
                docs.append((f, "", {**info, "scanned": True}))
                continue
            cleaned, running = strip_running_lines(pages)
            docs.append((f, "\n\n".join(cleaned), {**info, "running": running, "scanned": False}))
        else:
            docs.append((f, f.read_text(encoding="utf-8", errors="replace"), {"scanned": False}))
    return docs


# --------------------------------------------------------------- analysis

def analyse_headings(text: str) -> list[dict]:
    out = []
    for name, detector, template in HEADING_FAMILIES:
        rx = re.compile(detector, re.MULTILINE)
        matches = list(rx.finditer(text))
        if len(matches) < 2:
            continue
        gd = matches[0].groupdict()
        by_kw: Counter[str] = Counter()
        for m in matches:
            key = (m.groupdict().get("kw") or m.groupdict().get("hashes") or name)
            by_kw[key] += 1
        out.append(
            {
                "family": name,
                "count": len(matches),
                "variants": by_kw.most_common(6),
                "template": template,
                "samples": [m.group(0).strip()[:70] for m in matches[:4]],
                "has_number": "num" in gd,
            }
        )
    return sorted(out, key=lambda d: -d["count"])


def propose_hierarchy(text: str, findings: list[dict]) -> list[dict]:
    """Turn detections into concrete, testable regexes ordered outermost first."""
    RANK = {
        "book": 0, "livre": 0, "part": 1, "partie": 1, "titre": 2, "title": 2,
        "chapter": 3, "chapitre": 3, "section": 4, "article": 5, "annex": 6,
        "annexe": 6, "appendix": 6,
    }
    proposals: list[dict] = []
    for f in findings:
        if f["family"] == "numbered_keyword":
            for kw, count in f["variants"]:
                level = kw.lower()
                pattern = f["template"].replace("{kw}", re.escape(kw))
                m = re.search(pattern, text, re.MULTILINE)
                proposals.append(
                    {
                        "level": level, "pattern": pattern, "count": count,
                        "rank": RANK.get(level, 4),
                        "example": m.group(0).strip()[:80] if m else "",
                    }
                )
        elif f["family"] == "markdown":
            for hashes, count in f["variants"]:
                pattern = f["template"].replace("{hashes}", re.escape(hashes))
                m = re.search(pattern, text, re.MULTILINE)
                proposals.append(
                    {
                        "level": f"h{len(hashes)}", "pattern": pattern, "count": count,
                        "rank": len(hashes),
                        "example": m.group(0).strip()[:80] if m else "",
                    }
                )
        else:
            m = re.search(f["template"], text, re.MULTILINE)
            proposals.append(
                {
                    "level": f["family"], "pattern": f["template"], "count": f["count"],
                    "rank": 7,
                    "example": m.group(0).strip()[:80] if m else "",
                }
            )

    seen, uniq, dropped = set(), [], []
    for p in sorted(proposals, key=lambda p: (p["rank"], -p["count"])):
        if p["level"] in seen:
            continue
        seen.add(p["level"])
        # One occurrence in a sample is usually noise, but on a short sample it can
        # be a real outer level. Surface it rather than discarding it silently.
        (uniq if p["count"] >= 2 else dropped).append(p)
    for d in dropped:
        d["low_confidence"] = True
    # Re-sort by rank after merging. hierarchy must be outermost-first, so a
    # low-confidence outer level cannot simply be appended at the end.
    merged = sorted(uniq + dropped, key=lambda p: (p["rank"], -p["count"]))
    return merged[:6]


def candidate_entities(text: str, top: int = 25) -> list[tuple[str, int]]:
    """Recurring capitalised noun phrases. A hint at node types, not an answer:
    frequency finds what the corpus talks about, not what users will ask for."""
    stop = {
        "The", "This", "That", "These", "Those", "It", "If", "When", "For", "But",
        "And", "You", "Your", "They", "There", "Then", "With", "From", "Chapter",
        "Figure", "Table", "Page", "Note", "See", "One", "Two", "Three", "First",
        "Second", "Third", "Now", "After", "Before", "While", "Since", "Because",
    }
    phrases = re.findall(r"\b([A-Z][a-z]{2,}(?:\s+[a-z]{2,}){0,2}\s+[a-z]{3,})\b", text)
    counts: Counter[str] = Counter()
    for p in phrases:
        head = p.split()[0]
        if head in stop:
            continue
        counts[p.lower()] += 1
    return [(p, c) for p, c in counts.most_common(top * 3) if c >= 3][:top]


def report(doc_path: Path, text: str, meta: dict, args) -> None:
    print(f"\n{'=' * 74}\n{doc_path.name}\n{'=' * 74}")

    if meta.get("scanned"):
        print("  NO TEXT LAYER. This is a scanned or raster document.")
        print("  OCR it before designing anything:")
        print(f"    ocrmypdf --force-ocr -l eng '{doc_path}' '{doc_path.stem}_ocr.pdf'")
        return

    lines = text.splitlines()
    nonblank = [l for l in lines if l.strip()]
    print(f"  sampled      : {meta.get('pages') or '?'} pages total, {len(text):,} chars read")
    print(f"  lines        : {len(nonblank):,} non-blank")
    if meta.get("running"):
        print(f"  page furniture stripped: {len(meta['running'])} repeating line(s)")
        for r in meta["running"][:3]:
            print(f"      {r[:64]}")

    fm = [
        (i, l.strip()[:60]) for i, l in enumerate(lines)
        if l.strip() and FRONT_MATTER.match(l.strip())
    ]
    if fm:
        print(f"\n  non-content regions found ({len(fm)}). Declare these in structure.skip_regions;")
        print("  they match heading patterns and cost tokens to extract nothing:")
        for _, l in fm[:6]:
            print(f"      {l}")

    findings = analyse_headings(text)
    if not findings:
        print("\n  NO HEADING STRUCTURE DETECTED.")
        print("  Either the text layer is mangled, or this is continuous prose.")
        print("  Read the sample before proposing a hierarchy; do not invent one.")
    else:
        print("\n  heading families detected:")
        for f in findings[:4]:
            variants = ", ".join(f"{k}({v})" for k, v in f["variants"][:4])
            print(f"      {f['family']:<18} {f['count']:>5} matches   {variants}")
            for s in f["samples"][:2]:
                print(f"          {s}")

        proposals = propose_hierarchy(text, findings)
        if proposals:
            print("\n  proposed structure.hierarchy (verify every example before using):\n")
            print("  hierarchy:")
            confident = [p for p in proposals if not p.get("low_confidence")]
            for p in proposals:
                flag = "   # only 1 match in sample: confirm on the full corpus" if p.get("low_confidence") else ""
                print(f"    - level: {p['level']}{flag}")
                print(f"      pattern: '{p['pattern']}'")
                if p["example"]:
                    print(f"      example: \"{p['example']}\"")
            deepest = (confident or proposals)[-1]
            print(f"\n    chunk_at: {deepest['level']}   # {deepest['count']} chunks from this sample")

            # Measure from match positions, not re.split: a pattern with capture
            # groups makes split return the groups as elements too, which reports
            # a median of a dozen characters and looks like catastrophic
            # over-splitting when nothing is wrong.
            marks = [m.start() for m in re.finditer(deepest["pattern"], text, re.MULTILINE)]
            bounds = marks + [len(text)]
            sizes = sorted(
                len(text[bounds[i]:bounds[i + 1]].strip()) for i in range(len(marks))
            )
            if sizes:
                med = sizes[len(sizes) // 2]
                print(f"    # chunk size at that level: median {med}, max {sizes[-1]} chars")
                if med < 200:
                    print("    # WARNING: very small. Likely over-splitting; relations will be cut in half.")
                if sizes[-1] > 12000:
                    print("    # note: some units are large; set max_chunk_chars and a subsplit_pattern.")

    ents = candidate_entities(text)
    if ents:
        print("\n  recurring noun phrases (a hint at node types, not an answer):")
        for p, c in ents[:16]:
            print(f"      {c:>4}  {p}")
        print("\n  Frequency shows what the corpus talks about, not what users will ask.")
        print("  Decide node types from the workload, then check they appear here.")

    if args.show_sample:
        print("\n  --- first 1500 chars ---")
        print("\n".join("  " + l for l in text[:1500].splitlines()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--sample", type=int, default=30, help="PDF pages to read per document")
    ap.add_argument("--show-sample", action="store_true")
    args = ap.parse_args()

    docs = load(Path(args.input), args.sample)
    print(f"{len(docs)} document(s)")
    for path, text, meta in docs:
        report(path, text, meta, args)

    print(f"\n{'=' * 74}")
    print("Next: propose the ontology from the workload, not from this output.")
    print("Ask what questions this corpus must answer, then check the types you")
    print("need actually appear above. Get sign-off before any extraction runs.")


if __name__ == "__main__":
    main()
