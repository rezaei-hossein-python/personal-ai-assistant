from app.core.logging import logger


memory_store = {}


def save_message(conversation_id: str, role: str, content: str):
    logger.info(f"Saving message for conversation {conversation_id}")

    if conversation_id not in memory_store:
        memory_store[conversation_id] = []

    memory_store[conversation_id].append(
        {
            "role": role,
            "content": content
        }
    )


def get_conversation(conversation_id: str):
    logger.info(f"Retrieving memory for conversation {conversation_id}")

    return memory_store.get(conversation_id, [])