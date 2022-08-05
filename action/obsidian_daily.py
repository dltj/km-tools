import logging
import os
from datetime import datetime

from config import config
from source import Resource, hypothesis, pinboard
from source.obsidian_db import obsidiandb
from util import obsidian

from action import Action

logger = logging.getLogger(__name__)


class ObsidianDaily(Action):
    attributes_supplied = ["obsidian_daily_filepath"]
    action_table = "action_obsidian"

    def __init__(self) -> None:
        super().__init__()

    def record(self, source: Resource, obsidian_daily_filepath: str) -> None:
        """
        Record the output of the Resource into an Obsidian database

        :param source: Instance of class WebResource

        :returns: None
        """
        Action._save_attributes(
            self, source, self.attributes_supplied, [obsidian_daily_filepath]
        )

    def new_sources(self):
        db = config.kmtools_db
        for origin in [
            pinboard.pinboard_origin,
            hypothesis.hypothesis_annotation_origin,
        ]:
            search_cur = db.cursor()
            query = (
                f"SELECT origin.{origin.origin_key} FROM {origin.origin_table} origin "
                f"LEFT JOIN {self.action_table} action ON action.url=origin.{origin.origin_key} "
                f"WHERE action.obsidian_daily_filepath IS NULL"
            )
            logger.debug(f"Executing {query=}")
            for row in search_cur.execute(query):
                logger.info(f"Now {row[origin.origin_key]} of {origin.origin_name}")
                source = origin.make_resource(uri=row[origin.origin_key])
                yield source


obsidian_daily_action = ObsidianDaily()


def daily(details):
    """Perform daily functions"""

    # Test to see if daily page already exists
    daily_page = obsidiandb.daily_page_path()
    if os.path.exists(daily_page) and not details.dry_run:
        logger.warning(f"Daily page {daily_page} already exists.")
        return

    # Make daily note navigation
    logger.info(f"Creating daily note file for today")
    with details.output_fd(daily_page) as daily_fh:
        daily_fh.write(
            f"""---
type: Daily note
---
Weekday:: {datetime.today().strftime('%A')}
Two weeks ago:: {obsidian.get_link_for_file(obsidiandb.daily_page(offset=-14))}
Last week:: {obsidian.get_link_for_file(obsidiandb.daily_page(offset=-7))}
Yesterday:: {obsidian.get_link_for_file(obsidiandb.daily_page(offset=-1))}
Tomorrow:: {obsidian.get_link_for_file(obsidiandb.daily_page(offset=1))}

## Tags for Today
```dataview
LIST FROM #{datetime.today().strftime('%d-%b')} 
```

## Morning Notes
Dream:: 
Morning comments:: 
Grateful for:: 

## Yesterday's readings
"""
        )

        seen_headlines = list()
        for source in obsidian_daily_action.new_sources():
            if source.headline not in seen_headlines:
                if source.origin.obsidian_tagless and not source.tags:
                    logger.info(f"Adding source with no tags: {source.title}")
                    daily_fh.write(
                        f"* Bookmark: [{source.headline}]({source.uri}) ({source.publisher}): {source.description}\n"
                    )
                else:
                    logger.info(f"Source with tags; link to '{source.title}'")
                    daily_fh.write(
                        f"* {type(source).__name__}: [[{source.headline}]] ({source.publisher})\n"
                    )
                if not config.dry_run:
                    obsidian_daily_action.record(source, daily_page)
                seen_headlines.append(source.headline)

        daily_fh.write("\n## Daily notes\n\n\n\n## End-of-day\n\n")
        for stat in [
            "Storyworthy",
            "Positive",
            "Negative",
            "Want to improve",
            "Day rating",
            "Stress",
            "Illness",
        ]:
            daily_fh.write(f"{stat}:: \n")
