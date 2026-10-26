"""Gemini-powered elective planning assistant with a deterministic fallback."""

from __future__ import annotations

import logging
from typing import Sequence

from .config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE
from .schemas import ChatResponse, ChatTurn, PlannerResponse
from .services import CatalogEntry, fallback_answer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Lex, the elective planning assistant for a law school trimester.

Your job:
- Help a student choose up to four electives from the catalogue.
- Explain timetable clashes, suggest clash-free alternatives, and describe the weekly calendar.
- The first elective is unrestricted. Every later elective must avoid the same weekday and overlapping class time.
- Be concise: at most 220 words, short bullets, no fluff.

Hard rules:
- Use only the catalogue and planner state provided below. Never invent course titles, faculty, credits, rooms, days, or times.
- If a course is not in the catalogue, say it is not offered in this data.
- When you mention a course, use its exact title and its published schedule.
- Do not claim a course is compatible unless the planner status says "compatible".
- If the student has no selection, invite them to pick any first elective.
- If the question is unrelated to elective planning, briefly redirect.
- Never mention internal IDs unless the student asks for them.
"""


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


class ElectiveAssistant:
    def __init__(self) -> None:
        self._llm = None
        self._init_error: str | None = None
        if not GEMINI_API_KEY:
            self._init_error = "No Gemini API key configured"
            return
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=LLM_TEMPERATURE,
            )
        except Exception as exc:  # pragma: no cover - depends on local environment
            self._init_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Gemini assistant unavailable: %s", self._init_error)

    @property
    def configured(self) -> bool:
        return self._llm is not None

    @property
    def model(self) -> str:
        return GEMINI_MODEL

    async def answer(
        self,
        question: str,
        context: str,
        history: Sequence[ChatTurn],
        entries: Sequence[CatalogEntry],
        planner: PlannerResponse,
    ) -> ChatResponse:
        if self._llm is None:
            return ChatResponse(
                answer=fallback_answer(question, entries, planner),
                provider="fallback",
                model=None,
            )

        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=SYSTEM_PROMPT + "\n\n" + context),
            ]
            for turn in history[-8:]:
                if turn.role == "user":
                    messages.append(HumanMessage(content=turn.content))
                else:
                    messages.append(AIMessage(content=turn.content))
            messages.append(HumanMessage(content=question))

            response = await self._llm.ainvoke(messages)
            text = _content_to_text(response.content).strip()
            if not text:
                raise ValueError("Gemini returned an empty answer")
            return ChatResponse(answer=text, provider="gemini", model=GEMINI_MODEL)
        except Exception as exc:  # pragma: no cover - network/API dependent
            logger.warning("Gemini request failed (%s); using fallback", type(exc).__name__)
            return ChatResponse(
                answer=fallback_answer(question, entries, planner),
                provider="fallback",
                model=None,
            )


assistant = ElectiveAssistant()
