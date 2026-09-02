import os
import re
import sys


# ==========================================================
# ROOT DIRECTORY
# ==========================================================

ROOT_BASE = "."

if len(sys.argv) < 2:
    print("Usage: python3 search_fails.py FOLDER_NAME")
    sys.exit(1)

folder_name = sys.argv[1]

ROOT = os.path.join(
    ROOT_BASE,
    folder_name
)


# ==========================================================
# KEYWORDS FILE
#
# Examples:
#
# Test '
#
# AMD_SERIAL_NUMBER #" ",5
#
# TEST_STAGE #" ",5,6
#
# TEST_STAGE #" ",3,7
#
# Result #",",4,5,6
#
# regex:dom\d+ #" ",2,4
#
#
# No #:
#     output full matching line
#
# With #:
#
#     #"separator",column,column,...
#
# Column numbering starts from 1 like awk
# ==========================================================

KEYWORDS_FILE = "keywords.txt"

KEYWORDS = []


with open(
    KEYWORDS_FILE,
    "r",
    encoding="utf-8"
) as f:

    for line in f:

        line = line.rstrip("\r\n")

        if not line:
            continue

        keyword = line
        separator = None
        columns = []

        # --------------------------------------------------
        # Optional column extraction
        # --------------------------------------------------

        if "#" in line:

            keyword_part, options_part = line.split(
                "#",
                1
            )

            keyword = keyword_part.rstrip()

            # Examples:
            #
            # " ",5
            # " ",5,6
            # " ",3,7
            # ",",4,5,6

            match = re.fullmatch(
                r'\s*"([^"]*)"\s*,\s*'
                r'(\d+(?:\s*,\s*\d+)*)\s*',
                options_part
            )

            if not match:

                print(
                    "Invalid keyword format:"
                )

                print(
                    repr(line)
                )

                print(
                    'Example: TEST_STAGE #" ",5,6'
                )

                continue

            separator = match.group(1)

            columns = [
                int(number.strip())
                for number
                in match.group(2).split(",")
            ]

        KEYWORDS.append({
            "keyword": keyword,
            "separator": separator,
            "columns": columns
        })


# ==========================================================
# EXCLUDE PHRASES
# ==========================================================

EXCLUDE_FILE = "exclude.txt"

with open(
    EXCLUDE_FILE,
    "r",
    encoding="utf-8"
) as f:

    EXCLUDE_PHRASES = [
        line.rstrip("\r\n")
        for line in f
        if line.rstrip("\r\n") != ""
    ]


# ==========================================================
# OUTPUT FILE
# ==========================================================

OUTPUT_FILE = os.path.join(
    ROOT,
    "search_results.txt"
)


# ==========================================================
# BINARY EXTENSIONS TO SKIP
# ==========================================================

SKIP_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".sys",

    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",

    ".mp3",
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",

    ".zip",
    ".rar",
    ".7z",
    ".gz",
    ".tar",

    ".iso",
    ".bin",
    ".pdf",
}


# ==========================================================
# FILE NAME PATTERNS TO SKIP
#
# Examples:
#
# abc.log.1
# abc.log.17
# abc.log.500
# ==========================================================

SKIP_FILE_PATTERNS = [
    r"\.log\.\d+$",
]


# ==========================================================
# GET FIRST DIRECTORY AFTER ROOT
# ==========================================================

def get_top_directory(directory):

    relative_path = os.path.relpath(
        directory,
        ROOT
    )

    if relative_path == ".":
        return "ROOT"

    return relative_path.split(
        os.sep
    )[0]


# ==========================================================
# SPLIT LINE INTO FIELDS
# ==========================================================

def split_fields(
    line,
    separator
):

    text = line.rstrip(
        "\r\n"
    )

    # ------------------------------------------------------
    # Space behaves similar to awk
    #
    # Multiple spaces/tabs collapse into one separator
    # ------------------------------------------------------

    if separator == " ":
        return text.split()

    # ------------------------------------------------------
    # TAB support
    #
    # Example in keywords.txt:
    #
    # TEST #"\t",2,5
    # ------------------------------------------------------

    if separator == r"\t":
        separator = "\t"

    # ------------------------------------------------------
    # Literal separator
    # ------------------------------------------------------

    return text.split(
        separator
    )


# ==========================================================
# EXTRACT SELECTED COLUMNS
# ==========================================================

def extract_columns(
    line,
    separator,
    columns
):

    fields = split_fields(
        line,
        separator
    )

    selected = []

    for column in columns:

        # User:
        # column 1
        #
        # Python:
        # index 0

        index = column - 1

        if 0 <= index < len(fields):

            selected.append(
                fields[index].strip()
            )

        else:

            selected.append(
                f"<COLUMN_{column}_NOT_FOUND>"
            )

    return selected


# ==========================================================
# CHECK KEYWORD MATCH
# ==========================================================

def keyword_matches(
    keyword,
    line
):

    # ------------------------------------------------------
    # REGEX MODE
    #
    # Example:
    #
    # regex:dom\d+
    # ------------------------------------------------------

    if keyword.startswith(
        "regex:"
    ):

        pattern = keyword[
            len("regex:"):
        ]

        try:

            return bool(
                re.search(
                    pattern,
                    line
                )
            )

        except re.error as error:

            print(
                f"Invalid regex: {keyword}"
            )

            print(
                f"Reason: {error}"
            )

            return False

    # ------------------------------------------------------
    # LITERAL MODE
    #
    # Exact character sequence
    #
    # Example:
    #
    # Test '
    #
    # Finds:
    #
    # Test 'SYSTEM:CHECK'
    #
    # Does NOT find:
    #
    # Test'
    # Test  '
    # TEST '
    # ------------------------------------------------------

    return keyword in line


