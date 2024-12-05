from pprint import pprint
from typing import TypedDict, cast
from bs4 import BeautifulSoup
import requests

from main import Source
from seleniumbase import SB, BaseCase
from config import manhua_plus_url


class OldChapters(TypedDict):
    latest_link: str
    scansite: str


class UnparsedData(TypedDict):
    title: str
    latest: str
    latest_link: str
    time_updated: float
    scansite: str
    type: str
    domain: str
    old_chapters: dict[str, OldChapters]


class ManhuaPlus(Source):
    def __init__(self, sb: BaseCase, url: str, scansite: str) -> None:
        super().__init__(sb)
        self.url = url
        self.scansite = scansite

    def scrape(
        self, scrape_site: bool = True, debug=False
    ) -> list[UnparsedData] | list:
        print(f'scraping {self.url}')
        if not scrape_site:
            with open(
                "scrapers/test_pages/manhua_updates.html", "r", encoding="utf-8"
            ) as f:
                data: str = f.read()
                soup = BeautifulSoup(data, "html.parser")
        else:
            try:
                rq = requests.get(self.url, timeout=1)
                rq.raise_for_status()  # Raises HTTPError for bad responses
                soup = BeautifulSoup(rq.text, "html.parser")
            except requests.RequestException as e:
                print(f"Error fetching {self.url}: {e}")
                if isinstance(e, requests.ConnectTimeout):
                    return []
                print("Switching to Selenium...")
                page_content = self.html_page_source(self.url, "#loop-content")
                if not page_content:
                    return []
                soup = BeautifulSoup(page_content, "html.parser")
        latest_chapters = soup.find_all("div", {"class": "item-summary"})
        if not latest_chapters:
            return []
        updated_chapters: list[UnparsedData] = []
        for el in latest_chapters:
            try:
                old_chapters = cast(dict[str, OldChapters], {})
                d = cast(UnparsedData, {})
                title = el.find("div", class_="post-title").text
                title = self.clean_title(title)
                chapter_container = el.find_all("div", "chapter-item")
                time_updated_el = el.find("span", class_="post-on")
                time_updated = self.convert_time(time_updated_el.text)
                for chapter_el in chapter_container[::-1]:
                    chapter = self.clean_chapter(chapter_el.text.strip())
                    if not chapter:
                        continue
                    d["title"] = title
                    d["latest"] = chapter
                    d["latest_link"] = chapter_el.find('a').get("href")
                    d["scansite"] = self.scansite  # "manhua-plus"
                    d["domain"] = self.url  # "https://manhuaplus.com"
                    d["type"] = self.scansite
                    d["time_updated"] = time_updated
                    old_chapters[chapter] = {
                        "latest_link": d["latest_link"],
                        "scansite": d["scansite"],
                    }
                    d["old_chapters"] = old_chapters
                updated_chapters.append(d)
            except Exception:
                print(f"{self.url} chapter error, {self.url}")
                continue
        if debug:
            pprint(updated_chapters)
        if len(updated_chapters) == 0:
            print(f"{self.url} broken check logs no data returned")
            return []
        return updated_chapters


if __name__ == "__main__":
    with SB(undetectable=True) as sb:
        # ManhuaPlus(sb).scrape(scrape_site=True)
        manhua_plus = ManhuaPlus(
            sb, url='https://manhuaplus.com/', scansite="manhua-plus"
        ).scrape(debug=True)
        # manhua_fast = ManhuaPlus(
        #     sb, url='https://manhuafast.net/', scansite="manhuafast"
        # ).scrape(debug=True)
