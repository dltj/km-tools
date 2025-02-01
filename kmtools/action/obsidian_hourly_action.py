import logging

from sqlalchemy.orm import Session

from kmtools.action.action_base import ActionBase
from kmtools.models import ActionObsidianHourly, WebResource
from kmtools.obsidian.source_page import ObsidianSourcePage
from kmtools.util.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

config.dry_run = True


class SaveToObsidian(ActionBase):
    """Save resource to Obsidian database"""

    action_name = "ObsidianHourlyAction"

    def process(self, session: Session, resource: WebResource) -> None:
        """Save a resource to the Obsidian knowledgebase

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Obsidian results in an error
        """

        obsidian_hourly_action: ActionObsidianHourly = ActionObsidianHourly(
            resource=resource
        )
        obsidian_source_page = ObsidianSourcePage(page_title=resource.headline)
        obsidian_source_page.frontmatter["source_url"] = resource.url
        obsidian_source_page.frontmatter["origin"] = resource.__class__.__name__
        obsidian_source_page.frontmatter["bookmark_saved"] = (
            resource.saved_timestamp.strftime("%Y-%m-%d")
        )
        obsidian_source_page.frontmatter["source_created"] = (
            "unknown"
            if not resource.action_summary
            else resource.action_summary.derived_date
        )
        obsidian_source_page.frontmatter["publisher"] = resource.publisher
        if resource.action_kagi:
            obsidian_source_page.content = (
                f"Kagi summary:: {resource.action_kagi.kagi_summary}\n\n"
            )
        if resource.action_summary:
            obsidian_source_page.content += (
                f"Automated summary:: {resource.action_summary.summary}\n\n"
            )
        if hasattr(resource, "tags"):
            obsidian_source_page.content += "Tags:: " + ", ".join(
                [f"[[{tag}]]" for tag in resource.tags]
            )

        obsidian_source_page.save()
        obsidian_hourly_action.filename = obsidian_source_page.filepath.as_posix()
        session.add(obsidian_hourly_action)
        return


def main():
    # database.Base.metadata.create_all(database.engine)
    # with Session(database.engine) as session:
    #     pinb: Pinboard = Pinboard(
    #         hash="hashblah", href="hrefbalh", time="tieblah", shared=1, toread=1
    #     )
    #     session.add(pinb)
    #     session.commit()

    actions = [
        SaveToObsidian(),
        # SaveToWaybackAction(),
        # PostToMastodonAction(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
