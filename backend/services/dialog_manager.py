from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from services.llm_agent import DeepSeekAgent


class DialogManager:
    """Manages multi-turn dialog sessions for travel planning.

    Coordinates between user messages, intent parsing, algorithm
    selection, and LLM-based response generation.
    """

    def __init__(self):
        self.agent = DeepSeekAgent()
        # In-memory session store: { dialog_id: [messages] }
        self._sessions: dict[str, list[dict]] = {}

    def _get_or_create_session(self, dialog_id: str | None = None) -> tuple[str, list[dict]]:
        if dialog_id and dialog_id in self._sessions:
            return dialog_id, self._sessions[dialog_id]
        new_id = dialog_id or str(uuid.uuid4())
        self._sessions[new_id] = []
        return new_id, self._sessions[new_id]

    async def process_message(
        self,
        message: str,
        dialog_id: str | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Process an incoming user message and yield response chunks.

        Yields:
            dict with keys: "dialog_id", "content", "done", and optionally "intent" / "plan".
        """
        did, history = self._get_or_create_session(dialog_id)
        history.append({"role": "user", "content": message})

        # Step 1: Parse intent
        intent = await self.agent.parse_user_intent(message)
        yield {"dialog_id": did, "content": "", "done": False, "intent": intent}

        # Step 2: Stream LLM response
        destination = intent.get("destination_city")
        if destination:
            async for token in self.agent.plan_route_stream(
                destination_city=destination,
                days=intent.get("days", 3),
                budget=intent.get("budget", "medium"),
                travel_style=intent.get("travel_style"),
            ):
                yield {"dialog_id": did, "content": token, "done": False}
        else:
            # No destination detected -- ask clarifying question
            clarification = "Could you tell me which city you'd like to visit? "
            for word in clarification.split(" "):
                yield {"dialog_id": did, "content": word + " ", "done": False}

        yield {"dialog_id": did, "content": "", "done": True}
