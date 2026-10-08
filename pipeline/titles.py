import re

FUZZY_IDENTITY_THRESHOLD = 92
TITLE_QUALIFIER_TOKENS = {
    "spinoff",
    "spin-off",
    "side-story",
    "sidestory",
    "gaiden",
    "novel",
    "oneshot",
}


def _normalize_words(title: str) -> set[str]:
    return set([word for word in re.split(r"[^a-z0-9]+", title.lower()) if word])


def _has_qualifier(title: str, qualifier_tokens) -> bool:
    words = _normalize_words(title)
    normalized_title = re.sub(r"[^a-z0-9]+", "", title.lower())
    for token in qualifier_tokens:
        normalized_token = re.sub(r"[^a-z0-9]+", "", token.lower())
        if not normalized_token:
            continue
        if normalized_token == "au":
            if "au" in words:
                return True
            continue
        if normalized_token in normalized_title:
            return True
    return False


def _qualifier_mismatch(title_1: str, title_2: str, qualifier_tokens) -> bool:
    return _has_qualifier(title_1, qualifier_tokens) != _has_qualifier(
        title_2, qualifier_tokens
    )


def _normalize_title_for_prefix(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


class PrefixCandidateIndex:
    """Sorted prefix index over normalized manga titles.

    Titles are bucketed by an adaptive prefix: the prefix grows from
    ``prefix_len`` up to ``max_prefix_len`` until the bucket holds at most
    ``target_bucket_size`` entries. ``fallback`` is returned whenever no
    bucket can be built for a title.
    """

    def __init__(self, prefix_len: int, max_prefix_len: int, target_bucket_size: int):
        self.prefix_len = prefix_len
        self.max_prefix_len = max_prefix_len
        self.target_bucket_size = target_bucket_size
        self.sorted_titles: list[tuple[str, dict]] = []

    def ensure_sorted(self, items: list[dict]):
        if self.sorted_titles:
            return
        for item in items:
            self.sorted_titles.append(
                (_normalize_title_for_prefix(item["title"]), item)
            )
        self.sorted_titles.sort(key=lambda entry: entry[0])

    def reset(self, items: list[dict] = None):
        self.sorted_titles = []
        if items is not None:
            self.ensure_sorted(items)

    def is_empty(self) -> bool:
        return not self.sorted_titles

    def scan(self, prefix: str) -> list[dict]:
        if not prefix:
            return []
        candidates = []
        in_prefix_range = False
        for normalized_title, item in self.sorted_titles:
            if normalized_title.startswith(prefix):
                in_prefix_range = True
                candidates.append(item)
            elif in_prefix_range or normalized_title > prefix:
                break
        return candidates

    def candidates(self, title: str, fallback) -> list[dict]:
        normalized = _normalize_title_for_prefix(title)
        if not normalized:
            return fallback

        start_len = min(self.prefix_len, len(normalized))
        max_len = min(self.max_prefix_len, len(normalized))
        if start_len == 0:
            return fallback

        prefix = normalized[:start_len]
        candidates = self.scan(prefix)
        last_non_empty = candidates
        if 0 < len(candidates) <= self.target_bucket_size or start_len >= max_len:
            return candidates or fallback

        for length in range(start_len + 1, max_len + 1):
            deeper_prefix = normalized[:length]
            deeper_candidates = self.scan(deeper_prefix)
            if deeper_candidates:
                last_non_empty = deeper_candidates
            if 0 < len(deeper_candidates) <= self.target_bucket_size:
                return deeper_candidates
            if not deeper_candidates:
                break

        return last_non_empty or fallback
