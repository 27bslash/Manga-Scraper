import time
from selenium.webdriver.common.by import By

from main import Source


class Flix(Source):
    def __init__(self, driver) -> None:
        self.driver = driver
        self.scansite = "flixscans"
        pass

    def get_title_list(self):
        xpath = "//div[@class='px-2']//div[@dir='ltr']"
        titles = self.driver.find_elements(By.XPATH, xpath)
        self.title_list = [self.clean_title(title.text) for title in titles]
        self.test = "test"
        return self.title_list

    def get_chapter_list(self):
        xpath = "//div[@class='px-2']//div[@class='v-chip__content']"
        chapters = self.driver.find_elements(By.XPATH, xpath)
        self.chapter_list = [chapter.text for chapter in chapters]
        return [self.clean_chapter(chapter.text) for chapter in chapters]

    def get_url_list(self):
        xpath = "//div[@class= 'px-2']//a"
        urls = self.driver.find_elements(By.XPATH, xpath)
        self.url_list = [url.get_attribute("href") for url in urls]
        return self.url_list

    def get_update_times_list(self):
        xpath = "//div[@class='px-2']//timeago"
        update_times = self.driver.find_elements(By.XPATH, xpath)
        self.update_times = [
            self.convert_time(update_times.text) for update_times in update_times
        ]
        while len(self.update_times) != len(self.title_list):
            self.update_times.insert(0, time.time())

        return self.update_times

    def scrape(self) -> list:
        ret = []
        self.driver.get("https://flixscans.org/webtoons/action/home")
        self.get_title_list()
        self.get_chapter_list()
        self.get_url_list()
        self.get_update_times_list()
        for i in range(len(self.title_list)):
            d = {}
            d["title"] = self.title_list[i]
            d["latest"] = self.chapter_list[i]
            d["latest_link"] = self.url_list[i]
            d["time_updated"] = self.update_times[i]
            d["scansite"] = self.scansite
            d["domain"] = "https://flixscans.org"
            d["type"] = self.scansite
            ret.append(d)
        return ret
