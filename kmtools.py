#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import sys
import logging
import sqlite3
from logging.handlers import TimedRotatingFileHandler
import click
from omegaconf import OmegaConf
from command import hourly
from action import twitter, wayback
from source import pinboard
from source import hypothesis


def _create_rotating_log(level=logging.INFO, logpath=None):
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    if logpath:
        try:
            handler = TimedRotatingFileHandler(logpath, when="midnight", backupCount=8)
        except IOError:
            logger.error("Could not write to %s, falling back to stdout", logpath)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s@%(lineno)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class Details:  # pylint: disable=too-few-public-methods
    """Application-specific context"""

    twitter_short_url_length = None

    def __init__(
        self,
        logger_handle=None,
        dry_run=False,
        config=None,
        dispatch=None,
        actions=None,
    ):
        self.logger = logger_handle
        self.dry_run = dry_run
        self.config = config
        self.dispatch = dispatch
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
    logpath = logfile if logfile else config.kmtools.logfile

    if debug:
        log = _create_rotating_log(logging.DEBUG, logpath)
    elif verbose:
        log = _create_rotating_log(logging.INFO, logpath)
    else:
        log = _create_rotating_log(logging.WARNING, logpath)

    # Register source dispatchers
    dispatch = {}
    dispatch["Pinboard"] = pinboard.register_source()
    dispatch["Hypothesis"] = hypothesis.register_source()

    # Register actions
    actions = {}
    actions["Twitter"] = twitter.register_action()

    ctx.obj = Details(log, dry_run, config, dispatch, actions)


# Register commands
cli.add_command(pinboard.pinboard)
cli.add_command(hypothesis.hypothesis)
cli.add_command(wayback.wayback)
cli.add_command(hourly.hourly)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
