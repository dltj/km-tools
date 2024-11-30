"""Abstract base class for all Actions"""

import logging
from typing import List, Optional

from dateutil.parser import isoparse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from kmtools.exceptions import ActionError, ActionSkip
from kmtools.models import (
    HypothesisAnnotation,
    Pinboard,
    ProcessStatus,
    ProcessStatusEnum,
    VisibilityEnum,
    WebResource,
)
from kmtools.util import database

logger = logging.getLogger(__name__)


class ActionBase:
    """Abstract Base Class for all Actions"""

    action_name: str  # Each subclass should define this

    def __init__(self, retry_limit: int = 5) -> None:
        self.retry_limit: int = retry_limit

    def get_unprocessed_resources(self, session: Session) -> List[WebResource]:
        """For this action, retrieve resources with either no entry in ProcessStatus or with retries < retry limit."""
        # Start with a subquery where retries have been exceeded or process completed.
        # We will negate this in the subsequent query to get webresources where a
        # process has not started.
        subquery = (
            select(ProcessStatus.resource_id)
            .where(ProcessStatus.action_name == self.action_name)
            .where(
                or_(
                    ProcessStatus.status == ProcessStatusEnum.RETRIES_EXCEEDED,
                    ProcessStatus.status == ProcessStatusEnum.COMPLETED,
                )
            )
        )

        resources: List[WebResource] = session.scalars(
            select(WebResource)
            .where(~WebResource.id.in_(subquery))
            .options(joinedload("*"))
        ).unique()

        return resources

    def run(self) -> None:
        """Process all unprocessed WebResources."""

        with Session(database.engine, autoflush=False) as session:
            logging.debug(
                "Looking for unprocessed resources for %s", self.__class__.__name__
            )
            resources = self.get_unprocessed_resources(session)

            for resource in resources:
                logging.info(
                    "(%s) Processing resource: %s",
                    self.__class__.__name__,
                    resource.href,
                )

                # Get a process_status record, if one exists.
                process_status: Optional[ProcessStatus] = (
                    session.query(ProcessStatus)
                    .filter_by(resource_id=resource.id, action_name=self.action_name)
                    .first()
                )

                # If we've exceeded the retry limit for this resource, update the
                # process_status record and continue.
                if process_status and process_status.retries > self.retry_limit:
                    process_status.status = ProcessStatusEnum.RETRIES_EXCEEDED
                    process_status.processed_at = func.now()
                    session.commit()
                    logging.warning(
                        "Retries exceeded at %s for %s", self.retry_limit, resource.url
                    )
                    continue

                # When this is the first time we've tried to process a resource, create
                # a process_status record.
                if not process_status:
                    process_status = ProcessStatus(
                        resource_id=resource.id,
                        action_name=self.action_name,
                        retries=0,
                    )
                    session.add(process_status)

                # Process the resource.
                try:
                    self.process(session, resource)
                    process_status.status = ProcessStatusEnum.COMPLETED
                    logging.debug("Successful processed: %s", resource.href)
                except ActionSkip as e:
                    logging.debug("Skipping process_table commit: %s", e)
                    session.rollback()
                    continue
                except ActionError as e:
                    process_status.retries += 1
                    process_status.status = ProcessStatusEnum.RETRYABLE
                    logging.warning(
                        "Process failed for %s. Retrying (%s/%s). Failed because: %s",
                        resource.href,
                        process_status.retries,
                        self.retry_limit,
                        e.detail,
                    )

                process_status.processed_at = func.now()  # pylint:disable=not-callable
                session.commit()
                logging.debug(
                    "(%s) Done processing resource: %s",
                    self.__class__.__name__,
                    resource.href,
                )

    def process(self, session: Session, resource: WebResource) -> str:
        """To be implemented in subclass. Define the processing logic."""
        raise NotImplementedError


def main():
    database.Base.metadata.create_all(database.engine)
    with Session(database.engine) as session:
        new_pinboard = Pinboard(
            hash="SampleHash",
            href="https://dltj.org/article/ffmpeg-pipeline/",
            title="Processing WOLFcon Conference Recordings with FFMPEG | Disruptive Library Technology Jester",
            description="",
            meta="b7c6324dd46577daf55ab12ab4fc7e74",
            saved_timestamp=isoparse("2023-09-19T14:07:48+00:00"),
            shared=VisibilityEnum.PUBLIC,
            toread="0",
            tags=["blue", "green"],
        )
        session.add(new_pinboard)
        session.commit()

        new_hyp_annotation, new_hyp_page = HypothesisAnnotation.create_with_page(
            session,
            "https://storage.courtlistener.com/recap/gov.uscourts.ca2.60988/gov.uscourts.ca2.60988.306.1.pdf",
            "Opinion: Hachette Book Group, Inc. v. Internet Archive (23-1260), Court of Appeals for the Second Circuit",
        )
        new_hyp_page.shared = VisibilityEnum.PRIVATE
        new_hyp_page.saved_timestamp = isoparse("2024-09-05T01:09:10.922094+00:00")

        new_hyp_annotation.hyp_id = "dWaYZmsjEe-v6lvancUNFg"
        new_hyp_annotation.annotation = '## Factor 4: "does not disprove market harm, and Publishers convincingly claim both present and future market harm"'
        new_hyp_annotation.time_created = isoparse("2024-09-05T01:09:10.922094+00:00")
        new_hyp_annotation.time_updated = isoparse("2024-09-05T01:09:10.922094+00:00")
        new_hyp_annotation.quote = "In sum, IA has not met its “burden of proving that the secondary use doesnot compete in the relevant market[s].” Warhol I, 11 F.4th at 49. Its empiricalevidence does not disprove market harm, and Publishers convincingly claim bothpresent and future market harm. Any short-term public benefits of IA’s FreeDigital Library are outweighed not only by harm to Publishers and authors butalso by the long-term detriments society may suffer if IA’s infringing use wereallowed to continue. For these reasons, the fourth fair use factor favors Publisher"
        new_hyp_annotation.tags = []
        new_hyp_annotation.link_html = "https://hypothes.is/a/dWaYZmsjEe-v6lvancUNFg"
        new_hyp_annotation.link_incontext = "https://hyp.is/dWaYZmsjEe-v6lvancUNFg/storage.courtlistener.com/recap/gov.uscourts.ca2.60988/gov.uscourts.ca2.60988.306.1.pdf"
        new_hyp_annotation.shared = VisibilityEnum.PUBLIC
        new_hyp_annotation.flagged = 0
        session.commit()


if __name__ == "__main__":
    main()

    # hash: Mapped[str] = mapped_column(String)
    # href: Mapped[str] = mapped_column(String)
    # title: Mapped[Optional[str]] = mapped_column("description", String, nullable=True)
    # description: Mapped[Optional[str]] = mapped_column(
    #     "extended", String, nullable=True
    # )
    # meta: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # time: Mapped[str] = mapped_column(String)
    # shared: Mapped[int] = mapped_column(Integer)
    # toread: Mapped[int] = mapped_column(Integer)
    # tags: Mapped[Optional[str]] = mapped_column(String, nullable=True)
