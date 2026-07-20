"""Call summarization routines."""

import click

from kmtools.action.obsidian_utility_action import ObsidianPageCleanup


@click.group()
def obsidian():
    """Commands for Obsidian knowledgebase"""


@obsidian.command(name="clean")
@click.argument("file_date", type=str)
@click.pass_obj
def clean_command(_, file_date) -> None:
    """Cleanup unused elements of a daily notes page.

    FILE_DATE is the date of the daily page. If ommitted, the default is 6 days
    prior to today.
    """
    if not file_date:
        action = ObsidianPageCleanup()
    else:
        file_date = file_date.removesuffix(".md")
        action = ObsidianPageCleanup(file_date)

    action.run()
