from app.services.retrieval_service import RetrievedChunk, format_chunks_for_prompt


def build_chat_messages(
    message: str,
    history: list,
    memories: list | None = None,
    document_chunks: list[RetrievedChunk] | None = None,
) -> list[dict]:
    conversation = []

    if memories:
        memory_text = "\n".join(
            [
                f"{memory.key}: {memory.value}"
                for memory in memories
            ]
        )
        conversation.append(
            {
                "role": "system",
                "content": (
                    "Known user information:\n"
                    f"{memory_text}"
                )
            }
        )

    document_context = format_chunks_for_prompt(document_chunks or [])
    if document_context:
        conversation.append(
            {
                "role": "system",
                "content": (
                    "Relevant user document context. Preserve source document "
                    "and chunk metadata for future citation use.\n\n"
                    f"{document_context}"
                )
            }
        )

    for item in history:
        conversation.append(
            {
                "role": item["role"],
                "content": item["content"],
            }
        )

    conversation.append(
        {
            "role": "user",
            "content": message,
        }
    )

    return conversation
