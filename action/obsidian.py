import os

import arrow
import click

from action import obsidian_daily


@click.group()
def obsidian():
    """Commands for local Obsidian database"""


@obsidian.command(name="daily")
@click.pass_obj
def daily_command(details):
    """Make daily Obsidian diary page"""
    return obsidian_daily.daily(details)


class Obsidian:
    """Obsidian database manipulation"""

    def __init__(self, db_directory=None, daily_directory=None, source_directory=None):
        self.db_directory = db_directory
        self.daily_directory = daily_directory
        self.source_directory = source_directory

    def daily_page(self, offset=0):
        """Generate the full file path to a daily diary file.

        :param offset: Number of days to offset from current day

        :returns: Full path to file as string
        """
        file_date = arrow.now()
        if offset != 0:
            file_date = file_date.shift(days=offset)
        return file_date.format("YYYY-MM-DD")

    def daily_page_path(self, daily_page=None):
        """Get the full path to a daily page in the Obsidian database.

        :param daily_page: Daily page name

        :returns: Full path to the page in the Obsidian database
        """
        if daily_page is None:
            daily_page = self.daily_page()
        return self.page_to_path(daily_page, folder="daily")

    def source_page_path(self, source_title):
        """Get the full path to a source page in the Obsidian database.

        This method will remove problematic characters from the title to make it into a file name. It also attempts to guess the publisher of the source by splitting on '|'.

        :param source_title: Source page name

        :returns:
            - Full path to the page in the Obsidian database
            - Filename portion of page path
            - Publisher of the source (e.g. "Washington Post")
        """
        if "|" in source_title:
            filename, publisher = source_title.split("|", 1)
            filename = filename.strip().replace(":", "—").replace("/", "-")
            publisher = publisher.strip()
        else:
            filename = source_title
            publisher = ""
        return self.page_to_path(filename, folder="source"), filename, publisher

    def page_to_path(self, page, folder=None):
        """Return the full path of a page in the Obsidian database.

        :param page: Obsidian page name
        :param folder: Obsidian folder, if needed

        :returns: Full path to the page in the Obsidian database
        """
        if folder.lower() == "daily":
            folder = self.daily_directory
        if folder.lower() == "source":
            folder = self.source_directory
        return os.path.join(self.db_directory, folder, page + ".md")


def init_source(
    details, source_path_filename, publisher, url, created, derived_date, summary
):
    """If necessary, create a new source file in Obsidian and write the source's metadata

    :param source_path_filename: location source inside Obsidian database
    :param publisher: the originating website (e.g. "Washington Post")
    :param url: link to web source
    :param created: creation date for the source as string
    :param derived_date: presumed date of source publication
    :param summary: machine-generated summary of source

    :returns: None
    """
    if not os.path.exists(source_path_filename):
        with details.output_fd(source_path_filename) as source_fd:
            source_fd.write(
                "---\ntype: Source\n"
                f"source_url: {url}\n"
                f"bookmark_saved: {created}\n"
                f"source_created: {derived_date}\n"
                f"publisher: {publisher}\n"
                "---\n"
                f"Automated summary:: {summary}\n\n"
            )
    return


def get_link_for_file(file, link_text=""):
    """Create wiki-link syntax for a specific file name.

    :param file: file name to point to
    :param link_text: anchor text for the link

    :returns: Wiki-link syntax string
    """
    if link_text != "":
        return "[[" + file.replace(".md", "") + "|" + link_text + "]]"
    else:
        return "[[" + file.replace(".md", "") + "]]"
