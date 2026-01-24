"""
MedVoice AI - NVIDIA PersonaPlex Client
Full-duplex conversational AI client for natural voice interactions.

PersonaPlex enables simultaneous listening and speaking, supporting:
- Natural interruptions
- Backchannels ("uh-huh", "I see")
- Ultra-low latency responses
- Voice activity detection
"""

import asyncio
import logging
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Callable, Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PersonaPlexEvent(Enum):
    """Events emitted by the PersonaPlex stream."""
    AUDIO_CHUNK = "audio_chunk"           # Agent speaking audio
    TRANSCRIPT_PARTIAL = "transcript_partial"  # Partial user transcript
    TRANSCRIPT_FINAL = "transcript_final"      # Final user transcript
    AGENT_TEXT = "agent_text"             # Agent's text output
    TOOL_CALL = "tool_call"               # Tool call detected
    BACKCHANNEL = "backchannel"           # Backchannel utterance
    INTERRUPTION = "interruption"         # User interrupted agent
    TURN_START = "turn_start"             # Agent starting to speak
    TURN_END = "turn_end"                 # Agent finished speaking
    SESSION_END = "session_end"           # Session terminated
    ERROR = "error"                       # Error occurred


@dataclass
class PersonaPlexConfig:
    """Configuration for PersonaPlex connection."""
    # Connection settings
    endpoint_url: str = "wss://personaplex.nvidia.com/v1/stream"
    api_key: str = ""

    # Voice settings
    voice_id: str = "fr-CA-SylvieNeural"  # Default French Canadian voice
    voice_embedding_path: Optional[str] = None  # Custom voice embedding

    # Audio settings
    input_sample_rate: int = 16000   # Input audio sample rate (Hz)
    output_sample_rate: int = 24000  # Output audio sample rate (Hz)
    input_encoding: str = "pcm_s16le"  # Input audio encoding
    output_encoding: str = "pcm_s16le"  # Output audio encoding

    # Behavior settings
    enable_backchannels: bool = True
    enable_interruptions: bool = True
    vad_threshold: float = 0.5       # Voice activity detection threshold
    silence_timeout_ms: int = 700    # Silence before turn ends
    max_turn_duration_ms: int = 30000  # Max agent speaking time

    # Language settings
    primary_language: str = "fr-CA"
    secondary_language: str = "en-US"
    auto_language_switch: bool = True


