from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def record(**values):
    return SimpleNamespace(**values)


@asynccontextmanager
async def client_context(client):
    yield client


@pytest.fixture
def notebook():
    return record(id="nb-1", title="Research", sources_count=2, is_owner=True)


@pytest.fixture
def source():
    return record(
        id="src-1",
        title="Example",
        url="https://example.com",
        kind="web_page",
        status="ready",
    )


@pytest.fixture
def client(notebook, source):
    generation_started = record(task_id="task-1", status="in_progress")
    generation_done = record(task_id="task-1", status="completed", metadata={"pages": 3})
    research_started = record(task_id="research-1")
    research_done = record(
        task_id="research-1",
        status="completed",
        sources=[{"url": "https://example.com/result", "title": "Result"}],
    )
    answer = record(
        answer="Grounded answer [1]",
        references=[{"source_id": "src-1", "citation_number": 1}],
        conversation_id="conversation-1",
    )
    artifacts = SimpleNamespace(
        generate_audio=AsyncMock(return_value=generation_started),
        generate_video=AsyncMock(return_value=generation_started),
        generate_cinematic_video=AsyncMock(return_value=generation_started),
        generate_slide_deck=AsyncMock(return_value=generation_started),
        generate_report=AsyncMock(return_value=generation_started),
        generate_study_guide=AsyncMock(return_value=generation_started),
        generate_quiz=AsyncMock(return_value=generation_started),
        generate_flashcards=AsyncMock(return_value=generation_started),
        generate_mind_map=AsyncMock(return_value=record(note_id="note-1", mind_map={"name": "Root"})),
        generate_infographic=AsyncMock(return_value=generation_started),
        generate_data_table=AsyncMock(return_value=generation_started),
        wait_for_completion=AsyncMock(return_value=generation_done),
        list=AsyncMock(return_value=[record(id="task-1", title="Deck", kind="slide_deck", status="completed")]),
        download_audio=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_video=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_slide_deck=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_report=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_quiz=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_flashcards=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_mind_map=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_infographic=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
        download_data_table=AsyncMock(side_effect=lambda _nb, path, **_kwargs: path),
    )
    return SimpleNamespace(
        notebooks=SimpleNamespace(
            list=AsyncMock(return_value=[notebook]),
            create=AsyncMock(return_value=notebook),
            delete=AsyncMock(return_value=None),
            get_summary=AsyncMock(return_value="Notebook summary"),
        ),
        sources=SimpleNamespace(
            list=AsyncMock(return_value=[source]),
            add_url=AsyncMock(return_value=source),
            add_text=AsyncMock(return_value=source),
            add_file=AsyncMock(return_value=source),
        ),
        chat=SimpleNamespace(ask=AsyncMock(return_value=answer)),
        artifacts=artifacts,
        research=SimpleNamespace(
            start=AsyncMock(return_value=research_started),
            wait_for_completion=AsyncMock(return_value=research_done),
            import_sources=AsyncMock(return_value=[{"id": "src-imported", "title": "Result"}]),
        ),
    )
