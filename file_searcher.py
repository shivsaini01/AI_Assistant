import os
import re
import ctypes
from pathlib import Path
from difflib import SequenceMatcher


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(
    r"C:\AI_Assistant"
)

# Folders that are more useful for a personal assistant
PRIORITY_FOLDER_NAMES = {
    "desktop",
    "downloads",
    "documents",
    "pictures",
    "videos",
    "music",
    "ai_assistant",
}


# ==================================================
# NORMALIZE TEXT
# ==================================================

def normalize_search_text(text):
    """
    Normalize spaces, underscores, hyphens, dots, etc.

    Examples:

    test_test_123.py
    test-test-123.py
    test test 123.py

    all become approximately:

    test test 123 py
    """

    text = str(text).strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


# ==================================================
# TOKENIZE
# ==================================================

def get_tokens(text):

    normalized = normalize_search_text(
        text
    )

    if not normalized:
        return []

    return normalized.split()


# ==================================================
# WINDOWS DRIVES
# ==================================================

def get_logical_drives():

    drives = []

    try:

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()

        for index in range(26):

            if bitmask & (
                1 << index
            ):

                drive = (
                    chr(65 + index)
                    + ":\\"
                )

                if os.path.exists(
                    drive
                ):

                    drives.append(
                        Path(drive)
                    )

    except Exception:

        system_drive = os.environ.get(
            "SystemDrive",
            "C:"
        )

        drives.append(
            Path(
                system_drive + "\\"
            )
        )

    return drives


# ==================================================
# USER FOLDERS
# ==================================================

def get_user_priority_folders():

    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if not user_profile:
        return []

    profile = Path(
        user_profile
    )

    folders = [
        profile / "Desktop",
        profile / "Downloads",
        profile / "Documents",
        profile / "Pictures",
        profile / "Videos",
        profile / "Music",
    ]

    return [
        folder
        for folder in folders
        if folder.exists()
    ]


# ==================================================
# SEARCH LOCATIONS
# ==================================================

def resolve_search_roots(
    location=None
):

    if not location:

        roots = []

        # User folders first
        roots.extend(
            get_user_priority_folders()
        )

        # Jarvis project next
        if BASE_DIR.exists():

            roots.append(
                BASE_DIR
            )

        # Then all drives
        roots.extend(
            get_logical_drives()
        )

        return unique_paths(
            roots
        )

    location = str(
        location
    ).strip()

    if not location:

        return resolve_search_roots()

    lowered = location.lower()

    # ----------------------------------------------
    # Whole system
    # ----------------------------------------------

    if lowered in {
        "computer",
        "this pc",
        "my computer",
        "system",
        "all drives",
        "entire system",
        "whole system",
        "everywhere",
        "pc",
    }:

        return get_logical_drives()

    # ----------------------------------------------
    # Drive
    # ----------------------------------------------

    drive_match = re.match(
        r"^([a-z]):(?:\s+drive)?$",
        lowered
    )

    if drive_match:

        drive = (
            drive_match.group(1).upper()
            + ":\\"
        )

        path = Path(
            drive
        )

        if path.exists():

            return [
                path
            ]

        return []

    # ----------------------------------------------
    # Exact path
    # ----------------------------------------------

    expanded = os.path.expandvars(
        location
    )

    path = Path(
        expanded
    )

    if path.exists():

        return [
            path
        ]

    # ----------------------------------------------
    # Common folders
    # ----------------------------------------------

    user_profile = os.environ.get(
        "USERPROFILE"
    )

    if user_profile:

        profile = Path(
            user_profile
        )

        folder_map = {
        "desktop": "Desktop",
        "downloads": "Downloads",
        "documents": "Documents",
        "pictures": "Pictures",
        "videos": "Videos",
        "music": "Music",
    }

    if lowered == "ai assistant":

        if BASE_DIR.exists():
            return [
                BASE_DIR
            ]

        return []


    if lowered in folder_map:

        folder_name = folder_map[
            lowered
        ]

        candidates = [
            profile / folder_name
        ]

        one_drive = os.environ.get(
            "OneDrive"
        )

        if one_drive:

            candidates.append(
                Path(one_drive) / folder_name
            )

        existing = [
            folder
            for folder in candidates
            if folder.exists()
        ]

        return unique_paths(
            existing
        )

    return []


# ==================================================
# UNIQUE PATHS
# ==================================================

def unique_paths(
    paths
):

    unique = []

    seen = set()

    for path in paths:

        try:

            resolved = Path(
                path
            ).resolve()

            normalized = os.path.normcase(
                str(resolved)
            )

            if normalized not in seen:

                seen.add(
                    normalized
                )

                unique.append(
                    resolved
                )

        except Exception:

            continue

    return unique


