import json
import os
import re
from datetime import datetime
from urllib.parse import quote_plus

from ollama import chat

from commands import (
    create_file,
    register_skill,
    find_skill,
    execute_command,
    load_registry,
    remove_skill,
)

from jarvis_tools import (
    launch_app,
    open_url,
)

from intent_parser import (
    parse_user_intent,
)

from website_resolver import (
    resolve_website,
)

from file_searcher import (
    search_files,
)

from conversation_memory import (
    remember,
    get_recent_memory,
    build_context,
    build_context_with_metadata,
    get_last_command_context,
    remember_context,
    remember_context_many,
    get_context,
    get_context_value,
)


# ==================================================
# CONFIGURATION
# ==================================================

MODEL = "qwen2.5:7b-instruct-q3_K_M"

BASE_DIR = r"C:\AI_Assistant"

SAFE_FOLDER = os.path.join(
    BASE_DIR,
    "skills"
)

MAX_CONTEXT_TURNS = 8

# ==================================================
# SKILL CREATION STATE
# ==================================================

pending_skill_creation = None

# ==================================================
# SKILL REQUEST DETECTION
# ==================================================

def is_skill_creation_request(
    text
):

    if not text:

        return False

    text_lower = text.lower().strip()

    patterns = [
        "create a skill",
        "create skill",
        "make a skill",
        "make skill",
        "add a skill",
        "add skill",
        "new skill",
    ]

    return any(
        pattern in text_lower
        for pattern in patterns
    )

# ==================================================
# SKILL FILENAME
# ==================================================

def skill_filename(
    skill_name
):

    name = str(
        skill_name
    ).strip().lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "_",
        name
    )

    name = name.strip("_")

    if not name:

        return None

    return f"{name}.py"

# ==================================================
# GENERATE SKILL
# ==================================================

