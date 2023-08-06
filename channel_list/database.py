import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

db = create_engine(os.environ['DATABASE_URI'])
Session = sessionmaker(db)
