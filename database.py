import os
from sqlmodel import SQLModel, Session, create_engine, select
from datetime import datetime, timedelta
from models import CachedDashboard, CachedAchievements, CachedLibrary, CachedGenres, CachedBacklog, CachedPersonality, CachedLanding
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cache.db")
engine = create_engine(DATABASE_URL, echo=False)

CACHE_HOURS = 4


def create_db():
    SQLModel.metadata.create_all(engine)


def get_cached(model, steam_id: str):
    with Session(engine) as session:
        result = session.exec(select(model).where(model.steam_id == steam_id)).first()
        if not result:
            return None
        age = datetime.utcnow() - result.cached_at.replace(tzinfo=None)
        if age > timedelta(hours=CACHE_HOURS):
            return None
        data_with_meta = dict(result.data)
        data_with_meta["_cached"] = True
        data_with_meta["_cache_age_minutes"] = int(age.total_seconds() / 60)
        return data_with_meta


def save_cache(model, steam_id: str, data: dict):
    with Session(engine) as session:
        existing = session.exec(select(model).where(model.steam_id == steam_id)).first()
        if existing:
            existing.data = data
            existing.cached_at = datetime.utcnow()
            session.add(existing)
        else:
            new_record = model(steam_id=steam_id, data=data, cached_at=datetime.utcnow())
            session.add(new_record)
        session.commit()