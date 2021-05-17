""" Sources and actions to perform hourly """
import sqlite3
import click
from action.twitter import twitter
from source.Pinboard import pinboard
import exceptions


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from sources and action activations"""
    pinboard(details)

    db_con = sqlite3.connect("pinboard.db")
    db_con.row_factory = sqlite3.Row
    search_cur = db_con.cursor()
    for row in search_cur.execute(
        "SELECT * FROM posts WHERE posted_to_twitter=0 ORDER BY time"
    ):

        details.logger.info(f"Got {row['description']} and {row['href']}")
        try:
            twitter(details, row["description"], row["href"])
        except exceptions.TweetError as err:
            details.logger.error(err)
            raise SystemExit from err
        else:
            if not details.dry_run:
                update_cur = db_con.cursor()
                update_cur.execute(
                    "UPDATE posts SET posted_to_twitter=1 WHERE hash=?", [row["hash"]]
                )
                db_con.commit()
