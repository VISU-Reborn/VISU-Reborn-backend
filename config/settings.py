from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=".env", override=True)


class Settings(BaseSettings):
    DEEPGRAM_API_KEY: str
    OPENAI_API_KEY: str
    CARTESIA_API_KEY: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    JINA_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    SERIAL_PORT: Optional[str] = None  # e.g. /dev/ttyUSB0, COM6
    SERIAL_BAUD: int = 9600
    MOTOR_WAVE_CMD: str = "WAVE"       # Number sent to Arduino for wave motion
    MOTOR_GESTURE_CMD: str = "RANDOM"    # Number sent to Arduino for body language gesture
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

