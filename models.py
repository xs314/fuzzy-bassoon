from pydantic import BaseModel
from typing import Union,List
from enum import Enum


class actions(str,Enum):
    accept='accept'
    deny='deny'

class ModerateBody(BaseModel):
    key:str
    action:actions
    desc:Union[str,None]

class Question(BaseModel):
    q: str
    a: str

class QuestionGroup(BaseModel):
    title: str
    desc: str
    questions: List[Question]
    count: int
    passCount: int

class Paper(BaseModel):
    title: str
    desc: str
    passCount: int
    groups: List[QuestionGroup]
    time: int
    
class PaperRequest(BaseModel):
    key:str
    captcha_token:str

class GroupAnswers(BaseModel):
    a:List[str]
    
class PaperAnswer(BaseModel):
    akey:str
    answers:List[GroupAnswers]