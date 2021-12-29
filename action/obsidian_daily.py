import os
import json
from datetime import datetime
import exceptions
from action import obsidian
from source import hypothesis


def daily(details):
    """Perform daily functions"""

    # Test to see if daily page already exists
    daily_page = details.obsidian.daily_page_path()
    if os.path.exists(daily_page) and not details.dry_run:
        details.logger.warning(f"Daily page {daily_page} already exists.")
        return

    # Make daily note navigation
    details.logger.info(f"Creating log file for today")
    with details.output_fd(daily_page) as daily_fh:
        daily_fh.write(f"Weekday:: {datetime.today().strftime('%A')}\n")
        daily_fh.write(
            f"Yesterday:: {obsidian.get_link_for_file(details.obsidian.daily_page(offset=-1))}\n"
        )
        daily_fh.write(
            f"Tomorrow:: {obsidian.get_link_for_file(details.obsidian.daily_page(offset=1))}\n"
        )
        daily_fh.write(
            "\n## Morning Notes\n\nDream:: \n\nMorning comments:: \n\nGrateful for:: \n\n"
        )
        daily_fh.write("\n## Yesterday's readings\n")

    obsidian_db_column = "obsidian_file"
    obsidian_dispatch = {
        "pinboard": create_pinboard_entry,
    }

    for source_name, source in details.sources.items():
        if source_name.lower() == "hypothesis":
            continue  # Handled later as annotations, not as an individual source
        if source_name.lower() not in obsidian_dispatch:
            details.logger.warning(f"No Obsidian dispatch found for {source_name}.")
            continue

        new_entries = source.new_entries_handler(details, obsidian_db_column)
        details.logger.info(
            f"Found {len(new_entries)} new entries from {source_name} for Obsidian"
        )
        for entry in new_entries:
            details.logger.debug(
                f"New from {source_name} for Obsidian: {entry.title} ({entry.href})"
            )
            try:
                result = obsidian_dispatch[source_name.lower()](details, entry)
            except exceptions.KMException as err:
                details.logger.error(err)
                raise SystemExit from err
            if not details.dry_run:
                source.save_entry_handler(
                    details, obsidian_db_column, entry.href, result
                )
                details.logger.info(
                    f"Successfully handled {entry.href} from {source_name} for Obsidian"
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

    tags = _format_tags(entry.tags)
    if len(tags) > 1:
        output_path, output_filename, origin = details.obsidian.source_page_path(
            entry.title
        )
        obsidian.init_source(
            details,
            output_path,
            origin,
            entry.href,
            entry.archive_date,
            entry.derived_date,
            entry.summarization,
        )
        with details.output_fd(details.obsidian.daily_page_path()) as daily_fh:
            daily_fh.write(f"* New bookmark: [[{output_filename}]] ({origin})\n")
    else:
        output_path = details.obsidian.daily_page_path()

    with details.output_fd(output_path) as source_fh:
        source_fh.write(
            f"\n[{entry.title}]({entry.href})\n" f"{entry.description}\n" f"{tags}\n"
        )

    return output_path


def create_hypothesis_entries(details, daily_fh):
    """Output annotations from a Hypothesis source into Obsidian

    :param details: context object
    :param entry: the Website to be output
    :param daily_fd: file descriptor for the daily journal entry
    """

    new_sources = set()
    for ann in hypothesis.get_new_annotations(details):
        output_path, output_filename, origin = details.obsidian.source_page_path(
            ann.document_title
        )
        obsidian.init_source(details, output_path, origin, ann.uri, ann.created)

        with (details.output_fd(output_path)) as source_fh:
            tags = _format_tags(ann.tags)
            source_fh.write(
                f"> {ann.quote}\n\n"
                f"{ann.annotation}\n"
                f"[Annotation]({ann.link_incontext})\n{tags}\n"
            )
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
