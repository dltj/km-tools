"""Add resources to the Obsidian database"""

import logging

from config import config
from source import Annotation, Origin, Resource
from source.obsidian_db import obsidiandb

from action import Action

logger = logging.getLogger(__name__)


class ObsidianHourly(Action):
    attributes_supplied = ["obsidian_filepath"]
    action_table = "action_obsidian"

    def __init__(self) -> None:
        super().__init__()

    def url_action(self, source: Resource) -> None:
        """
        Add the source to the Obsidian database

        :param source: Instance of class Resource

        :returns: None
        """
        if isinstance(source, Annotation):
            page_source = source.source
        else:
            page_source = source
        if page_source.origin.obsidian_tagless and len(page_source.tags) == 0:
            obsidian_filename = None
            obsidian_filepath = None
            logger.info(f"Tagless source {page_source.uri} not added to Obsidian")
            return

        obsidian_filepath, obsidian_filename = obsidiandb.init_source(page_source)

        if isinstance(source, Annotation):
            source.output_annotation(obsidian_filepath)

        logger.info(
            f"Successfully added {source.uri} to Obsidian as {obsidian_filename} ({obsidian_filepath})"
        )

        Action._save_attributes(
            self, source, self.attributes_supplied, [obsidian_filepath]
        )
        return

    def attribute_read(self, source: Resource, name: str) -> str:
        return Action._attribute_read(self, name, self.action_table, source.uri)

    def process_new(self, origin: Origin) -> None:
        """Process entries that have not yet been processed by this action.

        :param origin: Instance of class Origin that we are processing

        :return: None
        """

        Action.process_new(
            self,
            action_table=self.action_table,
            origin=origin,
            url_action=self.url_action,
        )


obsidian_hourly_action = ObsidianHourly()
config.actions.append(obsidian_hourly_action)
