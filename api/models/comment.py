from sqlalchemy import Column, BigInteger, Integer, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.sql import func
from models.base import Base

class Comment(Base):
    __tablename__ = "comments"

    comment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    nickname = Column(String(50), nullable=False)
    comment = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
