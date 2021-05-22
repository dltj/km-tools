""" Sources and actions to perform hourly """
import urllib
import sqlite3
import click
from action.twitter import twitter
from source.Pinboard import pinboard
import source.hypothesis as hypothesis
import exceptions


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from sources and action activations"""
    pinboard(details)
    hypothesis.fetch(details)

    new_hypothesis = hypothesis.get_new(details)
    for row in new_hypothesis:
        details.logger.info(f"New Hypothesis: {row[1]} ({row[0]})")
        via_url = f"https://via.hypothes.is/{row[0]}"
        try:
            tweet_id = twitter(details, row[1], row[0], via_url)
        except exceptions.TweetError as err:
            details.logger.error(err)
            raise SystemExit from err
        hypothesis.save_twitter(details, row[0], tweet_id)

    db_con = sqlite3.connect("pinboard.db")
    db_con.row_factory = sqlite3.Row
    search_cur = db_con.cursor()
    for row in search_cur.execute(
        "SELECT * FROM posts WHERE posted_to_twitter=0 AND shared=1 ORDER BY time"
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
