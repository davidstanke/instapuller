from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Unicode
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Post (Base):
    __tablename__ = "posts"
    post_id = Column(Unicode(255), primary_key=True)
    username = Column(Unicode(255))
    shortcode = Column(Unicode(255))
    direct_link = Column(Unicode(2047))
    caption = Column(Unicode(8191))
    display_url = Column(Unicode(2047))
    thumbnail_src = Column(Unicode(2047))
    date_added = Column(DateTime, server_default=func.now())

class Media (Base):
    __tablename__ = "media"
    post_id = Column(Unicode(255),primary_key=True)
    display_url = Column(Unicode(2047))
    path = Column(Unicode(2047))
    date_added = Column(DateTime, server_default=func.now())