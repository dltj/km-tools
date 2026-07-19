import logging
from typing import cast

from sqlalchemy.orm import Session

from kmtools.models import ActionObsidianHourly, Pinboard, WebResource
from kmtools.obsidian.source_page import ObsidianSourcePage

from ..obsidian.sections import FieldSection
from .web_resource_action_base import WebResourceActionBase

logger = logging.getLogger(__name__)


class SaveToObsidian(WebResourceActionBase):
    """Save resource to Obsidian database"""

    action_name = "ObsidianHourlyAction"

    def process(self, session: Session, resource: WebResource) -> None:
        """Save a resource to the Obsidian knowledgebase

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Obsidian results in an error
        """
        with ObsidianSourcePage(page_title=resource.headline) as page:
            page.frontmatter["source_url"] = resource.url
            page.frontmatter["origin"] = resource.__class__.__name__
            page.frontmatter["bookmark_saved"] = resource.saved_timestamp.strftime(
                "%Y-%m-%d"
            )
            page.frontmatter["source_created"] = (
                "unknown"
                if not resource.action_summary
                else resource.action_summary.derived_date or "unknown"
            )
            page.frontmatter["publisher"] = resource.publisher

            preamble = cast(
                FieldSection, page.get_section(ObsidianSourcePage.SEC_PREAMBLE)
            )

            if resource.action_kagi and resource.action_kagi.kagi_summary:
                preamble.set_field("Kagi summary", resource.action_kagi.kagi_summary)
            if resource.action_summary and resource.action_summary.summary:
                preamble.set_field("Automated summary", resource.action_summary.summary)
            if isinstance(resource, Pinboard) and resource.tags:
                preamble.set_field(
                    "Concepts", ", ".join(f"[[{tag}]]" for tag in resource.tags)
                )

        obsidian_hourly_action: ActionObsidianHourly = ActionObsidianHourly(
            resource=resource
        )
        obsidian_hourly_action.filename = page.filepath.as_posix()
        session.add(obsidian_hourly_action)
