"""Abstract base class for all ANNOTATION Actions"""

import logging
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from kmtools.exceptions import ActionError, ActionSkip
from kmtools.models import AnnotationStatus, HypothesisAnnotation, ProcessStatusEnum
from kmtools.util import database

logger = logging.getLogger(__name__)


class AnnotationActionBase:
    """Abstract Base Class for all ANNOTATION Actions"""

    action_name: str  # Each subclass should define this

    def __init__(self, retry_limit: int = 5) -> None:
        self.retry_limit: int = retry_limit

    def get_unprocessed_annotations(
        self, session: Session
    ) -> List[HypothesisAnnotation]:
        """For this action, retrieve resources with either no entry in ProcessStatus or with retries < retry limit."""
        # Start with a subquery where retries have been exceeded or process completed.
        # We will negate this in the subsequent query to get webresources where a
        # process has not started.
        subquery = (
            select(AnnotationStatus.annotation_id)
            .where(AnnotationStatus.action_name == self.action_name)
            .where(
                or_(
                    AnnotationStatus.status == ProcessStatusEnum.RETRIES_EXCEEDED,
                    AnnotationStatus.status == ProcessStatusEnum.COMPLETED,
                )
            )
        )

        resources: List[HypothesisAnnotation] = session.scalars(
            select(HypothesisAnnotation)
            .where(~HypothesisAnnotation.id.in_(subquery))
            .options(joinedload("*"))
        ).unique()

        return resources

    def run(self) -> None:
        """Process all unprocessed HypothesisAnnotation records."""

        with Session(database.engine, autoflush=False) as session:
            logging.debug(
                "Looking for unprocessed annotations for %s", self.__class__.__name__
            )
            annotations = self.get_unprocessed_annotations(session)

            for annotation in annotations:
                logging.info(
                    "(%s) Processing resource: %s",
                    self.__class__.__name__,
                    annotation.hyp_id,
                )

                # Get a process_status record, if one exists.
                annotation_status: Optional[AnnotationStatus] = (
                    session.query(AnnotationStatus)
                    .filter_by(
                        annotation_id=annotation.id, action_name=self.action_name
                    )
                    .first()
                )

                # If we've exceeded the retry limit for this resource, update the
                # process_status record and continue.
                if annotation_status and annotation_status.retries > self.retry_limit:
                    annotation_status.status = ProcessStatusEnum.RETRIES_EXCEEDED
                    annotation_status.processed_at = func.now()
                    session.commit()
                    logging.warning(
                        "Retries exceeded at %s for %s",
                        self.retry_limit,
                        annotation.hyp_id,
                    )
                    continue

                # When this is the first time we've tried to process a resource, create
                # a process_status record.
                if not annotation_status:
                    process_status = AnnotationStatus(
                        annotation_id=annotation.id,
                        action_name=self.action_name,
                        retries=0,
                    )
                    session.add(process_status)

                # Process the resource.
                try:
                    self.process(session, annotation)
                    process_status.status = ProcessStatusEnum.COMPLETED
                    logging.debug("Successful processed: %s", annotation.hyp_id)
                except ActionSkip as e:
                    logging.debug("Skipping process_table commit: %s", e)
                    session.rollback()
                    continue
                except ActionError as e:
                    process_status.retries += 1
                    process_status.status = ProcessStatusEnum.RETRYABLE
                    logging.warning(
                        "Process failed for %s. Retrying (%s/%s). Failed because: %s",
                        annotation.hyp_id,
                        process_status.retries,
                        self.retry_limit,
                        e.detail,
                    )

                process_status.processed_at = func.now()  # pylint:disable=not-callable
                session.commit()
                logging.debug(
                    "(%s) Done processing resource: %s",
                    self.__class__.__name__,
                    annotation.hyp_id,
                )

    def process(self, session: Session, annotation: HypothesisAnnotation) -> str:
        """To be implemented in subclass. Define the processing logic."""
        raise NotImplementedError


# def main():
#     database.Base.metadata.create_all(database.engine)
#     with Session(database.engine) as session:
#         new_pinboard = Pinboard(
#             hash="SampleHash",
#             href="https://dltj.org/article/ffmpeg-pipeline/",
#             title="Processing WOLFcon Conference Recordings with FFMPEG | Disruptive Library Technology Jester",
#             description="",
#             meta="b7c6324dd46577daf55ab12ab4fc7e74",
#             saved_timestamp=isoparse("2023-09-19T14:07:48+00:00"),
#             shared=VisibilityEnum.PUBLIC,
#             toread="0",
#             tags=["blue", "green"],
#         )
#         session.add(new_pinboard)
#         session.commit()

#         new_hyp_annotation, new_hyp_page = HypothesisAnnotation.create_with_page(
#             session,
#             "https://storage.courtlistener.com/recap/gov.uscourts.ca2.60988/gov.uscourts.ca2.60988.306.1.pdf",
#             "Opinion: Hachette Book Group, Inc. v. Internet Archive (23-1260), Court of Appeals for the Second Circuit",
#         )
#         new_hyp_page.shared = VisibilityEnum.PRIVATE
#         new_hyp_page.saved_timestamp = isoparse("2024-09-05T01:09:10.922094+00:00")

#         new_hyp_annotation.hyp_id = "dWaYZmsjEe-v6lvancUNFg"
#         new_hyp_annotation.annotation = '## Factor 4: "does not disprove market harm, and Publishers convincingly claim both present and future market harm"'
#         new_hyp_annotation.time_created = isoparse("2024-09-05T01:09:10.922094+00:00")
#         new_hyp_annotation.time_updated = isoparse("2024-09-05T01:09:10.922094+00:00")
#         new_hyp_annotation.quote = "In sum, IA has not met its “burden of proving that the secondary use doesnot compete in the relevant market[s].” Warhol I, 11 F.4th at 49. Its empiricalevidence does not disprove market harm, and Publishers convincingly claim bothpresent and future market harm. Any short-term public benefits of IA’s FreeDigital Library are outweighed not only by harm to Publishers and authors butalso by the long-term detriments society may suffer if IA’s infringing use wereallowed to continue. For these reasons, the fourth fair use factor favors Publisher"
#         new_hyp_annotation.tags = []
#         new_hyp_annotation.link_html = "https://hypothes.is/a/dWaYZmsjEe-v6lvancUNFg"
#         new_hyp_annotation.link_incontext = "https://hyp.is/dWaYZmsjEe-v6lvancUNFg/storage.courtlistener.com/recap/gov.uscourts.ca2.60988/gov.uscourts.ca2.60988.306.1.pdf"
#         new_hyp_annotation.shared = VisibilityEnum.PUBLIC
#         new_hyp_annotation.flagged = 0
#         session.commit()


# if __name__ == "__main__":
#     main()

#     # hash: Mapped[str] = mapped_column(String)
#     # href: Mapped[str] = mapped_column(String)
#     # title: Mapped[Optional[str]] = mapped_column("description", String, nullable=True)
#     # description: Mapped[Optional[str]] = mapped_column(
#     #     "extended", String, nullable=True
#     # )
#     # meta: Mapped[Optional[str]] = mapped_column(String, nullable=True)
#     # time: Mapped[str] = mapped_column(String)
#     # shared: Mapped[int] = mapped_column(Integer)
#     # toread: Mapped[int] = mapped_column(Integer)
#     # tags: Mapped[Optional[str]] = mapped_column(String, nullable=True)
