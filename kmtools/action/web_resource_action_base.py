"""Base class for actions that operate on WebResource records."""

import logging
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from kmtools.action.action_base import ActionBase
from kmtools.models import ProcessStatus, ProcessStatusEnum, WebResource

logger = logging.getLogger(__name__)


class WebResourceActionBase(ActionBase[WebResource, ProcessStatus]):
    """ActionBase wired to WebResource + ProcessStatus."""

    def get_unprocessed(self, session: Session) -> List[WebResource]:
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
        return session.scalars(
            select(WebResource)
            .where(~WebResource.id.in_(subquery))
            .options(selectinload("*"))
        ).unique()

    def get_status(
        self, session: Session, resource: WebResource
    ) -> Optional[ProcessStatus]:
        return (
            session.query(ProcessStatus)
            .filter_by(resource_id=resource.id, action_name=self.action_name)
            .first()
        )

    def make_status(self, resource: WebResource) -> ProcessStatus:
        return ProcessStatus(
            resource_id=resource.id,
            action_name=self.action_name,
            status=ProcessStatusEnum.RETRYABLE,
            retries=0,
        )

    def get_resource_label(self, resource: WebResource) -> str:
        return resource.href
