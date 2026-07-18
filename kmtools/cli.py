#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

from __future__ import annotations

import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

import click
import psutil
from pydantic import ValidationError

from kmtools.command import (
    daily,
    hourly,
    hypothesis,
    pinboard,
    robustify,
    summarize,
    wayback,
)
from kmtools.util.config import Config, init_config
from kmtools.util.logging_util import PackagePathFilter

logger = logging.getLogger()


def find_and_kill_old_instances(max_runtime: int = 600) -> None:
    current_pid = os.getpid()

    # Iterate over all running processes
    for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]

            if not cmdline:
                continue

            is_old_style_script = (
                len(cmdline) > 1
                and Path(cmdline[0]).name.startswith("python")
                and Path(cmdline[1]).name == "kmtools"
            )

            is_console_script = Path(cmdline[0]).name == "kmtools"

            if (is_old_style_script or is_console_script) and proc.info[
                "pid"
            ] != current_pid:
                runtime = time.time() - proc.info["create_time"]

                if runtime > max_runtime:
                    print(
                        f"Killing old instance: PID {proc.info['pid']}, "
                        f"running for {runtime / 60:.2f} minutes.",
                        file=sys.stderr,
                    )
                    proc.terminate()

                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)

        except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
            pass


def configure_logging(
    config: Config,
    *,
    debug: bool = False,
    verbose: bool = False,
    logfile: str | Path | None = None,
) -> None:
    """
    Configure application logging.

    Behavior:

    - If --logfile is supplied, log there.
    - Else if stderr is attached to a terminal, log to stderr.
    - Else, assume cron/launchd/non-interactive execution and log to the
      configured common logfile.
    - If opening the logfile fails, fall back to stderr.
    """

    handler: logging.Handler

    running_interactively = sys.stderr.isatty()

    if logfile is not None:
        logpath = Path(logfile).expanduser()
    elif running_interactively:
        logpath = None
    else:
        logpath = config.kmtools.logfile.expanduser()

    if logpath is None:
        handler = logging.StreamHandler(sys.stderr)
    else:
        try:
            logpath.parent.mkdir(parents=True, exist_ok=True)

            handler = TimedRotatingFileHandler(
                logpath,
                when="midnight",
                backupCount=8,
            )
        except OSError as exc:
            print(
                f"Could not write to {logpath}: {exc}. Falling back to stderr.",
                file=sys.stderr,
            )
            handler = logging.StreamHandler(sys.stderr)

    handler.addFilter(PackagePathFilter())

    logging.basicConfig(
        handlers=[handler],
        format=(
            "%(asctime)s - %(levelname)-8s - %(relativepath)s@%(lineno)s - %(message)s"
        ),
        force=True,
    )

    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--dry-run", is_flag=True, help="Show what would happen without changing anything."
)
@click.option("-d", "--debug", is_flag=True, default=False, help="Turn on debugging.")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Turn on verbose messages.",
)
@click.option(
    "-l",
    "--logfile",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Log file path.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    dry_run: bool,
    debug: bool,
    verbose: bool,
    logfile: Path | None,
) -> None:
    """Root command line function."""

    overrides: dict[str, Any] = {
        "dry_run": dry_run,
    }

    kmtools_overrides: dict[str, Any] = {}

    if logfile is not None:
        kmtools_overrides["logfile"] = logfile

    if kmtools_overrides:
        overrides["kmtools"] = kmtools_overrides

    try:
        config = init_config(**overrides)
    except ValidationError as exc:
        raise click.ClickException(f"Configuration error:\n{exc}") from exc

    configure_logging(
        config,
        debug=debug,
        verbose=verbose,
        logfile=logfile,
    )

    ctx.obj = config

    find_and_kill_old_instances()


# Register commands
cli.add_command(pinboard.pinboard)
cli.add_command(hypothesis.hypothesis)
cli.add_command(wayback.wayback)
# cli.add_command(mastodon.mastodon)
cli.add_command(hourly.hourly)
cli.add_command(daily.daily)
cli.add_command(robustify.robustify)
cli.add_command(summarize.summarize_command)


# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
