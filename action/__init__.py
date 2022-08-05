# import collections
import time
from abc import ABCMeta, abstractmethod
from logging import getLogger
from typing import Callable, List

from config import config
from source import Origin, Resource

logger = getLogger(__name__)


class Action(object):
    __metaclass__ = ABCMeta

    attributes_supplied = list()
    action_table = None

    def __init__(self) -> None:
        pass

    @abstractmethod
    def process_new(
        self, action_table: str, origin: Origin, url_action: Callable
    ) -> None:
        """Process entries that have not yet been processed by this action.

        :param origin: Instance of class Origin that we are processing

        :return: None
        """

        db = config.kmtools_db
        search_cur = db.cursor()
        query = (
            f"SELECT origin.{origin.origin_key} FROM {origin.origin_table} origin "
            f"LEFT JOIN {action_table} action ON action.url=origin.{origin.origin_key} "
            f"WHERE action.url IS NULL"
        )
        logger.debug(f"Executing {query=}")
        for row in search_cur.execute(query):
            logger.info(f"Now {row[origin.origin_key]} of {origin.origin_name}")
            source = origin.make_resource(uri=row[origin.origin_key])
            url_action(source=source)

    @abstractmethod
    def attribute_read(source: Resource, name: str) -> str:
        raise NotImplementedError("attribute_read not implemented")

    def _attribute_read(self, name: str, action_table: str, url: str) -> str:
        db = config.kmtools_db
        search_cur = db.cursor()
        query = f"SELECT {name} FROM {action_table} WHERE url LIKE ?"
        values = [url]
        logger.debug(f"{query=} for {values=}")
        search_cur.execute(query, values)
        result = search_cur.fetchone()[0]
        logger.debug(f"{result=}")
        return result

    def _save_attributes(
        self, source: Resource, columns: List[str], attributes: List[str]
    ) -> None:
        """Save the attributes from this action to the database.

        It is assumed that the order of the attributes is the same as the order
        of the columns in each respective list.  This function automatically
        calculates the placeholder string for the SQL INSERT command based on
        the number of values in the lists.  If the number of columns does not
        equal the number of attributes, an exception is raised.

        :param source: Instance of class Resource
        :param columns: list of columns to save

        :returns: None
        """
        if len(columns) != len(attributes):
            raise TypeError(
                "Number of values in 'columns' does not match number of values in 'attributes'."
            )
        db = config.kmtools_db
        insert_cur = db.cursor()
        sql_placeholders = f"{','.join('?' * len(attributes))}"
        query = f"INSERT INTO {self.action_table} (url, timestamp, origin, {', '.join(columns)}) VALUES (?, ?, ?,{sql_placeholders}) ON CONFLICT DO UPDATE SET ({', '.join(columns)}) = ({sql_placeholders}) WHERE url = ? AND origin = ?"
        values = [
            source.uri,
            time.time(),
            source.origin.origin_name,
        ]
        values = (
            values + attributes + attributes + [source.uri, source.origin.origin_name]
        )
        logger.debug(f"With {query=}, inserting {values=}")
        insert_cur.execute(query, values)
        db.commit()
