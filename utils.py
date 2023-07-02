from deta import Deta
deta = Deta()
db_bottles=deta.Base('bottles')
db_unaudited_bottles=deta.Base('bottles_unaudited')
db_settings=deta.Base('settings')
db_blacklist=deta.Base('blacklist')
db_cmd_state=deta.Base('cmd_state')
from hashlib import sha1
from villa.event import SendMessageEvent
from villa import Bot
from villa.message import Message, MessageSegment
import logging,time
from typing import Tuple,List,Dict
import random,requests
import base64
from pydantic import BaseModel
from models import Paper

class bottle_post(BaseModel):
    content:str
    from_user_id:int
    from_vila_id:int
    from_user_nick:str
    from_room_id:int
    send_at:int
    msg_id:str

_log=logging.getLogger('utils')

async def put_bottle(evt:SendMessageEvent,bot:Bot)->str:
    #向unaudited_bottles投放漂流瓶等待审核
    #1.检查是否有加入时长要求
    jointime_req=db_settings.get('bottles:jointime')
    if not jointime_req:
        _log.warning('没有加入时长要求。生成一个默认要求')
        db_settings.put({'desc':'漂流瓶的群加入时长要求(sec)','val':0},'bottles:jointime')
    else:
        #get member jointime
        member_jointime=await bot.get_member(evt.villa_id,evt.from_user_id)
        member_jointime=member_jointime.joined_at
        #compare join time req:
        if int(time.time())-int(member_jointime)<int(jointime_req['val']):
            _log.warning('用户加入时间过短。')
            return f"用户加入时间过短，尝试更换别野再试。此别野你还需{round((int(jointime_req['val'])-(int(time.time())-int(member_jointime)))/3600,1)}小时才允许投稿。"
    #2.检查是否在黑名单
    if bl:=db_blacklist.get(f'U-{evt.from_user_id}'):
        _log.warning('用户在黑名单。')
        return f'当前用户无法投稿。因为：{bl["desc"]}'
    #V-vilaid
    if bl:=db_blacklist.get(f'V-{evt.villa_id}'):
        _log.warning('服务器在黑名单。')
        return f'服务器在黑名单，因为：{bl["desc"]}。更换服务器再试。'
    #3.投稿
    # put an item to unaudited with ttl of 7 days,content is /扔漂流瓶 <content> 
    # so content is basically can be get with split msg.text by / and by space and joining the space
    content=' '.join(evt.message.plain_text().split('/扔漂流瓶')[1].split(' ')[1:])
    if not content:
        return '但是你什么也没说诶'
    data=bottle_post(content=content,from_user_id=evt.from_user_id,from_vila_id=evt.villa_id,from_user_nick=evt.nickname,from_room_id=evt.room_id,send_at=evt.send_at,msg_id=evt.msg_uid)
    key=db_unaudited_bottles.put(data.dict(),expire_in=86400*7)['key']
    return f'投稿id:{key}'

async def moderate_accept(bottle_key:str,bot:Bot)->bool:
    #接收投稿并+1
    #0.do we have that key in unaudited?it should have but lets check
    post=db_unaudited_bottles.get(bottle_key)
    if not post:
        return False
    #1.先去取last_post
    last_post=db_settings.get('bottles:last_post')
    if not last_post:
        #add one and start by 0
        db_settings.put({'desc':'last:最后在池子中的id，spare:出于某些原因st被删的bottles的id，用于复用','val':{'last':0,'spare':[]}},'bottles:last_post')
        this_post='0' #keys need a str
    else:
        #has last post
        #if last_post['val']['spare'] is not empty,use spare,and remove a value from the spare
        #else use last+1
        #then update db_settings
        if len(last_post['val']['spare'])>0:
            this_post=str(last_post['val']['spare'].pop())
        else:
            this_post=str(last_post['val']['last']+1)
        #save db_settings but we remove the kry of last_post to prevent ke collasion
        del last_post['key']
        db_settings.put(last_post,'bottles:last_post')

    #2.post in bottles,bascially you delete the key and replace it with this_post in str
    #it with the new one
    db_unaudited_bottles.delete(bottle_key)

    bpp=bottle_post(**post)
    await bot.send(bpp.from_vila_id,bpp.from_room_id,(Message(f'管理员接受了您的投稿#{bottle_key}').mention_user(bpp.from_vila_id,bpp.from_user_id).quote(bpp.msg_id,bpp.send_at)))
    del post['key']
    del post['__expires']
    db_bottles.put(post,this_post)
    return True

async def random_bottle()-> str:
    #随朶投瓶
    #1.get last_post
    last_post=db_settings.get('bottles:last_post')
    item=None
    if not last_post:
        return '没有last_post，这可能说明数据库尚未初始化。'
    attempt=0
    while (not item and attempt<5):
        key=str(random.randint(0,last_post['val']['last']))
        item=db_bottles.get(key)
    if not item:
        return '超过5次请求无数据，这可能说明Bottles过于稀疏'
    else:
        return f'>>>{item["key"]}\n'+item['content']
    
async def moderate_deny(bottle_key:str,reason:str,bot:Bot)->bool:
    #拒绝投稿
    if post:=db_unaudited_bottles.get(bottle_key):
        bpp=bottle_post(**post)

        await bot.send(bpp.from_vila_id,bpp.from_room_id,(Message(f'管理员拒绝了您的投稿#{bottle_key}。理由如下：{reason}').mention_user(bpp.from_vila_id,bpp.from_user_id).quote(bpp.msg_id,bpp.send_at)))

        db_unaudited_bottles.delete(bottle_key)

    return True
    
async def list_unmoderated_bottles(last:str,limit:int=100):
    return db_unaudited_bottles.fetch({},limit=limit,last=last)


def check_paper_validity(paper: Paper) -> Tuple[bool,str]:
    # Check passCount constraint
    total_questions = sum(len(group.questions) for group in paper.groups)
    if paper.passCount > total_questions:
        error_message = "passCount cannot be greater than the total number of questions in all question groups."
        return [False,error_message]

    # Check count and passCount constraints for each question group
    for group in paper.groups:
        if len(group.questions) < group.count:
            error_message = f"count cannot be greater than the number of questions in the question group '{group.title}'."

            return [False,error_message]
        if group.count < group.passCount:
            error_message = f"passCount cannot be greater than count in the question group '{group.title}'."
            return [False,error_message]

    # Check paperJSON size constraint
    paper_json_size = len(paper.json())
    if paper_json_size > 256 * 1024:
        error_message = "paperJSON size exceeds the maximum allowed size of 256KB."
        
        return [False,error_message]

    return [True,'']



def put_cmd_state(ident:List,data:Dict,expire_in:int=3600)->str:
    #put in command state by put sha1('-'.join(ident)) as key so the same list is the same key for receiving
    #we also reserve a "m:state_data"=list for reference
    key=base64.urlsafe_b64encode(sha1('_'.join(ident)).digest()).decode('utf-8')
    db_cmd_state.put({'m:state_data':data,'data':data},key,expire_in=expire_in)
    return key

def get_cmd_state(ident:List)->Dict:
    #get from command state by put sha1('-'.join(ident)) as key so the same list is the same key for receiving
    #we also reserve a "m:state_data"=list for reference
    key=base64.urlsafe_b64encode(sha1('_'.join(ident)).digest()).decode('utf-8')
    return db_cmd_state.get(key)['data']