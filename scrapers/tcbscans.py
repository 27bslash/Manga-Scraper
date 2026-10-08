import datetime
import re
import time
import traceback

import requests
from bs4 import BeautifulSoup
from db import db
from main import Source
import undetected_chromedriver as uc
from seleniumbase import SB, BaseCase
from config import tcb_scans_url


class TcbScraper(Source):
    def main(self):
        req = requests.get("{tcb_scans_url}/")
        # print(req.status_code, req.text)
        with open("scrapers/tcb.html", "w", encoding="utf-8") as f:
            print(req.status_code)
            f.write(req.text)
        pass

    def scrape(self, debug=False):
        link_regex = r"[^\/]+$"
        title_regex = r".*(?=-chapter)"
        chapter_regex = r"(?<=chapter-)\d*\.?\d+"

        strt = time.perf_counter()
        try:
            strt = time.perf_counter()
            rq = requests.get(f"{tcb_scans_url}", timeout=5)
            print(f'tcbscans  took {time.perf_counter() - strt} seconds')
            rq.raise_for_status()  # Raises HTTPError for bad responses
            soup = BeautifulSoup(rq.text, "html.parser")
        except requests.RequestException as e:
            print(f'Error fetching "{tcb_scans_url}": {e}')
            if isinstance(e, requests.ConnectTimeout):
                return []
            print("Switching to Selenium...")
            data = super().html_page_source(
                f"{tcb_scans_url}", success_selector='.bg-card'
            )
            if not data:
                return []
            soup = BeautifulSoup(data, "html.parser")
        cards = soup.select('div[class*="bg-card"]')
        lst = []
        for card in cards:
            link = card.find("a")
            url = link.get("href")
            url = f"{tcb_scans_url}{url}"
            # print(timeago)
            d = {}
            try:
                timeago = card.find("time-ago").get("datetime")
                path = re.search(link_regex, url).group(0)
                title = re.search(title_regex, path).group(0)
                chapter = re.search(chapter_regex, path).group(0).strip()
                title = super().clean_title(title)
                time_updated = self.convert_time_string(timeago)
                d["type"] = "tcb"
                if time_updated:
                    d["time_updated"] = time_updated
                else:
                    d["time_updated"] = time.time() - self.seconds_since_update()
                if not title or not chapter or not link:
                    continue
                d["title"] = title
                d["latest"] = chapter
                d["domain"] = f"{tcb_scans_url}/"
                d["latest_link"] = url
                d["scansite"] = "tcbscans"
                lst.append(d)
                # print(d)
                if debug:
                    print("tcb", title, chapter, url, time_updated)
            except TypeError:
                print("tcb", url, traceback.format_exc())
                continue
        # print(lst)
        if len(lst) == 0:
            print("tcb broken check logs")
            print(
                f"  status_code : {rq.status_code if 'rq' in dir() else 'request failed'}"
            )
            print(f"  cards found : {len(cards)}")
            if cards:
                first = cards[0]
                print(f"  first card HTML snippet:\n{first.prettify()[:500]}")
                link = first.find("a")
                timeago = first.find("time-ago")
                print(
                    f"  first card has <a>        : {link is not None} | href={link.get('href') if link else 'N/A'}"
                )
                print(
                    f"  first card has <time-ago> : {timeago is not None} | datetime={timeago.get('datetime') if timeago else 'N/A'}"
                )
                if link:
                    path = re.search(link_regex, link.get("href", ""))
                    print(
                        f"  link_regex match          : {path.group(0) if path else 'NO MATCH'}"
                    )
                    if path:
                        title_m = re.search(title_regex, path.group(0))
                        chapter_m = re.search(chapter_regex, path.group(0))
                        print(
                            f"  title_regex match         : {title_m.group(0) if title_m else 'NO MATCH'}"
                        )
                        print(
                            f"  chapter_regex match       : {chapter_m.group(0) if chapter_m else 'NO MATCH'}"
                        )
                return []  # Return empty list if no valid data was extracted
            else:
                print("  selector 'div[class*=bg-card]' matched nothing")
                print(f"  page snippet:\n{soup.prettify()[:1000]}")
                # print(time.perf_counter()-strt)
                return lst
        return lst

    def convert_time_string(self, timestamp):
        datetime_object = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        unix_timestamp = datetime_object.timestamp()
        return unix_timestamp

    def seconds_since_update(self):
        today = datetime.datetime.today().weekday()
        days_since_thursday = 7 - (3 - today) % 7
        if today == 3:
            return 0
        else:
            return 86400 * days_since_thursday

    def __call__(self):
        return self.scrape()


# t = TcbScraper()()
if __name__ == "__main__":
    with SB(undetectable=True) as sb:
        t = TcbScraper(sb)
        t.scrape(debug=True)
    pass
