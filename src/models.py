from sqlalchemy import Column, String, Integer
from src.database import Base

class DBUserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    selected_voice = Column(String, default="default")
    rage_streak = Column(Integer, default=0)