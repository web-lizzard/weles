from collections.abc import Sequence

from domain.capture.capture_session import CaptureSession
from domain.capture.graph import (
    CaptureMachine,
    ConversationRequestSignal,
    Conversing,
    CoverageAssessed,
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
from domain.capture.turn import (
    AssistantMessageRecorded,
    CaptureTurn,
    ConversationRequested,
    DraftingConsentSignalled,
    NoteContentProduced,
    ReplyProduced,
    SessionTopicProposed,
    UserMessageRecorded,
)
from domain.capture.value_objects import (
    CapturePhase,
    ConversationRequest,
    DraftingConsent,
    Label,
    MessageContent,
    MessageRole,
    NoteContent,
    SessionTopic,
)
from domain.shared.graph.model import Tool, ToolResult


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


def _tool_names(tools: Sequence[Tool[CaptureTurn, ToolResult]]) -> set[str]:
    return {tool.name for tool in tools}


async def test_at_most_one_available_transition_and_each_intent_opens_its_edge() -> (
    None
):
    graph = CaptureMachine(_turn()).graph
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
    assert CaptureMachine(idle).available_transitions() == {}
    assert await CaptureMachine(idle).transition(CapturePhase.DRAFTING) is False
    assert CaptureMachine(consented).available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }
    assert CaptureMachine(drafting).available_transitions() == {}
    assert await CaptureMachine(drafting).transition(CapturePhase.CONVERSING) is False
    assert CaptureMachine(returning).available_transitions() == {
        CapturePhase.CONVERSING: Conversing().description,
    }
    assert CaptureMachine(both_intents_while_conversing).available_transitions() == {
        CapturePhase.DRAFTING: Drafting().description,
    }
    for turn in (
        idle,
        consented,
        drafting,
        returning,
        both_intents_while_conversing,
    ):
        assert len(CaptureMachine(turn).available_transitions()) <= 1


def test_conversing_withholds_the_session_topic_tool_once_the_session_has_one() -> None:
    unnamed = CaptureMachine(_turn())
    named = CaptureMachine(_turn(topic=SessionTopic(value="TCP handshakes")))
    drafting = CaptureMachine(_turn(phase=CapturePhase.DRAFTING))

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
    machine = CaptureMachine(_turn())
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

    assert Drafting().get_actions(machine.context, note_chunk) == ()
    assert Drafting().get_actions(machine.context, requested) != ()

    await machine.apply(requested)
    await machine.apply(note_chunk)

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
    machine = CaptureMachine(_turn(messages=()))
    consent = DraftingConsentSignalled()

    assert Conversing().get_actions(machine.context, consent)

    await machine.apply(consent)

    assert machine.context.session.drafting_consent is None
    assert machine.available_transitions() == {}
    assert await machine.transition(CapturePhase.DRAFTING) is False


async def test_proposal_tools_return_results_built_from_the_model_arguments() -> None:
    conversing = CaptureMachine(_turn())
    conversing_tools = {tool.name: tool for tool in Conversing().tools}
    drafting_tools = {tool.name: tool for tool in Drafting().tools}

    coverage = await conversing_tools["assess_coverage"].handler(
        conversing.context, {"coverage": 0.4}
    )
    session_topic = await conversing_tools["propose_session_topic"].handler(
        conversing.context, {"topic": "TCP handshakes"}
    )
    assert coverage == CoverageAssessed(coverage=0.4)
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

    assert coverage == CoverageAssessed(coverage=0.4)
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
    machine = CaptureMachine(_turn(messages=()))
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
    machine = CaptureMachine(_turn(phase=CapturePhase.DRAFTING, messages=()))
    incoming = _assistant_message(machine.context.session)
    recorded = AssistantMessageRecorded(message=incoming)
    user_recorded = UserMessageRecorded(message=_user_message(machine.context.session))

    assert Drafting().get_actions(machine.context, recorded) != ()
    assert Drafting().get_actions(machine.context, user_recorded) != ()
    assert Conversing().get_actions(machine.context, recorded) != ()

    await machine.apply(recorded)

    assert incoming in machine.context.messages
