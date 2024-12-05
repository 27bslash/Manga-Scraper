import time
import traceback
from selenium.webdriver.common.by import By

from main import Source
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from seleniumbase import SB, BaseCase
from selenium.webdriver.remote.webelement import WebElement


class Flix(Source):
    def __init__(self, driver: BaseCase) -> None:
        self.driver = driver
        self.scansite = "flixscans"
        pass

    def get_title(self, series):
        xpath = ".//div[@dir='ltr']"
        title = series.find_element(By.XPATH, xpath).text
        return self.clean_title(title)

    def get_chapter(self, series):
        return self.clean_chapter(
            series.find_element(By.XPATH, ".//div[@class='v-chip__content']").text
        )

    def get_timeago(self, series, path):
        try:
            timeago = series.find_element(By.XPATH, path)
            timeago = self.convert_time(timeago.text)
        except Exception:
            timeago = time.time()
        return timeago

    def scrape_simple_site(self):
        if (
            "local" not in self.driver.get_current_url()
            and "flix" not in self.driver.get_current_url()
        ):
            self.driver.get("https://flixscans.org/webtoons/action/home")
        ret = []
        try:
            xpath = "//div[@class='px-2']/div/div"
            all_series = self.driver.find_elements(By.XPATH, xpath)
            source = self.driver.get_page_source()
            soup = BeautifulSoup(source, "html.parser")
            series_container = soup.find(class_="px-2")
            all_series = series_container.find_all("div", {"dir": "ltr"})
            for series in all_series:
                try:
                    old_chapters = {}
                    title = series.text.strip()
                    li_el = series.parent.find("li")
                    chapter_link = f"https://flixscans.org{li_el.find('a').get('href')}"
                    chapter = li_el.find("a").text.strip()
                    time_updated = (
                        self.convert_time(li_el.find("timeago").text)
                        if li_el.find("timeago")
                        else time.time()
                    )
                    d = {
                        "title": self.clean_title(title),
                        "latest_link": chapter_link,
                        "latest": self.clean_chapter(chapter),
                        "time_updated": time_updated,
                        "scansite": self.scansite,
                        "domain": "https://flixscans.org",
                        "type": self.scansite,
                    }
                    old_chapters[d["latest"]] = {
                        "latest_link": chapter_link,
                        "scansite": self.scansite,
                    }
                    d["old_chapters"] = old_chapters
                    ret.append(d)
                except Exception as e:
                    print(f"scrape simple site failed on element: {e.__class__}")
        except Exception as e:
            print(f"flix scans can't find chapter container: {e.__class__}")
        return ret

    def scrape_complex_site(self):
        if (
            "local" not in self.driver.get_current_url()
            and "flix" not in self.driver.get_current_url()
        ):
            self.driver.get("https://flixscans.org/webtoons/action/home")
        try:
            ret = []
            xpath = "//div[@class='px-2']//a[contains(@href,'series')]"
            all_series = self.driver.find_elements(By.XPATH, xpath)
            for series in all_series:
                try:
                    old_chapters = {}
                    d = {
                        "title": self.get_title(series),
                        # "latest_link": f"https://flixscans.org/{series.get_attribute('href')}",
                        "latest_link": series.get_attribute("href"),
                        "latest": self.get_chapter(series),
                        "time_updated": self.get_timeago(series, ".//timeago"),
                        "scansite": self.scansite,
                        "domain": "https://flixscans.org",
                        "type": self.scansite,
                    }
                    old_chapters[d["latest"]] = {
                        "latest_link": d["latest_link"],
                        "scansite": self.scansite,
                    }
                    ret.append(d)
                except Exception as e:
                    print("flix scans complex site error:", e.__class__)
                    break
        except Exception as e:
            print(f"complex scans err: {e.__class__}")
        return ret

    def scrape(self):
        print("scraping complex flix scans")
        results = self.scrape_complex_site()
        if not results:
            print("scraping simple flix scans")
            results = self.scrape_simple_site()
        return results


if __name__ == "__main__":
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")
    # driver = uc.Chrome(options=options)
    with SB() as sb:
        Flix(sb).scrape()
