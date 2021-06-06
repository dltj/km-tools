import os
import sys
import json
import exceptions
from action import obsidian
from source import hypothesis


def daily(details):
    """Update local Hypothesis database"""

    obsidian_db_column = "obsidian_file"
    obsidian_dispatch = {}
    obsidian_dispatch["pinboard"] = daily_pinboard

    with (
        os.fdopen(os.dup(sys.stdout.fileno()), "w")
        if details.dry_run
        else open(details.obsidian_daily_file, "a")
    ) as daily_fd:

        for source_name, source in details.sources.items():
            if source_name.lower() == "hypothesis":
                continue  # handled as a special case below
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
                    result = obsidian_dispatch[source_name.lower()](
                        details, entry, daily_fd
                    )
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

        daily_hypothesis(details, daily_fd)


def daily_pinboard(details, entry, outfile):  # pylint: disable=w0613
    """Output a line to the daily note from Pinboard

    :param details: context object
    :param entry: the Website to be output
    :param outfile: file descriptor used for outputting the line

    :returns: file path where the note entry was placed
    """
    if not details.dry_run:  # pylint: disable=R1705
        tags = ""
        if entry.tags and entry.tags != "[]":
            tags = " #" + ", #".join(json.loads(entry.tags))

        print(f"* [{entry.title}]({entry.href}){tags}", file=outfile)
        return outfile.name
    else:
        details.logger.info(f"Would have written {entry.href} to daily file")
        return "dry-run"


def daily_hypothesis(details, daily_fd):
    """Output annotations from a Hypothesis source to a file and a
    line to the daily note from Hypothesis.

    :param details: context object
    :param outfile: file descriptor used for outputting the line
    """

    new_sources = set()
    for ann in hypothesis.get_new_annotations(details):
        source_path, source_filename = obsidian.calc_source_filename(
            details, ann.document_title
        )
        source_path_filename = os.path.join(source_path, source_filename) + ".md"
        with (
            os.fdopen(os.dup(sys.stdout.fileno()), "w")
            if details.dry_run
            else open(source_path_filename, "a")
        ) as source_fd:
            tags = ""
            if ann.tags and ann.tags != "[]":
                tags = ", #" + ", #".join(json.loads(ann.tags))
            print(
                f"> {ann.quote}\n\n"
                f"{ann.annotation}\n"
                f"[Annotation]({ann.link_incontext}){tags}\n",
                file=source_fd,
            )
            hypothesis.save_annotation(details, ann.id, source_path_filename)
            details.logger.info(f"Saved annotation {ann.id} to {ann.document_title}")
        new_sources.update([source_filename])

    for source in new_sources:
        print(f"* New/updated annotated source: [[{source}]]", file=daily_fd)
