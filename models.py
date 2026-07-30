from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON

class CachedDashboard(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedAchievements(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedLibrary(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedGenres(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedBacklog(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedPersonality(SQLModel, table=True):
    steam_id: str = Field(primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CachedLanding(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    data: dict = Field(sa_column=Column(JSON))
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))