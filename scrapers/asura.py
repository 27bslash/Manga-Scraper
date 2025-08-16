from pprint import pprint
import time
import traceback
from bs4 import BeautifulSoup
import requests
from main import Source
import re
from config import asura_url
import undetected_chromedriver as uc
from seleniumbase import SB


class Asura(Source):
    def __init__(self, sb, site: str, scansite: str) -> None:
        self.url = site
        self.scansite = scansite
        self.sb = sb

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"
    }

    def main(self, debug=False, scrape_site=True):
        print(f"scraping {self.url}")
        # with open('scrapers/test_pages/asura.html', 'w', encoding="utf-8") as f:
        #     f.write(requests.get('https://asuracomics.com/',
        #             headers=self.headers).text)
        data = None
        if not scrape_site:
            with open(f"scrapers/test_pages/asura.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
        else:
            try:
                strt = time.perf_counter()
                rq = requests.get(self.url, headers=self.headers, timeout=5)
                print(f'{self.url} took {time.perf_counter() - strt} seconds')
                data = rq.text
                rq.raise_for_status()  # Raises HTTPError for bad responses
                soup = BeautifulSoup(rq.text, "html.parser")
            except requests.RequestException as e:
                print(f"Error fetching {self.url}: {e}")
                if isinstance(e, requests.ConnectTimeout):
                    return []
                print("Switching to Selenium...")
                data = super().html_page_source(
                    self.url, ".col-span-9 space-y-1.5 overflow-hidden pl-[9px]"
                )
                if not data:
                    return []
                soup = BeautifulSoup(data, "html.parser")
        latest_updates = soup.find_all(
            "div", class_="col-span-9 space-y-1.5 overflow-hidden pl-[9px]"
        )
        lst = []
        if debug and data:
            with open('scrapers/test_pages/asura.html', 'w', encoding='utf-8') as file:
                file.write(data)
                pass
        for update in latest_updates:
            d = {}
            old_chapters = {}
            try:
                title = update.find("a").get('href')
                if title:
                    title = re.search(r".*/(.+)-", title).group(1)
                    title = super().clean_title(title)
                else:
                    continue
                if "raw" in title.lower():
                    continue
                chapters = update.find_all("a")
                del chapters[0]
                text_els = update.find_all("p")
                times_updated = []
                pay_walled = False
                for element in text_els:
                    text = element.text.strip().lower()
                    if 'ago' in text:
                        times_updated.append(text)
                    if 'public' in text:
                        pay_walled = True
                        break
                if pay_walled:
                    print('pay walled', title)
                    continue
                i = 0
                if not times_updated:
                    print(
                        f"Asura scans warning for {title} chapter elements length: {len(chapters)} update time elements length: {len(text_els)}"
                    )
                    continue
                d["time_updated"] = super().convert_time(times_updated[0])
                for chapter_link in chapters[::-1]:
                    chapter = chapter_link.find('svg').parent.text
                    link = chapter_link.get("href")
                    if not title or not chapter or not link:
                        continue
                    if asura_url not in link:
                        link = f"{asura_url}{link}"
                    d["title"] = title
                    d["latest"] = re.search(
                        r"\d+", super().clean_chapter(chapter)
                    ).group(0)
                    d["latest_link"] = link
                    d["scansite"] = self.scansite
                    d["domain"] = self.url
                    d["type"] = self.scansite
                    old_chapters[d["latest"]] = {
                        "latest_link": link,
                        "scansite": self.scansite,
                    }
                    d["old_chapters"] = old_chapters
                    i += 1
                # print(d['title'], d['latest'])
                lst.append(d)
                if debug:
                    pprint(d)
            except Exception as e:
                print(
                    f"{self.url} chapter error, {d['title']} {self.url} chapter {d['latest']} {times_updated} {len(chapters)} {traceback.format_exc()}"
                )
        if len(lst) == 0:
            print(f"{self.url} broken check logs no data returned")
        return lst

    def __call__(self):
        return self.main()


if __name__ == "__main__":
    # scans = alphascans , luminousscans, cosmicscans, asurascans
    # s = Asura(cosmic_url, "cosmicscans")
    with SB(undetectable=True) as sb:
        # chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument("--window-position=2000,0")
        # driver = uc.Chrome(options=chrome_options)
        Asura(sb, f"{asura_url}", "asurascans").main(debug=True, scrape_site=False)
        # driver.quit()
