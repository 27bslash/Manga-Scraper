from pprint import pprint
import time
import traceback
from typing import Any, Literal, Never, Optional, TypedDict
from bs4 import BeautifulSoup, Tag
import requests
from main import Source
import re
from config import asura_url, luminous_url, cosmic_url
import undetected_chromedriver as uc
from seleniumbase import SB


class OldChapters(TypedDict):
    latest_link: str
    time_updated: str
    old_chapters: Optional[dict[str, "OldChapters"]]  # Recursive type


class MangaDict(TypedDict):
    title: Optional[str]
    latest: Optional[str]
    latest_link: Optional[str]
    time_updated: float
    scansite: Optional[str]
    type: Optional[str]
    domain: Optional[str]
    old_chapters: OldChapters


class AsuraLikes(Source):
    def __init__(self, sb, site: str, scansite: str) -> None:
        self.url = site
        self.scansite = scansite
        self.sb = sb

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"
    }

    def main(self, debug=False, scrape_site=True) -> list[dict[str, Any]] | list[Never]:
        print(f"scraping {self.url}")
        # with open('scrapers/test_pages/asura.html', 'w', encoding="utf-8") as f:
        #     f.write(requests.get('https://asuracomics.com/',
        #             headers=self.headers).text)
        if not scrape_site:
            with open("scrapers/test_pages/luminous.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
        else:
            try:
                strt = time.perf_counter()
                rq = requests.get(self.url, headers=self.headers, timeout=5)
                print(f'{self.url} took {time.perf_counter() - strt} seconds')
                rq.raise_for_status()  # Raises HTTPError for bad responses

                soup = BeautifulSoup(rq.text, "html.parser")
            except requests.RequestException as e:
                if isinstance(e, requests.ConnectTimeout):
                    return []
                print(f"Error fetching {self.url}: {e}")
                print("Switching to Selenium...")
                data = super().html_page_source(self.url, ".luf")
                if not data:
                    return []
                soup = BeautifulSoup(data, "html.parser")
        latest_updates: list[Tag] = soup.find_all("div", class_="luf")
        lst = []
        for update in latest_updates:
            d: MangaDict = {}
            old_chapters: OldChapters = {}
            try:
                title = update.find("a").text.strip()
                if "raw" in title.lower():
                    continue
                chapter_container = update.find("ul")
                chapters: list[Tag] = chapter_container.find_all("li")
                for chapter_obj in chapters[::-1]:
                    chapter_link: Tag = chapter_obj.find("a")
                    chapter = chapter_link.text
                    link: str = chapter_link.get("href") # type: ignore
                    spans = chapter_obj.find_all("span")
                    time_updated = [span.get('id') for span in spans if span.get('id')][
                        0
                    ].replace('relativeTime_', '')

                    if not title or not chapter or not link:
                        continue
                    d["title"] = super().clean_title(title)
                    d["latest"] = re.search(
                        r"\d+", super().clean_chapter(chapter)
                    ).group(0)
                    d["latest_link"] = link
                    d["time_updated"] = float(time_updated)
                    d["scansite"] = self.scansite
                    d["domain"] = self.url
                    d["type"] = self.scansite
                    old_chapters[d["latest"]] = {
                        "latest_link": link,
                        "scansite": self.scansite,
                    }
                    d["old_chapters"] = old_chapters
                # print(d['title'], d['latest'])
                lst.append(d)
                if debug:
                    pprint(d)
            except Exception:
                print(
                    f"{self.url} chapter error, {time_updated} {traceback.format_exc()}"
                )
        if len(lst) == 0:
            print(f"{self.url} broken check logs no data returned")
        return lst


if __name__ == "__main__":
    # scans = alphascans , luminousscans, cosmicscans, asurascans
    # s = Asura(cosmic_url, "cosmicscans")
    with SB(undetectable=True) as sb:
        # chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument("--window-position=2000,0")
        # driver = uc.Chrome(options=chrome_options)
        # AsuraLikes(sb, luminous_url, "luminousscans").main(debug=True, scrape_site=True)
        riz_comics = AsuraLikes(sb, "https://hivetoon.com/", "hivecomics").main(
            scrape_site=True
        )

        # driver.quit()