@dataclass
class StreamEvent:
    """An event from the PersonaPlex stream."""
    event_type: PersonaPlexEvent
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ToolCallRequest:
    """Parsed tool call from PersonaPlex output."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str
    raw_output: str


class PersonaPlexTransport(ABC):
    """Abstract transport layer for PersonaPlex communication."""

    @abstractmethod
    async def connect(self, config: PersonaPlexConfig, system_prompt: str) -> None:
        """Establish connection to PersonaPlex."""
        pass

    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk to PersonaPlex."""
        pass

    @abstractmethod
    async def send_tool_result(self, call_id: str, result: str) -> None:
        """Send tool execution result back to PersonaPlex."""
        pass

    @abstractmethod
    async def receive_events(self) -> AsyncIterator[StreamEvent]:
        """Receive events from PersonaPlex."""
        pass

    @abstractmethod
    async def interrupt(self) -> None:
        """Signal an interruption (e.g., emergency detected)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass


class WebSocketTransport(PersonaPlexTransport):
    """
    WebSocket-based transport for PersonaPlex.

    This is a skeleton implementation - actual library calls will be
    added when NVIDIA's PersonaPlex SDK is available.
    """

    def __init__(self):
        self._ws = None
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()

    async def connect(self, config: PersonaPlexConfig, system_prompt: str) -> None:
        """
        Establish WebSocket connection to PersonaPlex.

        Protocol:
        1. Connect to endpoint with auth headers
        2. Send initialization message with config + system prompt
        3. Wait for ready acknowledgment
        """
        logger.info(f"Connecting to PersonaPlex at {config.endpoint_url}")

        try:
            # NOTE: Replace with actual websockets library when SDK available
            # import websockets
            # self._ws = await websockets.connect(
            #     config.endpoint_url,
            #     extra_headers={
            #         "Authorization": f"Bearer {config.api_key}",
            #         "X-PersonaPlex-Version": "1.0"
            #     }
            # )

            # Send initialization payload
            init_payload = {
                "type": "session.init",
                "config": {
                    "voice_id": config.voice_id,
                    "voice_embedding": config.voice_embedding_path,
                    "input_audio": {
                        "sample_rate": config.input_sample_rate,
                        "encoding": config.input_encoding
                    },
                    "output_audio": {
                        "sample_rate": config.output_sample_rate,
                        "encoding": config.output_encoding
                    },
                    "behavior": {
                        "enable_backchannels": config.enable_backchannels,
                        "enable_interruptions": config.enable_interruptions,
                        "vad_threshold": config.vad_threshold,
                        "silence_timeout_ms": config.silence_timeout_ms,
                        "max_turn_duration_ms": config.max_turn_duration_ms
                    },
                    "language": {
                        "primary": config.primary_language,
                        "secondary": config.secondary_language,
                        "auto_switch": config.auto_language_switch
                    }
                },
                "system_prompt": system_prompt
            }

            # await self._ws.send(json.dumps(init_payload))
            logger.info("PersonaPlex initialization sent, awaiting ready...")

            # Start receive loop
            # self._receive_task = asyncio.create_task(self._receive_loop())

            self._connected = True
            logger.info("PersonaPlex connection established")

        except Exception as e:
            logger.error(f"Failed to connect to PersonaPlex: {e}")
            raise ConnectionError(f"PersonaPlex connection failed: {e}")

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send raw audio bytes to PersonaPlex."""
        if not self._connected:
            raise RuntimeError("Not connected to PersonaPlex")

        # Binary message for audio
        # await self._ws.send(audio_chunk)
        pass

    async def send_tool_result(self, call_id: str, result: str) -> None:
        """Send tool execution result back to PersonaPlex."""
        if not self._connected:
            raise RuntimeError("Not connected to PersonaPlex")

        payload = {
            "type": "tool.result",
            "call_id": call_id,
            "result": result
        }
        # await self._ws.send(json.dumps(payload))
        logger.debug(f"Sent tool result for {call_id}")

    async def interrupt(self) -> None:
        """
        Signal an interruption - immediately stop agent audio output.
        Used for emergency keyword detection.
        """
        if not self._connected:
            return

        payload = {"type": "interrupt"}
        # await self._ws.send(json.dumps(payload))
        logger.info("Sent interrupt signal to PersonaPlex")

    async def receive_events(self) -> AsyncIterator[StreamEvent]:
        """Yield events from the event queue."""
        while self._connected:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.1
                )
                yield event
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error receiving events: {e}")
                break

    async def _receive_loop(self) -> None:
        """Background task to receive and parse WebSocket messages."""
        try:
            async for message in self._ws:
                event = self._parse_message(message)
                if event:
                    await self._event_queue.put(event)
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            await self._event_queue.put(StreamEvent(
                event_type=PersonaPlexEvent.ERROR,
                data={"error": str(e)}
            ))

    def _parse_message(self, message) -> Optional[StreamEvent]:
        """Parse a WebSocket message into a StreamEvent."""
        try:
            # Binary messages are audio
            if isinstance(message, bytes):
                return StreamEvent(
                    event_type=PersonaPlexEvent.AUDIO_CHUNK,
                    data=message
                )

            # JSON messages are events
            data = json.loads(message)
            event_type_str = data.get("type", "")

            event_map = {
                "transcript.partial": PersonaPlexEvent.TRANSCRIPT_PARTIAL,
                "transcript.final": PersonaPlexEvent.TRANSCRIPT_FINAL,
                "agent.text": PersonaPlexEvent.AGENT_TEXT,
                "tool.call": PersonaPlexEvent.TOOL_CALL,
                "backchannel": PersonaPlexEvent.BACKCHANNEL,
                "interruption": PersonaPlexEvent.INTERRUPTION,
                "turn.start": PersonaPlexEvent.TURN_START,
                "turn.end": PersonaPlexEvent.TURN_END,
                "session.end": PersonaPlexEvent.SESSION_END,
                "error": PersonaPlexEvent.ERROR
            }

            event_type = event_map.get(event_type_str)
            if event_type:
                return StreamEvent(event_type=event_type, data=data)

            logger.warning(f"Unknown event type: {event_type_str}")
            return None

        except json.JSONDecodeError:
            logger.error(f"Failed to parse message: {message[:100]}")
            return None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # if self._ws:
        #     await self._ws.close()

        logger.info("PersonaPlex connection closed")


