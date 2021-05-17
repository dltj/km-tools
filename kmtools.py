#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import sys
import logging
import click
from omegaconf import OmegaConf
from command import hourly

logger = logging.getLogger(sys.argv[0])
FORMAT = "%(asctime)s - %(levelname)s - %(module)s@%(lineno)s - %(message)s"
logging.basicConfig(format=FORMAT)


class Details:  # pylint: disable=too-few-public-methods
    """Application-specific context"""

    twitter_short_url_length = None

    def __init__(self, logger_handle=None, dry_run=False, config=None):
        self.logger = logger_handle
        self.dry_run = dry_run
        self.config = config


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--dry-run", is_flag=True)
@click.option("-d", "--debug", is_flag=True, default=False, help="turn on debugging")
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="turn on verbose messages"
)
@click.pass_context
def cli(ctx, dry_run, debug, verbose):
    """Root command line function"""
    config = OmegaConf.load("config.yml")
    OmegaConf.set_readonly(config, True)

    ctx.obj = Details(logger, dry_run, config)
    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


# Register commands
cli.add_command(hourly.hourly)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
