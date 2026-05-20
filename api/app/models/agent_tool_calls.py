from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AgentToolCall(Base):
    """Trace of every tool call made by the v3 agent during estimate generation.

    Provides full auditability and debuggability of the agentic reasoning process.
    """
    __tablename__ = "agent_tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)  # e.g. "search_materials"
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    estimate = relationship("Estimate")
