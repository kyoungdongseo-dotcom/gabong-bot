import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class Reminder:
    id: int
    type: str  # 'daily', 'weekly', 'biweekly', 'monthly', 'broadcast_daily', etc.
    time: str
    text: str
    chat_id: int
    days: Optional[str] = None  # for weekly/biweekly
    day: Optional[str] = None   # for monthly

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class GroupMessage:
    user_name: str
    text: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class BroadcastGroup:
    id: int
    name: str
    topic_id: int

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)