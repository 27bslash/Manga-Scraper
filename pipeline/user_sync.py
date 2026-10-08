import json
import time
import traceback

from db import db
from pipeline.titles import TITLE_QUALIFIER_TOKENS, PrefixCandidateIndex


class UserMangaScraper:
    def __init__(
        self,
        total_manga,
        testing,
        fuzzy_search,
        qualifier_tokens=None,
        prefix_len: int = 2,
        max_prefix_len: int = 4,
        target_bucket_size: int = 150,
    ):
        self.total_manga = total_manga
        self.testing = testing
        self.fuzzy_search = fuzzy_search
        self.qualifier_tokens = qualifier_tokens or TITLE_QUALIFIER_TOKENS
        self.prefix_len = prefix_len
        self.max_prefix_len = max_prefix_len
        self.target_bucket_size = target_bucket_size
        self.index = PrefixCandidateIndex(
            prefix_len=prefix_len,
            max_prefix_len=max_prefix_len,
            target_bucket_size=target_bucket_size,
        )

    def _ensure_sorted_total_manga(self):
        self.index.ensure_sorted(self.total_manga)

    def update_users(self, target_user_id=None):
        print("update users")
        changed_users = []
        if not self.total_manga:
            with open("new_list.json", "r") as f:
                self.total_manga = json.load(f)
        self.index.reset()
        self._ensure_sorted_total_manga()
        for user in db["manga-list"].find({}):
            user_list = user["manga-list"]
            user_id = user["user"]
            if "backup" in user_id:
                continue
            if target_user_id and target_user_id != user_id:
                continue
            if user_list and self.update_user_list(user_id, user_list):
                changed_users.append(user_id)
        print(f"user docs changed: {changed_users}")
        return changed_users

    def _find_best_matching_manga(self, user_manga, alternate_titles):
        """Find the best matching total_manga for a user_manga."""
        top_score = 0
        highest_scoring_user_matching_manga = None
        best_matching_total_manga = None

        for synonym in alternate_titles:
            candidates = self.index.candidates(synonym, [])
            for total_manga_dict in candidates[::-1]:
                search_res = self.fuzzy_search(synonym, total_manga_dict["title"])
                if search_res > top_score:
                    top_score = search_res
                    highest_scoring_user_matching_manga = user_manga
                    best_matching_total_manga = total_manga_dict
                if search_res == 100:
                    return (
                        top_score,
                        highest_scoring_user_matching_manga,
                        best_matching_total_manga,
                    )

        return top_score, highest_scoring_user_matching_manga, best_matching_total_manga

    def _get_current_source(self, user_manga):
        """Get the current source, defaulting to 'any' if not available."""
        current_source = user_manga.get("current_source", "any")
        return (
            "any"
            if current_source not in user_manga.get("sources", {})
            else current_source
        )

    def _process_matched_manga(
        self, user_id, user_manga, best_matching_total_manga, top_score
    ):
        """Process a matched manga and return whether series was updated."""
        user_manga["latest"] = best_matching_total_manga["sources"]["any"]["latest"]

        curr_source = self._get_current_source(user_manga)
        previous_latest = (
            user_manga.get("sources", {}).get(curr_source, {}).get("latest")
        )

        self.update_sources_and_read(
            user_id,
            best_matching_total_manga,
            user_manga,
            top_score,
        )

        curr_source = self._get_current_source(user_manga)
        latest_after_update = (
            user_manga.get("sources", {}).get(curr_source, {}).get("latest")
        )

        return previous_latest != latest_after_update

    def _should_skip_match(
        self,
        top_score,
        highest_scoring_user_matching_manga,
        best_matching_total_manga,
        historical_top_score,
    ):
        if top_score < 82:
            return True
        if not highest_scoring_user_matching_manga:
            return True
        if not best_matching_total_manga:
            return True
        return top_score < historical_top_score

    def _update_single_manga_match(
        self,
        user_id,
        user_manga,
        highest_scoring_user_matching_manga,
        best_matching_total_manga,
        top_score,
    ):
        user_manga["best_score"] = top_score
        user_manga["closest_title"] = best_matching_total_manga["title"]

        if self._check_massive_latest_disparity(
            user_manga=highest_scoring_user_matching_manga,
            best_matching_total_manga=best_matching_total_manga,
        ):
            print(
                f"Massive latest disparity detected for user {user_id} manga {user_manga['title']}  \
                    matched with {best_matching_total_manga['title']} score: {top_score}  \
                        user_latest = {float(user_manga['sources']['any']['latest'])}\
                            total_latest = {float(best_matching_total_manga['sources']['any']['latest'])}"
            )
            if user_manga['best_score'] != 100:
                return False
            print(
                "Exact title match with massive latest disparity, proceeding with update"
            )

        return self._process_matched_manga(
            user_id, user_manga, best_matching_total_manga, top_score
        )

    def update_user_list(self, user_id, user_list):
        if not self.total_manga:
            with open("new_list.json", "r") as f:
                self.total_manga = json.load(f)
        if self.index.is_empty():
            self._ensure_sorted_total_manga()
        series_updated = False
        strt = time.perf_counter() if user_list else None
        user_titles = [user_manga["title"] for user_manga in user_list]
        if self.testing:
            print(user_id, user_titles)

        for user_manga in user_list:
            alternate_titles = (
                set(user_manga['alternate_titles'])
                if 'alternate_titles' in user_manga
                else set()
            )
            alternate_titles.add(user_manga['title'])

            (
                top_score,
                highest_scoring_user_matching_manga,
                best_matching_total_manga,
            ) = self._find_best_matching_manga(user_manga, alternate_titles)
            historical_top_score = user_manga.get('best_score', 0)

            if self._should_skip_match(
                top_score,
                highest_scoring_user_matching_manga,
                best_matching_total_manga,
                historical_top_score,
            ):
                continue

            if self._update_single_manga_match(
                user_id,
                user_manga,
                highest_scoring_user_matching_manga,
                best_matching_total_manga,
                top_score,
            ):
                series_updated = True

        if series_updated and not self.testing:
            db["manga-list"].find_one_and_update(
                {"user": user_id},
                {"$set": {"manga-list": user_list}},
                return_document=True,
            )

        if strt and self.testing:
            print(f"updated user {user_id} in {time.perf_counter() - strt} seconds")
        return series_updated

    def _check_massive_latest_disparity(self, user_manga, best_matching_total_manga):
        try:
            user_latest = float(user_manga['sources']['any']['latest'])
            total_latest = float(best_matching_total_manga["sources"]["any"]["latest"])
            maximum = max(user_latest, total_latest)
            minimum = min(user_latest, total_latest)
            if maximum - minimum >= 10:
                return True
            return False
        except Exception:
            return True
            pass

    def update_sources_and_read(
        self,
        user_id,
        best_matching_manga,
        user_manga,
        search_res,
    ):

        user_manga["sources"] = self.update_user_sources(
            user_manga["sources"], best_matching_manga["sources"]
        )
        current_source = user_manga["current_source"]
        curr_source = (
            "any" if current_source not in user_manga["sources"] else current_source
        )
        try:
            user_manga["read"] = float(
                user_manga["sources"][curr_source]["latest"]
            ) <= float(user_manga["sources"][curr_source]["chapter"])
        except Exception:
            user_manga["read"] = float(
                user_manga["sources"][curr_source]["latest"]
            ) <= float(user_manga['chapter'])
        if not user_manga["read"]:
            print(
                f"in {user_id} {user_manga['title']} user chapter: {user_manga['sources'][curr_source]['chapter'] if 'chapter' in user_manga['sources'][curr_source] else 0} \
                    {user_manga['chapter']} /{best_matching_manga['latest']} {best_matching_manga['scansite']} score: {search_res} 'read: '{user_manga['read']}"
            )
        return user_manga

    def update_user_sources(self, user_manga: dict, total_manga: dict) -> dict:
        for source in total_manga:
            try:
                if source in user_manga:
                    if "url" in user_manga[source]:
                        total_manga[source]["url"] = user_manga[source]["url"]
                    if "chapter" in user_manga[source]:
                        total_manga[source]["chapter"] = user_manga[source]["chapter"]
                    if float(total_manga[source]["latest"]) < float(
                        user_manga[source]["latest"]
                    ):
                        print(
                            f"{total_manga[source]['latest']} < {user_manga[source]['latest']}",
                            source,
                            total_manga[source]['latest_link'],
                            source,
                            user_manga[source]["latest_link"],
                        )
            except Exception:
                print(
                    traceback.format_exc(),
                    total_manga[source]["latest_link"],
                    user_manga[source],
                )
        return total_manga
