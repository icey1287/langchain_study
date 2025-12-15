import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Literal
import json
from datetime import datetime

load_dotenv()
