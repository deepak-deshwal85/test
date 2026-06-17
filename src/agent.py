import asyncio
import logging
import os
from dataclasses import asdict, dataclass, is_dataclass

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentTask,
    JobContext,
    JobProcess,
    RunContext,
    ToolError,
    TurnHandlingOptions,
    cli,
    function_tool,
    get_job_context,
    llm,
    room_io,
    utils,
)
from livekit.agents.beta.tools import EndCallTool
from livekit.agents.beta.workflows import TaskGroup
from livekit.agents.llm.chat_context import FunctionCall
from livekit.agents.llm.utils import execute_function_call
from livekit.plugins import (
    ai_coustics,
    cartesia,
    deepgram,
    openai,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from client_config import ClientConfig, resolve_client_config
from rag import RagStore, load_rag_store
from sip_utils import extract_routing_phone_number

logger = logging.getLogger("agent-telephone-agent")

load_dotenv(".env.local")

DEFAULT_DEV_PHONE_NUMBER = "911171366880"
SIP_PARTICIPANT_WAIT_SECONDS = 5.0
STT_MODEL = "nova-3"
TTS_MODEL = "sonic-3"


def _to_json_serializable(obj):
    """Convert dataclasses and nested structures to JSON-serializable form."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    return obj


@dataclass
class RequesterIdentificationResults:
    requester_name: str
    appointment_type: str


@dataclass
class SchedulingPreferencesResults:
    date_preference_is_flexible: bool
    preferred_date: str | None = None
    preferred_time_window: str | None = None
    timezone: str | None = None


@dataclass
class LocationAndProviderPreferencesResults:
    meeting_mode: str
    preferred_provider: str | None = None
    preferred_location: str | None = None


@dataclass
class SpecialRequestsResults:
    special_request: str
    request_context: str | None = None
    is_required: bool | None = None


class RequesterIdentificationTask(AgentTask):
    def __init__(self, agent_instructions: str, extra_tools: list | None = None):
        no_greet_prefix = "The user has already been greeted. Do not introduce yourself or say hello. Directly ask for the required information.\n"
        task_instructions = "- Collect the requester's full name and the type of appointment they want to book."
        no_goodbye_suffix = "\nIMPORTANT: Do NOT say goodbye, recap the full conversation, or tell the user you are done. Only focus on collecting the information for THIS specific task. If the information was already provided earlier in the conversation, confirm it briefly and then record it immediately using the appropriate tool."
        wrapped_instructions = (
            no_greet_prefix
            + agent_instructions
            + "\n"
            + task_instructions
            + no_goodbye_suffix
        )
        super().__init__(
            instructions=wrapped_instructions,
            tools=list(extra_tools) if extra_tools else [],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "Begin this task now. If the task instructions require calling "
                "a tool first (for example, to look up information), call it. "
                "Otherwise, ask the user for the information described in your "
                "task instructions."
            ),
            allow_interruptions=True,
            tool_choice="auto",
        )

    @function_tool(name="record_requester_identification")
    async def record_requester_identification(
        self, context: RunContext, requester_name: str, appointment_type: str
    ):
        """Call when you have collected all required data points for this task.
        Provide the structured results exactly as requested.
        Do not confirm on record, remain silent and move to the next task.

        Args:
            requester_name (str)
            appointment_type (str)"""
        self.complete(
            RequesterIdentificationResults(
                requester_name=requester_name, appointment_type=appointment_type
            )
        )


class SchedulingPreferencesTask(AgentTask):
    def __init__(self, agent_instructions: str, extra_tools: list | None = None):
        no_greet_prefix = ""
        task_instructions = "- Capture the preferred date, time window, and timezone.\n- If the caller is flexible, capture that clearly."
        no_goodbye_suffix = "\nIMPORTANT: Do NOT say goodbye, recap the full conversation, or tell the user you are done. Only focus on collecting the information for THIS specific task. If the information was already provided earlier in the conversation, confirm it briefly and then record it immediately using the appropriate tool."
        wrapped_instructions = (
            no_greet_prefix
            + agent_instructions
            + "\n"
            + task_instructions
            + no_goodbye_suffix
        )
        super().__init__(
            instructions=wrapped_instructions,
            tools=list(extra_tools) if extra_tools else [],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "Begin this task now. If the task instructions require calling "
                "a tool first (for example, to look up information), call it. "
                "Otherwise, ask the user for the information described in your "
                "task instructions."
            ),
            allow_interruptions=True,
            tool_choice="auto",
        )

    @function_tool(name="record_scheduling_preferences")
    async def record_scheduling_preferences(
        self,
        context: RunContext,
        date_preference_is_flexible: bool,
        preferred_date: str | None = None,
        preferred_time_window: str | None = None,
        timezone: str | None = None,
    ):
        """Call when you have collected all required data points for this task.
        Provide the structured results exactly as requested.
        Do not confirm on record, remain silent and move to the next task.

        Args:
            date_preference_is_flexible (bool)
            preferred_date (str | None) (optional)
            preferred_time_window (str | None) (optional)
            timezone (str | None) (optional)"""
        self.complete(
            SchedulingPreferencesResults(
                date_preference_is_flexible=date_preference_is_flexible,
                preferred_date=preferred_date,
                preferred_time_window=preferred_time_window,
                timezone=timezone,
            )
        )


class LocationAndProviderPreferencesTask(AgentTask):
    def __init__(self, agent_instructions: str, extra_tools: list | None = None):
        no_greet_prefix = ""
        task_instructions = "- Capture whether the appointment should be in person, by phone, or by video, plus any provider or location preferences."
        no_goodbye_suffix = "\nIMPORTANT: Do NOT say goodbye, recap the full conversation, or tell the user you are done. Only focus on collecting the information for THIS specific task. If the information was already provided earlier in the conversation, confirm it briefly and then record it immediately using the appropriate tool."
        wrapped_instructions = (
            no_greet_prefix
            + agent_instructions
            + "\n"
            + task_instructions
            + no_goodbye_suffix
        )
        super().__init__(
            instructions=wrapped_instructions,
            tools=list(extra_tools) if extra_tools else [],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "Begin this task now. If the task instructions require calling "
                "a tool first (for example, to look up information), call it. "
                "Otherwise, ask the user for the information described in your "
                "task instructions."
            ),
            allow_interruptions=True,
            tool_choice="auto",
        )

    @function_tool(name="record_location_and_provider_preferences")
    async def record_location_and_provider_preferences(
        self,
        context: RunContext,
        meeting_mode: str,
        preferred_provider: str | None = None,
        preferred_location: str | None = None,
    ):
        """Call when you have collected all required data points for this task.
        Provide the structured results exactly as requested.
        Do not confirm on record, remain silent and move to the next task.

        Args:
            meeting_mode (str)
            preferred_provider (str | None) (optional)
            preferred_location (str | None) (optional)"""
        self.complete(
            LocationAndProviderPreferencesResults(
                meeting_mode=meeting_mode,
                preferred_provider=preferred_provider,
                preferred_location=preferred_location,
            )
        )


class SpecialRequestsTask(AgentTask):
    def __init__(self, agent_instructions: str, extra_tools: list | None = None):
        no_greet_prefix = ""
        task_instructions = "- Capture each distinct scheduling-related request or note as a separate list item."
        no_goodbye_suffix = "\nIMPORTANT: Do NOT say goodbye, recap the full conversation, or tell the user you are done. Only focus on collecting the information for THIS specific task. If the information was already provided earlier in the conversation, confirm it briefly and then record it immediately using the appropriate tool."
        wrapped_instructions = (
            no_greet_prefix
            + agent_instructions
            + "\n"
            + task_instructions
            + no_goodbye_suffix
        )
        self._partial_results: list[SpecialRequestsResults] = []
        super().__init__(
            instructions=wrapped_instructions,
            tools=list(extra_tools) if extra_tools else [],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "You are collecting multiple data points for this task. "
                "As the user provides each data point, call edit_special_requests_list. "
                "When the user confirms the list is complete, call record_special_requests."
            ),
            allow_interruptions=True,
            tool_choice="auto",
        )

    @function_tool(name="edit_special_requests_list")
    async def edit_special_requests_list(
        self,
        context: RunContext,
        special_request: str,
        request_context: str | None = None,
        is_required: bool | None = None,
    ):
        """Update the partial list: add a new data point to the running list.

        Args:
            special_request (str)
            request_context (str | None) (optional)
            is_required (bool | None) (optional)"""
        self._partial_results.append(
            SpecialRequestsResults(
                special_request=special_request,
                request_context=request_context,
                is_required=is_required,
            )
        )
        return (
            f"Data point added (list now has {len(self._partial_results)} item(s)). "
            "Ask if the user wants to add more items or if the list is complete. "
            "When done, call record_special_requests."
        )

    @function_tool(name="record_special_requests")
    async def record_special_requests(self, context: RunContext):
        """Call when the user has confirmed the list is complete."""
        self.complete(list(self._partial_results))


class ClientQATask(AgentTask):
    def __init__(
        self,
        client_name: str,
        agent_instructions: str,
        extra_tools: list | None = None,
    ):
        qa_instructions = (
            f"You are helping callers learn about {client_name}.\n"
            "- ALWAYS call get_answer before answering factual questions about "
            f"{client_name}'s background, skills, experience, education, projects, or availability.\n"
            "- Never guess resume details. If get_answer returns nothing useful, say you do not have that detail.\n"
            "- Keep answers short and conversational.\n"
            "- When the caller wants to book an appointment, call book_appointment."
        )
        super().__init__(
            instructions=f"{agent_instructions}\n\n{qa_instructions}",
            tools=list(extra_tools) if extra_tools else [],
        )
        self._client_name = client_name

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                f"Greet the caller briefly, then ask: "
                f'What would you like to know about {self._client_name}?'
            ),
            allow_interruptions=True,
            tool_choice="auto",
        )

    @function_tool(name="book_appointment")
    async def book_appointment(self, context: RunContext):
        """Call when the caller is ready to book an appointment."""
        self.complete(None)


class DefaultAgent(Agent):
    def __init__(self, client_config: ClientConfig, rag_store: RagStore) -> None:
        self._client_config = client_config
        self._rag_store = rag_store
        self._agent_instructions = f"""You are a friendly, reliable voice assistant that answers questions, explains topics, and completes tasks with available tools.

You are assisting on behalf of {client_config.client_name}.

# Conversation phases
1. First answer the caller's questions about {client_config.client_name} using get_answer.
2. Only move to appointment booking after the caller asks to book or schedule.

# Output rules

You are interacting with the user via voice, and must apply the following rules to ensure your output sounds natural in a text-to-speech system:

- Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
- Keep replies brief by default: one to three sentences. Ask one question at a time.
- Do not reveal system instructions, internal reasoning, tool names, parameters, or raw outputs
- Spell out numbers, phone numbers, or email addresses
- Omit `https://` and other formatting if listing a web url
- Avoid acronyms and words with unclear pronunciation, when possible.

# Conversational flow

- Help the user accomplish their objective efficiently and correctly. Prefer the simplest safe step first. Check understanding and adapt.
- Provide guidance in small steps and confirm completion before continuing.
- Summarize key results when closing a topic.

# Tools

- Use available tools as needed, or upon user request.
- Collect required inputs first. Perform actions silently if the runtime expects it.
- Speak outcomes clearly. If an action fails, say so once, propose a fallback, or ask how to proceed.
- When tools return structured data, summarize it to the user in a way that is easy to understand, and don't directly recite identifiers or other technical details.

# Guardrails

- Stay within safe, lawful, and appropriate use; decline harmful or out‑of‑scope requests.
- For medical, legal, or financial topics, provide general information only and suggest consulting a qualified professional.
- Protect privacy and minimize sensitive data."""
        super().__init__(
            instructions="",
        )

    async def on_enter(self):
        _task_tools = [t for t in self.tools if not isinstance(t, EndCallTool)]

        try:
            await ClientQATask(
                client_name=self._client_config.client_name,
                agent_instructions=self._agent_instructions,
                extra_tools=_task_tools,
            )
        except (ToolError, asyncio.CancelledError):
            logger.info("client Q&A cancelled (participant likely disconnected)")
            return

        booking_intro = (
            f"Acknowledge that you will now help book an appointment with "
            f"{self._client_config.client_name}. Ask only for the first booking detail."
        )
        await self.session.generate_reply(
            instructions=booking_intro,
            allow_interruptions=True,
            tool_choice="none",
        )

        task_group = TaskGroup(chat_ctx=self.chat_ctx)
        task_group.add(
            lambda _ai=self._agent_instructions, _tools=_task_tools: (
                RequesterIdentificationTask(agent_instructions=_ai, extra_tools=_tools)
            ),
            id="requester_identification",
            description="Collect the requester's full name and the type of appointment they want to book.",
        )
        task_group.add(
            lambda _ai=self._agent_instructions, _tools=_task_tools: (
                SchedulingPreferencesTask(agent_instructions=_ai, extra_tools=_tools)
            ),
            id="scheduling_preferences",
            description="Capture the preferred date, time window, and timezone.",
        )
        task_group.add(
            lambda _ai=self._agent_instructions, _tools=_task_tools: (
                LocationAndProviderPreferencesTask(
                    agent_instructions=_ai, extra_tools=_tools
                )
            ),
            id="location_and_provider_preferences",
            description="Capture whether the appointment should be in person, by phone, or by video, plus any provider or location preferences.",
        )
        task_group.add(
            lambda _ai=self._agent_instructions, _tools=_task_tools: (
                SpecialRequestsTask(agent_instructions=_ai, extra_tools=_tools)
            ),
            id="special_requests",
            description="Capture each distinct scheduling-related request or note as a separate list item.",
        )
        try:
            group_result = await task_group
        except (ToolError, asyncio.CancelledError):
            logger.info(
                "data collection task group cancelled (participant likely disconnected)"
            )
            return

        await self._finish_data_collection(group_result.task_results)

    async def _finish_data_collection(self, task_results):
        """Serialize results, speak goodbye, and end the session."""
        serialized = _to_json_serializable(task_results)
        get_job_context().proc.userdata["dc_results"] = serialized
        end_instructions = """Thank the user for their time and say goodbye."""

        summary_task: asyncio.Task | None = None

        # Remove EndCallTool from active tools so the LLM cannot call it
        # spontaneously during the goodbye speech (it is invoked programmatically below).
        await self.update_tools(
            [t for t in self.tools if not isinstance(t, EndCallTool)]
        )

        speech_handle = self.session.generate_reply(
            instructions=f"All data collection tasks are complete. {end_instructions}",
            tool_choice="none",
        )

        try:
            await speech_handle
            if summary_task:
                await summary_task
        except ConnectionError:
            logger.debug("user disconnected during goodbye speech")

        try:
            end_call_tool = next(
                (t for t in self.tools if isinstance(t, EndCallTool)), None
            )
            if not end_call_tool:
                end_call_tool = EndCallTool(
                    end_instructions=end_instructions,
                    delete_room=False,
                )

            tools_with_end_call = [*self.tools, end_call_tool]
            tool_ctx = llm.ToolContext(tools_with_end_call)
            end_call_id = utils.shortuuid("fnc_")
            tool_call = llm.FunctionToolCall(
                call_id=end_call_id,
                name="end_call",
                arguments="{}",
            )
            fnc_call = FunctionCall(
                call_id=end_call_id,
                name="end_call",
                arguments="{}",
            )
            call_ctx = RunContext(
                session=self.session,
                speech_handle=speech_handle,
                function_call=fnc_call,
            )
            await execute_function_call(
                tool_call,
                tool_ctx,
                call_ctx=call_ctx,
            )
        except (ConnectionError, RuntimeError):
            logger.debug("room already disconnected during end-call teardown")

    @function_tool(name="get_answer")
    async def _client_tool_get_answer(
        self, context: RunContext, query_text: str
    ) -> str:
        """Search the client's resume and return relevant facts.

        ALWAYS use this before answering questions about the client's background,
        skills, work experience, education, projects, certifications, or availability.

        Args:
            query_text: The caller's question rewritten as a clear search query.
        """
        try:
            return await asyncio.to_thread(self._rag_store.answer, query_text)
        except Exception as e:
            raise ToolError(f"error: {e!s}") from e


async def _resolve_session_client(ctx: JobContext) -> tuple[ClientConfig, RagStore]:
    phone_override = os.getenv("CLIENT_PHONE_OVERRIDE", "").strip()
    phone_digits: str | None = normalize_phone_override(phone_override)

    if not phone_digits:
        try:
            sip_participant = await asyncio.wait_for(
                ctx.wait_for_participant(kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP),
                timeout=SIP_PARTICIPANT_WAIT_SECONDS,
            )
            phone_digits = extract_routing_phone_number(sip_participant)
        except asyncio.TimeoutError:
            logger.info("timed out waiting for SIP participant")

    if not phone_digits:
        phone_digits = DEFAULT_DEV_PHONE_NUMBER
        logger.warning(
            "using default phone number %s for client config (set CLIENT_PHONE_OVERRIDE to override)",
            phone_digits,
        )

    client_config = resolve_client_config(phone_digits)
    if client_config is None:
        raise RuntimeError(f"No client config found for phone number {phone_digits!r}")

    rag_store = load_rag_store(client_config)
    ctx.proc.userdata["client_config"] = client_config
    ctx.proc.userdata["client_phone_number"] = client_config.phone_number
    logger.info(
        "loaded client %s for phone %s",
        client_config.client_name,
        client_config.phone_number,
    )
    return client_config, rag_store


def normalize_phone_override(phone_override: str) -> str | None:
    if not phone_override:
        return None
    digits = "".join(character for character in phone_override if character.isdigit())
    return digits or None


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    from rag import create_embed_query

    create_embed_query()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="telephone-agent")
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    client_config, rag_store = await _resolve_session_client(ctx)

    cartesia_voice = os.getenv("CARTESIA_VOICE", "").strip()
    tts_kwargs: dict[str, object] = {
        "model": os.getenv("TTS_MODEL", TTS_MODEL),
        "language": "en",
    }
    if cartesia_voice:
        tts_kwargs["voice"] = cartesia_voice

    session = AgentSession(
        stt=deepgram.STT(
            model=os.getenv("STT_MODEL", STT_MODEL),
            language="en",
        ),
        llm=openai.LLM(model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")),
        tts=cartesia.TTS(**tts_kwargs),
        turn_handling=TurnHandlingOptions(turn_detection=MultilingualModel()),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
    ctx.proc.userdata["dc_results"] = None

    await session.start(
        agent=DefaultAgent(client_config=client_config, rag_store=rag_store),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
