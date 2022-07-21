import json
import os
import re
from datetime import datetime

import exceptions
from source import hypothesis
from source.obsidian_db import obsidiandb
from util import obsidian


def daily(details):
    """Perform daily functions"""

    # Test to see if daily page already exists
    daily_page = obsidiandb.daily_page_path()
    if os.path.exists(daily_page) and not details.dry_run:
        details.logger.warning(f"Daily page {daily_page} already exists.")
        return

    # Make daily note navigation
    details.logger.info(f"Creating log file for today")
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
    obsidian_db_column = "obsidian_file"
    obsidian_dispatch = {
        "pinboard": create_pinboard_entry,
    }

    for origin_name, origin in details.origins.items():
        if origin_name.lower() == "hypothesis":
            continue  # Handled later as annotations, not as an individual source
        if origin_name.lower() not in obsidian_dispatch:
            details.logger.warning(f"No Obsidian dispatch found for {origin_name}.")
            continue

        new_entries = origin.new_entries_handler(details, obsidian_db_column)
        details.logger.info(
            f"Found {len(new_entries)} new entries from {origin_name} for Obsidian"
        )
        for entry in new_entries:
            details.logger.debug(
                f"New from {origin_name} for Obsidian: {entry.title} ({entry.href})"
            )
            try:
                result = obsidian_dispatch[origin_name.lower()](details, entry)
            except exceptions.KMException as err:
                details.logger.error(err)
                raise SystemExit from err
            if not details.dry_run:
                origin.save_entry_handler(
                    details, obsidian_db_column, entry.href, result
                )
                details.logger.info(
                    f"Successfully handled {entry.href} from {origin_name} for Obsidian"
                )
            else:
                details.logger.info(f"Would have saved {entry.href}")

    with details.output_fd(daily_page) as daily_fh:
        create_hypothesis_entries(details, daily_fh)
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


def create_pinboard_entry(details, entry):  # pylint: disable=w0613
    """Output an entry from Pinboard into Obsidian

    If a Pinboard entry has no tags, it is written as a single line in the daily
    journal entry.  If it does have tags, it is output as a source in Obsidian.

    :param details: context object
    :param entry: the Website to be output
    :param daily_fd: file descriptor for the daily journal entry

    :returns: file path where the note entry was placed
    """

    title_scan = re.compile("(.*?)\s+\[(.*?)\]\s+(.*)")
    if (match := title_scan.match(entry.title)) is not None:
        title = f"{match.group(1)} {match.group(3)}"
        description = f"_{match.group(2)}_\n\n{entry.description}"
    else:
        title = entry.title
        description = entry.description

    tags = _format_tags(entry.tags)
    if len(tags) > 1:
        output_path, output_filename, publisher = obsidiandb.init_source(
            title=title,
            url=entry.href,
            created=entry.archive_date,
            derived_date=entry.derived_date,
            summary=entry.summarization,
        )
        with details.output_fd(obsidiandb.daily_page_path()) as daily_fh:
            daily_fh.write(f"* New bookmark: [[{output_filename}]] ({publisher})\n")
        detail_output = f"[{title}]({entry.href})\n{description}\nTags:: {tags}\n"
    else:
        output_path = obsidiandb.daily_page_path()
        detail_output = f"* [{title}]({entry.href}): {description}\n"

    with details.output_fd(output_path) as source_fh:
        source_fh.write(detail_output)

    return output_path


def create_hypothesis_entries(details, daily_fh):
    """Output annotations from a Hypothesis source into Obsidian

    :param details: context object
    :param entry: the Website to be output
    :param daily_fd: file descriptor for the daily journal entry
    """

    new_sources = set()
    for ann in hypothesis.get_new_annotations(details):
        webpage = hypothesis.find_entry(details, ann.uri)
        output_path, output_filename, _ = obsidiandb.init_source(
            title=ann.document_title,
            url=ann.uri,
            created=ann.created,
            derived_date=webpage.derived_date,
            summary=webpage.summarization,
        )

        with (details.output_fd(output_path)) as source_fh:
            tags = _format_tags(ann.tags)
            quote = ann.quote.strip()
            annotation = ann.annotation.strip()
            # headline = discussion = ""
            if ann.annotation.startswith("##"):
                headline, _, discussion = annotation.partition("\n")
                headline = f"{headline}\n"
            else:
                headline = ""
                discussion = annotation.strip()
            if discussion:
                discussion = f"{discussion}\n\n"
            if len(tags) > 0:
                tags = f"- Tags:: {tags}\n"
            source_fh.write(
                f"{headline}"
                f"> {quote}\n\n"
                f"{discussion}"
                f"- Link to [Annotation]({ann.link_incontext})\n{tags}\n"
            )
            if not details.dry_run:
                hypothesis.save_annotation(details, ann.id, output_path)
            details.logger.info(f"Saved annotation {ann.id} to {ann.document_title}")
        new_sources.update([output_filename])

    for source in new_sources:
        daily_fh.write(f"* New/updated annotated source: [[{source}]]\n")


def _format_tags(tags_string):
    tags = ""
    if tags_string and tags_string != "[]":
        tag_array = json.loads(tags_string)
        # Dash to space
        tag_array = map(lambda x: x.replace("-", " "), tag_array)
        # Non hashtags to links
        tag_array = map(lambda x: f"[[{x}]]" if x[0] != "#" else x, tag_array)
        tags = ", ".join(tag_array)
    return tags
