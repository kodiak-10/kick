from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    user_profile = Column(Text)
    explain_output = Column(Text)
    goals = Column(Text)
    plan = Column(Text)


def get_engine(db_path):
    return create_engine(f"sqlite:///{db_path}")


def init_db(db_path):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
