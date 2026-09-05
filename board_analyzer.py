import fitz
import re
import sys
import csv
from pathlib import Path


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

# Сколько строк текста брать до и после найденного компонента
CONTEXT_LINES = 12

# Шаблоны, похожие на имена NET
NET_PATTERNS = [
    r'\b[A-Z][A-Z0-9_+\-/.]{2,}\b',
    r'\b[A-Za-z][A-Za-z0-9_+\-/.]*_[A-Za-z0-9_+\-/.]+\b',
]

# Слова, которые не надо считать NET
IGNORE_WORDS = {
    "PAGE",
    "SHEET",
    "TITLE",
    "DATE",
    "SIZE",
    "REV",
    "REVISION",
    "DRAWING",
    "DOCUMENT",
    "NUMBER",
    "DESCRIPTION",
    "COMPONENT",
    "VALUE",
    "POWER",
    "GROUND",
    "INPUT",
    "OUTPUT",
    "PIN",
    "PINS",
    "NOTES",
    "NOTE",
}


def load_components(filename):
    components = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().upper()

            if not line:
                continue

            if line.startswith("#"):
                continue

            components.append(line)

    return components


def extract_pdf_pages(pdf_file):
    doc = fitz.open(pdf_file)

    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")

        lines = []

        for line in text.splitlines():
            line = line.strip()

            if line:
                lines.append(line)

        pages.append(
            {
                "page": page_number,
                "lines": lines,
            }
        )

    return pages


def component_regex(component):
    return re.compile(
        rf'(?<![A-Za-z0-9_]){re.escape(component)}(?![A-Za-z0-9_])',
        re.IGNORECASE
    )


def looks_like_component(value):
    return bool(
        re.fullmatch(
            r'(U|R|C|L|Q|D|J|P|TP|FB|F|K|Y|X|SW|CN)\d+[A-Z]?',
            value,
            re.IGNORECASE
        )
    )


def looks_like_number(value):
    return bool(
        re.fullmatch(
            r'[\d.]+([KMGUNPF]|OHM|V|A|HZ)?',
            value,
            re.IGNORECASE
        )
    )


def extract_possible_nets(text):
    candidates = set()

    for pattern in NET_PATTERNS:
        for match in re.findall(pattern, text):
            value = match.strip()

            if len(value) < 3:
                continue

            value_upper = value.upper()

            if value_upper in IGNORE_WORDS:
                continue

            if looks_like_component(value_upper):
                continue

            if looks_like_number(value_upper):
                continue

            if value_upper.startswith("HTTP"):
                continue

            candidates.add(value)

    return sorted(candidates)


def analyze_component(component, pages):
    regex = component_regex(component)

    results = []

    for page_data in pages:

        page_number = page_data["page"]
        lines = page_data["lines"]

        for line_number, line in enumerate(lines):

            if not regex.search(line):
                continue

            start = max(0, line_number - CONTEXT_LINES)
            end = min(len(lines), line_number + CONTEXT_LINES + 1)

            context_lines = lines[start:end]

            context_text = "\n".join(context_lines)

            nets = extract_possible_nets(context_text)

            results.append(
                {
                    "component": component,
                    "page": page_number,
                    "line": line_number + 1,
                    "matched_text": line,
                    "nets": nets,
                    "context": context_text,
                }
            )

    return results


def save_csv(results, output_file):
    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "Component",
                "Page",
                "PDF_Text_Line",
                "Matched_Text",
                "Possible_NETs",
            ]
        )

        for item in results:
            writer.writerow(
                [
                    item["component"],
                    item["page"],
                    item["line"],
                    item["matched_text"],
                    " | ".join(item["nets"]),
                ]
            )


def save_detailed_report(results, output_file):
    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        current_component = None

        for item in results:

            if current_component != item["component"]:

                current_component = item["component"]

                f.write("\n")
                f.write("=" * 80 + "\n")
                f.write(f"COMPONENT: {current_component}\n")
                f.write("=" * 80 + "\n")

            f.write("\n")
            f.write(
                f"PAGE: {item['page']}   "
                f"TEXT LINE: {item['line']}\n"
            )

            f.write(
                f"MATCH: {item['matched_text']}\n"
            )

            f.write("\nPossible NETs:\n")

            if item["nets"]:

                for net in item["nets"]:
                    f.write(f"  {net}\n")

            else:
                f.write("  NONE FOUND\n")

            f.write("\nContext:\n")
            f.write("-" * 60 + "\n")

            f.write(item["context"])
            f.write("\n")

            f.write("-" * 60 + "\n")


def main():

    if len(sys.argv) != 3:

        print()
        print("Usage:")
        print(
            "python board_analyzer.py "
            "schematic.pdf components.txt"
        )
        print()

        sys.exit(1)

    pdf_file = Path(sys.argv[1])
    components_file = Path(sys.argv[2])

    if not pdf_file.exists():
        print(f"ERROR: PDF not found: {pdf_file}")
        sys.exit(1)

    if not components_file.exists():
        print(
            f"ERROR: component file not found: "
            f"{components_file}"
        )
        sys.exit(1)

    print()
    print("Loading components...")

    components = load_components(
        components_file
    )

    print(
        f"Components loaded: {len(components)}"
    )

    print()
    print("Reading PDF...")

    pages = extract_pdf_pages(
        pdf_file
    )

    print(
        f"PDF pages: {len(pages)}"
    )

    all_results = []

    print()
    print("Searching components...")
    print()

    for component in components:

        results = analyze_component(
            component,
            pages
        )

        all_results.extend(results)

        if results:

            pages_found = sorted(
                set(
                    r["page"]
                    for r in results
                )
            )

            print(
                f"[FOUND] {component}"
                f" -> pages: "
                f"{', '.join(map(str, pages_found))}"
            )

            all_nets = set()

            for result in results:
                all_nets.update(
                    result["nets"]
                )

            if all_nets:

                print("        Possible NETs:")

                for net in sorted(all_nets):
                    print(
                        f"          {net}"
                    )

        else:

            print(
                f"[NOT FOUND] {component}"
            )

    csv_output = "component_nets.csv"

    txt_output = "component_nets_report.txt"

    save_csv(
        all_results,
        csv_output
    )

    save_detailed_report(
        all_results,
        txt_output
    )

    print()
    print("=" * 60)

    print(
        f"CSV saved: {csv_output}"
    )

    print(
        f"Detailed report saved: "
        f"{txt_output}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()