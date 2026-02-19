import datetime
from pprint import pprint
import re
import time
import traceback
import requests
from bs4 import BeautifulSoup, Tag
from main import Source
from seleniumbase import SB
from config import leviatan_url


class Hive(Source):
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
            with open('scrapers/test_pages/hive.html', 'r', encoding="utf-8") as f:
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

        # divs_no_attrs = [
        #     div for div in item_summary[0].find_all('figure', recursive=False)
        # ]
        # select all series containers
        item_summary: list[Tag] = list(soup.select('figure'))
        if not item_summary:
            return []
        for item in item_summary:
            d = {}
            old_chapters = {}
            try:
                title_el: Tag = item.find("a", class_="text-base")
                title = super().clean_title(title_el.text)
                chapters = item.select("span.text-gray-400")
                for chapter_obj in chapters[::-1]:
                    chapter_link: Tag = chapter_obj.parent
                    chapter = chapter_obj.text
                    link: str = chapter_link.get("href")  # type: ignore
                    span = chapter_obj.find_next_sibling().text
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
                if d:
                    lst.append(d)
                if debug:
                    pprint(d)
            except Exception:
                print(self.scansite, traceback.format_exc())
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
        hive = Hive(sb, "https://hivetoon.com/", "hivecomics").scrape(
            scrape_site=False, debug=True
        )