def ask_skill_ai(user_request, skill_name):

    prompt = f"""
You are Jarvis's skill-generation engine.

Create a complete Python skill based on the user's request.

SKILL NAME:
{skill_name}

USER REQUEST:
{user_request}

AVAILABLE JARVIS TOOLS:

from jarvis_tools import launch_app, open_url

Desktop application:
launch_app("application name")

Website:
open_url("https://example.com")

IMPORTANT RULES:

1. Return ONLY valid Python source code.
2. Do NOT return markdown.
3. Do NOT return JSON.
4. Do NOT return explanations.
5. The generated code must be complete and runnable.
6. Import Jarvis tools at the beginning.
7. If the user requests a desktop application, use launch_app().
8. If the user requests multiple applications, launch EVERY requested application.
9. Do NOT replace a desktop application with its website.
10. Use open_url() ONLY when the user explicitly requests a website/webpage.
11. Do NOT use webbrowser.
12. Do NOT use subprocess.
13. Do NOT use PowerShell.
14. Do NOT ask the user for input.
15. Do NOT invent additional applications or websites.
16. Perform ALL actions requested by the user.
17. Preserve the exact meaning of the user's request.
18. The skill must execute automatically when the file is run.
19. Do not create a function that is never called.
20. The final Python code must not contain code fences.

EXAMPLE:

User request:
make a skill to open signal and obs

Correct behavior:
launch Signal desktop application
launch OBS desktop application

Correct code pattern:

from jarvis_tools import launch_app

launch_app("Signal")
launch_app("obs")

WRONG:
open_url("https://signal.me/")

because the user requested the Signal application, not the Signal website.

Another example:

User request:
make a skill to open youtube and chrome

Correct behavior:
open YouTube website
launch Chrome desktop application.

Generate the skill now.
"""

    try:

        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response[
            "message"
        ][
            "content"
        ].strip()

        content = re.sub(
            r"```(?:python|py)?",
            "",
            content,
            flags=re.IGNORECASE
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()

        if not content:
            return None

        return content

    except Exception as e:

        print(
            f"Jarvis: ❌ Skill generation error: {e}"
        )

        return None


# ==================================================
# CREATE SKILL
# ==================================================

def create_skill(user_request, skill_name):

    skill_name = str(
        skill_name
    ).strip()

    if not skill_name:
        print(
            "Jarvis: ❌ Invalid skill name."
        )
        return False

    filename = skill_filename(
        skill_name
    )

    if not filename:
        print(
            "Jarvis: ❌ Invalid skill name."
        )
        return False

    # ------------------------------------------
    # CHECK EXISTING SKILL
    # ------------------------------------------

    existing_skill = find_skill(
        skill_name
    )

    if existing_skill:
        print(
            f'Jarvis: ⚠️ Skill "{skill_name}" '
            "already exists. It was not modified."
        )
        return False

    # ------------------------------------------
    # CHECK EXISTING FILE
    # ------------------------------------------

    skill_path = os.path.join(
        SAFE_FOLDER,
        filename
    )

    if os.path.exists(skill_path):
        print(
            f'Jarvis: ⚠️ Skill file "{filename}" '
            "already exists. It was not modified."
        )
        return False

    # ------------------------------------------
    # GENERATE SKILL
    # ------------------------------------------

    print(
        "Jarvis: 🛠️ Creating skill..."
    )

    content = ask_skill_ai(
        user_request,
        skill_name
    )

    if not content:
        print(
            "Jarvis: ❌ I couldn't generate the skill."
        )
        return False

    # ------------------------------------------
    # CREATE FILE
    # ------------------------------------------

    success, result = create_file(
        filename,
        content
    )

    if not success:
        print(
            f"Jarvis: ❌ {result}"
        )
        return False

    # ------------------------------------------
    # REGISTER SKILL
    # ------------------------------------------

    registered = register_skill(
        skill_name=skill_name,
        filename=filename,
        triggers=[],
        description=(
            f"Skill created from request: "
            f"{user_request}"
        )
    )

    if not registered:

        try:
            if os.path.exists(skill_path):
                os.remove(skill_path)

        except Exception:
            pass

        print(
            f'Jarvis: ❌ Could not register '
            f'skill "{skill_name}".'
        )

        return False

    print(
        f'Jarvis: ✅ Skill "{skill_name}" '
        "created successfully."
    )

    return True

    # ------------------------------------------
    # CHECK EXISTING SKILL
    # ------------------------------------------

    existing_skill = find_skill(
        skill_name
    )

    if existing_skill:

        print(
            f'Jarvis: ⚠️ Skill "{skill_name}" '
            "already exists. It was not modified."
        )

        return False

    # ------------------------------------------
    # CHECK EXISTING FILE
    # ------------------------------------------

    skill_path = os.path.join(
        SAFE_FOLDER,
        filename
    )

    if os.path.exists(skill_path):

        print(
            f'Jarvis: ⚠️ Skill file "{filename}" '
            "already exists. It was not modified."
        )

        return False

    print(
        "Jarvis: 🛠️ Creating skill..."
    )

    # ------------------------------------------
    # GENERATE PYTHON CODE
    # ------------------------------------------

    content = ask_skill_ai(
        user_request,
        skill_name
    )

    if not content:

        print(
            "Jarvis: ❌ I couldn't generate the skill."
        )

        return False

    # ------------------------------------------
    # CREATE FILE
    # ------------------------------------------

    success, result = create_file(
        filename,
        content
    )

    if not success:

        print(
            f"Jarvis: ❌ {result}"
        )

        return False

    # ------------------------------------------
    # REGISTER SKILL
    # ------------------------------------------

    registered = register_skill(
        skill_name=skill_name,
        filename=filename,
        triggers=[],
        description=(
            f"Skill created from request: "
            f"{user_request}"
        )
    )

    if not registered:

        try:

            if os.path.exists(skill_path):
                os.remove(skill_path)

        except Exception:
            pass

        print(
            f'Jarvis: ❌ Could not register '
            f'skill "{skill_name}".'
        )

        return False

    print(
        f'Jarvis: ✅ Skill "{skill_name}" '
        "created successfully."
    )

    return True


# ==================================================
# SHORT-TERM FILE SEARCH MEMORY
# ==================================================

last_search_results = []


# ==================================================
# GREETING
# ==================================================

def is_greeting(text):

    greetings = {
        "hi",
        "hello",
        "hey",
        "hlo",
        "helo",
        "hi jarvis",
        "hello jarvis",
        "hey jarvis",
    }

    return (
        text.lower().strip()
        in greetings
    )


# ==================================================
# APP NAME VALIDATION
# ==================================================

def is_safe_app_name(app_name):

    if not isinstance(
        app_name,
        str
    ):
        return False

    app_name = app_name.strip()

    if not app_name:
        return False

    forbidden = [
        "\\",
        "/",
        ":",
        ";",
        "|",
        "&",
        ">",
        "<",
        '"',
        "'",
    ]

    return not any(
        character in app_name
        for character in forbidden
    )


# ==================================================
# URL VALIDATION
# ==================================================

def is_safe_url(url):

    if not isinstance(
        url,
        str
    ):
        return False

    url = url.strip()

    if not (
        url.startswith("https://")
        or
        url.startswith("http://")
    ):
        return False

    lowered = url.lower()

    blocked = [
        "file://",
        "javascript:",
        "data:",
        "vbscript:",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    ]

    return not any(
        value in lowered
        for value in blocked
    )


# ==================================================
# OPEN EXACT URL
# ==================================================

def handle_open_url(url):

    if not is_safe_url(url):

        print(
            "Jarvis: ❌ I can't open that website address."
        )

        return False

    success, message = open_url(
        url
    )

    if success:

        print(
            f"Jarvis: ✅ {message}"
        )

    else:

        print(
            f"Jarvis: ❌ {message}"
        )

    return success


# ==================================================
# OPEN WEBSITE
# ==================================================

def handle_open_website(website):

    if not isinstance(
        website,
        str
    ):

        print(
            "Jarvis: ❌ I couldn't identify the website."
        )

        return False

    website = website.strip()

    if not website:

        print(
            "Jarvis: ❌ I couldn't identify the website."
        )

        return False

    print(
        f"Jarvis: 🌐 Finding {website}..."
    )

    url = resolve_website(
        website
    )

    if not url:

        print(
            f"Jarvis: ❌ I couldn't find a website for '{website}'."
        )

        return False

    return handle_open_url(
        url
    )


# ==================================================
# WEB SEARCH
# ==================================================

def handle_web_search(
    site,
    query
):

    if not isinstance(
        site,
        str
    ):
        return False

    if not isinstance(
        query,
        str
    ):
        return False

    site = site.strip().lower()
    query = query.strip()

    if not site or not query:

        print(
            "Jarvis: ❌ Search information is incomplete."
        )

        return False

    search_templates = {

        "youtube":
            "https://www.youtube.com/results?search_query={query}",

        "google":
            "https://www.google.com/search?q={query}",

        "bing":
            "https://www.bing.com/search?q={query}",

        "github":
            "https://github.com/search?q={query}",

        "reddit":
            "https://www.reddit.com/search/?q={query}",

        "stackoverflow":
            "https://stackoverflow.com/search?q={query}",

        "wikipedia":
            "https://www.wikipedia.org/w/index.php?search={query}",
    }

    template = search_templates.get(
        site
    )

    if not template:

        print(
            f"Jarvis: ❌ I don't have a search method for {site} yet."
        )

        return False

    encoded_query = quote_plus(
        query
    )

    search_url = template.format(
        query=encoded_query
    )

    print(
        f'Jarvis: 🔎 Searching {site.title()} for "{query}"...'
    )

    return handle_open_url(
        search_url
    )


# ==================================================
# LAUNCH APPS
# ==================================================

def handle_launch_apps(apps):

    if not isinstance(
        apps,
        list
    ):
        return False

    overall_success = True

    for app_name in apps:

        if not is_safe_app_name(
            app_name
        ):

            print(
                "Jarvis: ❌ Invalid application name."
            )

            overall_success = False
            continue

        app_name = app_name.strip()

        print(
            f"Jarvis: 🔍 Looking for {app_name.title()}..."
        )

        success, message = launch_app(
            app_name
        )

        if success:

            print(
                f"Jarvis: ✅ {message}"
            )

        else:

            # ------------------------------------------
            # WEBSITE FALLBACK
            # ------------------------------------------

            if "was not found on this computer" in message.lower():

                url = resolve_website(
                    app_name
                )

                if url:

                    print(
                        f"Jarvis: 🌐 Opening {app_name.title()}..."
                    )

                    website_success, website_message = open_url(
                        url
                    )

                    if website_success:

                        print(
                            f"Jarvis: ✅ Website opened successfully."
                        )

                        continue

                    print(
                        f"Jarvis: ❌ {website_message}"
                    )

            print(
                f"Jarvis: ❌ {message}"
            )

            overall_success = False

    return overall_success


# ==================================================
# FILE SEARCH
# ==================================================

def handle_file_search(
    query,
    exact=False,
    location=None
):

    global last_search_results

    if not isinstance(
        query,
        str
    ):

        print(
            "Jarvis: ❌ Invalid file search."
        )

        return False

    query = query.strip()

    if not query:

        print(
            "Jarvis: ❌ File name is missing."
        )

        return False

    if location:

        print(
            f'Jarvis: 🔎 Searching for "{query}" in {location}...'
        )

    else:

        print(
            f'Jarvis: 🔎 Searching the computer for "{query}"...'
        )

    results = search_files(
        query=query,
        exact=bool(exact),
        location=location,
        max_results=100
    )

    last_search_results = results

    if not results:

        print(
            f'Jarvis: ❌ I couldn\'t find any files matching "{query}".'
        )

        return False

    print(
        f"Jarvis: ✅ Found {len(results)} file(s):"
    )

    for index, path in enumerate(
        results,
        start=1
    ):

        print(
            f"  {index}. {path}"
        )

    return True


# ==================================================
# OPEN FILE
# ==================================================

def handle_open_file(
    query="",
    exact=False,
    index=None,
    reference=""
):

    global last_search_results

    # ----------------------------------------------
    # OPEN RESULT BY INDEX
    # ----------------------------------------------

    if (
        index is not None
        and
        isinstance(
            index,
            int
        )
    ):

        if not last_search_results:

            print(
                "Jarvis: ❌ There are no recent file search results."
            )

            return False

        if (
            index < 1
            or
            index > len(last_search_results)
        ):

            print(
                "Jarvis: ❌ That result number doesn't exist."
            )

            return False

        path = last_search_results[
            index - 1
        ]

        return open_file_path(
            path
        )

    # ----------------------------------------------
    # OPEN LATEST SINGLE RESULT
    # ----------------------------------------------

    if reference == "latest_search":

        if not last_search_results:

            print(
                "Jarvis: ❌ There are no recent file search results."
            )

            return False

        if len(
            last_search_results
        ) == 1:

            return open_file_path(
                last_search_results[0]
            )

        print(
            f"Jarvis: I found {len(last_search_results)} files."
        )

        print(
            "Jarvis: Please tell me which result to open."
        )

        return False

    # ----------------------------------------------
    # SEARCH FOR REQUESTED FILE
    # ----------------------------------------------

    if not query:

        print(
            "Jarvis: ❌ I don't know which file to open."
        )

        return False

    print(
        f'Jarvis: 🔍 Looking for "{query}"...'
    )

    results = search_files(
        query=query,
        exact=bool(exact),
        max_results=20
    )

    last_search_results = results

    if not results:

        print(
            f'Jarvis: ❌ I couldn\'t find "{query}".'
        )

        return False

    if len(
        results
    ) == 1:

        return open_file_path(
            results[0]
        )

    print(
        f"Jarvis: I found {len(results)} matching files:"
    )

    for result_index, path in enumerate(
        results,
        start=1
    ):

        print(
            f"  {result_index}. {path}"
        )

    print(
        "Jarvis: Tell me which result to open, for example: open 2"
    )

    return False


# ==================================================
# OPEN FILE PATH
# ==================================================

def open_file_path(path):

    if not path:
        return False

    path = os.path.abspath(
        path
    )

    if not os.path.exists(
        path
    ):

        print(
            "Jarvis: ❌ That file no longer exists."
        )

        return False

    if not os.path.isfile(
        path
    ):

        print(
            "Jarvis: ❌ That path is not a file."
        )

        return False

    try:

        os.startfile(
            path
        )

        filename = os.path.basename(
            path
        )

        print(
            f"Jarvis: ✅ Opening {filename}..."
        )

        return True

    except Exception as e:

        print(
            f"Jarvis: ❌ I couldn't open the file: {e}"
        )

        return False


# ==================================================
# SHORT-TERM CONTEXT RESOLUTION
# ==================================================

def resolve_short_term_context(
    user_text
):

    if not user_text:
        return user_text

    memory = get_recent_memory(
        3
    )

    if not memory:
        return user_text

    text_lower = user_text.lower()

    reference_words = [
        " it ",
        " that ",
        " this ",
        " them ",
        " those ",
        " these ",
    ]

    has_reference = any(
        word in f" {text_lower} "
        for word in reference_words
    )

    if not has_reference:
        return user_text

    context_lines = []

    for turn in memory:

        context_lines.append(
            f"User: {turn.get('user', '')}"
        )

        context_lines.append(
            f"Jarvis: {turn.get('assistant', '')}"
        )

    context = "\n".join(
        context_lines
    )

    prompt = f"""
You are Jarvis's short-term context resolver.

The user is continuing a recent conversation.

Use the recent conversation to resolve references such as:

it
that
this
them
those
these

Do NOT answer the user.

Rewrite the user's message so that ambiguous references
are replaced with the most likely subject from the recent
conversation.

Keep the original intent unchanged.

If the message does not actually need context, return it
unchanged.

Return ONLY the rewritten user message.

Recent conversation:

{context}

Current user message:

{user_text}
"""

    try:

        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        resolved = response[
            "message"
        ][
            "content"
        ].strip()

        resolved = re.sub(
            r"^```.*?\n",
            "",
            resolved,
            flags=re.DOTALL
        )

        resolved = re.sub(
            r"\n```$",
            "",
            resolved
        )

        resolved = resolved.strip()

        if not resolved:
            return user_text

        return resolved

    except Exception as e:

        print(
            f"Context resolution error: {e}"
        )

        return user_text


# ==================================================
# CHAT
# ==================================================

def handle_chat(text):

    if not text:
        return False

    answer = ask_ai(
        text
    )

    print(
        f"Jarvis: {answer}"
    )

    return True


# ==================================================
# SKILL
# ==================================================

def handle_skill(
    skill_name
):

    if not skill_name:

        return False

    skill = find_skill(
        skill_name
    )

    if not skill:

        print(
            "Jarvis: ❌ Skill not found."
        )

        return False

    return execute_command(
        skill_name
    )

# ==================================================
# PROCESS MULTIPLE ACTIONS
# ==================================================

def process_actions(
    result
):

    if not isinstance(
        result,
        dict
    ):
        return False

    actions = result.get(
        "actions",
        []
    )

    if not isinstance(
        actions,
        list
    ):
        return False

    processed = False

    for action in actions:

        if not isinstance(
            action,
            dict
        ):
            continue

        action_type = action.get(
            "type"
        )

        # ------------------------------------------
        # SYSTEM INFO
        # ------------------------------------------

        if action_type == "system_info":

            info_type = action.get(
                "info",
                ""
            )

            now = datetime.now()

            # --------------------------------------
            # MULTIPLE COMPONENTS
            # --------------------------------------

            if isinstance(
                info_type,
                list
            ):

                for info in info_type:

                    info = str(
                        info
                    ).lower().strip()

                    if info == "day":
                        print(
                            f"📆 Day: {now.strftime('%A')}"
                        )

                    elif info == "date":
                        print(
                            f"📅 Date: {now.strftime('%d %B %Y')}"
                        )

                    elif info == "month":
                        print(
                            f"🗓️ Month: {now.strftime('%B')}"
                        )

                    elif info == "year":
                        print(
                            f"📌 Year: {now.strftime('%Y')}"
                        )

                    elif info == "time":
                        print(
                            f"🕒 Time: {now.strftime('%I:%M %p')}"
                        )

            # --------------------------------------
            # SINGLE COMPONENT
            # --------------------------------------

            else:

                info_type = str(
                    info_type
                ).lower().strip()

                if info_type == "day":

                    print(
                        f"📅 Today is {now.strftime('%A')}."
                    )

                elif info_type == "date":

                    print(
                        f"📅 Today's date is "
                        f"{now.strftime('%d %B %Y')}."
                    )

                elif info_type == "month":

                    print(
                        f"📅 The current month is "
                        f"{now.strftime('%B')}."
                    )

                elif info_type == "year":

                    print(
                        f"📅 The current year is "
                        f"{now.strftime('%Y')}."
                    )

                elif info_type == "time":

                    print(
                        f"🕒 The current time is "
                        f"{now.strftime('%I:%M %p')}."
                    )

                else:

                    print(
                        "I couldn't determine the requested "
                        "system information."
                    )

            processed = True
            continue
        # ------------------------------------------
        # CHAT
        # ------------------------------------------

        if action_type == "chat":

            text = action.get(
                "text",
                ""
            )

            if text:

                handle_chat(
                    text
                )

                processed = True

        # ------------------------------------------
        # APP
        # ------------------------------------------

        elif action_type == "launch_app":

            apps = action.get(
                "apps",
                []
            )

            if apps:

                handle_launch_apps(
                    apps
                )

                processed = True

        # ------------------------------------------
        # EXACT URL
        # ------------------------------------------

        elif action_type == "open_url":

            url = action.get(
                "url",
                ""
            )

            if url:

                handle_open_url(
                    url
                )

                processed = True

        # ------------------------------------------
        # WEBSITE
        # ------------------------------------------

        elif action_type == "open_website":

            website = action.get(
                "website",
                ""
            )

            if website:

                handle_open_website(
                    website
                )

                processed = True

        # ------------------------------------------
        # WEB SEARCH
        # ------------------------------------------

        elif action_type == "web_search":

            site = action.get(
                "site",
                ""
            )

            query = action.get(
                "query",
                ""
            )

            if site and query:

                handle_web_search(
                    site,
                    query
                )

                processed = True

        # ------------------------------------------
        # FILE SEARCH
        # ------------------------------------------

        elif action_type == "search_files":

            query = action.get(
                "query",
                ""
            )

            exact = action.get(
                "exact",
                False
            )

            location = action.get(
                "location",
                ""
            )

            if query:

                handle_file_search(
                    query=query,
                    exact=exact,
                    location=location
                )

                processed = True

        # ------------------------------------------
        # OPEN FILE
        # ------------------------------------------

        elif action_type == "open_file":

            query = action.get(
                "query",
                ""
            )

            exact = action.get(
                "exact",
                False
            )

            index = action.get(
                "index"
            )

            reference = action.get(
                "reference",
                ""
            )

            if isinstance(
                index,
                str
            ):

                try:

                    index = int(
                        index
                    )

                except ValueError:

                    index = None

            handle_open_file(
                query=query,
                exact=exact,
                index=index,
                reference=reference
            )

            processed = True

        # ------------------------------------------
        # SKILL
        # ------------------------------------------

        elif action_type == "skill":

            skill = action.get(
                "skill",
                ""
            )

            if skill:

                handle_skill(
                    skill
                )

                processed = True

    return processed



# ==================================================
# NORMAL AI
# ==================================================

def ask_ai(
    user_text,
    conversation_context=""
):

    try:

        system_prompt = """
You are Jarvis, a personal AI assistant.

Respond naturally and conversationally.

Keep normal answers short and easy to speak aloud.

Default:

- 1 to 4 short sentences.
- Answer directly.
- Use simple language.
- Sound friendly.
- Avoid unnecessary headings.
- Avoid long lists for simple questions.
- Do not write essays unless the user asks.

For greetings, sound natural.

Example:

User:

hlo

Assistant:

Hey sir! How can I help?

Example:

User:

who is Shah Rukh Khan?

Assistant:

Shah Rukh Khan is a famous Indian actor, widely known as the King of Bollywood. He has appeared in many successful Hindi films.

Only give detailed answers when the user asks for
details, examples, steps, or a full explanation.

Use the recent conversation when the user says:

"it", "this", "that", "he", "she", "they",
"the first one", "the second one",
or similar references.

If the answer depends on previous conversation,
use that context.

Recent conversation:

""" + conversation_context

        response = chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ]
        )

        return response[
            "message"
        ][
            "content"
        ].strip()

    except Exception as e:

        return f"AI error: {e}"


