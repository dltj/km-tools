#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import getpass
import logging
import sys
import time
from logging.handlers import TimedRotatingFileHandler

import click
import psutil
from omegaconf import OmegaConf

from kmtools.action import mastodon
from kmtools.command import daily, hourly, obsidian, robustify, summarize, wayback
from kmtools.source import hypothesis, pinboard
from kmtools.util.config import config
from kmtools.util.logging_util import PackagePathFilter

logger = logging.getLogger()


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
    config.dry_run = dry_run
    config.settings = OmegaConf.load("config.yml")
    OmegaConf.set_readonly(config.settings, True)

    if sys.stdin and sys.stdin.isatty():
        if not logfile:
            handler = logging.StreamHandler(sys.stderr)
        else:
            try:
                handler = logging.FileHandler(logfile)
            except IOError:
                print(
                    f"Could not write to {logfile}, falling back to stdout",
                    file=sys.stderr,
                )
    else:
        logpath = logfile if logfile else config.settings.kmtools.logfile
        if logpath:
            try:
                handler = TimedRotatingFileHandler(
                    logpath, when="midnight", backupCount=8
                )
            except IOError:
                print(
                    f"Could not write to {logpath}, falling back to stdout",
                    file=sys.stderr,
                )
    handler.addFilter(PackagePathFilter())
    logging.basicConfig(
        handlers=[handler],
        format="%(asctime)s - %(levelname)-8s - %(relativepath)s@%(lineno)s - %(message)s",
    )
    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    ctx.obj = config

    ## If there is an instance of us that has been running for over 60 seconds, kill it
    for proc in psutil.process_iter(["pid", "name", "cmdline", "username"]):
        if (
            proc.info["username"] != getpass.getuser()
            or proc.info["name"].casefold() != "python"
        ):
            continue
        if len(proc.info["cmdline"]) > 1 and "kmtools" in proc.info["cmdline"][1]:
            runtime = int(time.time()) - int(proc.create_time())
            if runtime < 60:
                continue
            logger.warning(
                "PID %s running for %s seconds; killing.", proc.info["pid"], runtime
            )
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                proc.kill()


# Register commands
cli.add_command(pinboard.pinboard)
cli.add_command(hypothesis.hypothesis)
cli.add_command(wayback.wayback)
cli.add_command(obsidian.obsidian)
cli.add_command(mastodon.mastodon)
cli.add_command(hourly.hourly)
cli.add_command(daily.daily)
cli.add_command(robustify.robustify)
cli.add_command(summarize.summarize_command)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
