""" Sources and actions to perform hourly """
import click
from action.twitter import twitter
from action import wayback
from source import pinboard
from source import hypothesis
import exceptions


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from sources and action activations"""

    hypothesis.fetch(details)

    new_hypothesis_twitter = hypothesis.new_twitter(details)
    details.logger.debug(
        f"Found {len(new_hypothesis_twitter)} new entries from Hypothesis for Twitter"
    )
    for row in new_hypothesis_twitter:
        details.logger.debug(f"New Hypothesis: {row[1]} ({row[0]})")
        via_url = f"https://via.hypothes.is/{row[0]}"
        try:
            tweet_id = twitter(details, row[1], row[0], via_url)
        except exceptions.TweetError as err:
            details.logger.error(err)
            raise SystemExit from err
        hypothesis.save_twitter(details, row[0], tweet_id)
        details.logger.info(f"Successfully tweeted about {row[1]}")

    new_hypothesis_archive = hypothesis.new_wayback(details)
    details.logger.debug(
        f"Found {len(new_hypothesis_archive)} new entries from Hypothesis for Wayback"
    )
    for row in new_hypothesis_archive:
        details.logger.debug(f"New Hypothesis for Wayback: {row}")
        try:
            wayback_job_id = wayback.save_url(details, row)
        except exceptions.WaybackError as err:
            details.logger.error(err)
            raise SystemExit from err
        hypothesis.save_wayback(details, row, wayback_job_id)
        details.logger.info(f"Started Wayback archive of {row} as job {wayback_job_id}")

    wayback_jobs = hypothesis.get_wayback_jobs(details)
    details.logger.debug(f"Found {len(wayback_jobs)} Wayback job entries to check")
    for row in wayback_jobs:
        details.logger.debug(f"Checking status of Wayback job {row}")
        results = wayback.check_job(details, row)
        if results and results.completed:
            hypothesis.save_wayback(details, results.original_url, results.wayback_url)
            details.logger.info(
                f"{results.original_url} saved as {results.wayback_url}"
            )

    pinboard.fetch(details)

    new_pinboard_twitter = pinboard.new_twitter(details)
    details.logger.debug(
        f"Found {len(new_pinboard_twitter)} new entries from Pinboard for Twitter"
    )
    for row in new_pinboard_twitter:
        details.logger.debug(f"New bookmark to tweet: {row.description} ({row.href})")
        try:
            tweet_id = twitter(details, row.description, row.href)
        except exceptions.TweetError as err:
            details.logger.error(err)
            raise SystemExit from err
        pinboard.save_twitter(details, row.hash_value, tweet_id)
        details.logger.info(f"Successfully tweeted about {row.href}")

    new_pinboard_archive = pinboard.new_wayback(details)
    details.logger.debug(
        f"Found {len(new_hypothesis_archive)} new entries from Pinboard for Wayback"
    )
    for row in new_pinboard_archive:
        details.logger.debug(f"New Pinboard for Wayback: {row}")
        try:
            wayback_job_id = wayback.save_url(details, row)
        except exceptions.WaybackError as err:
            details.logger.error(err)
            raise SystemExit from err
        pinboard.save_wayback(details, row, wayback_job_id)
        details.logger.info(f"Started Wayback archive of {row} as job {wayback_job_id}")

    wayback_jobs = pinboard.get_wayback_jobs(details)
    details.logger.debug(f"Found {len(wayback_jobs)} Wayback job entries to check")
    for row in wayback_jobs:
        details.logger.debug(f"Checking status of Wayback job {row}")
        results = wayback.check_job(details, row)
        if results and results.completed:
            pinboard.save_wayback(details, results.original_url, results.wayback_url)
            details.logger.info(
                f"{results.original_url} saved as {results.wayback_url}"
            )
