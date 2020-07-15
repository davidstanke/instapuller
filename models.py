from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Unicode
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Post (Base):
    __tablename__ = "posts"
    post_id = Column(Unicode, primary_key=True)
    username = Column(Unicode)
    shortcode = Column(Unicode)
    direct_link = Column(Unicode)
    caption = Column(Unicode)
    display_url = Column(Unicode)
    thumbnail_src = Column(Unicode)
    date_added = Column(DateTime, server_default=func.now())

class Media (Base):
    __tablename__ = "media"
    post_id = Column(Unicode,primary_key=True)
    display_url = Column(Unicode)
    path = Column(Unicode)
    date_added = Column(DateTime, server_default=func.now())
