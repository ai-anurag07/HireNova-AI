import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load our .env file
load_dotenv()

# Get the database URL from the .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the async engine (The bridge to PostgreSQL)
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory (To talk to the database)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False
)

# This is the base class for all our database tables
Base = declarative_base()

# Dependency to get the database session in our API routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session