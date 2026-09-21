# ==================================================
# JARVIS CONVERSATION MEMORY
# Persistent SQLite-backed memory
# ==================================================

from memory_manager import (
    DEFAULT_USER_ID,
    save_conversation,
    get_recent_conversations,
    set_context,
    get_context as db_get_context,
    get_last_command,
)


# ==================================================
# CONFIGURATION
# ==================================================

MAX_TURNS = 10


# ==================================================
# REMEMBER CONVERSATION
# ==================================================

def remember(
    user_text,
    assistant_text,
    metadata=None,
    user_id=DEFAULT_USER_ID,
    session_id=None
):

    save_conversation(
        user_text=user_text,
        assistant_text=assistant_text,
        metadata=metadata or {},
        user_id=user_id,
        session_id=session_id
    )


# ==================================================
# GET RECENT MEMORY
# ==================================================

def get_recent_memory(
    limit=MAX_TURNS,
    user_id=DEFAULT_USER_ID
):

    return get_recent_conversations(
        limit=limit,
        user_id=user_id
    )


# ==================================================
# BUILD BASIC CONTEXT
# ==================================================

def build_context(
    limit=MAX_TURNS,
    user_id=DEFAULT_USER_ID
):

    memories = get_recent_memory(
        limit=limit,
        user_id=user_id
    )

    if not memories:
        return ""

    lines = []

    for memory in memories:

        lines.append(
            f"User: {memory['user']}"
        )

        lines.append(
            f"Jarvis: {memory['assistant']}"
        )

    return "\n".join(lines)


# ==================================================
# BUILD CONTEXT WITH METADATA
# ==================================================

def build_context_with_metadata(
    limit=MAX_TURNS,
    user_id=DEFAULT_USER_ID
):

    memories = get_recent_memory(
        limit=limit,
        user_id=user_id
    )

    if not memories:
        return ""

    lines = []

    for memory in memories:

        lines.append(
            f"User: {memory['user']}"
        )

        lines.append(
            f"Jarvis: {memory['assistant']}"
        )

        metadata = memory.get(
            "metadata",
            {}
        )

        if metadata:

            lines.append(
                f"Metadata: {metadata}"
            )

    return "\n".join(lines)


# ==================================================
# REMEMBER CONTEXT
# ==================================================

def remember_context(
    key,
    value,
    user_id=DEFAULT_USER_ID
):

    set_context(
        context_key=key,
        context_value=value,
        user_id=user_id
    )


# ==================================================
# REMEMBER MULTIPLE CONTEXT VALUES
# ==================================================

def remember_context_many(
    context_data,
    user_id=DEFAULT_USER_ID
):

    if not context_data:
        return

    for key, value in context_data.items():

        remember_context(
            key,
            value,
            user_id=user_id
        )


# ==================================================
# GET CONTEXT
# ==================================================

def get_context(
    key,
    user_id=DEFAULT_USER_ID,
    default=None
):

    return db_get_context(
        context_key=key,
        user_id=user_id,
        default=default
    )


# ==================================================
# GET SIMPLE CONTEXT VALUE
# ==================================================

def get_context_value(
    key,
    default=None,
    user_id=DEFAULT_USER_ID
):

    value = get_context(
        key,
        user_id=user_id,
        default=default
    )

    return value


# ==================================================
# GET LAST COMMAND CONTEXT
# ==================================================

def get_last_command_context(
    user_id=DEFAULT_USER_ID
):

    return get_last_command(
        user_id=user_id
    )