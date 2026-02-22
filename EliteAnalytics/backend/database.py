from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "elite_analytics.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Base = declarative_base()

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    date = Column(String)
    competition = Column(String)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    home_score = Column(Integer)
    away_score = Column(Integer)
    
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    events = relationship("Event", back_populates="match", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    
    players = relationship("Player", back_populates="team")


class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    position = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id"))
    
    team = relationship("Team", back_populates="players")
    events = relationship("Event", back_populates="player")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    
    event_id = Column(Integer) # Original provider ID
    minute = Column(Integer)
    second = Column(Integer)
    
    type_name = Column(String) # Pass, Shot, Carry, Dribble, Tackle, Interception, etc.
    outcome = Column(String)   # Successful, Unsuccessful, Goal, Saved
    
    x = Column(Float)
    y = Column(Float)
    end_x = Column(Float, nullable=True)
    end_y = Column(Float, nullable=True)
    
    # Advanced Context
    is_shot = Column(Boolean, default=False)
    xg = Column(Float, nullable=True)
    xt = Column(Float, nullable=True) # Expected Threat added by metrics engine
    
    under_pressure = Column(Boolean, default=False)
    is_big_chance = Column(Boolean, default=False)
    is_penalty = Column(Boolean, default=False)
    
    # Advanced Passing Logic
    is_final_third_pass = Column(Boolean, default=False)
    is_progressive_pass = Column(Boolean, default=False)
    
    # Sequence Analysis
    possession_chain_id = Column(Integer, nullable=True)
    
    qualifiers = Column(JSON, nullable=True) # Store raw qualifiers for deep analysis
    
    match = relationship("Match", back_populates="events")
    team = relationship("Team")
    player = relationship("Player", back_populates="events")


def init_db():
    Base.metadata.create_all(engine)

def get_session():
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