# ==================================================
# PATH PRIORITY
# ==================================================

def get_path_priority(
    path
):

    path_lower = str(
        path
    ).lower()

    score = 0

    # ----------------------------------------------
    # Personal folders
    # ----------------------------------------------

    if "\\downloads\\" in path_lower:
        score += 50

    if "\\desktop\\" in path_lower:
        score += 48

    if "\\documents\\" in path_lower:
        score += 46

    if "\\pictures\\" in path_lower:
        score += 30

    if "\\videos\\" in path_lower:
        score += 30

    if "\\music\\" in path_lower:
        score += 30

    # ----------------------------------------------
    # Jarvis project
    # ----------------------------------------------

    if path_lower.startswith(
        str(BASE_DIR).lower()
    ):

        score += 45

    # ----------------------------------------------
    # De-prioritize system folders
    # ----------------------------------------------

    low_priority_folders = [
        "\\windows\\",
        "\\program files\\",
        "\\program files (x86)\\",
        "\\appdata\\",
        "\\winsxs\\",
        "\\system32\\",
        "\\node_modules\\",
        "\\git\\",
    ]

    for folder in low_priority_folders:

        if folder in path_lower:

            score -= 40

    return score


# ==================================================
# FILE MATCH SCORE
# ==================================================

def calculate_match_score(
    query,
    filename,
    full_path,
    exact=False
):

    query_lower = query.lower().strip()

    filename_lower = filename.lower()

    filename_without_extension = os.path.splitext(
        filename_lower
    )[0]

    normalized_query = normalize_search_text(
        query
    )

    normalized_filename = normalize_search_text(
        filename
    )

    normalized_name_only = normalize_search_text(
        filename_without_extension
    )

    query_tokens = get_tokens(
        query
    )

    filename_tokens = get_tokens(
        filename_without_extension
    )

    score = 0.0

    # ----------------------------------------------
    # EXACT FILENAME
    # ----------------------------------------------

    if filename_lower == query_lower:

        score += 1000

    # ----------------------------------------------
    # Exact name without extension
    # ----------------------------------------------

    if (
        filename_without_extension
        == query_lower
    ):

        score += 900

    # ----------------------------------------------
    # Starts with query
    # ----------------------------------------------

    if filename_lower.startswith(
        query_lower
    ):

        score += 500

    # ----------------------------------------------
    # Normalized exact
    #
    # test test 123
    # test_test_123
    # ----------------------------------------------

    if (
        normalized_name_only
        == normalized_query
    ):

        score += 850

    # ----------------------------------------------
    # Normalized starts with
    # ----------------------------------------------

    if normalized_name_only.startswith(
        normalized_query
    ):

        score += 450

    # ----------------------------------------------
    # Query contained in normalized filename
    # ----------------------------------------------

    if normalized_query in normalized_name_only:

        score += 350

    # ----------------------------------------------
    # All query words present
    # ----------------------------------------------

    if query_tokens:

        matched_tokens = sum(
            1
            for token in query_tokens
            if token in filename_tokens
        )

        if matched_tokens == len(
            query_tokens
        ):

            score += 400

        elif matched_tokens > 0:

            score += (
                matched_tokens
                / len(query_tokens)
            ) * 250

    # ----------------------------------------------
    # Fuzzy similarity
    # ----------------------------------------------

    similarity = SequenceMatcher(
        None,
        normalized_query,
        normalized_name_only
    ).ratio()

    score += similarity * 150

    # ----------------------------------------------
    # Path priority
    # ----------------------------------------------

    score += get_path_priority(
        full_path
    )

    return score


# ==================================================
# SEARCH FILES
# ==================================================

