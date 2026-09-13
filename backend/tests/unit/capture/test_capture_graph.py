from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC

import pytest

from adapters.out.in_memory.capture.embedding import DeterministicEmbeddingAdapter
from adapters.out.in_memory.capture.message_repository import (
    InMemoryMessageRepository,
)
from adapters.out.in_memory.capture.message_store import InMemoryMessageStore
from adapters.out.in_memory.capture.note_repository import InMemoryNoteRepository
from adapters.out.in_memory.capture.note_vocabulary_repository import (
    InMemoryNoteVocabularyRepository,
)
from adapters.out.in_memory.capture.tag_repository import InMemoryTagRepository
from adapters.out.in_memory.capture.topic_repository import InMemoryTopicRepository
from domain.capture.capture_session import CaptureSession
from domain.capture.deps import NULL_CAPTURE_DEPS, CaptureDeps
from domain.capture.exceptions import CoverageOutOfRangeError, DraftTopicMissingError
from domain.capture.graph import (
    CaptureMachine,
    ConversationRequestSignal,
    Conversing,
    CoverageAssessment,
    Drafting,
    DraftingConsentSignal,
    NoteContentProposal,
    NoteTagProposal,
    NoteTopicProposal,
    SessionTopicProposal,
    consent_given,
    conversation_requested,
)
from domain.capture.message import Message
from domain.capture.note import Note
from domain.capture.tag import Tag
from domain.capture.topic import Topic
from domain.capture.turn import (
    AssistantMessageRecorded,
    CaptureTurn,
    ConversationRequested,
    CoverageAssessed,
    DraftCompleted,
    DraftingConsentSignalled,
    NoteContentProduced,
    NoteDraft,
    NoteTagProposed,
    NoteTopicProposed,
    ReplyProduced,
    SessionTopicProposed,
    UserMessageRecorded,
)
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    Coverage,
    DraftingConsent,
    Embedding,
    Label,
    MessageContent,
    MessageRole,
    NoteContent,
    SessionTopic,
    SimilarityScore,
)
from domain.capture.vocabulary import MatchCriteria, VocabularyResolver
from domain.shared.graph.model import Tool, ToolResult

_EMBEDDING_MODEL = "test"


def _user_message(session: CaptureSession) -> Message:
    return Message.record(
        session_id=session.id,
        role=MessageRole.USER,
        content=MessageContent(value="Let's talk about TCP handshakes"),
    )


def _assistant_message(session: CaptureSession) -> Message:
    return Message.record(
        session_id=session.id,
        role=MessageRole.AGENT,
        content=MessageContent(value="We can write this up as a note."),
    )


def _turn(
    *,
    phase: CapturePhase = CapturePhase.CONVERSING,
    topic: SessionTopic | None = None,
    messages: Sequence[Message] | None = None,
    drafting_consent: DraftingConsent | None = None,
    conversation_request: ConversationRequest | None = None,
) -> CaptureTurn:
    session = CaptureSession.start()
    if topic is not None:
        session.assign_topic(topic)
    session.phase = phase
    session.drafting_consent = drafting_consent
    session.conversation_request = conversation_request
    if messages is None:
        messages = (_user_message(session),)
    return CaptureTurn(session=session, messages=messages)


def _machine(turn: CaptureTurn) -> CaptureMachine:
    return CaptureMachine(turn, NULL_CAPTURE_DEPS)


@dataclass
class _CaptureDeps:
    messages: InMemoryMessageRepository
    notes: InMemoryNoteRepository
    topics: InMemoryTopicRepository
    tags: InMemoryTagRepository
    note_vocabulary: InMemoryNoteVocabularyRepository
    vocabulary: VocabularyResolver


def _capture_deps() -> _CaptureDeps:
    topics = InMemoryTopicRepository()
    tags = InMemoryTagRepository()
    return _CaptureDeps(
        messages=InMemoryMessageRepository(InMemoryMessageStore()),
        notes=InMemoryNoteRepository(),
        topics=topics,
        tags=tags,
        note_vocabulary=InMemoryNoteVocabularyRepository(topics, tags),
        vocabulary=VocabularyResolver(
            DeterministicEmbeddingAdapter(),
            MatchCriteria(threshold=SimilarityScore(value=0.85)),
        ),
    )


