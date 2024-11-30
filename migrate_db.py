#!/bin/env python
"""Migrate from the old database schema to the new."""

import datetime as DT
import logging
import sqlite3

from dateutil.parser import isoparse
from sqlalchemy import select
from sqlalchemy.orm import Session

from kmtools.models import (
    ActionKagi,
    ActionMastodon,
    ActionObsidianDaily,
    ActionObsidianHourly,
    ActionSummary,
    ActionWayback,
    HypothesisAnnotation,
    HypothesisPage,
    Pinboard,
    ProcessStatus,
    ProcessStatusEnum,
    VisibilityEnum,
)
from kmtools.util import database

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

migration_start_timestamp = DT.datetime.now()

kmtools_db_conn = sqlite3.connect("kmtools—prior to migration.sqlite3")
kmtools_db_conn.row_factory = sqlite3.Row
kmtools_db_conn.execute("BEGIN EXCLUSIVE")
kmtools_db_conn.set_trace_callback(logger.debug)

wayback_cur = kmtools_db_conn.cursor()
summary_cur = kmtools_db_conn.cursor()
mastodon_cur = kmtools_db_conn.cursor()
kagi_cur = kmtools_db_conn.cursor()
obsidian_hourly_cur = kmtools_db_conn.cursor()
obsidian_daily_cur = kmtools_db_conn.cursor()

database.Base.metadata.create_all(database.engine)


