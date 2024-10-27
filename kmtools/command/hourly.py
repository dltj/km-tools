""" Sources and actions to perform hourly """

import click

from kmtools import action
from kmtools.action import obsidian_hourly
from kmtools.source import hypothesis, pinboard
from kmtools.util.config import config


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from origins and action activations"""

    pinboard.fetch(details)
    hypothesis.fetch(details)

    action.wayback.wayback_action.update_jobs()

    for origin in config.origins:
        action.summarize.summarize_action.process_new(origin)
        action.kagi.kagi_action.process_new(origin)
        action.mastodon.mastodon_action.process_new(origin)
        action.wayback.wayback_action.process_new(origin)

    obsidian_hourly.obsidian_hourly_action.process_new(pinboard.pinboard_origin)
    obsidian_hourly.obsidian_hourly_action.process_new(
        hypothesis.hypothesis_annotation_origin
    )
