""" Sources and actions to perform hourly """
import click
import exceptions
from action import wayback
from source import hypothesis, pinboard

from command import summarize


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from origins and action activations"""

    pinboard.fetch(details)
    hypothesis.fetch(details)

    for action_name, action in details.actions.items():
        for origin_name, origin in details.origins.items():
            action_name = action_name.upper()
            origin_name = origin_name.upper()
            new_entries = origin.new_entries_handler(details, action.db_column)
            details.logger.info(
                f"Found {len(new_entries)} new entries from {origin_name} for {action_name}"
            )
            for row in new_entries:
                details.logger.debug(
                    f"New from {origin_name} for {action_name}: {row.title} ({row.href})"
                )
                try:
                    result = action.action_handler(
                        details, row.href, row.title, row.annotation_href
                    )
                except exceptions.KMException as err:
                    details.logger.error(err)
                    raise SystemExit from err
                origin.save_entry_handler(details, action.db_column, row.href, result)
                details.logger.info(
                    f"Successfully handled {row.href} from {origin_name} for {action_name}"
                )

    unsummarized_urls = pinboard.get_unsummarized(details)
    for url in unsummarized_urls:
        details.logger.debug(f"Getting summarization for {url}")
        derived_date, summarization = summarize.summarize(details, url)
        if derived_date:
            details.logger.debug(f"Saving derived date of {derived_date} for {url}")
            pinboard.save_entry(details, "derived_date", url, derived_date)
        if summarization:
            details.logger.debug(f"Saving summary for {url}")
            pinboard.save_entry(details, "summarization", url, summarization)

    unsummarized_urls = hypothesis.get_unsummarized(details)
    for url in unsummarized_urls:
        details.logger.debug(f"Getting summarization for {url}")
        derived_date, summarization = summarize.summarize(details, url)
        if derived_date:
            details.logger.debug(f"Saving derived date of {derived_date} for {url}")
            hypothesis.save_entry(details, "derived_date", url, derived_date)
        if summarization:
            details.logger.debug(f"Saving summary for {url}")
            hypothesis.save_entry(details, "summarization", url, summarization)

    # FIXME: These should probably be done in a "clean-up" on the actions
    wayback_jobs = hypothesis.get_wayback_jobs(details)
    details.logger.debug(
        f"Found {len(wayback_jobs)} Wayback job entries from HYPOTHESIS to check"
    )
    for row in wayback_jobs:
        details.logger.debug(f"Checking status of Wayback job {row}")
        results = wayback.check_job(details, row)
        if results and results.completed:
            hypothesis.save_entry(
                details, "archive_url", results.original_url, results.wayback_url
            )
            details.logger.info(
                f"{results.original_url} saved as {results.wayback_url}"
            )

    wayback_jobs = pinboard.get_wayback_jobs(details)
    details.logger.debug(
        f"Found {len(wayback_jobs)} Wayback job entries from PINBOARD to check"
    )
    for row in wayback_jobs:
        details.logger.debug(f"Checking status of Wayback job {row}")
        results = wayback.check_job(details, row)
        if results and results.completed:
            pinboard.save_entry(
                details, "archive_url", results.original_url, results.wayback_url
            )
            details.logger.info(
                f"{results.original_url} saved as {results.wayback_url}"
            )
