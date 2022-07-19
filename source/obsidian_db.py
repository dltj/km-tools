import os

import arrow
from config import config


class ObsidianDb:
    """Obsidian database manipulation"""

    def __init__(self, db_directory=None, daily_directory=None, source_directory=None):
        self._db_directory = db_directory
        self._daily_directory = daily_directory
        self._source_directory = source_directory

    @property
    def db_directory(self):
        """Get path to the top of the Obsidian database directory"""
        if not self._db_directory:
            self._db_directory = config.settings.obsidian.db_directory
        return self._db_directory

    @property
    def daily_directory(self):
        """Get the subdirectory name for daily files"""
        if not self._daily_directory:
            self._daily_directory = config.settings.obsidian.daily_directory
        return self._daily_directory

    @property
    def source_directory(self):
        """Get the subdirectory name for source files"""
        if not self._source_directory:
            self._source_directory = config.settings.obsidian.source_directory
        return self._source_directory

    def daily_page(self, offset=0):
        """Get the name of the daily page for today or from a +/- offset from today.

        :param offset: Number of days to offset from current day

        :returns: File name for daily page
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
        self, title=None, url=None, created=None, derived_date=None, summary=None
    ):
        """If necessary, create a new source file in Obsidian and write the source's metadata

        :param title: title of the source
        :param publisher: the originating website (e.g. "Washington Post")
        :param url: link to source
        :param created: creation date for the source as string
        :param derived_date: presumed date of source publication
        :param summary: machine-generated summary of source

        :returns:
            - Full path to the page in the Obsidian database
            - Filename of source file
            - Publisher string
        """
        source_path_filename, output_filename, publisher = obsidiandb.source_page_path(
            title
        )
        if not os.path.exists(source_path_filename):
            with config.output_fd(source_path_filename) as source_fd:
                source_fd.write(
                    "---\ntype: Source\n"
                    f"source_url: {url}\n"
                    f"bookmark_saved: {created}\n"
                    f"source_created: {derived_date}\n"
                    f"publisher: {publisher}\n"
                    "---\n"
                    f"Automated summary:: {summary}\n\n"
                )
        return source_path_filename, output_filename, publisher


obsidiandb = ObsidianDb()
