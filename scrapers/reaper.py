from pprint import pprint
import re
import traceback
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from main import Source
from config import reaper_url


class Reaper(Source):
    def main(self):
        return

    def scrape(self, debug=False, scrape_site=True):
        if not scrape_site:
            with open(
                "scrapers/test_pages/reaper.html", "r", encoding="utf-8"
            ) as element:
                text = element.read()
                soup = BeautifulSoup(text, "html.parser")
        if scrape_site:
            try:
                req = requests.get(reaper_url)
            except:
                return []
            # text = ''
            if req.status_code != 200:
                print("reaper", req.status_code, "broken")
                try:
                    soup = BeautifulSoup(
                        super().html_page_source(reaper_url), "html.parser"
                    )
                except:
                    print("reaper error", traceback.format_exc())
                    return []
            else:
                text = req.text
                soup = BeautifulSoup(text, "html.parser")

        lst = []
        # content = soup.find("div", {"class": "space-y-4"})
        latest_comics = soup.find_all("div", {"class": "focus:outline-none"})
        if latest_comics is None:
            print("reaper broken check logs no content")
            with open("reaper_err.txt", "w", encoding="utf-8") as f:
                f.write(text)
            return lst
        for element in latest_comics:
            d = {}
            old_chapters = {}
            try:
                chapter_container = element.find("div").find_all("a")
                title = element.find("a").text

                for el in chapter_container:
                    latest = el
                    title = title.strip()
                    title = re.sub(r"manhwa", "", title.lower())
                    title = super().clean_title(title)

                    link = latest.get("href")

                    # print(title, link,latest)
                    chapter = re.search(r"Chapter (\d+)", latest.text)[1]
                    chapter = super().clean_chapter(chapter)

                    time_updated = latest.find("p").text
                    time_updated = super().convert_time(time_updated.strip())
                    if not title or not chapter or not link:
                        continue
                    d["title"] = title
                    d["latest"] = chapter
                    d["type"] = "reaper"
                    d["time_updated"] = time_updated
                    d["latest_link"] = link
                    d["scansite"] = "reaperscans"
                    d["domain"] = "https://reaperscans.com"
                    lst.append(d)
                    old_chapters[d["latest"]] = {
                        "latest_link": link,
                        "scansite": "reaperscans",
                    }
                    d["old_chapters"] = old_chapters
                if debug:
                    pprint(d)
            except Exception as e:
                print("reaper chapter err", traceback.format_exc())
                pass
        if len(lst) == 0:
            print("reaper broken check logs no data returned")
        return lst

        # print(foc)
        # for item in content:
        #     d = {}
        #     parent = item.parent
        #     # print(parent)
        #     title = item.select('.series-title')[0]
        #     link = parent.select('.series-content')[0].find('a').get('href')
        #     chapter = parent.find('span', {'class': 'series-badge'}).text
        #     time_updated = parent.find('span', {'class': 'series-time'}).text
        #     # ... test
        #     title = title.text.strip()
        #     if re.search(r'\.\.+$', title):
        #         title = self.title_from_link(link)
        #     if title is None:
        #         continue
        #     title = re.sub(r"manhwa", "", title.lower())
        #     title = super().clean_title(title)
        #     # print('title', title.text,title)
        #     time_updated = super().convert_time(time_updated)
        #     # title = super().clean_title(title)
        #     chapter = super().clean_chapter(chapter)
        #     # print(title, chapter, time)
        #     res = self.recursive_parent(parent)
        #     if res:
        #         # print(title, chapter, time)
        #         d['title'] = title
        #         d['latest'] = chapter
        #         d['type'] = 'reaper'
        #         d['time_updated'] = time_updated
        #         d['latest_link'] = link
        #         d['scansite'] = 'reaperscans'
        #         d['domain'] = 'https://reaperscans.com'
        #         lst.append(d)

    def title_from_link(self, link):
        new_title = re.sub(r"\/$", "", link)
        title = re.search(r"(?<=com\/).*(?=\/)", new_title)
        if title:
            title = re.search(r"\/(.*)", title.group(0))
            title = title.group(1).replace("manhwa", "").replace("-", " ")
            return title
        return None

    def recursive_parent(self, element) -> bool:
        if element.parent.attrs["class"] == ["latest"]:
            return True
        elif (
            element.parent.name == "section"
            and element.parent.attrs["class"] is not ["latest"] is None
            or element.parent.name == "body"
        ):
            return False
        else:
            return self.recursive_parent(element.parent)

    def __call__(self):
        return self.scrape()


if __name__ == "__main__":
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--window-position=2000,0")
    driver = uc.Chrome(use_subprocess=True, options=chrome_options)
    Reaper(driver).scrape(debug=True, scrape_site=False)
