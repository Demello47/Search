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
# FORMAT:
#
# Test '
#
# AMD_SERIAL_NUMBER #" ",5
#
# TEST_STAGE #" ",3,7
#
# Result #",",4,5,6
#
# regex:dom\d+ #" ",2,4
#
#
# Если # отсутствует:
#     выводится вся найденная строка.
#
# Если # присутствует:
#
#     #"разделитель",столбец,столбец,...
#
# Нумерация столбцов начинается с 1,
# как в awk.
# ==========================================================

KEYWORDS_FILE = "keywords.txt"

KEYWORDS = []


with open(
    KEYWORDS_FILE,
    "r",
    encoding="utf-8"
) as f:

    for line in f:

        line = line.rstrip(
            "\r\n"
        )

        if not line:
            continue


        # --------------------------------------------------
        # Значения по умолчанию
        # --------------------------------------------------

        keyword = line

        separator = None

        columns = []


        # --------------------------------------------------
        # Есть настройки столбцов
        #
        # Example:
        #
        # AMD_SERIAL_NUMBER #" ",5
        #
        # TEST_STAGE #" ",3,7
        # --------------------------------------------------

        if "#" in line:

            keyword_part, options_part = line.split(
                "#",
                1
            )


            # Убираем пробелы только справа от keyword.
            # Внутренние пробелы keyword НЕ меняем.
            keyword = keyword_part.rstrip()


            # ----------------------------------------------
            # Разбираем:
            #
            # " ",5
            #
            # " ",3,7
            #
            # ",",4,5,6
            # ----------------------------------------------

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
                    'Expected example: '
                    'AMD_SERIAL_NUMBER #" ",3,5'
                )

                continue


            separator = match.group(1)


            # ----------------------------------------------
            # Columns:
            #
            # "3,7"
            #
            # ->
            #
            # [3, 7]
            # ----------------------------------------------

            columns = [

                int(number.strip())

                for number
                in match.group(2).split(",")

            ]


        # --------------------------------------------------
        # SAVE RULE
        # --------------------------------------------------

        KEYWORDS.append({

            "keyword":
                keyword,

            "separator":
                separator,

            "columns":
                columns
        })


# ==========================================================
# SHOW LOADED RULES
# ==========================================================

print()
print("=" * 60)
print("KEYWORDS LOADED")
print("=" * 60)


for rule in KEYWORDS:

    print(
        "Keyword:",
        repr(
            rule["keyword"]
        )
    )

    if rule["columns"]:

        print(
            "  Separator:",
            repr(
                rule["separator"]
            )
        )

        print(
            "  Columns:",
            rule["columns"]
        )

    else:

        print(
            "  Output: FULL LINE"
        )


print("=" * 60)
print()


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

def get_top_directory(
    directory
):

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
# SPLIT LINE INTO COLUMNS
# ==========================================================

def split_fields(
    line,
    separator
):

    # Remove only newline
    text = line.rstrip(
        "\r\n"
    )


    # ------------------------------------------------------
    # Separator = one space
    #
    # Behaves similar to awk:
    #
    # ABC     DEF     GHI
    #
    # becomes:
    #
    # ABC
    # DEF
    # GHI
    #
    # Multiple spaces/tabs are collapsed.
    # ------------------------------------------------------

    if separator == " ":

        return text.split()


    # ------------------------------------------------------
    # TAB support:
    #
    # keywords.txt:
    #
    # TEST #"\t",2,5
    # ------------------------------------------------------

    if separator == r"\t":

        separator = "\t"


    # ------------------------------------------------------
    # Literal separator
    #
    # Examples:
    #
    # ,
    # :
    # |
    # ;
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


    extracted = []


    for column in columns:

        # ----------------------------------------------
        # User columns start from 1.
        #
        # Python list starts from 0.
        #
        # Column 1 -> index 0
        # Column 5 -> index 4
        # ----------------------------------------------

        index = column - 1


        if (
            index >= 0
            and index < len(fields)
        ):

            value = fields[
                index
            ].strip()


            extracted.append({

                "column":
                    column,

                "value":
                    value
            })


        else:

            extracted.append({

                "column":
                    column,

                "value":
                    f"<COLUMN_{column}_NOT_FOUND>"
            })


    return extracted


