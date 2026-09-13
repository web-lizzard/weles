from adapters.out.sqlalchemy.capture.mapping import tag_to_domain, topic_to_domain
from adapters.out.sqlalchemy.capture.models import CaptureTagRow, CaptureTopicRow
from domain.capture.exceptions import NoteVocabularyIncompleteError
from domain.capture.note import Note
from domain.capture.note_vocabulary import NoteVocabulary
from domain.capture.tag import Tag
from domain.capture.value_objects import TagId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyNoteVocabularyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def resolve(self, note: Note) -> NoteVocabulary:
        topic_statement = select(CaptureTopicRow).where(
            CaptureTopicRow.id == note.topic_id
        )
        topic_row = (await self._session.execute(topic_statement)).scalar_one_or_none()
        if topic_row is None:
            raise NoteVocabularyIncompleteError
        topic = topic_to_domain(topic_row)

        tags_by_id: dict[TagId, Tag] = {}
        if note.tag_ids:
            tags_statement = select(CaptureTagRow).where(
                CaptureTagRow.id.in_(note.tag_ids)
            )
            tag_rows = (await self._session.execute(tags_statement)).scalars().all()
            tags_by_id = {row.id: tag_to_domain(row) for row in tag_rows}

        tags: list[Tag] = []
        for tag_id in note.tag_ids:
            tag = tags_by_id.get(tag_id)
            if tag is None:
                raise NoteVocabularyIncompleteError
            tags.append(tag)

        return NoteVocabulary(topic=topic, tags=tags)
