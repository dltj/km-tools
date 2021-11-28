#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import sys
import os
from datetime import datetime
import logging
import sqlite3
from logging.handlers import TimedRotatingFileHandler
import click
from omegaconf import OmegaConf
from command import hourly, daily
from action import twitter, wayback, obsidian, mastodon
from source import pinboard
from source import hypothesis


class Details:  # pylint: disable=too-few-public-methods
    """Application-specific context"""

    def __init__(
        self,
        logger_handle=None,
        dry_run=False,
        config=None,
        sources=None,
        actions=None,
    ):
        self.logger = logger_handle
        self.dry_run = dry_run
        self.config = config
        self.sources = sources
        self.actions = actions
        self.kmtools_db_conn = None

    @property
    def kmtools_db(self):
        if self.kmtools_db_conn:
            return self.kmtools_db_conn
        if self.config.kmtools.dbfile:
            self.kmtools_db_conn = sqlite3.connect(self.config.kmtools.dbfile)
            self.kmtools_db_conn.row_factory = sqlite3.Row
            self.kmtools_db_conn.execute("BEGIN EXCLUSIVE")
            self.kmtools_db_conn.set_trace_callback(self.logger.debug)
        else:
            raise RuntimeError("KM-Tools database location not set")
        return self.kmtools_db_conn

    @property
    def obsidian_daily_file(self):
        diary_filename = datetime.now().strftime("%Y-%m-%d")
        diary_path = os.path.join(
            self.config.obsidian.db_directory,
            self.config.obsidian.daily_directory,
            f"{diary_filename}.md",
        )
        return diary_path


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--dry-run", is_flag=True)
@click.option("-d", "--debug", is_flag=True, default=False, help="turn on debugging")
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="turn on verbose messages"
)
@click.option("-l", "--logfile", default=None, help="log file path")
@click.pass_context
def cli(ctx, dry_run, debug, verbose, logfile):
    """Root command line function"""
    config = OmegaConf.load("config.yml")
    OmegaConf.set_readonly(config, True)

    log = logging.getLogger(__name__)
    if sys.stdin and sys.stdin.isatty():
        if not logfile:
            handler = logging.StreamHandler(sys.stderr)
        else:
            try:
                handler = logging.FileHandler(logfile)
            except IOError:
                log.error("Could not write to %s, falling back to stdout", logfile)
    else:
        logpath = logfile if logfile else config.kmtools.logfile
        if logpath:
            try:
                handler = TimedRotatingFileHandler(
                    logpath, when="midnight", backupCount=8
                )
            except IOError:
                log.error("Could not write to %s, falling back to stdout", logpath)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s@%(lineno)s - %(message)s"
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)

    if debug:
        log.setLevel(logging.DEBUG)
    elif verbose:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.WARNING)

    # Register source dispatchers
    sources = {}
    sources["Pinboard"] = pinboard.register_source()
    sources["Hypothesis"] = hypothesis.register_source()

    # Register actions
    actions = {}
    actions["Twitter"] = twitter.register_hourly_action()
    actions["Wayback"] = wayback.register_hourly_action()
    actions["Mastodon"] = mastodon.register_hourly_action()

    ctx.obj = Details(log, dry_run, config, sources, actions)


# Register commands
cli.add_command(pinboard.pinboard)
cli.add_command(hypothesis.hypothesis)
cli.add_command(wayback.wayback)
cli.add_command(obsidian.obsidian)
cli.add_command(mastodon.mastodon)
cli.add_command(hourly.hourly)
cli.add_command(daily.daily)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