def _machine_with_deps(turn: CaptureTurn, deps: CaptureDeps) -> CaptureMachine:
    return CaptureMachine(turn, deps)


def _tool_names(tools: Sequence[Tool[CaptureTurn, ToolResult]]) -> set[str]:
    return {tool.name for tool in tools}


def test_turn_bootstrap_stamps_session_created_at_in_utc() -> None:
    turn = _turn()

    assert turn.session.created_at.tzinfo is UTC


async def test_at_most_one_available_transition_and_each_intent_opens_its_edge() -> (
    None
):
    graph = _machine(_turn()).graph
    idle = _turn()
    consented = _turn(drafting_consent=DraftingConsent())
    drafting = _turn(phase=CapturePhase.DRAFTING)
    returning = _turn(
        phase=CapturePhase.DRAFTING,
        conversation_request=ConversationRequest(),
    )
    both_intents_while_conversing = _turn(
        drafting_consent=DraftingConsent(),
        conversation_request=ConversationRequest(),
    )

    assert graph.terminal_states == frozenset()
    assert graph.reachable_from(CapturePhase.CONVERSING) == frozenset(
        {CapturePhase.CONVERSING, CapturePhase.DRAFTING}
    )
    assert graph.reachable_from(CapturePhase.DRAFTING) == frozenset(
        {CapturePhase.CONVERSING, CapturePhase.DRAFTING}
    )
    assert consent_given(idle) is False
    assert conversation_requested(drafting) is False
    assert consent_given(consented) is True
    assert conversation_requested(returning) is True
    assert _machine(idle).available_transitions() == {}
    assert await _machine(idle).transition(CapturePhase.DRAFTING) is False
    assert _machine(consented).available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }
    assert _machine(drafting).available_transitions() == {}
    assert await _machine(drafting).transition(CapturePhase.CONVERSING) is False
    assert _machine(returning).available_transitions() == {
        CapturePhase.CONVERSING: Conversing().description,
    }
    assert _machine(both_intents_while_conversing).available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }
    for turn in (
        idle,
        consented,
        drafting,
        returning,
        both_intents_while_conversing,
    ):
        assert len(_machine(turn).available_transitions()) <= 1


def test_conversing_withholds_the_session_topic_tool_once_the_session_has_one() -> None:
    unnamed = _machine(_turn())
    named = _machine(_turn(topic=SessionTopic(value="TCP handshakes")))
    drafting = _machine(_turn(phase=CapturePhase.DRAFTING))

    assert _tool_names(Conversing().tools) == {
        "assess_coverage",
        "propose_session_topic",
        "signal_drafting_consent",
    }
    assert _tool_names(unnamed.get_tools()) == {
        "assess_coverage",
        "propose_session_topic",
        "signal_drafting_consent",
    }
    assert _tool_names(named.get_tools()) == {
        "assess_coverage",
        "signal_drafting_consent",
    }
    assert _tool_names(Drafting().tools) == {
        "propose_note_topic",
        "propose_note_tag",
        "propose_note_content",
        "request_conversation",
    }
    assert _tool_names(drafting.get_tools()) == {
        "propose_note_topic",
        "propose_note_tag",
        "propose_note_content",
        "request_conversation",
    }


async def test_drafting_consent_with_messages_opens_drafting_and_spends_intent() -> (
    None
):
    machine = _machine(_turn())
    reply = ReplyProduced(text="Shall we write this up?")
    consent = DraftingConsentSignalled()
    topic_proposed = SessionTopicProposed(topic=SessionTopic(value="TCP handshakes"))
    consent_actions = Conversing().get_actions(machine.context, consent)
    topic_actions = Conversing().get_actions(machine.context, topic_proposed)

    assert Conversing().get_actions(machine.context, reply) == ()
    assert consent_actions != ()
    assert topic_actions != ()
    assert topic_actions != consent_actions

    await machine.apply(reply)
    await machine.apply(consent)

    assert machine.context.session.drafting_consent == DraftingConsent()
    assert machine.available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }

    moved = await machine.transition(CapturePhase.DRAFTING)

    assert moved is True
    assert machine.current_state_name is CapturePhase.DRAFTING
    assert machine.context.session.drafting_consent is None
    assert machine.available_transitions() == {}
    assert await machine.transition(CapturePhase.CONVERSING) is False

    requested = ConversationRequested()
    note_chunk = NoteContentProduced(content=NoteContent(value="A draft."))

    assert Drafting().get_actions(machine.context, note_chunk) != ()
    assert Drafting().get_actions(machine.context, requested) != ()

    await machine.apply(requested)

    assert machine.context.session.conversation_request == ConversationRequest()
    assert machine.available_transitions() == {
        CapturePhase.CONVERSING: Conversing().description,
    }

    returned = await machine.transition(CapturePhase.CONVERSING)

    assert returned is True
    assert machine.current_state_name is CapturePhase.CONVERSING
    assert machine.context.session.conversation_request is None
    assert machine.available_transitions() == {}


