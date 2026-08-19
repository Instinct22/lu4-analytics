from typing import Literal

from pydantic import BaseModel

LifeStatus = Literal["yes", "no"]


class RaidBossLifeItem(BaseModel):
    name: str
    life: LifeStatus


class RaidBossLifeResponse(BaseModel):
    bosses: list[RaidBossLifeItem]