# ==================================================
# BUILD COMMAND MEMORY
# ==================================================

def build_command_metadata(
    result
):

    """
    Extract useful structured information from
    executed actions so future messages can refer
    to previous commands.
    """

    metadata = {
        "type": "command",
        "actions": result.get(
            "actions",
            []
        )
    }

    actions = result.get(
        "actions",
        []
    )

    if not isinstance(
        actions,
        list
    ):

        return metadata

    for action in actions:

        if not isinstance(
            action,
            dict
        ):

            continue

        action_type = action.get(
            "type"
        )

        # ------------------------------------------
        # WEB SEARCH
        # ------------------------------------------

        if action_type == "web_search":

            metadata.update({
                "intent": "web_search",
                "site": action.get(
                    "site",
                    ""
                ),
                "query": action.get(
                    "query",
                    ""
                )
            })

            break

        # ------------------------------------------
        # OPEN WEBSITE
        # ------------------------------------------

        if action_type == "open_website":

            metadata.update({
                "intent": "open_website",
                "website": action.get(
                    "website",
                    ""
                )
            })

            break

        # ------------------------------------------
        # OPEN URL
        # ------------------------------------------

        if action_type == "open_url":

            metadata.update({
                "intent": "open_url",
                "url": action.get(
                    "url",
                    ""
                )
            })

            break

        # ------------------------------------------
        # LAUNCH APP
        # ------------------------------------------

        if action_type == "launch_app":

            metadata.update({
                "intent": "launch_app",
                "apps": action.get(
                    "apps",
                    []
                )
            })

            break

        # ------------------------------------------
        # FILE SEARCH
        # ------------------------------------------

        if action_type == "search_files":

            metadata.update({
                "intent": "search_files",
                "query": action.get(
                    "query",
                    ""
                ),
                "exact": action.get(
                    "exact",
                    False
                ),
                "location": action.get(
                    "location",
                    ""
                )
            })

            break

        # ------------------------------------------
        # FILE OPEN
        # ------------------------------------------

        if action_type == "open_file":

            metadata.update({
                "intent": "open_file",
                "query": action.get(
                    "query",
                    ""
                ),
                "index": action.get(
                    "index"
                ),
                "reference": action.get(
                    "reference",
                    ""
                )
            })

            break

        # ------------------------------------------
        # SKILL
        # ------------------------------------------

        if action_type == "skill":

            metadata.update({
                "intent": "skill",
                "skill": action.get(
                    "skill",
                    ""
                )
            })

            break

    return metadata


