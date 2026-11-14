"""Stage 4 research pipeline package."""

def run_meeting_research(*args, **kwargs):
    from app.services.research_pipeline.research_service import run_meeting_research as _run

    return _run(*args, **kwargs)


__all__ = ["run_meeting_research"]
