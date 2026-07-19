from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    metadata: dict


def chunk_text(
    text: str,
    max_characters: int = 1200,
    overlap_characters: int = 150,
) -> list[TextChunk]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(normalized_text):
        end = min(start + max_characters, len(normalized_text))
        content = normalized_text[start:end].strip()
        if content:
            chunks.append(
                TextChunk(
                    content=content,
                    chunk_index=chunk_index,
                    metadata={
                        "start_character": start,
                        "end_character": end,
                    },
                )
            )
            chunk_index += 1

        if end == len(normalized_text):
            break

        start = max(0, end - overlap_characters)

    return chunks
