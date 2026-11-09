from collections.abc import Callable


def split_to_token_limit(
    text: str,
    count_tokens: Callable[[str], int],
    max_tokens: int,
    prefix: str = "passage: ",
) -> list[str]:
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")

    text = text.strip()
    if not text:
        raise ValueError("text must not be empty")

    pending = [text]
    chunks = []

    while pending:
        part = pending.pop()

        if count_tokens(prefix + part) <= max_tokens:
            chunks.append(part)
            continue

        if len(part) == 1:
            raise ValueError("Token budget cannot fit a single character")

        midpoint = len(part) // 2
        boundary = midpoint

        if " " in part:
            candidates = [
                i for i, char in enumerate(part) if char == " "
            ]
            boundary = min(
                candidates,
                key=lambda i: abs(i - midpoint),
            )

        left = part[:boundary].strip()
        right = part[boundary:].strip()
        pending.extend([right, left])

    return chunks