import json
import re

from ollama import chat


# ==================================================
# CONFIGURATION
# ==================================================

MODEL = "qwen2.5:7b-instruct-q3_K_M"


# ==================================================
# CLEAN JSON
# ==================================================

def clean_json_response(
    text
):

    if not text:
        return ""

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


# ==================================================
# STAGE 1
# CONVERSATION OR COMMAND
# ==================================================

def classify_message(
    user_text,
    conversation_context=""
):

    prompt = f"""
You are Jarvis's first-stage intent classifier.

Decide whether the CURRENT user message is:

1. conversation
2. command

You have access to recent conversation context and
structured information about previous commands.

IMPORTANT:
Use previous context to understand references such as:

- it
- this
- that
- them
- those
- these
- he
- she
- they
- there
- here
- the first one
- the second one
- the same thing
- the previous one
- the above

A message is a COMMAND when the user wants Jarvis
to perform an action OR retrieve live/current information
from the computer/system.

IMPORTANT:
Requests for the current system date, day, month, year,
time, or datetime are ALWAYS commands, not conversation.

SYSTEM INFORMATION:
Questions asking for the current date or time are COMMANDS,
because Jarvis must retrieve the value from the computer.

Examples:
"what time it is" => command
"what time is it" => command
"what day today" => command
"what day is today" => command
"what date is it" => command
"what month is it" => command
"what year is this" => command

A message is CONVERSATION when the user is only asking
a question, discussing something, or asking Jarvis
to explain something.

Examples:

"why did I say open google?"
=> conversation

"what happens when I say open signal?"
=> conversation

"who is Shah Rukh Khan?"
=> conversation

"tell me more about him"
=> conversation

But:

"open google"
=> command

"start signal"
=> command

"search it on google"
=> command

"search python courses on youtube"
=> command

IMPORTANT:

A command can contain references to previous context.

Example:

Previous:
User: search python courses on youtube

Current:
search it on google

=> command

Return ONLY valid JSON.

Format:

{{
    "mode": "conversation"
}}

or:

{{
    "mode": "command"
}}

==================================================
RECENT CONVERSATION + STRUCTURED CONTEXT
==================================================

{conversation_context}

==================================================
CURRENT MESSAGE
==================================================

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

        content = response[
            "message"
        ][
            "content"
        ].strip()

        content = clean_json_response(
            content
        )

        data = json.loads(
            content
        )

        if not isinstance(
            data,
            dict
        ):
            return None

        mode = data.get(
            "mode"
        )

        if mode not in {
            "conversation",
            "command"
        }:
            return None

        return {
            "mode": mode
        }

    except Exception as e:

        print(
            f"Classification error: {e}"
        )

        return None


# ==================================================
# STAGE 2
# EXTRACT ACTIONS
# ==================================================

def extract_actions(
    user_text,
    conversation_context=""
):

    # ------------------------------------------
    # NEGATIVE COMMAND
    # ------------------------------------------

    text_lower = str(
        user_text
    ).strip().lower()

    negative_patterns = [
        r"^do not\s+",
        r"^don't\s+",
        r"^dont\s+",
        r"^do n't\s+",
        r"^never\s+",
    ]

    if any(
        re.match(
            pattern,
            text_lower
        )
        for pattern in negative_patterns
    ):
        return {
            "actions": []
        }    

    prompt = f"""
You are Jarvis's action extractor.

The CURRENT message has already been classified
as a command.

Your job is to convert the current message into
one or more executable actions.

Use BOTH:

1. Recent conversation
2. Structured previous-command context

to resolve references.

==================================================
REFERENCE RESOLUTION
==================================================

Words such as:

it
this
that
them
those
these
he
she
they
there
here
the first one
the second one
the previous one
the same thing

may refer to something from recent conversation.

IMPORTANT:

If structured context contains a previous command,
prefer the structured information over guessing.

==================================================
WEB SEARCH REFERENCE
==================================================

Previous command:

intent = web_search
site = youtube
query = python course

Current:

search it on google

Correct action:

{{
    "type": "web_search",
    "site": "google",
    "query": "python course"
}}

DO NOT return:

{{
    "type": "web_search",
    "site": "google",
    "query": "it"
}}

The word "it" must not become the final query
when the previous context identifies what it means.

==================================================
WEBSITE REFERENCE
==================================================

Previous command:

intent = open_website
website = youtube

Current:

search python course on it