# ==================================================
# MAIN
# ==================================================

def main():

    print("=" * 60)
    print("JARVIS SMART AI ASSISTANT")
    print("=" * 60)

    print(
        "Type 'exit' to quit."
    )

    print()

    while True:

        try:

            user_text = input(
                "You: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                "\nJarvis: Goodbye."
            )

            break

        if not user_text:
            continue

        # ------------------------------------------
        # EXIT
        # ------------------------------------------

        if user_text.lower() in {
            "exit",
            "quit",
            "bye"
        }:

            print(
                "Jarvis: Goodbye."
            )

            break

        # ------------------------------------------
        # GREETING
        # ------------------------------------------

        if is_greeting(
            user_text
        ):

            assistant_response = (
                "Hey! How can I help?"
            )

            print(
                f"Jarvis: {assistant_response}"
            )

            remember(
                user_text,
                assistant_response,
                metadata={
                    "type": "greeting"
                }
            )

            continue

        # ------------------------------------------
        # NAME
        # ------------------------------------------

        if user_text.lower().startswith("my name is "):

            name = user_text[11:].strip()

            if name:

                assistant_response = f"Nice to meet you, {name}."

                print(f"Jarvis: {assistant_response}")

                remember_context(
                    "personal_information",
                    {
                        "name": name
                    }
                )

                remember(
                    user_text,
                    assistant_response,
                    metadata={
                        "type": "personal_information",
                        "name": name
                    }
                )

            continue

        # ------------------------------------------
        # PENDING SKILL NAME
        # ------------------------------------------

        global pending_skill_creation

        if pending_skill_creation:

            skill_name = user_text.strip()

            skill_request = pending_skill_creation

            pending_skill_creation = None

            if skill_name:

                success = create_skill(
                    skill_request,
                    skill_name
                )

                assistant_response = (
                    f'Skill "{skill_name}" created successfully.'
                    if success
                    else
                    f'I could not create skill "{skill_name}".'
                )

                remember(
                    user_text,
                    assistant_response,
                    metadata={
                        "type": "skill_creation",
                        "skill": skill_name
                    }
                )

            continue

        # ------------------------------------------
        # SKILL CREATION
        # ------------------------------------------

        if is_skill_creation_request(
            user_text
        ):

            pending_skill_creation = user_text

            print("Jarvis: What would you like to name this skill?")

            continue

        # ------------------------------------------
        # REMOVE REGISTERED SKILL
        # ------------------------------------------

        remove_match = re.match(
            r"^(?:please\s+)?(?:remove|delete)\s+(.+?)(?:\s+skill)?$",
            user_text.strip(),
            re.IGNORECASE
        )

        if remove_match:

            skill_name = remove_match.group(1).strip()

            print(
                f"Jarvis: 🗑️ Removing skill '{skill_name}'..."
            )

            success = remove_skill(
                skill_name
            )

            if success:

                assistant_response = (
                    f"Skill '{skill_name}' removed successfully."
                )

                print(
                    f"Jarvis: ✅ {assistant_response}"
                )

            else:

                assistant_response = (
                    f"Skill '{skill_name}' was not found."
                )

                print(
                    f"Jarvis: ❌ {assistant_response}"
                )

            continue

        # ------------------------------------------
        # REGISTERED SKILL CHECK
        # ------------------------------------------

        skill_match = find_skill(
            user_text
        )

        if skill_match:

            registry = load_registry()

            matched_skill_name = None

            for name, data in registry.items():

                if data == skill_match:
                    matched_skill_name = name
                    break

            if matched_skill_name:

                print(
                    f"Jarvis: ▶ Running skill '{matched_skill_name}'..."
                )

                success = handle_skill(
                    matched_skill_name
                )

                if success:
                    assistant_response = (
                        f"Skill '{matched_skill_name}' executed successfully."
                    )
                else:
                    assistant_response = (
                        f"Skill '{matched_skill_name}' failed."
                    )

                print(
                    f"Jarvis: {'✅' if success else '❌'} "
                    f"{assistant_response}"
                )

                command_metadata = {
                    "type": "command",
                    "intent": "skill",
                    "skill": matched_skill_name
                }

                remember_context(
                    "last_command",
                    command_metadata
                )

                remember(
                    user_text,
                    assistant_response,
                    metadata=command_metadata
                )

                continue

        # ------------------------------------------
        # GET RECENT CONVERSATION CONTEXT
        # ------------------------------------------

        conversation_context = (
            build_context_with_metadata(
                MAX_CONTEXT_TURNS
            )
        )

        # ------------------------------------------
        # GET LAST STRUCTURED COMMAND
        # ------------------------------------------

        last_command = get_last_command_context()

        if last_command:

            command_lines = [
                "",
                "==================================================",
                "LATEST STRUCTURED COMMAND STATE",
                "=================================================="
            ]

            for key, value in last_command.items():

                if key == "actions":
                    continue

                command_lines.append(
                    f"{key}: {value}"
                )

            conversation_context += (
                "\n".join(
                    command_lines
                )
            )

        # ------------------------------------------
        # TWO-STAGE INTENT
        # ------------------------------------------

        result = parse_user_intent(
            user_text,
            conversation_context
        )

        # ------------------------------------------
        # NO INTENT RESULT
        # ------------------------------------------

        if not result:

            answer = ask_ai(
                user_text,
                conversation_context
            )

            print(
                f"Jarvis: {answer}"
            )

            remember(
                user_text,
                answer,
                metadata={
                    "type": "conversation"
                }
            )

            continue

        # ------------------------------------------
        # NORMAL CONVERSATION
        # ------------------------------------------

        if result.get(
            "mode"
        ) == "conversation":

            answer = ask_ai(
                user_text,
                conversation_context
            )

            print(
                f"Jarvis: {answer}"
            )

            remember(
                user_text,
                answer,
                metadata={
                    "type": "conversation"
                }
            )

            continue

        # ------------------------------------------
        # COMMAND
        # ------------------------------------------

        if result.get(
            "mode"
        ) == "command":

            handled = process_actions(
                result
            )

            if handled:

                command_metadata = build_command_metadata(
                    result
                )

                remember_context(
                    "last_command",
                    command_metadata
                )

                remember(
                    user_text,
                    "Command executed.",
                    metadata=command_metadata
                )

                continue
        # ------------------------------------------
        # FALLBACK
        # ------------------------------------------

        answer = ask_ai(
            user_text,
            conversation_context
        )

        print(
            f"Jarvis: {answer}"
        )

        remember(
            user_text,
            answer,
            metadata={
                "type": "conversation"
            }
        )


# ==================================================
# START
# ==================================================

if __name__ == "__main__":
    main()
