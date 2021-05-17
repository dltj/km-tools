import sqlite3
import click
from TwitterAPI import TwitterAPI


def twitter(details):
    """Post to Twitter"""
    twiter_api = TwitterAPI(
        details.config.twitter.consumer_key,
        details.config.twitter.consumer_secret,
        details.config.twitter.access_token_key,
        details.config.twitter.access_token_secret,
    )

    # Get the number of characters a Twitter-shortened URL will take up
    r = twiter_api.request("help/configuration")
    twitter_config = r.json()
    short_url_length = twitter_config["short_url_length_https"]

    db_con = sqlite3.connect("pinboard.db")
    db_con.row_factory = sqlite3.Row
    search_cur = db_con.cursor()
    for row in search_cur.execute(
        "SELECT * FROM posts WHERE posted_to_twitter=0 ORDER BY time"
    ):
        url_length = short_url_length if len(row[1]) > short_url_length else len(row[1])
        meta_text = 4
        text_length = 280 - url_length - meta_text
        tweet_text = f"🔖 {row['description'][:text_length]} {row['href']}"
        if not details.dry_run:
            r = twiter_api.request("statuses/update", {"status": tweet_text})
            if r.status_code == 200:
                click.echo("SUCCESS")
                update_cur = db_con.cursor()
                update_cur.execute(
                    "UPDATE posts SET posted_to_twitter=1 WHERE hash=?", [row["hash"]]
                )
                db_con.commit()
            else:
                click.echo("PROBLEM: " + r.text)
        else:
            click.echo(f"Would have tweeted: {tweet_text}")
