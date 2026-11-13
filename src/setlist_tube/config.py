"""Settings read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    setlistfm_api_key: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(setlistfm_api_key=os.environ.get("SETLISTFM_API_KEY", "").strip())
