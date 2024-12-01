#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler

import click
import psutil

from kmtools.command import daily, hourly, obsidian, wayback
from kmtools.source import hypothesis, pinboard
from kmtools.util.config import config
from kmtools.util.logging_util import PackagePathFilter

logger = logging.getLogger()


def find_and_kill_old_instances(max_runtime: int = 600) -> None:
    current_pid = os.getpid()

    # Iterate over all running processes
    for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]

            # Python scripts often have the command line as [python, script_path, ...]
            if (
                cmdline
                and len(cmdline) > 1
                and cmdline[0].endswith("python")
                and cmdline[1].endswith("kmtools")
                and proc.info["pid"] != current_pid
            ):
                runtime = time.time() - proc.info["create_time"]

                if runtime > max_runtime:
                    print(
                        f"Killing old instance: PID {proc.info['pid']}, "
                        f"Running for {runtime / 60:.2f} minutes."
                    )
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)

        except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
            # Handle exceptions where the process may have already exited
            # or a permission error occurred
            pass


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

    find_and_kill_old_instances()


# Register commands
cli.add_command(pinboard.pinboard)
cli.add_command(hypothesis.hypothesis)
cli.add_command(wayback.wayback)
cli.add_command(obsidian.obsidian)
# cli.add_command(mastodon.mastodon)
cli.add_command(hourly.hourly)
cli.add_command(daily.daily)
# cli.add_command(robustify.robustify)
# cli.add_command(summarize.summarize_command)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
