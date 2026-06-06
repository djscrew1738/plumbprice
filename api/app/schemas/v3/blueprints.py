from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlueprintTakeoffV3(BaseModel):
    job_id: int
    fixtures: list[dict]
    rooms: list[dict]
    pipe_runs: list[dict]
    pages: list[dict]
    needs_review: list[dict]
    total_fixture_count: int
    total_room_count: int
    total_pipe_run_ft: float