# ==========================================================
# CHECK IF KEYWORD MATCHES
# ==========================================================

def keyword_matches(
    keyword,
    line
):

    # ------------------------------------------------------
    # REGEX MODE
    #
    # keywords.txt:
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
                f"Invalid regex: "
                f"{keyword}"
            )

            print(
                f"Reason: {error}"
            )

            return False


    # ------------------------------------------------------
    # LITERAL MODE
    #
    # Exact sequence of characters.
    #
    # keyword:
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
                # EXCLUDE CHECK
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
                # CHECK EVERY KEYWORD RULE
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


                    # --------------------------------------
                    # Keyword not found
                    # --------------------------------------

                    if not keyword_matches(
                        keyword,
                        line
                    ):

                        continue


                    # --------------------------------------
                    # Keyword FOUND
                    #
                    # No columns configured:
                    #
                    # save full line
                    # --------------------------------------

                    if not columns:

                        matches.append({

                            "keyword":
                                keyword,

                            "mode":
                                "full_line",

                            "separator":
                                None,

                            "columns":
                                [],

                            "values":
                                [],

                            "text":
                                line.rstrip(
                                    "\r\n"
                                )
                        })


                    # --------------------------------------
                    # Columns configured
                    # --------------------------------------

                    else:

                        values = extract_columns(

                            line,

                            separator,

                            columns

                        )


                        matches.append({

                            "keyword":
                                keyword,

                            "mode":
                                "columns",

                            "separator":
                                separator,

                            "columns":
                                columns,

                            "values":
                                values,

                            "text":
                                line.rstrip(
                                    "\r\n"
                                )
                        })


                # ==========================================
                # SAVE PHYSICAL LINE ONCE
                # ==========================================

                if matches:

                    found.append({

                        "line":
                            line_number,

                        "matches":
                            matches,

                        "full_text":
                            line.rstrip(
                                "\r\n"
                            )
                    })


    except (
        PermissionError,
        OSError
    ) as error:

        print(
            f"Cannot read: "
            f"{file_path}"
        )

        print(
            f"Reason: "
            f"{error}"
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
            f"ROOT directory "
            f"not found: "
            f"{ROOT}"
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
                os.path.abspath(
                    file_path
                )
                ==
                os.path.abspath(
                    OUTPUT_FILE
                )
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
                f"Scanning: "
                f"{file_path}",
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

            top_directory = (
                get_top_directory(
                    directory
                )
            )


            # ==============================================
            # WRITE REPORT
            # ==============================================

            with open(
                OUTPUT_FILE,
                "a",
                encoding="utf-8"
            ) as output:


                output.write(
                    "\n"
                )

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
                # MATCHES
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
                        # ----------------------------------

                        if (
                            item["mode"]
                            == "full_line"
                        ):


                            output.write(

                                f"[{keyword}] "
                                f"Line "
                                f"{match['line']}: "
                                f"{item['text']}"
                                f"\n\n"

                            )


                        # ----------------------------------
                        # SELECTED COLUMNS
                        # ----------------------------------

                        else:


                            column_numbers = ",".join(

                                str(column)

                                for column
                                in item["columns"]

                            )


                            output.write(

                                f"[{keyword}] "
                                f"Line "
                                f"{match['line']} "
                                f"Columns "
                                f"{column_numbers}\n"

                            )


                            for value in item[
                                "values"
                            ]:


                                output.write(

                                    f"  Column "
                                    f"{value['column']}: "
                                    f"{value['value']}\n"

                                )


                            output.write(
                                "\n"
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