Correct action:

{{
    "type": "web_search",
    "site": "youtube",
    "query": "python course"
}}

==================================================
WEB SEARCH
==================================================

Use web_search only when the user wants to search.

Examples:

"search python courses on youtube"

=> site = youtube
=> query = python courses

"search python courses on google"

=> site = google
=> query = python courses

"search it on google"

If previous structured context contains:

site = youtube
query = python courses

Then:

=> site = google
=> query = python courses

Never use unresolved pronouns as the final query.

==================================================
FILE SEARCH
==================================================

Use search_files when the user wants to find files.

Examples:

"find test"

=> query = test

"find exact tester.exe"

=> query = tester.exe
=> exact = true

==================================================
FILE SEARCH LOCATION
==================================================

When the user specifies a folder or location, preserve it
in the "location" field.

Examples:

"find abc.txt in documents"

=>

{{
    "type": "search_files",
    "query": "abc.txt",
    "exact": false,
    "location": "documents"
}}

"find report.pdf in downloads"

=>

{{
    "type": "search_files",
    "query": "report.pdf",
    "exact": false,
    "location": "downloads"
}}

"find tester.exe on desktop"

=>

{{
    "type": "search_files",
    "query": "tester.exe",
    "exact": false,
    "location": "desktop"
}}

If no location is specified:

"find abc.txt"

=>

{{
    "type": "search_files",
    "query": "abc.txt",
    "exact": false,
    "location": ""
}}

IMPORTANT:
Never remove or ignore a location explicitly provided by the user.

==================================================
FILE OPEN
==================================================

Use open_file when the user wants to open a file.

For:

"open the first one"

use:

{{
    "type": "open_file",
    "index": 1,
    "reference": "latest_search"
}}

For:

"open the second one"

use:

{{
    "type": "open_file",
    "index": 2,
    "reference": "latest_search"
}}

For:

"open the file I just found"

use:

{{
    "type": "open_file",
    "index": null,
    "reference": "latest_search"
}}

==================================================
REGISTERED SKILLS
==================================================

Use the "skill" action when the user wants to execute
a registered Jarvis skill.

Skill names are dynamic.

Do NOT assume any specific skill name.

Examples:

"run game mode"

=>

{{
    "type": "skill",
    "skill": "game mode"
}}

"start game mode"

=>

{{
    "type": "skill",
    "skill": "game mode"
}}

"turn on game mode"

=>

{{
    "type": "skill",
    "skill": "game mode"
}}

"activate game mode"

=>

{{
    "type": "skill",
    "skill": "game mode"
}}

"open game mode"

=>

{{
    "type": "skill",
    "skill": "game mode"
}}

The words:

run
start
open
activate
launch
turn on

can indicate skill execution.

Do not interpret the command as launch_app when
the target refers to a registered Jarvis skill.

==================================================
APPLICATION
==================================================

Use launch_app for desktop applications.

Examples:

"open signal"

=> apps = ["signal"]

"start signal and discord"

=> apps = ["signal", "discord"]

==================================================
WEBSITE
==================================================

"open github"

=> open_website
=> website = github

"open https://github.com"

=> open_url
=> url = https://github.com

==================================================
MULTI INTENT
==================================================

"what is Docker and start vscode"

=> chat + launch_app

"search Python courses on YouTube and start Signal"

=> web_search + launch_app

==================================================
ALLOWED ACTIONS
==================================================

ALLOWED ACTIONS:

- chat
- launch_app
- open_url
- open_website
- web_search
- search_files
- open_file
- system_info
- skill
- none

==================================================
SYSTEM DATE AND TIME
==================================================

Use system_info when the user asks for current
date/time information from the computer.

Determine the requested component carefully.

RULES:

1. DAY ONLY
Examples:
"what day is it"
"what day today"
"which day is today"

Return:
{{
    "type": "system_info",
    "info": "day"
}}

2. DATE ONLY
Examples:
"what is today's date"
"what date is it"
"tell me today's date"

Return:
{{
    "type": "system_info",
    "info": "date"
}}

3. MONTH ONLY
Examples:
"what month"
"what month is it"
"which month are we in"
"tell me the current month"

Return:
{{
    "type": "system_info",
    "info": "month"
}}

4. YEAR ONLY
Examples:
"what year"
"what year is it"
"which year are we in"
"tell me the current year"

Return:
{{
    "type": "system_info",
    "info": "year"
}}