def add_other_records(session, new_resource_href, new_resource_object):
    wayback_query = "select * from action_wayback where url=?"
    wayback_cur.execute(wayback_query, [new_resource_href])
    wayback_rows = wayback_cur.fetchall()
    if len(wayback_rows) == 0:
        print(f"No rows found for {new_resource_href} in wayback table")
    else:
        wayback_row = wayback_rows[0]
        if not wayback_row["wayback_url"] == "https://web.archive.org/":
            new_wayback = ActionWayback(resource=new_resource_object)
            new_wayback.wayback_url = wayback_row["wayback_url"]
            new_wayback.wayback_timestamp = wayback_row["wayback_timestamp"]
            new_wayback.wayback_details = wayback_row["wayback_details"]
            wayback_record_timestamp = DT.datetime.fromtimestamp(
                wayback_row["timestamp"], DT.timezone.utc
            )
            new_wayback.processed_at = wayback_record_timestamp
            session.add(new_wayback)
        else:
            wayback_record_timestamp = migration_start_timestamp
        new_wayback_process_status_save = ProcessStatus(resource=new_resource_object)
        new_wayback_process_status_save.action_name = "WaybackSaveAction"
        new_wayback_process_status_save.status = ProcessStatusEnum.COMPLETED
        new_wayback_process_status_save.processed_at = wayback_record_timestamp
        new_wayback_process_status_save.retries = "-1"
        session.add(new_wayback_process_status_save)
        new_wayback_process_status_retr = ProcessStatus(resource=new_resource_object)
        new_wayback_process_status_retr.action_name = "WaybackResultsAction"
        new_wayback_process_status_retr.status = ProcessStatusEnum.COMPLETED
        new_wayback_process_status_retr.processed_at = wayback_record_timestamp
        new_wayback_process_status_retr.retries = "-1"
        session.add(new_wayback_process_status_retr)
        session.commit()

    summary_query = "select * from action_summary where url=?"
    summary_cur.execute(summary_query, [new_resource_href])
    summary_rows = summary_cur.fetchall()
    if len(summary_rows) == 0:
        print(f"No rows found for {new_resource_href} in summary table")
    else:
        summary_row = summary_rows[0]
        if (
            not summary_row["summary"] == "old"
            and summary_row["summary"] is not None
            and summary_row["summary"] != ""
        ):
            new_summary = ActionSummary(resource=new_resource_object)
            new_summary.derived_date = summary_row["derived_date"]
            new_summary.summary = summary_row["summary"]
            summary_record_timestamp = DT.datetime.fromtimestamp(
                summary_row["timestamp"], DT.timezone.utc
            )
            new_summary.processed_at = summary_record_timestamp
            session.add(new_summary)
        else:
            summary_record_timestamp = migration_start_timestamp
        new_summary_process_status = ProcessStatus(resource=new_resource_object)
        new_summary_process_status.action_name = "SummarizeAction"
        new_summary_process_status.status = ProcessStatusEnum.COMPLETED
        new_summary_process_status.processed_at = summary_record_timestamp
        new_summary_process_status.retries = "-1"
        session.add(new_summary_process_status)
        session.commit()

    mastodon_query = "select * from action_mastodon where url=?"
    mastodon_cur.execute(mastodon_query, [new_resource_href])
    mastodon_rows = mastodon_cur.fetchall()
    if len(mastodon_rows) == 0:
        print(f"No rows found for {new_resource_href} in mastodon table")
    else:
        mastodon_row = mastodon_rows[0]
        if not mastodon_row["toot_url"] == "old":
            new_mastodon = ActionMastodon(resource=new_resource_object)
            new_mastodon.toot_uri = mastodon_row["toot_url"]
            mastodon_record_timestamp = DT.datetime.fromtimestamp(
                mastodon_row["timestamp"], DT.timezone.utc
            )
            new_mastodon.processed_at = mastodon_record_timestamp
            session.add(new_mastodon)
        else:
            mastodon_record_timestamp = migration_start_timestamp
        new_mastodon_process_status = ProcessStatus(resource=new_resource_object)
        new_mastodon_process_status.action_name = "MastodonAction"
        new_mastodon_process_status.status = ProcessStatusEnum.COMPLETED
        new_mastodon_process_status.processed_at = mastodon_record_timestamp
        new_mastodon_process_status.retries = "-1"
        session.add(new_mastodon_process_status)
        session.commit()

    kagi_query = "select * from action_kagi where url=?"
    kagi_cur.execute(kagi_query, [new_resource_href])
    kagi_rows = kagi_cur.fetchall()
    if len(kagi_rows) == 0:
        print(f"No rows found for {new_resource_href} in kagi table")
    else:
        kagi_row = kagi_rows[0]
        if not kagi_row["kagi_summary"] == "old":
            new_kagi = ActionKagi(resource=new_resource_object)
            new_kagi.kagi_summary = kagi_row["kagi_summary"]
            kagi_record_timestamp = DT.datetime.fromtimestamp(
                kagi_row["timestamp"], DT.timezone.utc
            )
            new_kagi.processed_at = kagi_record_timestamp
            session.add(new_kagi)
        else:
            kagi_record_timestamp = migration_start_timestamp
        new_kagi_process_status = ProcessStatus(resource=new_resource_object)
        new_kagi_process_status.action_name = "KagiAction"
        new_kagi_process_status.status = ProcessStatusEnum.COMPLETED
        new_kagi_process_status.processed_at = kagi_record_timestamp
        new_kagi_process_status.retries = "-1"
        session.add(new_kagi_process_status)
        session.commit()

    obsidian_hourly_query = "select * from action_obsidian where url=?"
    obsidian_hourly_cur.execute(obsidian_hourly_query, [new_resource_href])
    obsidian_hourly_rows = obsidian_hourly_cur.fetchall()
    if len(obsidian_hourly_rows) == 0:
        print(f"No rows found for {new_resource_href} in obsidian_hourly table")
    else:
        obsidian_hourly_row = obsidian_hourly_rows[0]
        if (
            not obsidian_hourly_row["obsidian_filepath"] == "old"
            and obsidian_hourly_row["obsidian_filepath"] is not None
            and obsidian_hourly_row["obsidian_filepath"] != ""
        ):
            new_obsidian_hourly = ActionObsidianHourly(resource=new_resource_object)
            new_obsidian_hourly.filename = obsidian_hourly_row["obsidian_filepath"]
            obsidian_hourly_record_timestamp = DT.datetime.fromtimestamp(
                obsidian_hourly_row["timestamp"], DT.timezone.utc
            )
            new_obsidian_hourly.processed_at = obsidian_hourly_record_timestamp
            session.add(new_obsidian_hourly)
        else:
            obsidian_hourly_record_timestamp = migration_start_timestamp
        new_obsidian_hourly_process_status = ProcessStatus(resource=new_resource_object)
        new_obsidian_hourly_process_status.action_name = "ObsidianHourlyAction"
        new_obsidian_hourly_process_status.status = ProcessStatusEnum.COMPLETED
        new_obsidian_hourly_process_status.processed_at = (
            obsidian_hourly_record_timestamp
        )
        new_obsidian_hourly_process_status.retries = "-1"
        session.add(new_obsidian_hourly_process_status)
        session.commit()

    obsidian_daily_query = "select * from action_obsidian where url=?"
    obsidian_daily_cur.execute(obsidian_daily_query, [new_resource_href])
    obsidian_daily_rows = obsidian_daily_cur.fetchall()
    if len(obsidian_daily_rows) == 0:
        print(f"No rows found for {new_resource_href} in obsidian_daily table")
    else:
        obsidian_daily_row = obsidian_daily_rows[0]
        if (
            not obsidian_daily_row["obsidian_daily_filepath"] == "old"
            and obsidian_daily_row["obsidian_daily_filepath"] != None
        ):
            new_obsidian_daily = ActionObsidianDaily(resource=new_resource_object)
            new_obsidian_daily.daily_filename = obsidian_daily_row[
                "obsidian_daily_filepath"
            ]
            obsidian_daily_record_timestamp = DT.datetime.fromtimestamp(
                obsidian_daily_row["timestamp"], DT.timezone.utc
            )
            new_obsidian_daily.processed_at = obsidian_daily_record_timestamp
            session.add(new_obsidian_daily)
        else:
            obsidian_daily_record_timestamp = migration_start_timestamp
        new_obsidian_daily_process_status = ProcessStatus(resource=new_resource_object)
        new_obsidian_daily_process_status.action_name = "ObsidianDailyAction"
        new_obsidian_daily_process_status.status = ProcessStatusEnum.COMPLETED
        new_obsidian_daily_process_status.processed_at = obsidian_daily_record_timestamp
        new_obsidian_daily_process_status.retries = "-1"
        session.add(new_obsidian_daily_process_status)
        session.commit()


