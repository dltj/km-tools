import os
import sys
import json
import exceptions
from action import obsidian
from source import hypothesis


def daily(details):
    """Perform daily functions"""

    obsidian_db_column = "obsidian_file"
    obsidian_dispatch = {
        "pinboard": create_pinboard_entry,
    }

    with details.output_fd(details.obsidian_daily_file) as daily_fd:
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

        create_hypothesis_entries(details, daily_fd)


def create_pinboard_entry(details, entry):  # pylint: disable=w0613
    """Output an entry from Pinboard into Obsidian

    If a Pinboard entry has no tags, it is written as a single line in the daily
    journal entry.  If it does have tags, it is output as a source in Obsidian.

    :param details: context object
    :param entry: the Website to be output
    :param daily_fd: file descriptor for the daily journal entry

    :returns: file path where the note entry was placed
    """

    tags = ""
    if entry.tags and entry.tags != "[]":
        tag_array = json.loads(entry.tags)
        tag_array = map(lambda x: x.replace("-", " "), tag_array)
        tags = "[[" + "]], [[".join(tag_array) + "]]"
        source_path, source_filename = obsidian.calc_source_filename(
            details, entry.title
        )
        output_filename = os.path.join(source_path, source_filename) + ".md"
        obsidian.init_source(details, output_filename, entry.href, entry.archive_date)
        with details.output_fd(details.obsidian_daily_file) as daily_fd:
            print(f"* New bookmark: {entry.title}\n", file=daily_fd)
    else:
        output_filename = details.obsidian_daily_file

    with details.output_fd(output_filename) as source_fd:
        print(
            f"\n[{entry.title}]({entry.href})\n" f"{entry.description}\n" f"{tags}\n",
            file=source_fd,
        )

    return output_filename


def create_hypothesis_entries(details, daily_fd):
    """Output annotations from a Hypothesis source into Obsidian

    :param details: context object
    :param entry: the Website to be output
    :param daily_fd: file descriptor for the daily journal entry
    """

    new_sources = set()
    for ann in hypothesis.get_new_annotations(details):
        source_path, source_filename = obsidian.calc_source_filename(
            details, ann.document_title
        )
        source_path_filename = os.path.join(source_path, source_filename) + ".md"
        obsidian.init_source(details, source_path_filename, ann.uri, ann.created)

        with (details.output_fd(source_path_filename)) as source_fd:
            tags = ""
            if ann.tags and ann.tags != "[]":
                tag_array = json.loads(ann.tags)
                tag_array = map(lambda x: x.replace("-", " "), tag_array)
                tags = "[[" + "]], [[".join(tag_array) + "]]"
            print(
                f"> {ann.quote}\n\n"
                f"{ann.annotation}\n"
                f"[Annotation]({ann.link_incontext})\n{tags}\n",
                file=source_fd,
            )
            hypothesis.save_annotation(details, ann.id, source_path_filename)
            details.logger.info(f"Saved annotation {ann.id} to {ann.document_title}")
        new_sources.update([source_filename])

    for source in new_sources:
        print(f"* New/updated annotated source: {source}\n", file=daily_fd)
