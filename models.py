from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
import enum
from database import Base


class LinkPrecedence(str, enum.Enum):
    primary = "primary"
    secondary = "secondary"


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    phoneNumber = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    linkedId = Column(Integer, nullable=True)  
    linkPrecedence = Column(Enum(LinkPrecedence), nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deletedAt = Column(DateTime(timezone=True), nullable=True)