from pprint import pprint
import traceback
from bs4 import BeautifulSoup
import requests
from main import Source
import re
from config import asura_url, luminous_url, cosmic_url
import undetected_chromedriver as uc


class Asura(Source):
    def __init__(self, driver, site: str, scansite: str) -> None:
        self.url = site
        self.scansite = scansite
        self.driver = driver

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"
    }

    def main(self, debug=False, scrape_site=True):
        print(f"scraping {self.url}")
        # with open('scrapers/test_pages/asura.html', 'w', encoding="utf-8") as f:
        #     f.write(requests.get('https://asuracomics.com/',
        #             headers=self.headers).text)
        if not scrape_site:
            with open(f"scrapers/test_pages/asura.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
        try:
            rq = requests.get(self.url, headers=self.headers, timeout=15)
        except Exception as e:
            print(f"{self.url} requests.get failed", e.__class__)
        if scrape_site and rq and rq.status_code == 200:
            soup = BeautifulSoup(rq.text, "html.parser")
        elif scrape_site:
            print("selenium", self.url)
            try:
                soup = BeautifulSoup(super().html_page_source(self.url), "html.parser")
            except Exception as e:
                print(f"selnium failed {self.url} {e.__class__}")
                return []
        latest_updates = soup.find_all("div", class_="luf")
        lst = []
        for update in latest_updates:
            d = {}
            old_chapters = {}
            try:
                title = update.find("a").text
                if "raw" in title.lower():
                    continue
                chapter_container = update.find("ul")
                chapters = chapter_container.find_all("li")
                for chapter_obj in chapters[::-1]:
                    chapter_link = chapter_obj.find("a")
                    chapter = chapter_link.text
                    link = chapter_link.get("href")
                    time_updated = chapter_obj.find("span").text
                    if not title or not chapter or not link:
                        continue
                    d["title"] = super().clean_title(title)
                    d["latest"] = re.search(
                        r"\d+", super().clean_chapter(chapter)
                    ).group(0)
                    d["latest_link"] = link
                    d["time_updated"] = super().convert_time(time_updated)
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
            except Exception as e:
                print(f"{self.url} chapter error, {self.url}, {update}")
        if len(lst) == 0:
            print(f"{self.url} broken check logs no data returned")
        return lst

    def __call__(self):
        return self.main()


def test():
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument("--window-position=2000,0")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    driver.minimize_window()
    driver.get("https://www.google.com/")
    return driver.page_source


if __name__ == "__main__":
    # scans = alphascans , luminousscans, cosmicscans, asurascans
    # s = Asura(cosmic_url, "cosmicscans")
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--window-position=2000,0")
    driver = uc.Chrome(options=chrome_options)
    Asura(driver, asura_url, "asurascans").main(debug=True)
    driver.quit()
