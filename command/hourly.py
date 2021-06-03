""" Sources and actions to perform hourly """
import click
import action
from action.twitter import twitter
from action import wayback
from source import pinboard
from source import hypothesis
import exceptions


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from sources and action activations"""

    pinboard.fetch(details)
    hypothesis.fetch(details)

    for action_name, action_param in details.actions.items():
        for source_name, handler in details.dispatch.items():
            new_entries = handler.new_entries_handler(details, action_param.db_column)
            details.logger.info(
                f"Found {len(new_entries)} new entries from {source_name} for {action_name}"
            )
            for row in new_entries:
                details.logger.debug(
                    f"New from {source_name} for {action_name}: {row.title} ({row.href})"
                )
                try:
                    result = twitter(details, row.title, row.href, row.annotation_href)
                except exceptions.KMException as err:
                    details.logger.error(err)
                    raise SystemExit from err
                handler.save_entry_handler(
                    details, action_param.db_column, row.ident, result
                )
                details.logger.info(
                    f"Successfully handled {row.href} from {source_name} for {action_name}"
                )

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

    new_pinboard_archive = pinboard.new_wayback(details)
    details.logger.info(
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