class ToolCallParser:
    """
    Parses tool calls from PersonaPlex agent text output.

    PersonaPlex may output tool calls in various formats:
    1. Structured JSON: {"tool": "name", "args": {...}}
    2. Tagged format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    3. Function-style: CALL: function_name(arg1="val1", arg2="val2")
    """

    # Regex patterns for different tool call formats
    PATTERNS = [
        # JSON format with tool_call tags
        re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL),
        # Direct JSON object with "tool" key
        re.compile(r'\{["\']tool["\']:\s*["\'](\w+)["\'].*?\}', re.DOTALL),
        # Function call style
        re.compile(r'CALL:\s*(\w+)\s*\((.*?)\)', re.DOTALL),
    ]

    @classmethod
    def parse(cls, text: str) -> Optional[ToolCallRequest]:
        """
        Attempt to parse a tool call from text.

        Returns ToolCallRequest if found, None otherwise.
        """
        # Try JSON with tags first
        match = cls.PATTERNS[0].search(text)
        if match:
            try:
                data = json.loads(match.group(1))
                return ToolCallRequest(
                    tool_name=data.get("name") or data.get("tool", ""),
                    arguments=data.get("arguments") or data.get("args", {}),
                    call_id=data.get("id", f"tc_{datetime.utcnow().timestamp()}"),
                    raw_output=match.group(0)
                )
            except json.JSONDecodeError:
                pass

        # Try direct JSON
        match = cls.PATTERNS[1].search(text)
        if match:
            try:
                # Find the full JSON object
                start = text.find('{', match.start())
                depth = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break

                data = json.loads(text[start:end])
                return ToolCallRequest(
                    tool_name=data.get("tool", ""),
                    arguments=data.get("args") or data.get("arguments", {}),
                    call_id=f"tc_{datetime.utcnow().timestamp()}",
                    raw_output=text[start:end]
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Try function call style
        match = cls.PATTERNS[2].search(text)
        if match:
            func_name = match.group(1)
            args_str = match.group(2)

            # Parse key="value" pairs
            args = {}
            for arg_match in re.finditer(r'(\w+)\s*=\s*["\']?([^"\'",]+)["\']?', args_str):
                args[arg_match.group(1)] = arg_match.group(2)

            return ToolCallRequest(
                tool_name=func_name,
                arguments=args,
                call_id=f"tc_{datetime.utcnow().timestamp()}",
                raw_output=match.group(0)
            )

        return None


class PersonaPlexClient:
    """
    High-level client for NVIDIA PersonaPlex full-duplex conversations.

    This client manages:
    - Audio streaming (bidirectional)
    - Text transcript collection
    - Tool call detection and delegation
    - Emergency interruption handling
    - Session lifecycle

    Usage:
        client = PersonaPlexClient(config)
        await client.start_session(system_prompt, tool_handler)

        # Push audio continuously
        async for audio_chunk in microphone_stream:
            await client.push_audio(audio_chunk)

        # Receive agent audio and events
        async for event in client.events():
            if event.event_type == PersonaPlexEvent.AUDIO_CHUNK:
                play_audio(event.data)
            elif event.event_type == PersonaPlexEvent.AGENT_TEXT:
                log_transcript(event.data)
    """

    def __init__(
        self,
        config: PersonaPlexConfig,
        transport: Optional[PersonaPlexTransport] = None
    ):
        self.config = config
        self._transport = transport or WebSocketTransport()

        # Session state
        self._session_active = False
        self._current_language = config.primary_language

        # Tool handling
        self._tool_handler: Optional[Callable] = None
        self._pending_tool_calls: Dict[str, ToolCallRequest] = {}

        # Transcript accumulation
        self._user_transcript_buffer = ""
        self._agent_transcript_buffer = ""
        self._full_transcript: List[Dict[str, Any]] = []

        # Interruption state
        self._interrupted = False

        # Event callbacks
        self._on_tool_call: Optional[Callable[[ToolCallRequest], Any]] = None
        self._on_emergency: Optional[Callable[[str], None]] = None
        self._on_transcript: Optional[Callable[[str, str], None]] = None

    async def start_session(
        self,
        system_prompt: str,
        tool_handler: Optional[Callable[[str, Dict], Any]] = None,
        on_emergency: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Start a PersonaPlex conversation session.

        Args:
            system_prompt: The persona/instruction prompt for the agent
            tool_handler: Async function to execute tool calls: (name, args) -> result
            on_emergency: Callback when emergency keyword detected
        """
        logger.info("Starting PersonaPlex session")

        self._tool_handler = tool_handler
        self._on_emergency = on_emergency
        self._session_active = True

        await self._transport.connect(self.config, system_prompt)

        logger.info("PersonaPlex session started")

    async def push_audio(self, audio_chunk: bytes) -> None:
        """
        Push audio data from the user's microphone.

        Args:
            audio_chunk: Raw audio bytes (PCM format)
        """
        if not self._session_active:
            raise RuntimeError("Session not active")

        await self._transport.send_audio(audio_chunk)

    async def events(self) -> AsyncIterator[StreamEvent]:
        """
        Async generator yielding events from the PersonaPlex stream.

        Handles:
        - Audio chunks (pass through for playback)
        - Transcripts (accumulate and log)
        - Tool calls (intercept, execute, return result)
        - Interruptions (handle emergency keywords)
        """
        async for event in self._transport.receive_events():
            # Process event internally
            processed_event = await self._process_event(event)

            # Yield to caller (they handle audio playback, UI updates, etc.)
            if processed_event:
                yield processed_event

            # Check for session end
            if event.event_type == PersonaPlexEvent.SESSION_END:
                self._session_active = False
                break

    async def _process_event(self, event: StreamEvent) -> Optional[StreamEvent]:
        """Process an event internally and optionally modify it."""

        if event.event_type == PersonaPlexEvent.TRANSCRIPT_PARTIAL:
            # Accumulate partial transcript
            self._user_transcript_buffer = event.data.get("text", "")
            return event

        elif event.event_type == PersonaPlexEvent.TRANSCRIPT_FINAL:
            # Final user transcript - check for emergencies
            user_text = event.data.get("text", "")
            self._user_transcript_buffer = ""

            # Log to full transcript
            self._full_transcript.append({
                "speaker": "user",
                "text": user_text,
                "timestamp": event.timestamp.isoformat()
            })

            # Callback for transcript logging
            if self._on_transcript:
                self._on_transcript("user", user_text)

            return event

        elif event.event_type == PersonaPlexEvent.AGENT_TEXT:
            # Agent text output - check for tool calls
            agent_text = event.data.get("text", "")
            self._agent_transcript_buffer += agent_text

            # Try to parse tool call
            tool_call = ToolCallParser.parse(self._agent_transcript_buffer)
            if tool_call:
                # Clear buffer and handle tool call
                self._agent_transcript_buffer = ""
                await self._handle_tool_call(tool_call)

                # Return tool call event instead
                return StreamEvent(
                    event_type=PersonaPlexEvent.TOOL_CALL,
                    data=tool_call
                )

            # Log agent text
            if agent_text.strip():
                self._full_transcript.append({
                    "speaker": "agent",
                    "text": agent_text,
                    "timestamp": event.timestamp.isoformat()
                })

                if self._on_transcript:
                    self._on_transcript("agent", agent_text)

            return event

        elif event.event_type == PersonaPlexEvent.TURN_END:
            # Clear agent buffer on turn end
            self._agent_transcript_buffer = ""
            return event

        elif event.event_type == PersonaPlexEvent.INTERRUPTION:
            logger.info("User interrupted agent")
            self._interrupted = True
            return event

        return event

    async def _handle_tool_call(self, tool_call: ToolCallRequest) -> None:
        """Execute a tool call and send result back to PersonaPlex."""
        logger.info(f"Executing tool: {tool_call.tool_name}")

        if not self._tool_handler:
            logger.warning("No tool handler configured")
            await self._transport.send_tool_result(
                tool_call.call_id,
                json.dumps({"error": "Tool execution not available"})
            )
            return

        try:
            # Execute the tool
            result = await self._tool_handler(
                tool_call.tool_name,
                tool_call.arguments
            )

            # Send result back to PersonaPlex
            result_str = result if isinstance(result, str) else json.dumps(result)
            await self._transport.send_tool_result(tool_call.call_id, result_str)

            logger.info(f"Tool {tool_call.tool_name} completed")

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            await self._transport.send_tool_result(
                tool_call.call_id,
                json.dumps({"error": str(e)})
            )

    async def trigger_emergency_interrupt(self, emergency_text: str) -> None:
        """
        Immediately interrupt the agent for an emergency.

        This stops any ongoing agent speech and triggers the emergency callback.
        """
        logger.warning(f"Emergency interrupt triggered: {emergency_text}")

        # Send interrupt signal to stop agent audio
        await self._transport.interrupt()

        # Trigger emergency callback
        if self._on_emergency:
            self._on_emergency(emergency_text)

        self._interrupted = True

    async def inject_text(self, text: str) -> None:
        """
        Inject text directly into the conversation (e.g., emergency message).

        This is used when we need to override the agent's response,
        such as for emergency messages.
        """
        # This would send a special message to PersonaPlex to speak specific text
        payload = {
            "type": "inject.text",
            "text": text,
            "priority": "high"
        }
        # await self._transport._ws.send(json.dumps(payload))
        logger.info(f"Injected text: {text[:50]}...")

    async def end_session(self) -> Dict[str, Any]:
        """
        End the PersonaPlex session gracefully.

        Returns:
            Session summary with transcript and metrics
        """
        logger.info("Ending PersonaPlex session")

        self._session_active = False
        await self._transport.close()

        return {
            "transcript": self._full_transcript,
            "language": self._current_language,
            "interrupted": self._interrupted
        }

    def get_transcript(self) -> List[Dict[str, Any]]:
        """Get the full conversation transcript."""
        return self._full_transcript.copy()

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self._session_active


class PersonaPlexClientFactory:
    """Factory for creating PersonaPlex clients with different configurations."""

    @staticmethod
    def create_for_clinic(
        api_key: str,
        voice_id: str = "fr-CA-SylvieNeural",
        voice_embedding_path: Optional[str] = None,
        endpoint_url: str = "wss://personaplex.nvidia.com/v1/stream"
    ) -> PersonaPlexClient:
        """
        Create a PersonaPlex client configured for medical clinic use.

        Args:
            api_key: NVIDIA PersonaPlex API key
            voice_id: Voice identifier for TTS
            voice_embedding_path: Path to custom voice embedding file
            endpoint_url: PersonaPlex WebSocket endpoint

        Returns:
            Configured PersonaPlexClient
        """
        config = PersonaPlexConfig(
            endpoint_url=endpoint_url,
            api_key=api_key,
            voice_id=voice_id,
            voice_embedding_path=voice_embedding_path,
            # Medical clinic optimizations
            enable_backchannels=True,  # Reassuring feedback
            enable_interruptions=True,  # Allow patient to interrupt
            vad_threshold=0.4,  # Slightly lower threshold for quieter speakers
            silence_timeout_ms=800,  # Slightly longer for elderly patients
            max_turn_duration_ms=45000,  # Allow longer explanations
            primary_language="fr-CA",
            secondary_language="en-US",
            auto_language_switch=True
        )

        return PersonaPlexClient(config)
