import datetime
import re
import time
import traceback
import requests
from bs4 import BeautifulSoup, Tag
from main import Source
from seleniumbase import SB
from config import leviatan_url


class Leviatan(Source):
    def __init__(self, sb, url, scansite) -> None:
        self.url = url
        self.scansite = scansite
        super().__init__(sb)

    
    def convert_dates(self, date):
        try:
            date_object = datetime.datetime.strptime(date.strip(), "%b %d, %Y")
            stamp = date_object.timestamp()
            return stamp
        except:
            return None

    def scrape(self, scrape_site=True, debug=False) -> list:
        # self.main()
        print(f"scraping {self.scansite}")
        lst = []
        title_list = []
        if not scrape_site:
            with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
                data = f.read()
                soup = BeautifulSoup(data, 'html.parser')
        else:
            try:
                strt = time.perf_counter()
                rq = requests.get(self.url, timeout=5)
                print(f'leviatan scans  took {time.perf_counter() - strt} seconds')

                rq.raise_for_status()  # Raises HTTPError for bad responses
                soup = BeautifulSoup(rq.text, "html.parser")
            except requests.RequestException as e:
                print(f"Error fetching {self.url}: {e}")
                print("Switching to Selenium...")
                data = super().html_page_source(
                    self.url, success_selector='.chapter-item'
                )
                if not data:
                    return []
                soup = BeautifulSoup(data, "html.parser")

        # with open('scrapers/test_pages/leviatan.html', 'w', encoding="utf-8") as f:
        #     f.write(text)
        # with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        item_summary = soup.select('div[class*="luf"]')
        for item in item_summary:
            d = {}
            old_chapters = {}
            title_el = item.find("a").text
            title = super().clean_title(title_el)
            try:
                chapter_el = item.find("ul")
                if not chapter_el:
                    continue
                chapter_container = item.find("ul")
                chapters: list[Tag] = chapter_container.find_all("li")
                for chapter_obj in chapters[::-1]:
                    chapter_link: Tag = chapter_obj.find("a")
                    chapter = chapter_link.text
                    link: str = chapter_link.get("href")  # type: ignore
                    span = chapter_obj.find("span").text
                    time_updated = super().convert_time(span)

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
                lst.append(d)
                if debug:
                    print({self.scansite}, title, chapter, time_updated)
            except Exception:
                print({self.scansite}, title, traceback.format_exc())
                pass
        if len(lst) == 0:
            print(f"{self.scansite} broken check logs")
        return lst
        # print(lst)
        # for card in titles:
        #     link = card.find_all('a')
        #     print(link)
        # chapter =


if __name__ == "__main__":
    with SB() as sb:
        manhua_fast = Leviatan(sb, "https://hivetoon.com/", "hivecomics").scrape(
            scrape_site=False, debug=True
        )