async def test_applying_drafting_consent_without_messages_does_not_open_drafting() -> (
    None
):
    machine = _machine(_turn(messages=()))
    consent = DraftingConsentSignalled()

    assert Conversing().get_actions(machine.context, consent)

    await machine.apply(consent)

    assert machine.context.session.drafting_consent is None
    assert machine.available_transitions() == {}
    assert await machine.transition(CapturePhase.DRAFTING) is False


async def test_assess_coverage_rejects_bool_coverage() -> None:
    """Bool must not coerce to a coverage score."""
    conversing = _machine(_turn())
    assess = next(tool for tool in Conversing().tools if tool.name == "assess_coverage")

    with pytest.raises(TypeError):
        _ = await assess.handler(conversing.context, {"coverage": True})


async def test_assess_coverage_rejects_a_score_outside_the_closed_unit_interval() -> (
    None
):
    conversing = _machine(_turn())
    assess = next(tool for tool in Conversing().tools if tool.name == "assess_coverage")

    with pytest.raises(CoverageOutOfRangeError):
        _ = await assess.handler(conversing.context, {"coverage": 1.01})


async def test_coverage_assessed_appends_to_session_assessments() -> None:
    machine = _machine(_turn())
    assessed = CoverageAssessed(coverage=Coverage(value=0.55))

    assert Conversing().get_actions(machine.context, assessed) != ()

    await machine.apply(assessed)

    assert machine.context.session.assessments == (Coverage(value=0.55),)


async def test_two_coverage_assessed_events_append_in_order_on_session() -> None:
    machine = _machine(_turn())
    first = CoverageAssessed(coverage=Coverage(value=0.25))
    second = CoverageAssessed(coverage=Coverage(value=0.9))

    await machine.apply(first)
    await machine.apply(second)

    assert machine.context.session.assessments == (
        Coverage(value=0.25),
        Coverage(value=0.9),
    )


async def test_proposal_tools_return_results_built_from_the_model_arguments() -> None:
    conversing = _machine(_turn())
    conversing_tools = {tool.name: tool for tool in Conversing().tools}
    drafting_tools = {tool.name: tool for tool in Drafting().tools}

    coverage = await conversing_tools["assess_coverage"].handler(
        conversing.context, {"coverage": 0.4}
    )
    session_topic = await conversing_tools["propose_session_topic"].handler(
        conversing.context, {"topic": "TCP handshakes"}
    )
    assert coverage == CoverageAssessment(coverage=Coverage(value=0.4))
    assert session_topic == SessionTopicProposal(
        topic=SessionTopic(value="TCP handshakes")
    )

    consent = await conversing_tools["signal_drafting_consent"].handler(
        conversing.context, {}
    )
    note_topic = await drafting_tools["propose_note_topic"].handler(
        conversing.context, {"label": "TCP handshakes"}
    )
    note_tag = await drafting_tools["propose_note_tag"].handler(
        conversing.context, {"label": "networking"}
    )
    note_content = await drafting_tools["propose_note_content"].handler(
        conversing.context, {"content": "We discussed how connections are established."}
    )
    conversation = await drafting_tools["request_conversation"].handler(
        conversing.context, {}
    )

    topic_proposed = SessionTopicProposed(topic=SessionTopic(value="TCP handshakes"))
    assert Conversing().get_actions(conversing.context, topic_proposed) != ()
    await conversing.apply(topic_proposed)

    assert coverage == CoverageAssessment(coverage=Coverage(value=0.4))
    assert session_topic == SessionTopicProposal(
        topic=SessionTopic(value="TCP handshakes")
    )
    assert consent == DraftingConsentSignal()
    assert note_topic == NoteTopicProposal(label=Label(value="TCP handshakes"))
    assert note_tag == NoteTagProposal(label=Label(value="networking"))
    assert note_content == NoteContentProposal(
        content=NoteContent(value="We discussed how connections are established.")
    )
    assert conversation == ConversationRequestSignal()
    assert conversing.context.session.topic == SessionTopic(value="TCP handshakes")
    assert _tool_names(conversing.get_tools()) == {
        "assess_coverage",
        "signal_drafting_consent",
    }