def search_files(
    query,
    exact=False,
    location=None,
    max_results=100
):

    if not query:

        return []

    query = str(
        query
    ).strip()

    if not query:

        return []

    roots = resolve_search_roots(
        location
    )

    if not roots:

        return []

    matches = []

    seen = set()

    query_lower = query.lower()

    normalized_query = normalize_search_text(
        query
    )

    for root_index, root in enumerate(
        roots
    ):

        root = Path(
            root
        )

        if not root.exists():

            continue

        try:

            for current_root, dirs, files in os.walk(
                root,
                topdown=True
            ):

                # ----------------------------------
                # Skip noisy / unnecessary folders
                # ----------------------------------

                dirs[:] = [
                    directory
                    for directory in dirs
                    if directory.lower() not in {
                        "$recycle.bin",
                        "system volume information",
                        "__pycache__",
                        ".git",
                        "node_modules",
                    }
                ]

                current_root_lower = (
                    current_root.lower()
                )

                for filename in files:

                    full_path = os.path.join(
                        current_root,
                        filename
                    )

                    normalized_path = os.path.normcase(
                        os.path.abspath(
                            full_path
                        )
                    )

                    if normalized_path in seen:

                        continue

                    filename_lower = filename.lower()

                    filename_without_extension = (
                        os.path.splitext(
                            filename_lower
                        )[0]
                    )

                    normalized_filename = normalize_search_text(
                        filename
                    )

                    normalized_name_only = normalize_search_text(
                        filename_without_extension
                    )

                    # ==================================
                    # EXACT SEARCH
                    # ==================================

                    if exact:

                        exact_match = (
                            filename_lower
                            == query_lower
                        )

                        if not exact_match:

                            continue

                    # ==================================
                    # NORMAL SEARCH
                    # ==================================

                    else:

                        direct_match = (
                            normalized_query
                            in normalized_filename
                        )

                        query_tokens = get_tokens(
                            query
                        )

                        filename_tokens = get_tokens(
                            filename_without_extension
                        )

                        all_words_match = (
                            bool(query_tokens)
                            and
                            all(
                                token in filename_tokens
                                for token in query_tokens
                            )
                        )

                        # ----------------------------------
                        # Fuzzy fallback
                        # ----------------------------------

                        fuzzy_match = False

                        similarity = SequenceMatcher(
                            None,
                            normalized_query,
                            normalized_name_only
                        ).ratio()

                        if (
                            len(normalized_query) >= 4
                            and
                            similarity >= 0.65
                        ):

                            fuzzy_match = True

                        if not (
                            direct_match
                            or
                            all_words_match
                            or
                            fuzzy_match
                        ):

                            continue

                    # ==================================
                    # SCORE
                    # ==================================

                    score = calculate_match_score(
                        query=query,
                        filename=filename,
                        full_path=full_path,
                        exact=exact
                    )

                    seen.add(
                        normalized_path
                    )

                    matches.append(
                        (
                            score,
                            full_path
                        )
                    )

        except (
            PermissionError,
            OSError
        ):

            continue

    # ----------------------------------------------
    # Sort best matches first
    # ----------------------------------------------

    matches.sort(
        key=lambda item: (
            -item[0],
            item[1].lower()
        )
    )

    results = [
        path
        for score, path in matches[
            :max_results
        ]
    ]

    return results


# ==================================================
# SEARCH WITH FALLBACK
# ==================================================

def search_with_fallback(
    query,
    location=None,
    max_results=100
):
    """
    First attempt exact search.

    If nothing is found, perform a broader search.
    Returns:

    {
        "exact_results": [...],
        "fallback_results": [...]
    }
    """

    exact_results = search_files(
        query=query,
        exact=True,
        location=location,
        max_results=max_results
    )

    if exact_results:

        return {
            "exact_results": exact_results,
            "fallback_results": []
        }

    fallback_results = search_files(
        query=query,
        exact=False,
        location=location,
        max_results=max_results
    )

    return {
        "exact_results": [],
        "fallback_results": fallback_results
    }


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS SMART FILE SEARCH TEST")
    print("=" * 60)
    print()

    # ----------------------------------------------
    # TEST 1
    # ----------------------------------------------

    print(
        "TEST 1: Search 'test'"
    )

    results = search_files(
        "test",
        exact=False,
        max_results=20
    )

    for index, path in enumerate(
        results,
        start=1
    ):

        print(
            f"{index}. {path}"
        )

    print()
    print("-" * 60)
    print()

    # ----------------------------------------------
    # TEST 2
    # ----------------------------------------------

    print(
        "TEST 2: Search 'test test 123'"
    )

    results = search_files(
        "test test 123",
        exact=False,
        max_results=20
    )

    for index, path in enumerate(
        results,
        start=1
    ):

        print(
            f"{index}. {path}"
        )

    print()
    print("-" * 60)
    print()

    # ----------------------------------------------
    # TEST 3
    # ----------------------------------------------

    print(
        "TEST 3: Exact 'tester.exe'"
    )

    results = search_files(
        "tester.exe",
        exact=True,
        max_results=20
    )

    for index, path in enumerate(
        results,
        start=1
    ):

        print(
            f"{index}. {path}"
        )

    if not results:

        print(
            "No exact match found."
        )

        fallback = search_files(
            "tester.exe",
            exact=False,
            max_results=20
        )

        if fallback:

            print()
            print(
                "Possible matches:"
            )

            for index, path in enumerate(
                fallback,
                start=1
            ):

                print(
                    f"{index}. {path}"
                )

    print()
    print("=" * 60)