5. TIME ONLY
Examples:
"what time is it"
"what time it is"
"tell me the current time"

Return:
{{
    "type": "system_info",
    "info": "time"
}}

6. MULTIPLE DATE/TIME COMPONENTS

If the user asks for multiple date/time components,
return a system_info action with an "info" list.

Use these component names:

- day
- date
- month
- year
- time

Examples:

"what time and year"

Return:
{{
    "type": "system_info",
    "info": ["time", "year"]
}}

"what month and year"

Return:
{{
    "type": "system_info",
    "info": ["month", "year"]
}}

"what day and month"

Return:
{{
    "type": "system_info",
    "info": ["day", "month"]
}}

"what date and time"

Return:
{{
    "type": "system_info",
    "info": ["date", "time"]
}}

"what day month and year"

Return:
{{
    "type": "system_info",
    "info": ["day", "month", "year"]
}}

"display current date and time"

Return:
{{
    "type": "system_info",
    "info": ["date", "time"]
}}

IMPORTANT:
Return ONLY the components explicitly requested by
the user.

Do not automatically include date, day, month, year,
or time if the user did not request them.

Examples:

"what is month and year"
=> ["month", "year"]

"what is the date and time"
=> ["date", "time"]

"tell me the month and year"
=> ["month", "year"]

"display current date and time"
=> ["date", "time"]

"show date month and year"
=> ["date", "month", "year"]

"tell me day month and year"
=> ["day", "month", "year"]


==================================================
IMPORTANT
==================================================

Do not invent missing information.

Use structured context when available.

Do not return shell commands.

Do not return PowerShell commands.

Do not return executable paths.

Do not return Python code.

Return ONLY valid JSON.

Format:

{{
    "actions": [
        {{
            "type": "chat",
            "text": "..."
        }},
        {{
            "type": "launch_app",
            "apps": ["signal"]
        }},
        {{
            "type": "open_url",
            "url": "https://example.com"
        }},
        {{
            "type": "open_website",
            "website": "github"
        }},
        {{
            "type": "web_search",
            "site": "google",
            "query": "python courses"
        }},
        {{
            "type": "search_files",
            "query": "test",
            "exact": false,
            "location": ""
        }},
        {{
            "type": "open_file",
            "query": "",
            "exact": false,
            "index": 1,
            "reference": "latest_search"
        }},

        {{
            "type": "system_info",
            "info": "time"
        }},

        {{
            "type": "skill",
            "skill": "example"
        }}
    ]
}}

==================================================
RECENT CONVERSATION + STRUCTURED CONTEXT
==================================================

{conversation_context}

==================================================
CURRENT MESSAGE
==================================================

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

        content = response[
            "message"
        ][
            "content"
        ].strip()

    

        content = clean_json_response(
            content
        )

        data = json.loads(
            content
        )

        if not isinstance(
            data,
            dict
        ):
            return None

        actions = data.get(
            "actions"
        )

        if actions is None:

            if isinstance(
                data.get("type"),
                str
            ):
                actions = [
                    data
                ]

            else:
                actions = []

        if not isinstance(
            actions,
            list
        ):
            return None

        return {
            "actions": actions
        }

    except Exception as e:

        print(
            f"Action extraction error: {e}"
        )

        return None


# ==================================================
# MAIN PARSER
# ==================================================

def parse_user_intent(
    user_text,
    conversation_context=""
):

    classification = classify_message(
        user_text,
        conversation_context
    )

    if not classification:

        return None

    if classification.get(
        "mode"
    ) == "conversation":

        return {
            "mode": "conversation"
        }

    actions = extract_actions(
        user_text,
        conversation_context
    )

    if not actions:

        return {
            "mode": "conversation"
        }

    return {
        "mode": "command",
        "actions": actions.get(
            "actions",
            []
        )
    }


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS CONTEXT-AWARE INTENT TEST")
    print("=" * 60)
    print()

    context = """
User: search python course on youtube
Jarvis: Searching Youtube for "python course"...

Structured context:
- type: command
- intent: web_search
- site: youtube
- query: python course
"""

    tests = [
        "search it on google",
        "search python course on it",
        "open google",
    ]

    for text in tests:

        print(
            f"USER: {text}"
        )

        result = parse_user_intent(
            text,
            context
        )

        print(
            json.dumps(
                result,
                indent=4
            )
        )

        print(
            "-" * 60
        )