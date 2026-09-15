import json
import os
import re
import subprocess

from jarvis_tools import (
    launch_app,
    open_url
)


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = r"C:\AI_Assistant"

SKILLS_FOLDER = os.path.join(
    BASE_DIR,
    "skills"
)

CREATE_FOLDER = SKILLS_FOLDER

REGISTRY_FILE = os.path.join(
    BASE_DIR,
    "skills.json"
)


# ==================================================
# FOLDER SETUP
# ==================================================

def ensure_folders():

    os.makedirs(
        SKILLS_FOLDER,
        exist_ok=True
    )


# ==================================================
# LOAD REGISTRY
# ==================================================

def load_registry():

    ensure_folders()

    if not os.path.exists(
        REGISTRY_FILE
    ):

        return {}

    try:

        with open(
            REGISTRY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            dict
        ):

            return data

    except Exception as e:

        print(
            f"Registry error: {e}"
        )

    return {}


# ==================================================
# SAVE REGISTRY
# ==================================================

def save_registry(
    registry
):

    ensure_folders()

    try:

        with open(
            REGISTRY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                registry,
                file,
                indent=4
            )

        return True

    except Exception as e:

        print(
            f"Failed to save registry: {e}"
        )

        return False


# ==================================================
# CLEAN FILENAME
# ==================================================

def clean_filename(
    filename
):

    if not filename:

        return None

    filename = os.path.basename(
        str(filename)
    ).strip()

    if not filename:

        return None

    if ".." in filename:

        return None

    return filename


# ==================================================
# CREATE FILE SAFELY
# ==================================================

def create_file(
    filename,
    content
):

    ensure_folders()

    filename = clean_filename(
        filename
    )

    if not filename:

        return (
            False,
            "Invalid filename."
        )

    file_path = os.path.join(
        CREATE_FOLDER,
        filename
    )

    # ----------------------------------------------
    # NEVER OVERWRITE EXISTING FILE
    # ----------------------------------------------

    if os.path.exists(file_path):

        return (
            False,
            f"File already exists: {filename}"
        )

    try:

        with open(
            file_path,
            "x",
            encoding="utf-8"
        ) as file:

            file.write(
                content
            )

        return (
            True,
            file_path
        )

    except FileExistsError:

        return (
            False,
            f"File already exists: {filename}"
        )

    except Exception as e:

        return (
            False,
            f"Failed to create file: {e}"
        )


# ==================================================
# GET SKILL PATH
# ==================================================

def get_skill_path(
    filename
):

    filename = clean_filename(
        filename
    )

    if not filename:

        return None

    if not filename.lower().endswith(
        ".py"
    ):

        filename += ".py"

    return os.path.join(
        SKILLS_FOLDER,
        filename
    )


# ==================================================
# REGISTER SKILL
# ==================================================

def register_skill(
    skill_name,
    filename,
    triggers=None,
    description=""
):

    ensure_folders()

    if not skill_name:

        return False

    skill_name = str(
        skill_name
    ).strip()

    if not skill_name:

        return False

    if triggers is None:

        triggers = []

    filename = clean_filename(filename)

    if not filename:
        return False

    if not filename.lower().endswith(".py"):
        filename += ".py"

    # ------------------------------------------
    # VERIFY SKILL FILE EXISTS
    # ------------------------------------------

    skill_path = get_skill_path(filename)

    if not os.path.isfile(skill_path):
        return False

    registry = load_registry()

    # ----------------------------------------------
    # NEVER OVERWRITE EXISTING SKILL
    # ----------------------------------------------

    for existing_name in registry:

        if existing_name.lower() == skill_name.lower():

            return False

    # ----------------------------------------------
    # NEVER REGISTER SAME FILE TWICE
    # ----------------------------------------------

    for existing_data in registry.values():

        existing_filename = existing_data.get(
            "filename",
            ""
        )

        if (
            existing_filename.lower()
            == filename.lower()
        ):

            return False

    registry[skill_name] = {
        "filename": filename,
        "triggers": triggers,
        "description": description
    }

    return save_registry(
        registry
    )

def find_skill(text):

    if not text:
        return None

    text_lower = str(
        text
    ).lower().strip()

    registry = load_registry()

    # ------------------------------------------
    # EXECUTION ACTIONS
    # ------------------------------------------

    execution_actions = {
        "open",
        "run",
        "start",
        "launch",
        "activate",
        "execute",
        "use",
        "enable",
    }

    # ------------------------------------------
    # REMOVE / NON-EXECUTION ACTIONS
    # ------------------------------------------

    non_execution_actions = {
        "remove",
        "delete",
        "update",
        "edit",
        "modify",
        "disable",
        "stop",
        "close",
        "about",
        "what",
        "which",
        "tell",
        "show",
        "list",
    }

    words = text_lower.split()

    # ------------------------------------------
    # EXACT SKILL NAME
    # ------------------------------------------

    for skill_name, skill_data in registry.items():

        filename = skill_data.get(
            "filename",
            ""
        )

        skill_path = get_skill_path(
            filename
        )

        # Ignore stale registry entries
        if not skill_path or not os.path.isfile(
            skill_path
        ):
            continue

        skill_name_lower = (
            skill_name.lower().strip()
        )

        if not skill_name_lower:
            continue

        # --------------------------------------
        # EXACT NAME
        # --------------------------------------

        if skill_name_lower == text_lower:
            return skill_data

        # --------------------------------------
        # EXACT FILENAME
        # --------------------------------------

        filename_without_ext = os.path.splitext(
            filename
        )[0].lower().strip()

        if filename_without_ext == text_lower:
            return skill_data

        # --------------------------------------
        # EXACT TRIGGER
        # --------------------------------------

        triggers = skill_data.get(
            "triggers",
            []
        )

        for trigger in triggers:

            if not isinstance(
                trigger,
                str
            ):
                continue

            if trigger.lower().strip() == text_lower:
                return skill_data

        # --------------------------------------
        # SKILL NAME INSIDE COMMAND
        # --------------------------------------

        pattern = (
            r"\b"
            + re.escape(skill_name_lower)
            + r"\b"
        )

        if not re.search(
            pattern,
            text_lower
        ):
            continue

        # --------------------------------------
        # CHECK COMMAND INTENT
        # --------------------------------------

        first_word = words[0] if words else ""

        # Explicit non-execution command
        if first_word in non_execution_actions:
            continue

        # Execution command
        if first_word in execution_actions:
            return skill_data

        # "turn on <skill>"
        if (
            len(words) >= 3
            and words[0] == "turn"
            and words[1] == "on"
        ):
            return skill_data

        # "please open <skill>"
        if (
            len(words) >= 2
            and words[0] == "please"
            and words[1] in execution_actions
        ):
            return skill_data

    return None

