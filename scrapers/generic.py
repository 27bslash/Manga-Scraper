import re
import time
import traceback
from dataclasses import dataclass, replace

from bs4 import Tag
from seleniumbase import BaseCase

from main import Source


DEFAULT_CHAPTER_REGEX = r"Chapter\s+(\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class ScrapeConfig:
    """Declarative description of an HTML "latest chapters" listing page.

    A single GenericScraper walks ``container`` elements, pulls the title and
    each chapter out of them using CSS selectors, and hands the result to
    ``Source.build_series_item``.
    """

    scansite: str
    url: str
    success_selector: str
    test_file: str
    domain: str | None = None
    type: str | None = None
    container: str = ""
    title: str = ""
    title_attr: str | None = None
    title_replace: tuple[tuple[str, str], ...] = ()
    chapters: str | None = None
    chapter_text: str | None = None
    chapter_regex: str = DEFAULT_CHAPTER_REGEX
    link: str | None = None
    link_attr: str = "href"
    link_skip: tuple[str, ...] = ()
    time: str | None = None
    time_attr: str | None = None
    series_time: str | None = None
    series_time_attr: str | None = None
    per_chapter: bool = False
    time_fallback_now: bool = False


class GenericScraper(Source):
    def __init__(self, sb: BaseCase, config: ScrapeConfig) -> None:
        super().__init__(sb)
        self.config = config
        self.url = config.url
        self.scansite = config.scansite

    def scrape(self, debug: bool = False, scrape_site: bool = True) -> list[dict]:
        config = self.config
        soup = self.fetch_html(
            config.url,
            success_selector=config.success_selector,
            scrape_site=scrape_site,
            test_file=config.test_file,
        )
        if not soup:
            return []

        if not config.container:
            return []

        domain = config.domain or config.url
        type_ = config.type or config.scansite

        results: list[dict] = []
        for container in soup.select(config.container):
            try:
                results.extend(self._extract(container, domain, type_, debug))
            except Exception:
                print(f"{config.scansite} chapter error: {traceback.format_exc()}")

        if not results:
            print(f"{config.scansite} broken check logs no data returned")
        return results

    def _extract(self, container: Tag, domain, type_, debug):
        config = self.config
        title = self._title(container)
        if not title:
            return []

        old_chapters: dict = {}
        series_time = self._series_time(container)
        entries: list[dict] = []
        latest: dict | None = None

        for chapter_el in self._chapters(container)[::-1]:
            chapter = self._chapter_number(chapter_el)
            link = self._chapter_link(chapter_el)
            if not chapter or not link:
                continue
            time_updated = self._chapter_time(chapter_el, series_time)
            entry = self.build_series_item(
                title=title,
                chapter=chapter,
                link=link,
                time_updated=time_updated,
                scansite=config.scansite,
                domain=domain,
                type_=type_,
                old_chapters=old_chapters,
            )
            if config.per_chapter:
                entries.append(entry)
            else:
                latest = entry
            if debug:
                print(config.scansite, title, chapter, time_updated)

        if config.per_chapter:
            return entries
        return [latest] if latest else []

    def _chapters(self, container: Tag) -> list[Tag]:
        if self.config.chapters:
            return container.select(self.config.chapters)
        return [container]

    def _title(self, container: Tag):
        node = self._find(container, self.config.title)
        if node is None:
            return None
        value = node.get(self.config.title_attr) if self.config.title_attr else node.text
        if value is None:
            return None
        value = value.strip()
        for pattern, repl in self.config.title_replace:
            value = re.sub(pattern, repl, value, flags=re.IGNORECASE)
        return self.clean_title(value)

    def _chapter_number(self, chapter_el: Tag):
        node = self._find(chapter_el, self.config.chapter_text)
        if node is None:
            return None
        match = re.search(self.config.chapter_regex, node.text)
        if not match:
            return None
        return match.group(1) if match.groups() else match.group(0)

    def _chapter_link(self, chapter_el: Tag):
        node = self._find(chapter_el, self.config.link)
        if node is None:
            return None
        link = node.get(self.config.link_attr)
        if link and any(skip in link for skip in self.config.link_skip):
            return None
        return link

    def _chapter_time(self, chapter_el: Tag, series_time):
        config = self.config
        if series_time is not None:
            return series_time
        node = self._find(chapter_el, config.time)
        if node is None:
            if config.time_fallback_now:
                return time.time()
            return None
        raw = node.get(config.time_attr) if config.time_attr else node.text
        if raw is None:
            return None
        return self.convert_time(raw.strip())

    def _series_time(self, container: Tag):
        config = self.config
        if not config.series_time:
            return None
        node = self._find(container, config.series_time)
        if node is None:
            return None
        raw = (
            node.get(config.series_time_attr)
            if config.series_time_attr
            else node.text
        )
        if raw is None:
            return None
        return self.convert_time(raw.strip())

    @staticmethod
    def _find(element: Tag, selector: str | None) -> Tag | None:
        if element is None:
            return None
        if not selector:
            return element
        return element.select_one(selector)

    def __call__(self):
        return self.scrape()


