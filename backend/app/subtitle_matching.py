"""Rank an already recency-limited subtitle list; preserve recency for ties."""
import re
from difflib import SequenceMatcher
from pathlib import PurePath


def normalized_title(name):
    return " ".join(re.findall(r"[^\W_]+", PurePath(name).stem.casefold()))


def rank_subtitles(video_name, recent):
    title = normalized_title(video_name)
    return sorted(recent, key=lambda item: SequenceMatcher(
        None, title, normalized_title(item.file_name)
    ).ratio(), reverse=True)
