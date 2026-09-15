# ==================================================
# JARVIS SHORT-TERM MEMORY
# ==================================================

from collections import deque
from typing import Any, Dict, List, Optional


# ==================================================
# CONFIG
# ==================================================

MAX_TURNS = 8


# ==================================================
# MEMORY
# ==================================================

conversation_memory = deque(maxlen=MAX_TURNS)

# Generic structured context.
# STM does not decide what the values mean.
context_memory: Dict[str, Any] = {}


# ==================================================
# CONVERSATION MEMORY
# ==================================================

def remember(
    user_text: str,
    assistant_text: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Store one conversation turn.
    """

    if not user_text:
        return

    turn = {
        "user": str(user_text).strip(),
        "assistant": str(assistant_text or "").strip(),
        "metadata": dict(metadata or {})
    }

    conversation_memory.append(turn)


def get_memory() -> List[Dict[str, Any]]:
    return [dict(turn) for turn in conversation_memory]


def get_recent_memory(count: int = 3) -> List[Dict[str, Any]]:
    if count <= 0:
        return []

    recent = list(conversation_memory)[-count:]

    return [
        dict(turn)
        for turn in recent
    ]


def get_last_turn() -> Optional[Dict[str, Any]]:
    if not conversation_memory:
        return None

    return dict(conversation_memory[-1])


def get_last_exchange() -> Dict[str, str]:
    if not conversation_memory:
        return {
            "user": "",
            "assistant": ""
        }

    turn = conversation_memory[-1]

    return {
        "user": turn.get("user", ""),
        "assistant": turn.get("assistant", "")
    }


def get_last_user_message() -> str:
    if not conversation_memory:
        return ""

    return conversation_memory[-1].get("user", "")


def get_last_assistant_message() -> str:
    if not conversation_memory:
        return ""

    return conversation_memory[-1].get("assistant", "")


def get_last_metadata() -> Dict[str, Any]:
    if not conversation_memory:
        return {}

    metadata = conversation_memory[-1].get("metadata", {})

    if not isinstance(metadata, dict):
        return {}

    return dict(metadata)


def get_last_command_context() -> Dict[str, Any]:
    """
    Return the most recent command metadata.
    """

    for turn in reversed(conversation_memory):

        metadata = turn.get("metadata", {})

        if not isinstance(metadata, dict):
            continue

        if metadata.get("type") == "command":
            return dict(metadata)

    return {}


def find_previous_user_message(offset: int = 1) -> str:
    """
    Find an earlier user message.

    offset=1 -> previous user message
    offset=2 -> two user messages back
    """

    if offset <= 0:
        return get_last_user_message()

    user_messages = [
        turn.get("user", "")
        for turn in conversation_memory
        if turn.get("user")
    ]

    if len(user_messages) <= offset:
        return ""

    return user_messages[-(offset + 1)]


# ==================================================
# STRUCTURED CONTEXT
# ==================================================

def remember_context(key: str, value: Any) -> None:
    """
    Store generic structured context.

    STM does not interpret the key or value.
    """

    if not key:
        return

    context_memory[str(key)] = value


def remember_context_many(values: Dict[str, Any]) -> None:
    """
    Store multiple context values.
    """

    if not isinstance(values, dict):
        return

    for key, value in values.items():

        if key:
            context_memory[str(key)] = value


def get_context_value(
    key: str,
    default: Any = None
) -> Any:

    return context_memory.get(key, default)


def get_context() -> Dict[str, Any]:
    return dict(context_memory)


def forget_context(key: str) -> None:
    context_memory.pop(key, None)


# ==================================================
# BUILD AI CONTEXT
# ==================================================

def build_context(count: int = 3) -> str:
    """
    Build recent conversation context for the AI.
    """

    recent = get_recent_memory(count)

    if not recent:
        return ""

    lines = []

    for turn in recent:

        user = turn.get("user", "")
        assistant = turn.get("assistant", "")

        if user:
            lines.append(f"User: {user}")

        if assistant:
            lines.append(f"Jarvis: {assistant}")

    return "\n".join(lines)


def build_context_with_metadata(count: int = 3) -> str:
    """
    Build complete short-term context.

    Includes:
    - recent conversation
    - structured metadata
    - current structured memory
    """

    recent = get_recent_memory(count)

    lines = []

    # ------------------------------
    # Recent conversation
    # ------------------------------

    if recent:

        lines.append("RECENT CONVERSATION:")

        for turn in recent:

            user = turn.get("user", "")
            assistant = turn.get("assistant", "")
            metadata = turn.get("metadata", {})

            if user:
                lines.append(f"User: {user}")

            if assistant:
                lines.append(f"Jarvis: {assistant}")

            if metadata:

                lines.append("Turn metadata:")

                for key, value in metadata.items():

                    # Actions can be large and are already represented
                    # by other metadata.
                    if key == "actions":
                        continue

                    lines.append(
                        f"- {key}: {value}"
                    )

    # ------------------------------
    # Structured memory
    # ------------------------------

    if context_memory:

        lines.append("")
        lines.append("CURRENT STRUCTURED MEMORY:")

        for key, value in context_memory.items():

            lines.append(
                f"- {key}: {value}"
            )

    return "\n".join(lines)


# ==================================================
# MEMORY MANAGEMENT
# ==================================================

def clear_memory() -> None:
    """
    Clear both conversation and structured STM.
    """

    conversation_memory.clear()
    context_memory.clear()


def memory_count() -> int:
    return len(conversation_memory)