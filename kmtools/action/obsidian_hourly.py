"""Add resources to the Obsidian database"""

import logging

from kmtools.action import Action
from kmtools.source import Annotation, Origin, Resource
from kmtools.source.obsidian_db import obsidiandb
from kmtools.util.config import config

logger = logging.getLogger(__name__)


class ObsidianHourly(Action):
    """Class representing the Obsidian Hourly Action"""

    key_attribute = "obsidian_filepath"
    additional_attributes = list()
    attributes_supplied = ["obsidian_filepath"]
    action_table = "action_obsidian"

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
            obsidian_filepath = "No tags"
            logger.info("Tagless source %s not added to Obsidian", page_source.uri)
        else:
            obsidian_filepath, obsidian_filename = obsidiandb.init_source(page_source)
            if isinstance(source, Annotation):
                source.output_annotation(obsidian_filepath)
            logger.info(
                "Successfully added %s to Obsidian as %s (%s)",
                source.uri,
                obsidian_filename,
                obsidian_filepath,
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
