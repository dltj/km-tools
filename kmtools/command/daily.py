"""Actions that are performed daily."""

import click

from kmtools.action.obsidian_daily_action import AddToObsidianDaily, SetupObsidianDaily


@click.command()
@click.pass_obj
def daily(_):
    """Perform the daily activities"""

    actions = [
        SetupObsidianDaily(),
        AddToObsidianDaily(),
    ]

    for action in actions:
        action.run()
