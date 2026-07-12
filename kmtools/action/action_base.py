"""Abstract base class for all Actions"""

import logging
from abc import abstractmethod
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session

from kmtools.exceptions import ActionError, ActionSkip
from kmtools.models import ProcessStatusEnum
from kmtools.util.database import get_session

logger = logging.getLogger(__name__)

ResourceT = TypeVar("ResourceT")
StatusT = TypeVar("StatusT")


class ActionBase(Generic[ResourceT, StatusT]):
    """Abstract Base Class for all Actions.

    Subclasses must define:
        - action_name: str
        - get_unprocessed(session) -> List[ResourceT]
        - get_status(session, resource) -> Optional[StatusT]
        - make_status(resource) -> StatusT
        - get_resource_label(resource) -> str  (for logging)
        - process(session, resource) -> None
    And the status model must have:
        - .status, .retries, .processed_at  attributes
    """

    action_name: str

    def __init__(self, retry_limit: int = 5) -> None:
        self.retry_limit = retry_limit

    # -- Methods subclasses must implement --

    @abstractmethod
    def get_unprocessed(self, session: Session) -> List[ResourceT]:
        """Return resources that have not yet been successfully processed."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, session: Session, resource: ResourceT) -> Optional[StatusT]:
        """Return the existing status record for this resource, or None."""
        raise NotImplementedError

    @abstractmethod
    def make_status(self, resource: ResourceT) -> StatusT:
        """Create a new (unsaved) status record for this resource."""
        raise NotImplementedError

    @abstractmethod
    def get_resource_label(self, resource: ResourceT) -> str:
        """Return a human-readable identifier for the resource (for logging)."""
        raise NotImplementedError

    @abstractmethod
    def process(self, session: Session, resource: ResourceT) -> None:
        """Perform the action on a single resource. Raise ActionError or ActionSkip as needed."""
        raise NotImplementedError

    # -- The shared run loop --

    def run(self) -> None:
        """Process all unprocessed resources."""
        with get_session() as session:
            logger.debug(
                "Looking for unprocessed resources for %s", self.__class__.__name__
            )
            resources = self.get_unprocessed(session)

            for resource in resources:
                label = self.get_resource_label(resource)
                logger.info("(%s) Processing: %s", self.__class__.__name__, label)

                status: Optional[StatusT] = self.get_status(session, resource)

                if status and status.retries > self.retry_limit:
                    status.status = ProcessStatusEnum.RETRIES_EXCEEDED
                    status.processed_at = func.now()
                    session.commit()
                    logger.warning(
                        "Retries exceeded at %s for %s", self.retry_limit, label
                    )
                    continue

                if not status:
                    status = self.make_status(resource)
                    session.add(status)

                try:
                    self.process(session, resource)
                    status.status = ProcessStatusEnum.COMPLETED
                    logger.debug("Successfully processed: %s", label)
                except ActionSkip as e:
                    logger.debug("Skipping %s: %s", label, e)
                    session.rollback()
                    continue
                except ActionError as e:
                    status.retries += 1
                    status.status = ProcessStatusEnum.RETRYABLE
                    logger.warning(
                        "Process failed for %s. Retry %s/%s. Reason: %s",
                        label,
                        status.retries,
                        self.retry_limit,
                        e.detail,
                    )

                status.processed_at = func.now()
                session.commit()
                logger.debug("(%s) Done: %s", self.__class__.__name__, label)
