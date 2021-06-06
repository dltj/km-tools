import os
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


def calc_source_filename(details, title):
    """Calculate what the filename will be for a source in Obsidian based on the title of the source

    :param details: context object
    :param title: the title of the source

    :returns:
        - file path to the source directory in Obsidian
        - trimmed file name
    """
    filename = title.split("|")[0].strip()
    source_path = os.path.join(
        details.config.obsidian.db_directory,
        details.config.obsidian.source_directory,
    )
    return source_path, filename