FLAME_CONFIG = ScrapeConfig(
    scansite="flamescans",
    url="https://flamecomics.com/",
    success_selector=".bigor",
    test_file="scrapers/test_pages/flame.html",
    container="div.bigor",
    title="div.tt",
    chapter_text="div.epxs",
    link="div.chapter-list a",
    series_time="div.epxdate",
)

MANHUA_PLUS_CONFIG = ScrapeConfig(
    scansite="manhua-plus",
    url="https://manhuaplus.com/",
    success_selector="#loop-content",
    test_file="scrapers/test_pages/manhua_updates.html",
    container="div.item-summary",
    title="div.post-title",
    chapters="div.chapter-item",
    link="a",
    series_time="span.post-on",
)

SCYTHE_CONFIG = ScrapeConfig(
    scansite="scythe",
    url="https://scythescans.com/",
    success_selector=".postbody",
    test_file="scrapers/test_pages/scythe.html",
    container="div.bsx",
    title="div.tt a",
    title_attr="title",
    chapters="li",
    chapter_text="span.fivchap",
    chapter_regex=r"\d+\.?\d*",
    link="a",
    time="span.fivtime",
    per_chapter=True,
)

REAPER_CONFIG = ScrapeConfig(
    scansite="reaperscans",
    url="https://reapercomics.com/latest/comics",
    success_selector=".font-sans",
    test_file="scrapers/test_pages/reaper.html",
    domain="https://reaperscans.com",
    container="div.focus:outline-none",
    title="a",
    chapters="div a",
    chapter_regex=r"Chapter\s+(\d+)",
    link_attr="href",
    link_skip=("/novels",),
    time="p",
    title_replace=((r"manhwa", ""),),
)

VORTEX_CONFIG = ScrapeConfig(
    scansite="vortexscans",
    url="https://vortexscans.org/",
    success_selector=".newly-free-chapter-row",
    test_file="scrapers/test_pages/vortex.html",
    container="div.relative.h-full.p-1",
    title="a[title]",
    title_attr="title",
    chapters='a[href*="/chapter-"]',
    chapter_text="span",
    link_attr="href",
    time="time",
    time_fallback_now=True,
)

SITE_CONFIGS = {
    "flamescans": FLAME_CONFIG,
    "manhua-plus": MANHUA_PLUS_CONFIG,
    "scythe": SCYTHE_CONFIG,
    "reaperscans": REAPER_CONFIG,
    "vortexscans": VORTEX_CONFIG,
}


class Flame(GenericScraper):
    def __init__(self, sb: BaseCase, scrape_site: bool = True, debug: bool = False):
        super().__init__(sb, FLAME_CONFIG)
        self.scrape_site = scrape_site
        self.debug = debug

    def scrape(self, debug: bool = False, scrape_site: bool | None = None) -> list[dict]:
        return super().scrape(
            debug=debug or self.debug,
            scrape_site=self.scrape_site if scrape_site is None else scrape_site,
        )


class ManhuaPlus(GenericScraper):
    def __init__(
        self,
        sb: BaseCase,
        url: str = "https://manhuaplus.com/",
        scansite: str = "manhua-plus",
    ) -> None:
        super().__init__(sb, replace(MANHUA_PLUS_CONFIG, url=url, scansite=scansite))


class Scythe(GenericScraper):
    def __init__(self, sb: BaseCase, scrape_site: bool = True, debug: bool = False):
        super().__init__(sb, SCYTHE_CONFIG)
        self.scrape_site = scrape_site
        self.debug = debug

    def scrape(self, debug: bool = False, scrape_site: bool | None = None) -> list[dict]:
        return super().scrape(
            debug=debug or self.debug,
            scrape_site=self.scrape_site if scrape_site is None else scrape_site,
        )


class Vortex(GenericScraper):
    def __init__(self, sb: BaseCase, scrape_site: bool = True, debug: bool = False):
        super().__init__(sb, VORTEX_CONFIG)
        self.scrape_site = scrape_site
        self.debug = debug

    def scrape(self, debug: bool = False, scrape_site: bool | None = None) -> list[dict]:
        return super().scrape(
            debug=debug or self.debug,
            scrape_site=self.scrape_site if scrape_site is None else scrape_site,
        )

