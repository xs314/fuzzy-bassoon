from pydantic import BaseModel
from typing import Union,List
from enum import Enum
class bottle_post(BaseModel):
    content:str
    from_user_id:int=0
    from_vila_id:int=0
    from_user_nick:str=''
    from_room_id:int=0
    send_at:int=0
    msg_id:str=''
    anon:bool=False
    image_url:str=''

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

class EditPaperRequest(BaseModel):
    key:str
    passwd:str