def create_hypothesis(session, hrow):
    new_hype_page = False
    hstmt = select(HypothesisPage).where(HypothesisPage.href == hrow["uri"])
    hyp_page = session.execute(hstmt).scalars().first()
    if not hyp_page:
        hyp_page = HypothesisPage(
            href=hrow["uri"],
            title=hrow["document_title"],
            saved_timestamp=isoparse(hrow["created"]),
        )
        if hrow["hidden"]:
            hyp_page.shared = VisibilityEnum.PRIVATE
        else:
            hyp_page.shared = VisibilityEnum.PUBLIC

        session.add(hyp_page)
        session.commit()
        new_hype_page = True

    new_hypothesis = HypothesisAnnotation(
        hyp_id=hrow["id"],
        page_id=hyp_page.id,
        annotation=hrow["annotation"],
        time_created=isoparse(hrow["created"]),
        time_updated=isoparse(hrow["updated"]),
        quote=hrow["quote"],
        _tags=hrow["tags"],
        document_title=hrow["document_title"],
        link_html=hrow["link_html"],
        link_incontext=hrow["link_incontext"],
        flagged=hrow["flagged"],
    )
    if hrow["hidden"]:
        new_hypothesis.shared = VisibilityEnum.PRIVATE
    else:
        new_hypothesis.shared = VisibilityEnum.PUBLIC
        hyp_page.shared = VisibilityEnum.PUBLIC
    session.add(new_hypothesis)
    session.commit()
    if new_hype_page:
        return hyp_page
    return None


def create_pinboard(session, prow):
    new_pinboard = Pinboard(
        hash=prow["hash"],
        href=prow["href"],
        title=prow["description"],
        description=prow["extended"],
        meta=prow["meta"],
        saved_timestamp=isoparse(prow["time"]),
        toread=prow["toread"],
        _tags=prow["tags"],
    )
    if prow["shared"]:
        new_pinboard.shared = VisibilityEnum.PUBLIC
    else:
        new_pinboard.shared = VisibilityEnum.PRIVATE
    session.add(new_pinboard)
    session.commit()
    return new_pinboard


with Session(database.engine) as session:
    database.Base.metadata.create_all(database.engine)
    pinboard_cur = kmtools_db_conn.cursor()
    hypothesis_cur = kmtools_db_conn.cursor()

    hypothesis_query = "select * from hyp_posts order by created"
    hypothesis_cur.execute(hypothesis_query)
    hypothesis_records = hypothesis_cur.fetchall()

    pinboard_query = "select * from pinb_posts order by time"
    pinboard_cur.execute(pinboard_query)
    pinboard_records = pinboard_cur.fetchall()

    i, j = 0, 0

    while i < len(pinboard_records) and j < len(hypothesis_records):
        pinboard_date = isoparse(pinboard_records[i]["time"])
        hypothesis_date = isoparse(hypothesis_records[j]["created"])
        new_resource = None
        if pinboard_date <= hypothesis_date:
            new_resource = create_pinboard(session, pinboard_records[i])
            url = pinboard_records[i]["href"]
            i += 1
        else:
            new_resource = create_hypothesis(session, hypothesis_records[j])
            url = hypothesis_records[j]["uri"]
            j += 1
        if new_resource:
            add_other_records(session, url, new_resource)

    # If there are remaining items in either list, add them to the merged list
    for row in pinboard_records[i:]:
        new_resource = create_pinboard(session, row)
        url = row["href"]
        add_other_records(session, url, new_resource)

    for row in hypothesis_records[j:]:
        new_resource = create_hypothesis(session, row)
        url = row["href"]
        if new_resource:
            add_other_records(session, url, new_resource)
