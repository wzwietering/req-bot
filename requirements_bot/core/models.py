# requirements_bot/core/models.py
from pydantic import BaseModel
from typing import List, Literal, Optional

class Question(BaseModel):
    id: str
    text: str
    category: Literal["scope","users","constraints","nonfunctional","interfaces","data","risks","success"]
    required: bool = True

class Answer(BaseModel):
    question_id: str
    text: str

class Requirement(BaseModel):
    id: str
    title: str
    rationale: Optional[str] = None
    priority: Literal["MUST","SHOULD","COULD"] = "MUST"

class Session(BaseModel):
    project: str
    questions: List[Question]
    answers: List[Answer] = []
    requirements: List[Requirement] = []
