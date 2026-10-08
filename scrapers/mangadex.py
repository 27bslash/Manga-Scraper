from datetime import datetime
from pprint import pprint

import requests

from main import Source

MANGA_DEX_URL = "https://mangadex.org"
MANGA_DEX_API_URL = "https://api.mangadex.org"
MANGA_DEX_SCANSITE = "mangadex"
PAGE_LIMIT = 100
TITLE_BLACKLIST = ("doujinshi", "twitter")
MANGA_DEX_EXCLUDED_TAGS = ("b13b2a48-c720-44a9-9c77-39c9979373fb",)
MANGA_DEX_LANGUAGES = ("ja", "zh", "zh-hk", "ko")
MANGA_DEX_MIN_CHAPTERS = 20


CHAPTER_FEED_URL = (
    f"{MANGA_DEX_API_URL}/chapter"
    f"?limit={PAGE_LIMIT}&translatedLanguage[]=en"
    "&includes[]=scanlation_group&includes[]=manga"
    "&contentRating[]=safe&contentRating[]=suggestive"
    "&order[readableAt]=desc"
)


class MangaDex(Source):
    def __init__(self, scansite: str = MANGA_DEX_SCANSITE, debug: bool = False) -> None:
        self.base_url = MANGA_DEX_URL
        self.name = "MangaDex"
        self.source = MANGA_DEX_SCANSITE
        self.scansite = scansite
        self.debug = debug

    @staticmethod
    def _to_unix_timestamp(value):
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _pick_title(title_map):
        if not isinstance(title_map, dict):
            return None
        for language in ("en", "ja-ro", "ja"):
            value = title_map.get(language)
            if isinstance(value, str) and value.strip():
                return value
        for value in title_map.values():
            if isinstance(value, str) and value.strip():
                return value
        return None

    @staticmethod
    def _is_blacklisted(title):
        if not title:
            return False
        lowered = title.lower()
        return any(keyword in lowered for keyword in TITLE_BLACKLIST)

    @staticmethod
    def _manga_attributes(relationships):
        if not isinstance(relationships, list):
            return None
        for relationship in relationships:
            if (
                not isinstance(relationship, dict)
                or relationship.get("type") != "manga"
            ):
                continue
            attributes = relationship.get("attributes")
            if isinstance(attributes, dict):
                return attributes
        return None

    @staticmethod
    def _has_excluded_tags(attributes):
        if not isinstance(attributes, dict):
            return False
        tags = attributes.get("tags")
        if not isinstance(tags, list):
            return False
        return any(
            isinstance(tag, dict) and tag.get("id") in MANGA_DEX_EXCLUDED_TAGS
            for tag in tags
        )

    @staticmethod
    def _is_desired_language(attributes):
        return isinstance(attributes, dict) and attributes.get(
            "originalLanguage"
        ) in MANGA_DEX_LANGUAGES

    @staticmethod
    def _has_enough_chapters(attributes):
        if not isinstance(attributes, dict):
            return False
        last_chapter = attributes.get("lastChapter")
        if not isinstance(last_chapter, str) or not last_chapter.strip():
            return False
        try:
            return float(last_chapter) >= MANGA_DEX_MIN_CHAPTERS
        except ValueError:
            return False

    @staticmethod
    def _manga_title(attributes):
        if not isinstance(attributes, dict):
            return None
        candidates = []
        title = MangaDex._pick_title(attributes.get("title"))
        if title:
            candidates.append(title)
        alt_titles = attributes.get("altTitles")
        if isinstance(alt_titles, list):
            for alt_title in alt_titles:
                alt = MangaDex._pick_title(alt_title)
                if alt:
                    candidates.append(alt)
        if any(MangaDex._is_blacklisted(c) for c in candidates):
            return None
        if candidates:
            return Source.clean_title(candidates[0])
        return None

    def _internal_api_call(self, url):
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
        }
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                return self._parse_internal_api_response(response.json())
            except (requests.RequestException, ValueError) as e:
                print(
                    f"Error fetching MangaDex data from {url}: {e} retrying ({attempt + 1}/3)"
                )
        return []

    @staticmethod
    def _parse_internal_api_response(data):
        if isinstance(data, dict):
            data = data.get("data")
        if not isinstance(data, list):
            return []

        series = {}
        for chapter in data:
            try:
                parsed = MangaDex._parse_internal_api_chapter(chapter)
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                print(f"Error parsing MangaDex chapter: {error}")
                continue
            if parsed is None:
                continue

            title, chapter_num, chapter_link, chapter_timestamp = parsed
            entry = series.get(title)
            if entry is None:
                entry = {
                    "title": title,
                    "latest": str(chapter_num),
                    "old_chapters": {},
                    "time_updated": chapter_timestamp,
                    "domain": MANGA_DEX_URL,
                    "scansite": MANGA_DEX_SCANSITE,
                    "type": MANGA_DEX_SCANSITE,
                    "latest_link": chapter_link,
                }
                series[title] = entry
            entry["old_chapters"][str(chapter_num)] = {
                "latest_link": chapter_link,
                "scansite": MANGA_DEX_SCANSITE,
            }

        return list(series.values())

    @staticmethod
    def _parse_internal_api_chapter(chapter):
        if not isinstance(chapter, dict) or chapter.get("type") != "chapter":
            return None

        attributes = chapter.get("attributes")
        if not isinstance(attributes, dict):
            return None
        if attributes.get("isUnavailable"):
            return None

        manga_attributes = MangaDex._manga_attributes(chapter.get("relationships"))
        if manga_attributes is None:
            return None
        if MangaDex._has_excluded_tags(manga_attributes):
            return None
        if not MangaDex._is_desired_language(manga_attributes):
            return None
        if not MangaDex._has_enough_chapters(manga_attributes):
            return None

        chapter_num = attributes.get("chapter")
        if chapter_num is None or (
            isinstance(chapter_num, str) and not chapter_num.strip()
        ):
            return None

        title = MangaDex._manga_title(manga_attributes)
        if not title:
            return None

        chapter_timestamp = MangaDex._to_unix_timestamp(
            attributes.get("readableAt") or attributes.get("publishAt")
        )
        if chapter_timestamp is None:
            return None

        # MangaDex does not host external chapters, so the real link is the
        # external URL rather than a mangadex.org/chapter page.
        chapter_link = attributes.get("externalUrl")
        if not isinstance(chapter_link, str) or not chapter_link.strip():
            chapter_id = chapter.get("id")
            if not isinstance(chapter_id, str) or not chapter_id.strip():
                return None
            chapter_link = f"{MANGA_DEX_URL}/chapter/{chapter_id}"

        return title, chapter_num, chapter_link, chapter_timestamp

    @staticmethod
    def _merge_series(series_lists):
        merged = {}
        for entries in series_lists:
            for entry in entries:
                title = entry["title"]
                existing = merged.get(title)
                if existing is None:
                    merged[title] = entry
                    continue
                existing["old_chapters"].update(entry["old_chapters"])
                if entry["time_updated"] > existing["time_updated"]:
                    existing["latest"] = entry["latest"]
                    existing["latest_link"] = entry["latest_link"]
                    existing["time_updated"] = entry["time_updated"]
        return list(merged.values())

    def _fetch_api_series(self):
        pages = [
            self._internal_api_call(f"{CHAPTER_FEED_URL}&offset=0"),
            self._internal_api_call(f"{CHAPTER_FEED_URL}&offset={PAGE_LIMIT}"),
        ]
        results = self._merge_series(pages)
        if self.debug:
            pprint(results)
        return results

    def main(self, debug=False, scrape_site=True):
        results = self._fetch_api_series()
        if results:
            print(f"mangadex internal API returned {len(results)} series")
        else:
            print("No results from MangaDex internal API")
        return results

    def __call__(self):
        return self.main()


if __name__ == "__main__":
    MangaDex(debug=True).main(debug=True)
    print("done")
