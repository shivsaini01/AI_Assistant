import os
import re
import winreg
from difflib import SequenceMatcher


# ==================================================
# WINDOWS APPLICATION DETECTOR
# ==================================================

START_MENU_LOCATIONS = [
    os.path.expandvars(
        r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"
    ),
    os.path.expandvars(
        r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"
    ),
]


# ==================================================
# NORMALIZE NAME
# ==================================================

def normalize_name(name):
    """
    Convert an application name into a simple
    comparable format.
    """

    name = os.path.splitext(name)[0]

    name = name.lower()

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    return " ".join(name.split())


# ==================================================
# SEARCH START MENU
# ==================================================

def search_start_menu(app_name):

    target = normalize_name(app_name)

    best_match = None
    best_score = 0.0

    for start_menu in START_MENU_LOCATIONS:

        if not os.path.exists(start_menu):
            continue

        for root, dirs, files in os.walk(start_menu):

            for file in files:

                if not file.lower().endswith(
                    (".lnk", ".url", ".exe")
                ):
                    continue

                full_path = os.path.join(
                    root,
                    file
                )

                file_name = normalize_name(file)

                if not file_name:
                    continue

                # Exact match
                if file_name == target:

                    return full_path

                # Name contained inside filename
                if target in file_name:

                    score = 0.90

                else:

                    score = SequenceMatcher(
                        None,
                        target,
                        file_name
                    ).ratio()

                if score > best_score:

                    best_score = score
                    best_match = full_path

    if best_score >= 0.72:

        return best_match

    return None


# ==================================================
# SEARCH WINDOWS REGISTRY
# ==================================================

def search_registry(app_name):

    target = normalize_name(app_name)

    registry_locations = [
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ),
    ]

    best_match = None
    best_score = 0.0

    for hive, path in registry_locations:

        try:

            with winreg.OpenKey(
                hive,
                path
            ) as uninstall_key:

                subkey_count = winreg.QueryInfoKey(
                    uninstall_key
                )[0]

                for i in range(subkey_count):

                    try:

                        subkey_name = winreg.EnumKey(
                            uninstall_key,
                            i
                        )

                        with winreg.OpenKey(
                            uninstall_key,
                            subkey_name
                        ) as app_key:

                            try:
                                display_name = winreg.QueryValueEx(
                                    app_key,
                                    "DisplayName"
                                )[0]
                            except FileNotFoundError:
                                continue

                            if not display_name:
                                continue

                            normalized_display = normalize_name(
                                str(display_name)
                            )

                            if not normalized_display:
                                continue

                            # ----------------------------------
                            # Find executable information
                            # ----------------------------------

                            executable = None

                            for value_name in (
                                "DisplayIcon",
                                "InstallLocation",
                                "UninstallString",
                            ):

                                try:

                                    value = winreg.QueryValueEx(
                                        app_key,
                                        value_name
                                    )[0]

                                    if value:

                                        executable = str(value)

                                        if value_name == "DisplayIcon":
                                            executable = executable.split(",")[0]
                                            executable = executable.strip('"')

                                        break

                                except FileNotFoundError:
                                    continue

                            if not executable:
                                continue

                            # Only keep useful paths
                            if not os.path.exists(
                                executable
                            ):

                                install_location = os.path.dirname(
                                    executable
                                )

                                if os.path.exists(
                                    install_location
                                ):
                                    executable = install_location
                                else:
                                    continue

                            # ----------------------------------
                            # Calculate match
                            # ----------------------------------

                            if normalized_display == target:

                                return executable

                            if target in normalized_display:

                                score = 0.92

                            else:

                                score = SequenceMatcher(
                                    None,
                                    target,
                                    normalized_display
                                ).ratio()

                            if score > best_score:

                                best_score = score
                                best_match = executable

                    except (
                        OSError,
                        PermissionError
                    ):
                        continue

        except (
            OSError,
            PermissionError
        ):
            continue

    if best_score >= 0.72:

        return best_match

    return None


# ==================================================
# SEARCH COMMON PROGRAM DIRECTORIES
# ==================================================

def search_program_files(app_name):

    target = normalize_name(app_name)

    program_locations = [
        os.environ.get(
            "PROGRAMFILES",
            r"C:\Program Files"
        ),
        os.environ.get(
            "PROGRAMFILES(X86)",
            r"C:\Program Files (x86)"
        ),
        os.environ.get(
            "LOCALAPPDATA",
            ""
        ),
    ]

    best_match = None
    best_score = 0.0

    for base_path in program_locations:

        if not base_path:
            continue

        if not os.path.exists(base_path):
            continue

        try:

            for root, dirs, files in os.walk(
                base_path
            ):

                # Avoid scanning huge unrelated folders
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in {
                        "windows",
                        "system32",
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "site-packages",
                        "python",
                    }
                ]

                for file in files:

                    if not file.lower().endswith(
                        ".exe"
                    ):
                        continue

                    file_name = normalize_name(
                        file
                    )

                    if not file_name:
                        continue

                    if file_name == target:

                        return os.path.join(
                            root,
                            file
                        )

                    if target in file_name:

                        score = 0.90

                    else:

                        score = SequenceMatcher(
                            None,
                            target,
                            file_name
                        ).ratio()

                    if score > best_score:

                        best_score = score

                        best_match = os.path.join(
                            root,
                            file
                        )

        except (
            OSError,
            PermissionError
        ):
            continue

    if best_score >= 0.78:

        return best_match

    return None


# ==================================================
# FIND APPLICATION
# ==================================================

def find_app(app_name):

    if not app_name:
        return None

    app_name = str(
        app_name
    ).strip()

    if not app_name:
        return None

    # 1. Start Menu
    result = search_start_menu(
        app_name
    )

    if result:
        return result

    # 2. Registry
    result = search_registry(
        app_name
    )

    if result:
        return result

    # 3. Program Files
    result = search_program_files(
        app_name
    )

    if result:
        return result

    return None


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS DYNAMIC APPLICATION DETECTOR")
    print("=" * 60)
    print()

    test_apps = [
        "brave",
        "obs",
        "signal",
        "calculator",
        "notepad",
        "discord",
        "spotify",
        "vscode",
    ]

    for app in test_apps:

        print(
            f"Searching for: {app}"
        )

        result = find_app(app)

        if result:

            print(
                f"[FOUND] {result}"
            )

        else:

            print(
                "[NOT FOUND]"
            )

        print()

    print("=" * 60)