# ==================================================
# RUN SKILL
# ==================================================

def run_skill(
    skill_name
):

    skill = find_skill(
        skill_name
    )

    if not skill:

        print(
            f"Skill not found: {skill_name}"
        )

        return False

    filename = skill.get(
        "filename"
    )

    skill_path = get_skill_path(
        filename
    )

    if not skill_path:

        print(
            "Invalid skill path."
        )

        return False

    if not os.path.isfile(
        skill_path
    ):

        print(
            f"Skill file not found: {filename}"
        )

        return False

    try:

        # ------------------------------------------
        # ALLOW SKILL TO IMPORT JARVIS MODULES
        # ------------------------------------------

        env = os.environ.copy()

        existing_pythonpath = env.get(
            "PYTHONPATH",
            ""
        )

        if existing_pythonpath:

            env["PYTHONPATH"] = (
                BASE_DIR
                + os.pathsep
                + existing_pythonpath
            )

        else:

            env["PYTHONPATH"] = BASE_DIR

        # ------------------------------------------
        # RUN SKILL
        # ------------------------------------------

        result = subprocess.run(
            [
                "python",
                skill_path
            ],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
            text=True
        )

        if result.stdout:

            print(
                result.stdout.strip()
            )

        if result.stderr:

            print(
                result.stderr.strip()
            )

        return result.returncode == 0

    except Exception as e:

        print(
            f"Failed to run skill: {e}"
        )

        return False


# ==================================================
# EXECUTE APPROVED COMMAND
# ==================================================

def execute_command(
    command
):

    if not command:

        return False

    command = command.strip()

    # ----------------------------------------------
    # BRAVE
    # ----------------------------------------------

    if command == "open_brave":

        success, message = launch_app(
            "brave"
        )

        print(
            message
        )

        return success

    # ----------------------------------------------
    # OBS
    # ----------------------------------------------

    if command == "open_obs":

        success, message = launch_app(
            "obs"
        )

        print(
            message
        )

        return success

    # ----------------------------------------------
    # URL
    # ----------------------------------------------

    if command.startswith(
        "open_url:"
    ):

        url = command[
            len("open_url:")
        ].strip()

        if not url:

            return False

        success, message = open_url(
            url
        )

        print(
            message
        )

        return success

    # ----------------------------------------------
    # REGISTERED SKILL
    # ----------------------------------------------

    skill = find_skill(
        command
    )

    if skill:

        return run_skill(
            command
        )

    print(
        f"Unknown command: {command}"
    )

    return False


# ==================================================
# LIST SKILLS
# ==================================================

def load_registry():

    ensure_folders()

    if not os.path.exists(REGISTRY_FILE):
        return {}

    try:

        with open(
            REGISTRY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            registry = json.load(file)

        if not isinstance(registry, dict):
            return {}

        # ------------------------------------------
        # REMOVE STALE SKILLS
        # ------------------------------------------

        cleaned_registry = {}

        changed = False

        for skill_name, skill_data in registry.items():

            if not isinstance(skill_data, dict):
                changed = True
                continue

            filename = skill_data.get(
                "filename",
                ""
            )

            skill_path = get_skill_path(
                filename
            )

            # File no longer exists
            if not skill_path or not os.path.isfile(
                skill_path
            ):
                changed = True
                continue

            cleaned_registry[
                skill_name
            ] = skill_data

        # ------------------------------------------
        # SAVE CLEANED REGISTRY
        # ------------------------------------------

        if changed:

            with open(
                REGISTRY_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    cleaned_registry,
                    file,
                    indent=4
                )

        return cleaned_registry

    except (
        json.JSONDecodeError,
        OSError
    ):

        return {}

# ==================================================
# REMOVE SKILL
# ==================================================

def remove_skill(
    skill_name
):

    registry = load_registry()

    skill = find_skill(
        skill_name
    )

    if not skill:

        print(
            f"Skill not found: {skill_name}"
        )

        return False

    skill_to_remove = None

    for name, data in registry.items():

        if data == skill:

            skill_to_remove = name

            break

    if not skill_to_remove:

        return False

    filename = skill.get(
        "filename"
    )

    skill_path = get_skill_path(
        filename
    )

    del registry[
        skill_to_remove
    ]

    save_registry(
        registry
    )

    if (
        skill_path
        and
        os.path.exists(
            skill_path
        )
    ):

        try:

            os.remove(
                skill_path
            )

        except Exception as e:

            print(
                f"Could not delete skill file: {e}"
            )

    print(
        f"Removed skill: {skill_to_remove}"
    )

    return True


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS COMMANDS TEST")
    print("=" * 60)
    print()

    print(
        "Testing Signal..."
    )

    execute_command(
        "open_url:https://www.youtube.com"
    )

    print()

    print("=" * 60)