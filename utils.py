from deta import Deta
deta = Deta()
db_bottles=deta.Base('bottles')
db_unaudited_bottles=deta.Base('bottles_unaudited')
db_settings=deta.Base('settings')
db_blacklist=deta.Base('blacklist')
from villa.event import SendMessageEvent
from villa import Bot
import logging,time
from typing import Tuple,List,Dict
import random
_log=logging.getLogger('utils')

async def put_bottle(evt:SendMessageEvent)->str:
    #向unaudited_bottles投放漂流瓶等待审核
    #1.检查是否有加入时长要求
    # jointime_req=db_settings.get('bottles:jointime')
    # if not jointime_req:
    #     _log.warning('没有加入时长要求。生成一个默认要求')
    #     db_settings.put({'desc':'漂流瓶的群加入时长要求(sec)','val':0},'bottles:jointime')
    # else:
    #     #get member jointime
    #     member_jointime=await bot.get_member(evt.villa_id,evt.from_user_id)
    #     member_jointime=member_jointime.joined_at
    #     #compare join time req:
    #     if int(time.time())-int(member_jointime)<int(jointime_req['val']):
    #         _log.warning('用户加入时间过短。')
    #         return '用户加入时间过短。更换服务器再试。'
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
    content=' '.join(evt.message.plain_text().split('/扔漂流瓶')[1].split(' ')[1])
    if not content:
        return '但是你什么也没说诶'
    key=db_unaudited_bottles.put({'content':content,'from_user_id':evt.from_user_id,'from_user_nick':evt.nickname,'from_room_id':evt.room_id,'from_vila_id':evt.villa_id},expire_in=86400*7)['key']
    return f'投稿id:{key}'

async def moderate_accept(bottle_key:str)->Tuple[bool,str]:
    #接收投稿并+1
    #0.do we have that key in unaudited?it should have but lets check
    post=db_unaudited_bottles.get(bottle_key)
    if not post:
        return (False,'无此投稿')

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
        del last_post['__expires']
        db_settings.put(last_post,'bottles:last_post')

    #2.post in bottles,bascially you delete the key and replace it with this_post in str
    #it with the new one
    db_unaudited_bottles.delete(bottle_key)
    del post['key']
    db_bottles.put(post,this_post)
    return (True,this_post)

async def random_bottle()-> str:
    #随朶投瓶
    #1.get last_post
    last_post=db_settings.get('bottles:last_post')
    if not last_post:
        return '没有last_post，这可能说明数据库尚未初始化。'
    attempt=0
    while (not item and attempt<5):
        key=str(random.randint(0,last_post['val']['last']))
        item=db_bottles.get(key)
    if not item:
        return '超过5次请求无数据，这可能说明Bottles过于稀疏'
    else:
        return item['content']
    
async def moderate_deny(bottle_key:str)->bool:
    #拒绝投稿
    db_unaudited_bottles.delete(bottle_key)
    return True
    
async def list_unmoderated_bottles(last:str,limit:int=100)->List[Dict]:
    pass




