import json
import re
import time
import traceback
from datetime import datetime
from pprint import pprint

from bs4 import BeautifulSoup, Tag
import requests
from seleniumbase import SB, BaseCase

from config import asura_api_url, asura_url
from main import Source


class Asura(Source):
    def __init__(self, sb: BaseCase, site: str, scansite: str, debug=False) -> None:
        self.url = site
        self.scansite = scansite
        self.sb = sb
        self.debug = debug

    @staticmethod
    def _get_chapter_url(chapter_info, short_url, chapter_num):
        try:
            slug = chapter_info.get("slug")
            if not isinstance(short_url, str) or not short_url.strip():
                return None
            if not isinstance(slug, str) or not slug.strip():
                return None
            return f"{asura_url}/{short_url.lstrip('/')}/chapter/{slug}"
        except (AttributeError, TypeError) as error:
            print(f"Error constructing chapter URL for chapter {chapter_num}: {error}")
            return None

    @staticmethod
    def _to_unix_timestamp(value):
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _internal_api_call(self, url):
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
        }
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                return self._parse_internal_api_response(response.json())
            except (requests.RequestException, ValueError) as e:
                print(
                    f"Error fetching internal API data from {url}: {e} retrying ({attempt + 1}/3)"
                )
        return self._browser_api_call(url)

    def _browser_api_call(self, url):
        print(f"Fetching internal API data through the browser: {url}")
        try:
            self.sb.get(url)
            body = self.sb.execute_script(
                "return document.body ? document.body.innerText : ''"
            )
            return self._parse_internal_api_response(json.loads(body))
        except Exception:
            print(f"Browser API fetch failed for {url}: {traceback.format_exc()}")
            return []

    @staticmethod
    def _parse_internal_api_response(data):
        if isinstance(data, dict):
            data = data.get("data")
        if not isinstance(data, list):
            return []

        parsed_series = []
        for series in data:
            try:
                parsed = Asura._parse_internal_api_series(series)
                if parsed is not None:
                    parsed_series.append(parsed)
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                print(f"Error parsing Asura series: {error}")

        return parsed_series

    @staticmethod
    def _parse_internal_api_series(series):
        if not isinstance(series, dict):
            return None

        title = series.get("title")
        if not isinstance(title, str) or not title.strip():
            print("Skipping Asura series with missing title")
            return None

        chapters = series.get("latest_chapters")
        if not isinstance(chapters, list):
            print(f"Skipping Asura series without chapter data: {title}")
            return None

        old_chapters = {}
        latest_found = False

        for chapter_info in chapters:
            chapter = Asura._parse_internal_api_chapter(
                chapter_info, series.get("public_url")
            )
            if chapter is None:
                continue

            chapter_num, chapter_link, chapter_timestamp = chapter
            old_chapters[str(chapter_num)] = {
                "latest_link": chapter_link,
                "scansite": "asurascans",
            }

            if not latest_found and chapter_timestamp is not None:
                latest_chapter = chapter_num
                latest_link = chapter_link
                time_updated = chapter_timestamp
                latest_found = True

        if not latest_found:
            print(f"Skipping Asura series without a complete latest chapter: {title}")
            return None
        if not time_updated:
            print(f"Skipping Asura series with invalid timestamp: {title}")
            return None
        return {
            "title": Source.clean_title(title),
            "latest": str(latest_chapter),
            "old_chapters": old_chapters,
            "time_updated": time_updated,
            "domain": asura_url,
            "scansite": "asurascans",
            "type": "asurascans",
            "latest_link": latest_link,
        }

    @staticmethod
    def _parse_internal_api_chapter(chapter_info, short_url):
        if not isinstance(chapter_info, dict) or chapter_info.get("is_premium"):
            return None

        chapter_num = chapter_info.get("number")
        if chapter_num is None or (
            isinstance(chapter_num, str) and not chapter_num.strip()
        ):
            return None

        chapter_link = Asura._get_chapter_url(chapter_info, short_url, chapter_num)
        if not isinstance(chapter_link, str) or not chapter_link.strip():
            return None

        chapter_timestamp = Asura._to_unix_timestamp(
            chapter_info.get("early_access_until") or chapter_info.get("published_at")
        )
        return chapter_num, chapter_link, chapter_timestamp

    def _scrape_page(self, url, debug=False, scrape_site=True):
        print(f"scraping {url}")
        data = None
        if not scrape_site:
            with open("scrapers/test_pages/asura.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
        else:
            # strt = time.perf_counter()
            # rq = requests.get(url, headers=self.headers, timeout=5)
            # print(f'{url} took {time.perf_counter() - strt} seconds')
            # data = rq.text
            # rq.raise_for_status()  # Raises HTTPError for bad responses
            # soup = BeautifulSoup(rq.text, "html.parser")
            # sb.get(self.url)
            print("Switching to Selenium...")

            data = super().html_page_source(url, ".content-start")
            if '2' not in url:
                el = self.sb.find_element(
                    'a[href="/login"],a[href="/register"]', timeout=5
                )
                if not data or not el:
                    print('no data from selenium ')
                    return []
            fgfg = self.sb.get_page_source()
            soup = BeautifulSoup(fgfg, "html.parser")
        if self.debug and scrape_site:
            with open('scrapers/test_pages/asura.html', 'w', encoding='utf-8') as file:
                file.write(fgfg)

        lst = []
        pay_walled_key_words = [
            'paywall',
            'premium',
            'members only',
            'exclusive',
            'public',
            'private',
            'locked',
            'vip',
            'subscriber',
            'subscription',
            'donor',
            'supporter',
            'patron',
            'sponsor',
            'contributor',
            'backer',
            'funder',
            'investor',
            "in",
        ]
        lst = self.dk(soup)
        if len(lst) == 0:
            print(f"{url} broken check logs no data returned")
        return lst

    def dk(self, soup):
        latest_updates = soup.find_all(
            'div',
            class_="grid-cols-12",
        )
        lst = []
        for update in latest_updates:
            self._handle_series(update, lst=lst)
        return lst

    def _handle_series(
        self,
        update: Tag,
        lst,
    ):
        d = {}
        old_chapters = {}
        try:
            title = update.find('a').get('href')
            if title:
                title = re.search(r".*/(.+)-", title).group(1)
                title = self.clean_title(title)
            else:
                return False
            if "raw" in title.lower():
                return False
            self._handle_chapters(update, d, old_chapters, title)
            lst.append(d)
            if self.debug:
                pprint(d)
        except Exception as e:
            print(
                f"Asura {title if title else None} series error, {e} {traceback.format_exc()}"
            )
        return True

    def _handle_chapters(self, update, d, old_chapters, title):
        chapters = update.find('div').find_all("a")
        del chapters[0]
        for chapter_link in chapters[::-1]:
            try:
                self._update_chapter(chapter_link, title, d, old_chapters)
            except Exception:
                print(
                    f'asura chapter error for {title} Error: {traceback.format_exc()}'
                )

    def _check_paywall(self, element: Tag):
        lock_svg = element.find('svg', recursive=True)
        if lock_svg:
            return True
        # selenium check
        href = element.get('href')
        if not href:
            print("no href somehow")
            return False
        href_str = f'a[href="{href}"] svg'
        try:
            self.sb.find_element(href_str, timeout=0.1)
            return True
        except Exception:
            return False

    @staticmethod
    def _should_update(d, new_latest):
        if "latest" not in d or d["latest"] is None:
            should_update = True
        else:
            try:
                should_update = float(new_latest) > float(d["latest"])
            except ValueError:
                # fallback if chapter isn't numeric (e.g. "12.5", "Extra", etc.)
                should_update = str(new_latest) > str(d["latest"])
        return should_update

    def _update_chapter(self, chapter_link, title, d, old_chapters):
        unclean_chapter = chapter_link.find('span').text
        if 'novel' in unclean_chapter.lower():
            return False
        if not unclean_chapter or not re.search(r"\d", unclean_chapter):
            print(f"{unclean_chapter} is not a valid chapter for {title}")
            return False
        chapter = re.search(r"\d+\.?\d*", self.clean_chapter(unclean_chapter)).group(0)
        if self._check_paywall(chapter_link):
            print('pay walled', title, chapter)
            return False
        link = chapter_link.get("href")
        time_el = chapter_link.find('time')

        time_updated = self.convert_time(time_el.text.strip().lower())
        if not title or not chapter or not link:
            return False
        if asura_url not in link:
            link = f"{asura_url}{link}"
        if self._should_update(d, chapter):
            d["title"] = title
            d["latest"] = chapter
            d['time_updated'] = time_updated
            d["latest_link"] = link
            d["scansite"] = self.scansite
            d["domain"] = self.url
            d["type"] = self.scansite
        old_chapters[d["latest"]] = {
            "latest_link": link,
            "scansite": self.scansite,
        }
        d["old_chapters"] = old_chapters
        return True

    def _fetch_api_series(self):
        results = self._internal_api_call(f"{asura_api_url}/api/series?limit=20")
        time.sleep(1)
        results += self._internal_api_call(
            f"{asura_api_url}/api/series?limit=20&offset=20"
        )
        if self.debug:
            pprint(results)
        return results

    def main(self, debug=False, scrape_site=True, include_page_2=False):
        if scrape_site:
            results = self._fetch_api_series()
            if results:
                print(f"asura internal API returned {len(results)} series")
                return results
            print("No results from internal API, falling back to scraping")

        lst = self._scrape_page(self.url, debug=debug, scrape_site=scrape_site)

        if lst and include_page_2:
            lst.extend(
                self._scrape_page(
                    f"{self.url}/?page=2",
                    debug=debug,
                    scrape_site=scrape_site,
                )
            )

        return lst

    def __call__(self):
        return self.main()


if __name__ == "__main__":
    # scans = alphascans , luminousscans, cosmicscans, asurascans
    # s = Asura(cosmic_url, "cosmicscans")

    with SB(undetectable=True, headless=True) as sb:
        # chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument("--window-position=2000,0")
        # driver = uc.Chrome(options=chrome_options)
        Asura(sb, f"{asura_url}", "asurascans", debug=True).main(
            debug=True, scrape_site=True, include_page_2=True
        )
        # driver.quit()
        print('done')

    # with SB(undetectable=True) as sb:
    #     # chrome_options = uc.ChromeOptions()
    #     # chrome_options.add_argument("--window-position=2000,0")
    #     # driver = uc.Chrome(options=chrome_options)
    #     url = (
    #         Path(r"D:\projects\python\reddit-manga\scrapers\test_pages\paywalled.html")
    #         .resolve()
    #         .as_uri()
    #     )
    #     sb.get(url)
    #     with open("scrapers/test_pages/paywalled.html", "r", encoding="utf-8") as f:
    #         soup = BeautifulSoup(f.read(), "html.parser")
    #         Asura(sb, "url", "asurascans", debug=True).dk(soup)
