#!/usr/bin/env python
# encoding: utf-8
"""Knowledge Management CLI."""

import click
from omegaconf import OmegaConf
from action import Twitter
from source import Pinboard


class Details:  # pylint: disable=too-few-public-methods
    """Application-specific context"""

    def __init__(self, dry_run=False, config=None):
        self.dry_run = dry_run
        self.config = config


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cli(ctx, dry_run):
    """Root command line function"""
    config = OmegaConf.load("config.yml")
    OmegaConf.set_readonly(config, True)

    ctx.obj = Details(dry_run, config)


# Register commands
cli.add_command(Twitter.twitter)
cli.add_command(Pinboard.pinboard)

# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    cli()
