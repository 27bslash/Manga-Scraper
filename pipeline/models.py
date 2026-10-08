from typing import  Optional, TypedDict


class Chapter(TypedDict):
    latest_link: str
    scansite: str


class Sources(TypedDict):
    latest_link: str
    latest: str
    old_chapters: Optional[dict[str, Chapter]]
    time_updated: float


class ComicData(TypedDict):
    time_updated: float
    title: str
    latest: str
    latest_link: str
    scansite: str
    domain: str
    type: str
    old_chapters: Optional[dict[str, Chapter]]
    sources: Optional[dict[str, Sources]]