# ==========================================================
# SEARCH ONE FILE
# ==========================================================

def search_file(
    file_path
):

    found = []

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1
            ):

                # ==========================================
                # EXCLUDES
                # ==========================================

                if any(
                    exclude.lower()
                    in line.lower()
                    for exclude
                    in EXCLUDE_PHRASES
                ):
                    continue

                matches = []

                # ==========================================
                # CHECK ALL KEYWORDS
                # ==========================================

                for rule in KEYWORDS:

                    keyword = rule[
                        "keyword"
                    ]

                    separator = rule[
                        "separator"
                    ]

                    columns = rule[
                        "columns"
                    ]

                    if not keyword_matches(
                        keyword,
                        line
                    ):
                        continue

                    # --------------------------------------
                    # FULL LINE
                    # --------------------------------------

                    if not columns:

                        matches.append({
                            "keyword": keyword,
                            "mode": "full_line",
                            "text": line.rstrip("\r\n")
                        })

                    # --------------------------------------
                    # SELECTED COLUMNS
                    # --------------------------------------

                    else:

                        values = extract_columns(
                            line,
                            separator,
                            columns
                        )

                        matches.append({
                            "keyword": keyword,
                            "mode": "columns",
                            "values": values
                        })

                # ==========================================
                # SAVE MATCHED LINE
                # ==========================================

                if matches:

                    found.append({
                        "line": line_number,
                        "matches": matches
                    })

    except (
        PermissionError,
        OSError
    ) as error:

        print(
            f"Cannot read: {file_path}"
        )

        print(
            f"Reason: {error}"
        )

    return found


# ==========================================================
# MAIN
# ==========================================================

def main():

    # ======================================================
    # CHECK ROOT
    # ======================================================

    if not os.path.isdir(
        ROOT
    ):

        print(
            f"ROOT directory not found: {ROOT}"
        )

        return


    # ======================================================
    # CLEAR OLD OUTPUT
    # ======================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ):
        pass


    # ======================================================
    # RECURSIVE WALK
    # ======================================================

    for (
        directory,
        subdirectories,
        files
    ) in os.walk(
        ROOT
    ):

        for filename in files:

            file_path = os.path.join(
                directory,
                filename
            )

            # ==============================================
            # DO NOT SCAN OUTPUT FILE
            # ==============================================

            if (
                os.path.abspath(file_path)
                ==
                os.path.abspath(OUTPUT_FILE)
            ):
                continue


            # ==============================================
            # SKIP FILE NAME PATTERNS
            # ==============================================

            if any(
                re.search(
                    pattern,
                    filename,
                    re.IGNORECASE
                )
                for pattern
                in SKIP_FILE_PATTERNS
            ):
                continue


            # ==============================================
            # SKIP BINARY EXTENSIONS
            # ==============================================

            extension = os.path.splitext(
                filename
            )[1].lower()

            if extension in SKIP_EXTENSIONS:
                continue


            # ==============================================
            # SCAN FILE
            # ==============================================

            print(
                f"Scanning: {file_path}",
                flush=True
            )

            found = search_file(
                file_path
            )

            if not found:
                continue


            # ==============================================
            # TOP DIRECTORY
            # ==============================================

            top_directory = get_top_directory(
                directory
            )


            # ==============================================
            # WRITE REPORT
            # ==============================================

            with open(
                OUTPUT_FILE,
                "a",
                encoding="utf-8"
            ) as output:

                output.write("\n")

                output.write(
                    "=" * 80
                    + "\n"
                )

                output.write(
                    f"Directory: "
                    f"{top_directory}\n"
                )

                output.write(
                    f"File:      "
                    f"{filename}\n"
                )

                output.write(
                    f"Full Path: "
                    f"{file_path}\n"
                )

                output.write(
                    "-" * 80
                    + "\n"
                )


                # ==========================================
                # WRITE MATCHES
                # ==========================================

                for match in found:

                    for item in match[
                        "matches"
                    ]:

                        keyword = item[
                            "keyword"
                        ]

                        # ----------------------------------
                        # FULL LINE
                        #
                        # Example:
                        #
                        # [Test '] Line 350:
                        # Test 'SYSTEM:CHECK'
                        #
                        # Actually output is one line:
                        #
                        # [Test '] Line 350: Test 'SYSTEM...
                        # ----------------------------------

                        if (
                            item["mode"]
                            == "full_line"
                        ):

                            output.write(
                                f"[{keyword}] "
                                f"Line {match['line']}: "
                                f"{item['text']}\n"
                            )

                        # ----------------------------------
                        # SELECTED COLUMNS
                        #
                        # Example:
                        #
                        # [TEST_STAGE] Line 125: VALUE5 VALUE6
                        # ----------------------------------

                        else:

                            selected_text = " ".join(
                                item["values"]
                            )

                            output.write(
                                f"[{keyword}] "
                                f"Line {match['line']}: "
                                f"{selected_text}\n"
                            )


    # ======================================================
    # FINISHED
    # ======================================================

    print()

    print(
        "=" * 60
    )

    print(
        "Search completed."
    )

    print(
        f"Results saved to: "
        f"{OUTPUT_FILE}"
    )

    print(
        "=" * 60
    )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":
    main()