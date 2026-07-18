"""All Application models"""

import enum
import json
import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from kmtools.util.database import Base

logger = logging.getLogger(__name__)

docdrop_url_scan = re.compile(
    r"""^https?://docdrop.org/video/(.*?)/?$          # YouTube video id (group 1)
""",
    re.X,
)
dltjvid_url_scan = re.compile(
    r"https?://media.dltj.org/annotated-video/[\dT]+-([0-9A-Za-z_-]{10}[048AEIMQUYcgkosw])-"
)


class ProcessStatusEnum(enum.Enum):
    """Enumerated list of possible process statuses."""

    COMPLETED = "COMPLETED"
    RETRIES_EXCEEDED = "RETRIES_EXCEEDED"
    RETRYABLE = "RETRYABLE"


class VisibilityEnum(enum.Enum):
    """Enumerated list of visibility settings."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class WebResource(Base):
    __tablename__ = "webresource"
    __mapper_args__ = {
        "polymorphic_identity": "webresource",
        "polymorphic_on": "discriminator",
    }
    id: Mapped[int] = mapped_column(primary_key=True)
    discriminator: Mapped[str] = mapped_column(String)
    href: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    saved_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    _headline: Optional[str] = None
    _publisher: Optional[str] = None

    @declared_attr
    def process_status(cls) -> Mapped[List["ProcessStatus"]]:
        return relationship(
            "ProcessStatus", back_populates="resource", cascade="all, delete-orphan"
        )

    @declared_attr
    def action_summary(cls) -> Mapped["ActionSummary"]:
        return relationship(
            "ActionSummary",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @declared_attr
    def action_mastodon(cls) -> Mapped["ActionMastodon"]:
        return relationship(
            "ActionMastodon",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @declared_attr
    def action_wayback(cls) -> Mapped["ActionWayback"]:
        return relationship(
            "ActionWayback",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @declared_attr
    def action_kagi(cls) -> Mapped["ActionKagi"]:
        return relationship(
            "ActionKagi",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @declared_attr
    def action_obsidian_hourly(cls) -> Mapped["ActionObsidianHourly"]:
        return relationship(
            "ActionObsidianHourly",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @declared_attr
    def action_obsidian_daily(cls) -> Mapped["ActionObsidianDaily"]:
        return relationship(
            "ActionObsidianDaily",
            back_populates="resource",
            uselist=False,
            cascade="all, delete-orphan",
        )

    @property
    def url(self) -> str:
        """Return the URL for this resource."""
        return self.href

    @property
    def normalized_url(self) -> str:
        """A computed address for a resource, otherwise its uri.

        Subclasses like HypothesisPage override this to substitute annotated
        resource URLs; the default here is just the resource's own href.
        """
        return self.url

    @property
    def headline(self) -> str:
        """Get headline potion of a resource title

        Returns:
            str: headline
        """
        if not self._headline:
            self._parse_title()
        return self._headline or ""

    @property
    def publisher(self) -> str:
        """Get publisher portion of a resource title

        Returns:
            str: publisher
        """
        if not self._publisher:
            self._parse_title()
        return self._publisher or ""

    def _parse_title(self) -> None:
        title_scan = re.compile(
            r"""(.*?)\s+          # headline proper (group 1)
                (\[(.*?)\])?      # optionally, a comment/description in square brackets (group 3)
                (\s+(.*?))?\|\s+  # optionally, any other parts of the headline before the vertical bar (group 5)
                (.*)              # publisher after the vertical bar (group 6)
            """,
            re.X,
        )

        if match := title_scan.match(self.title):  # pylint: disable=no-member
            self._headline = f"{match.group(1)}"
            if title_comment := match.group(3):
                self.description = f"_{title_comment}_\n\n{self.description}"  # pylint: disable=no-member
            if headline_extra := match.group(5):
                self._headline = f"{self._headline} – {headline_extra}"
            self._publisher = match.group(6)
        else:
            self._headline = self.title  # pylint: disable=no-member
            self._publisher = None


class Pinboard(WebResource):
    __tablename__ = "pinboard_posts"
    __mapper_args__ = {"polymorphic_identity": "pinboard"}

    id: Mapped[int] = mapped_column(ForeignKey("webresource.id"), primary_key=True)
    hash: Mapped[str] = mapped_column(String)
    meta: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    shared: Mapped[VisibilityEnum] = mapped_column(SqlEnum(VisibilityEnum))
    toread: Mapped[int] = mapped_column(Integer)
    _tags: Mapped[Optional[str]] = mapped_column("tags", String, nullable=True)

    # Create native Python lists for stored JSON tag array structure
    @property
    def tags(self) -> Optional[List[str]]:
        """Parse the JSON string of tags and return a list of strings."""
        try:
            loaded_data = json.loads(self._tags) if self._tags else None
            if isinstance(loaded_data, list) and all(
                isinstance(item, str) for item in loaded_data
            ):
                return loaded_data
            else:
                raise ValueError("Stored data is not a list of strings.")
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning("Decoding error or validation failure: {%s}", e)
            return None

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        """Convert a list of strings to a JSON string for storage."""
        if value is not None:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                self._tags = json.dumps(value)
            else:
                raise TypeError("Data must be a list of strings.")
        else:
            self._tags = None


class HypothesisPage(WebResource):
    __tablename__ = "hypothesis_pages"
    __mapper_args__ = {"polymorphic_identity": "hypothesis"}
    _normalized_url = None
    _annotation_url = None

    id: Mapped[int] = mapped_column(ForeignKey("webresource.id"), primary_key=True)
    _shared: Mapped[Optional[VisibilityEnum]] = mapped_column(
        "shared", SqlEnum(VisibilityEnum)
    )
    annotations: Mapped[List["HypothesisAnnotation"]] = relationship(
        "HypothesisAnnotation", back_populates="page", cascade="all, delete-orphan"
    )

    @property
    def via_url(self) -> str:
        return f"https://via.hypothes.is/{self.href}"

    @property
    def shared(self) -> VisibilityEnum:
        return self._shared or VisibilityEnum.PRIVATE  # Default to PRIVATE if not set

    @shared.setter
    def shared(self, shared: VisibilityEnum) -> None:
        """
        Sets the visibility of the shared attribute with specific constraints.

        This setter method assigns a new value to the `_shared` attribute, which
        indicates the visibility level according to the `VisibilityEnum`. The method
        enforces a constraint: if the current visibility is `PUBLIC` and an attempt
        is made to set it to `PRIVATE`, the visibility remains `PUBLIC`. In all
        other cases, it updates `_shared` to the specified new value.
        """
        if self._shared == VisibilityEnum.PUBLIC and shared == VisibilityEnum.PRIVATE:
            self._shared = VisibilityEnum.PUBLIC
        else:
            self._shared = shared

    def _url_normalization(self):
        if match := docdrop_url_scan.match(self.href):
            logger.debug("Found DocDrop match for %s; adjusting URLs.", self.href)
            self._annotation_url = self.href
            self._normalized_url = f"https://youtube.com/watch?v={match.group(1)}"
        elif match := dltjvid_url_scan.match(self.href):
            logger.debug(
                "Found DLTJ video annotation match for %s; adjusting URLs.",
                self.href,
            )
            self._annotation_url = self.href
            self._normalized_url = f"https://youtube.com/watch?v={match.group(1)}"
        elif self.href.startswith("https://media.dltj.org/unchecked-transcript/"):
            (
                self._annotation_url,
                self._normalized_url,
                self.title,
                self._publisher,
            ) = self.transcript_urls()
        else:
            self._annotation_url = f"https://via.hypothes.is/{self.href}"
            self._normalized_url = self.href

    @property
    def normalized_url(self) -> str:
        if not self._normalized_url:
            self._url_normalization()
        assert self._normalized_url is not None, "Normalized URL should not be None"
        return self._normalized_url

    @property
    def annotation_url(self) -> str:
        if not self._annotation_url:
            self._url_normalization()
        assert self._annotation_url is not None, "Annotation URL should not be None"
        return self._annotation_url

    def transcript_urls(self) -> Tuple[str, str, str, str]:
        page = requests.get(self.href, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
        episode_id = soup.find("a", id="episode")
        podcast_id = soup.find("span", id="podcast")
        annotation_url = self.href
        normalized_url = str(episode_id["href"]) if isinstance(episode_id, Tag) else ""
        title = episode_id.text if isinstance(episode_id, Tag) else ""
        publisher = podcast_id.text if isinstance(podcast_id, Tag) else ""
        return annotation_url, normalized_url, title, publisher


class HypothesisAnnotation(Base):
    __tablename__ = "hypothesis_annotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("hypothesis_pages.id"))
    hyp_id: Mapped[str] = mapped_column(String)
    annotation: Mapped[str] = mapped_column(String)
    time_created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    time_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quote: Mapped[str] = mapped_column(String)
    document_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    link_html: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    link_incontext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    shared: Mapped[VisibilityEnum] = mapped_column(SqlEnum(VisibilityEnum))
    flagged: Mapped[int] = mapped_column(Integer)
    _tags: Mapped[Optional[str]] = mapped_column("tags", String, nullable=True)

    # Establish relationship back to HypothesisPage
    page: Mapped["HypothesisPage"] = relationship(
        "HypothesisPage", back_populates="annotations"
    )

    @declared_attr
    def annotation_status(cls) -> Mapped[List["AnnotationStatus"]]:
        return relationship(
            "AnnotationStatus",
            back_populates="annotation",
        )

    @declared_attr
    def action_obsidian_annotation(cls) -> Mapped["ActionObsidianAnnotation"]:
        return relationship(
            "ActionObsidianAnnotation",
            back_populates="annotation",
            uselist=False,
            cascade="all, delete-orphan",
        )

    # Create native Python lists for stored JSON tag array structures
    @property
    def tags(self) -> Optional[List[str]]:
        """Parse the JSON string of tags and return a list of strings."""
        try:
            loaded_data = json.loads(self._tags) if self._tags else None
            if isinstance(loaded_data, list) and all(
                isinstance(item, str) for item in loaded_data
            ):
                return loaded_data
            else:
                raise ValueError("Stored data is not a list of strings.")
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning("Decoding error or validation failure: {%s}", e)
            return None

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        """Convert a list of strings to a JSON string for storage."""
        if value is not None:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                self._tags = json.dumps(value)
            else:
                raise TypeError("Data must be a list of strings.")
        else:
            self._tags = None

    @classmethod
    def create_with_page(
        cls,
        session: Session,
        document_url: str,
        document_title: str,
        saved_timestamp: datetime,
    ) -> Tuple["HypothesisAnnotation", HypothesisPage]:
        """
        Creates a new HypothesisAnnotation and ensures the associated HypothesisPage exists.

        This method checks for the existence of a HypothesisPage with the given URI.
        If the page does not exist, it creates the page before proceeding to create
        the HypothesisAnnotation. Both the annotation and its associated page are
        added to the session but not yet committed to the database.

        Parameters:
        - session (Session): The SQLAlchemy session used for database operations.
        - document_url (str): The URI to associate with the HypothesisPage and HypothesisAnnotation.
        - document_title (str): The title of the document
        - saved_timestamp (datetime): Timestamp of when the annotation was created

        Returns:
        - Tuple[HypothesisAnnotation, HypothesisPage]: A tuple containing the newly
          created HypothesisAnnotation and the HypothesisPage it is associated with.

        Raises:
        - SQLAlchemyError: If there is an error from the database.

        Example:
            annotation, page = HypothesisAnnotation.create_with_page(session, "http://example.com")
            print(f"Annotation added to page with URI: {page.uri}")
        """
        # Ensure the HypothesisPage exists
        stmt = select(HypothesisPage).where(HypothesisPage.href == document_url)
        page: Optional[HypothesisPage] = session.execute(stmt).scalars().first()

        if not page:
            page = HypothesisPage(
                href=document_url,
                title=document_title,
                saved_timestamp=saved_timestamp,
            )
            session.add(page)

        # Create the HypothesisAnnotation
        annotation = cls()
        page.annotations.append(annotation)
        annotation.document_title = document_title
        annotation.time_created = saved_timestamp
        session.add(annotation)

        return annotation, page


class AnnotationStatus(Base):
    __tablename__ = "annotation_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hypothesis_annotation.id")
    )
    action_name: Mapped[str]
    status: Mapped[ProcessStatusEnum] = mapped_column(
        SqlEnum(ProcessStatusEnum), nullable=False, default=ProcessStatusEnum.RETRYABLE
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,
    )
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    annotation: Mapped[HypothesisAnnotation] = relationship(
        "HypothesisAnnotation",
        back_populates="annotation_status",
    )


class ProcessStatus(Base):
    __tablename__ = "process_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    action_name: Mapped[str]
    status: Mapped[ProcessStatusEnum] = mapped_column(
        SqlEnum(ProcessStatusEnum), nullable=False, default=ProcessStatusEnum.RETRYABLE
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="process_status"
    )

    def __repr__(self):
        return f"<ProcessStatus(resource_id={self.resource_id!r}, action_name='{self.action_name!r}', processed_at='{self.processed_at!r}')>"


class ActionSummary(Base):
    __tablename__ = "action_summary"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    derived_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_summary", uselist=False
    )


class ActionMastodon(Base):
    __tablename__ = "action_mastodon"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    toot_uri: Mapped[str]
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_mastodon", uselist=False
    )


class ActionWayback(Base):
    __tablename__ = "action_wayback"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    wayback_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wayback_timestamp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wayback_details: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_wayback", uselist=False
    )


class ActionKagi(Base):
    __tablename__ = "action_kagi"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    kagi_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_kagi", uselist=False
    )


class ActionObsidianHourly(Base):
    __tablename__ = "action_obsidian_hourly"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    filename: Mapped[str] = mapped_column(String)
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_obsidian_hourly", uselist=False
    )


class ActionObsidianDaily(Base):
    __tablename__ = "action_obsidian_daily"
    __table_args__ = (UniqueConstraint("resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("webresource.id"))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=func.now(),
        nullable=False,  # pylint:disable=not-callable
    )
    daily_filename: Mapped[str] = mapped_column(String)
    resource: Mapped[WebResource] = relationship(
        "WebResource", back_populates="action_obsidian_daily", uselist=False
    )


class ActionObsidianAnnotation(Base):
    __tablename__ = "action_obsidian_annotation"
    __table_args__ = (UniqueConstraint("annotation_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hypothesis_annotation.id")
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(), default=func.now(), nullable=False
    )
    filename: Mapped[str] = mapped_column(String)
    annotation: Mapped[HypothesisAnnotation] = relationship(
        "HypothesisAnnotation",
        back_populates="action_obsidian_annotation",
        uselist=False,
    )
