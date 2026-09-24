import uuid
from datetime import datetime
from sqlalchemy import Column

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
    )
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    current_round = Column(Integer, nullable=False, default=0)
    round_status = Column(String, nullable=False, default="waiting_for_clients")
    total_rounds = Column(Integer, nullable=False)
    local_epochs = Column(Integer, nullable=False)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(String, unique=True, nullable=False)
    ip_add = Column(String)
    reg_at = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    clients_submitted = Column(Integer, nullable=False, default=0)
    global_acc = Column(Float)
    acc_delta = Column(Float)

    __table_args__ = (
        UniqueConstraint("session_id", "round_number"),
    )


class RoundParticipation(Base):
    __tablename__ = "round_participation"

    id = Column(Integer, primary_key=True)

    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    round_number = Column(Integer, nullable=False)

    client_id = Column(
        String,
        ForeignKey("clients.client_id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(
        String,
        nullable=False,
        default="registered",
    )

    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "round_number",
            "client_id",
        ),
        ForeignKeyConstraint(
            ["session_id", "round_number"],
            ["rounds.session_id", "rounds.round_number"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN "
            "('registered', 'submitted', 'missed', 'disconnected')"
        ),
    )


class Credit(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True)

    client_id = Column(
        String,
        ForeignKey("clients.client_id", ondelete="CASCADE"),
        nullable=False,
    )

    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    round_number = Column("round", Integer, nullable=False)
    samples_trained = Column(Integer, nullable=False)
    time_seconds = Column(Float, nullable=False)
    points_earned = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "round_number"],
            ["rounds.session_id", "rounds.round_number"],
            ondelete="CASCADE",
        ),
    )


class GlobalModelCheckpoint(Base):
    __tablename__ = "global_model_checkpoint"

    id = Column(Integer, primary_key=True)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    round_number = Column(Integer, nullable=False)
    weights = Column(LargeBinary, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)