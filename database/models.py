from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from session import Base

class POPConfig(Base):
    __tablename__ = "pop_config"

    id = Column(Integer, primary_key=True, index=True)
    server = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String, nullable=True)
    port = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<POPConfig(id={self.id}, server='{self.server}', username='{self.username}', password='{self.password}', port={self.port})>"