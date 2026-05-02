from typing import TypedDict
from asyncio import Task


class WLScheduleEntry(TypedDict):
    post_id: str
    task: Task
    timestamp: int
