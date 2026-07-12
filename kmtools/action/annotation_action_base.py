"""Base class for actions that operate on HypothesisAnnotation records."""

import logging
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from kmtools.action.action_base import ActionBase
from kmtools.models import AnnotationStatus, HypothesisAnnotation, ProcessStatusEnum

logger = logging.getLogger(__name__)


class AnnotationActionBase(ActionBase[HypothesisAnnotation, AnnotationStatus]):
    """ActionBase wired to HypothesisAnnotation + AnnotationStatus."""

    def get_unprocessed(self, session: Session) -> List[HypothesisAnnotation]:
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
        return session.scalars(
            select(HypothesisAnnotation)
            .where(~HypothesisAnnotation.id.in_(subquery))
            .options(selectinload("*"))
        ).unique()

    def get_status(
        self, session: Session, annotation: HypothesisAnnotation
    ) -> Optional[AnnotationStatus]:
        return (
            session.query(AnnotationStatus)
            .filter_by(annotation_id=annotation.id, action_name=self.action_name)
            .first()
        )

    def make_status(self, annotation: HypothesisAnnotation) -> AnnotationStatus:
        return AnnotationStatus(
            annotation_id=annotation.id,
            action_name=self.action_name,
            status=ProcessStatusEnum.RETRYABLE,
            retries=0,
        )

    def get_resource_label(self, annotation: HypothesisAnnotation) -> str:
        return annotation.hyp_id
