"""
Hold the configuration for the application.
"""

import os
import sqlite3
import sys

import click


class Config:  # pylint: disable=too-few-public-methods
    """Application-specific context"""

    def __init__(self):
        self.dry_run = None
        self.logger = None
        self.settings = None
        self.origins = {}
        self.actions = {}
        self.kmtools_db_conn = None

    @property
    def kmtools_db(self):
        """Get the kmtools database connection."""
        if not self.kmtools_db_conn:
            if self.settings.kmtools.dbfile:
                self.kmtools_db_conn = sqlite3.connect(self.settings.kmtools.dbfile)
                self.kmtools_db_conn.row_factory = sqlite3.Row
                self.kmtools_db_conn.execute("BEGIN EXCLUSIVE")
                self.kmtools_db_conn.set_trace_callback(self.logger.debug)
            else:
                raise RuntimeError("KM-Tools database location not set")
        return self.kmtools_db_conn

    def output_fd(self, file):
        """Route output depending on whether the dry_run flag is set or not

        :param file: full path to output file to be ued when dry_run isn't set

        return: file descriptor, stdout when dry_run, otherwise append file descriptor
        """
        if self.dry_run:
            click.secho(f">>> Would write to {file} >>>", fg="green")
            fd = os.fdopen(os.dup(sys.stdout.fileno()), "w")
        else:
            fd = open(file, "a")

        return fd


config = Config()
