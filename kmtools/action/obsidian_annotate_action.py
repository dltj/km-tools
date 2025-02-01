import logging
import re

from sqlalchemy.orm import Session

from kmtools.action.annotation_action_base import AnnotationActionBase
from kmtools.models import ActionObsidianAnnotation, HypothesisAnnotation, WebResource
from kmtools.obsidian.source_page import ObsidianSourcePage
from kmtools.util.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

config.dry_run = True


class AnnotateObsidianPage(AnnotationActionBase):
    """Add annotation to an Obsidian source page"""

    action_name = "ObsidianAnnotateAction"

    def process(self, session: Session, annotation: HypothesisAnnotation) -> None:
        """Add an annotation to an Obsidian knowledgebase source page

        :param session: SQLAlchemy session
        :param annotation: Instance of class HypothesisAnnotation

        :raises:
            - ActionException: when the attempt to post to Obsidian results in an error
        """

        resource: WebResource = annotation.page
        obsidian_annotation_action: ActionObsidianAnnotation = ActionObsidianAnnotation(
            annotation=annotation
        )
        obsidian_source_page = ObsidianSourcePage(page_title=resource.headline)
        quote = annotation.quote.strip()
        quote = re.sub(r"\s*\n\s*\n\s*", "\n", quote)
        quote = re.sub(r"\n", "\n> ", quote)
        annotation_string = annotation.annotation.strip()
        if annotation_string.startswith("##"):
            headline, _, discussion = annotation_string.partition("\n")
        else:
            headline = None
            discussion = annotation_string.strip()
        if headline:
            obsidian_source_page.content += f"{headline}\n"
        if quote:
            obsidian_source_page.content += f"> {quote}\n"
        if discussion:
            obsidian_source_page.content += f"{discussion}\n"
        obsidian_source_page.content += (
            f"\n- Link to [annotation]({annotation.link_incontext})\n"
        )
        if annotation.tags:
            obsidian_source_page.content += (
                "- Tags:: "
                + ", ".join([f"[[{tag}]]" for tag in annotation.tags])
                + "\n"
            )
        obsidian_source_page.content += "\n"
        obsidian_source_page.save()

        obsidian_annotation_action.filename = obsidian_source_page.filepath.as_posix()
        session.add(obsidian_annotation_action)
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
        AnnotateObsidianPage(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