def test_recording_a_message_on_the_turn_appends_it_to_the_conversation() -> None:
    session = CaptureSession.start()
    turn = CaptureTurn(session=session, messages=())
    incoming = _user_message(session)

    turn.record_message(incoming)

    assert list(turn.messages) == [incoming]


async def test_applying_the_turns_own_first_message_then_consent_opens_drafting() -> (
    None
):
    deps = _capture_deps()
    machine = _machine_with_deps(_turn(messages=()), deps)
    incoming = _user_message(machine.context.session)
    recorded = UserMessageRecorded(message=incoming)
    consent = DraftingConsentSignalled()

    assert Conversing().get_actions(machine.context, recorded) != ()
    await machine.apply(recorded)

    assert incoming in machine.context.messages

    await machine.apply(consent)

    assert machine.context.session.drafting_consent == DraftingConsent()
    assert machine.available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }


async def test_applying_an_assistant_message_while_drafting_appends_it() -> None:
    deps = _capture_deps()
    machine = _machine_with_deps(_turn(phase=CapturePhase.DRAFTING, messages=()), deps)
    incoming = _assistant_message(machine.context.session)
    recorded = AssistantMessageRecorded(message=incoming)
    user_recorded = UserMessageRecorded(message=_user_message(machine.context.session))

    assert Drafting().get_actions(machine.context, recorded) != ()
    assert Drafting().get_actions(machine.context, user_recorded) != ()
    assert Conversing().get_actions(machine.context, recorded) != ()

    await machine.apply(recorded)

    assert incoming in machine.context.messages


async def test_first_draft_materialises_note_from_drafting_events() -> None:
    deps = _capture_deps()
    machine = _machine_with_deps(_turn(phase=CapturePhase.DRAFTING), deps)
    topic_event = NoteTopicProposed(label=Label(value="TCP handshakes"))
    tag_event = NoteTagProposed(label=Label(value="networking"))
    content_event = NoteContentProduced(
        content=NoteContent(value="We discussed how connections are established.")
    )

    assert Drafting().get_actions(machine.context, topic_event) != ()
    assert Drafting().get_actions(machine.context, tag_event) != ()
    assert Drafting().get_actions(machine.context, content_event) != ()

    await machine.apply(topic_event)
    await machine.apply(tag_event)
    await machine.apply(content_event)

    assert machine.context.draft is not None
    assert machine.context.draft.topic is not None
    assert machine.context.draft.topic.label == Label(value="TCP handshakes")
    assert len(machine.context.draft.tags) == 1
    assert machine.context.draft.tags[0].label == Label(value="networking")
    assert (
        machine.context.draft.content == "We discussed how connections are established."
    )

    await machine.apply(DraftCompleted())

    note = machine.context.note
    assert note is not None
    assert machine.context.session.note_id == note.id
    persisted = await deps.notes.get(note.id)
    assert persisted is not None
    assert persisted.content == NoteContent(
        value="We discussed how connections are established."
    )


