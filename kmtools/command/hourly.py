"""Sources and actions to perform hourly"""

import click

from kmtools.action.kagi_action import SummarizeWithKagiAction
from kmtools.action.mastodon_action import PostToMastodonAction
from kmtools.action.obsidian_hourly_action import SaveToObsidian
from kmtools.action.summarize_action import SummarizeAction
from kmtools.action.wayback_action import ResultsFromWaybackAction, SaveToWaybackAction
from kmtools.source import pinboard


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from origins and action activations"""

    pinboard.fetch(details)
    # hypothesis.fetch(details)

    actions = [
        ResultsFromWaybackAction(),
        SummarizeWithKagiAction(),
        SaveToWaybackAction(),
        SummarizeAction(),
        PostToMastodonAction(),
        SaveToObsidian(),
    ]

    for action in actions:
        action.run()

    # obsidian_hourly.obsidian_hourly_action.process_new(pinboard.pinboard_origin)
    # obsidian_hourly.obsidian_hourly_action.process_new(
    #     hypothesis.hypothesis_annotation_origin
    # )
