import os
import subprocess
import webbrowser

from app_detector import find_app


# ==================================================
# WINDOWS PROCESS FLAGS
# ==================================================

DETACHED_PROCESS = 0x00000008

CREATE_NEW_PROCESS_GROUP = 0x00000200


# ==================================================
# LAUNCH APPLICATION
# ==================================================

def launch_app(
    app_name
):
    """
    Dynamically find and launch a Windows application.

    Application output is detached from Jarvis's
    PowerShell console.
    """

    if not app_name:

        return (
            False,
            "Application name is empty."
        )

    path = find_app(
        app_name
    )

    if not path:

        return (
            False,
            f"{app_name.title()} was not found on this computer."
        )

    try:

        # ------------------------------------------
        # Windows shortcut
        # ------------------------------------------

        if path.lower().endswith(
            (".lnk", ".url")
        ):

            subprocess.Popen(
                [
                    "explorer.exe",
                    path
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    DETACHED_PROCESS
                    | CREATE_NEW_PROCESS_GROUP
                ),
                close_fds=True
            )

            return (
                True,
                f"{app_name.title()} launched successfully."
            )

        # ------------------------------------------
        # EXE
        # ------------------------------------------

        if path.lower().endswith(
            ".exe"
        ):

            working_dir = os.path.dirname(
                path
            )

            subprocess.Popen(
                [path],
                cwd=working_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    DETACHED_PROCESS
                    | CREATE_NEW_PROCESS_GROUP
                ),
                close_fds=True
            )

            return (
                True,
                f"{app_name.title()} launched successfully."
            )

        return (
            False,
            f"I found {app_name.title()}, but I cannot launch this file type."
        )

    except Exception as e:

        return (
            False,
            f"I couldn't launch {app_name.title()}: {e}"
        )


# ==================================================
# OPEN URL
# ==================================================

def open_url(
    url
):
    """
    Open an HTTP/HTTPS URL.
    """

    if not url:

        return (
            False,
            "No URL was provided."
        )

    try:

        webbrowser.open(
            url
        )

        return (
            True,
            "Website opened successfully."
        )

    except Exception as e:

        return (
            False,
            f"I couldn't open the website: {e}"
        )


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS TOOLS TEST")
    print("=" * 60)
    print()

    print(
        "Testing Signal..."
    )

    success, message = launch_app(
        "signal"
    )

    print(
        message
    )

    print()

    print(
        "Testing Discord..."
    )

    success, message = launch_app(
        "discord"
    )

    print(
        message
    )

    print()

    print(
        "Testing VS Code..."
    )

    success, message = launch_app(
        "vscode"
    )

    print(
        message
    )

    print()

    print(
        "Testing YouTube..."
    )

    success, message = open_url(
        "https://www.youtube.com"
    )

    print(
        message
    )

    print()

    print("=" * 60)