async def test_redraft_reconciles_tags_and_content_on_existing_note() -> None:
    deps = _capture_deps()
    session = CaptureSession.start()
    old_topic = Topic.mint(
        Label(value="Old topic"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2, 0.3)),
    )
    kept_tag = Tag.mint(
        Label(value="kept"), Embedding(model=_EMBEDDING_MODEL, values=(0.4, 0.5, 0.6))
    )
    dropped_tag = Tag.mint(
        Label(value="dropped"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.7, 0.8, 0.9)),
    )
    note = Note.draft(
        session.id,
        old_topic,
        NoteContent(value="Old body"),
        [kept_tag, dropped_tag],
    )
    session.note_id = note.id
    session.phase = CapturePhase.DRAFTING
    await deps.topics.add(old_topic)
    await deps.tags.add(kept_tag)
    await deps.tags.add(dropped_tag)
    await deps.notes.add(note)
    machine = _machine_with_deps(
        CaptureTurn(session=session, messages=(_user_message(session),), note=note),
        deps,
    )

    await machine.apply(NoteTopicProposed(label=Label(value="New topic")))
    await machine.apply(NoteTagProposed(label=Label(value="kept")))
    await machine.apply(NoteTagProposed(label=Label(value="fresh")))
    await machine.apply(NoteContentProduced(content=NoteContent(value="New body")))
    await machine.apply(DraftCompleted())

    redrafted = await deps.notes.get(note.id)
    assert redrafted is not None
    assert redrafted.content == NoteContent(value="New body")
    resolved = await deps.note_vocabulary.resolve(redrafted)
    assert {tag.label.value for tag in resolved.tags} == {"kept", "fresh"}
    assert "dropped" not in {tag.label.value for tag in resolved.tags}
    assert resolved.topic.label == Label(value="New topic")


async def test_applying_a_tag_before_a_topic_raises_draft_topic_missing_error() -> None:
    deps = _capture_deps()
    machine = _machine_with_deps(_turn(phase=CapturePhase.DRAFTING), deps)
    tag_event = NoteTagProposed(label=Label(value="networking"))

    assert Drafting().get_actions(machine.context, tag_event) != ()

    with pytest.raises(DraftTopicMissingError):
        await machine.apply(tag_event)


async def test_user_message_hydrates_draft_from_persisted_note() -> None:
    deps = _capture_deps()
    session = CaptureSession.start()
    topic = Topic.mint(
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2, 0.3)),
    )
    tag = Tag.mint(
        Label(value="networking"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.4, 0.5, 0.6)),
    )
    note = Note.draft(
        session.id,
        topic,
        NoteContent(value="Persisted body"),
        [tag],
    )
    session.note_id = note.id
    session.phase = CapturePhase.DRAFTING
    await deps.topics.add(topic)
    await deps.tags.add(tag)
    await deps.notes.add(note)
    machine = _machine_with_deps(
        CaptureTurn(
            session=session,
            messages=(_user_message(session),),
            note=note,
            draft=None,
        ),
        deps,
    )
    recorded = UserMessageRecorded(message=_user_message(session))

    await machine.apply(recorded)

    assert machine.context.draft is not None
    assert machine.context.draft.topic is not None
    assert machine.context.draft.topic.label == Label(value="TCP handshakes")
    assert machine.context.draft.topic_reused is True
    assert len(machine.context.draft.tags) == 1
    assert machine.context.draft.tags[0].label == Label(value="networking")
    assert machine.context.draft.tag_reused == [True]
    assert machine.context.draft.content == "Persisted body"


async def test_user_message_recorded_skips_hydration_when_draft_already_set() -> None:
    deps = _capture_deps()
    session = CaptureSession.start()
    topic = Topic.mint(
        Label(value="TCP handshakes"),
        Embedding(model=_EMBEDDING_MODEL, values=(0.1, 0.2, 0.3)),
    )
    note = Note.draft(session.id, topic, NoteContent(value="Persisted body"), [])
    session.note_id = note.id
    session.phase = CapturePhase.DRAFTING
    await deps.topics.add(topic)
    await deps.notes.add(note)
    existing_draft = NoteDraft(
        topic=topic,
        topic_reused=False,
        tags=[],
        tag_reused=[],
        content="Already set",
    )
    machine = _machine_with_deps(
        CaptureTurn(
            session=session,
            messages=(_user_message(session),),
            note=note,
            draft=existing_draft,
        ),
        deps,
    )

    await machine.apply(UserMessageRecorded(message=_user_message(session)))

    assert machine.context.draft is existing_draft
    assert existing_draft.content == "Already set"


async def test_user_message_recorded_skips_hydration_when_note_is_absent() -> None:
    deps = _capture_deps()
    session = CaptureSession.start()
    session.phase = CapturePhase.DRAFTING
    machine = _machine_with_deps(
        CaptureTurn(
            session=session,
            messages=(_user_message(session),),
            note=None,
            draft=None,
        ),
        deps,
    )

    await machine.apply(UserMessageRecorded(message=_user_message(session)))

    assert machine.context.draft is None
