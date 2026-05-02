from typing import TypedDict
from asyncio import Task


class WLScheduleEntry(TypedDict):
    link: str
    post_id: str
    task: Task | None
    timestamp: int
