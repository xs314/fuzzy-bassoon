from villa import Bot
from villa.event import SendMessageEvent
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import uvicorn
import utils
from deta import Deta

import time,requests
from pydantic import BaseModel
from typing import Union
from enum import Enum



deta = Deta()


app = FastAPI()

bot = Bot(bot_id=os.environ.get('bot_id'), bot_secret=os.environ.get('bot_secret'), callback_url=os.environ.get('bot_callback'))
# 初始化Bot，填写你的bot_id、密钥以及回调地址endpoint
# 举例：若申请时提供的回调地址为https://域名/callback，这里的callback_url就填`/callback`

@bot.on_startswith("ping",prefix='/')
async def alive(event: SendMessageEvent):
    await event.send('pong',mention_sender=True)
    return
    
@bot.on_startswith("扔漂流瓶",prefix='/')
async def throw(event: SendMessageEvent):        
    msg = await utils.put_bottle(event,bot)
    await event.send(msg,mention_sender=True,quote_message=True)
    return
    # 一个简单的处理函数，向你的Bot发送包含`hello`关键词的消息，它将会回复你`world`！

@bot.on_startswith("捡漂流瓶",prefix='/')
async def fetch(event: SendMessageEvent):

    msg = await utils.random_bottle()
    await event.send(msg,mention_sender=True)
    return

class ModerateBody(BaseModel):
    id:str
    action:str
    desc:str = None

#fastapi admintools
@app.get("/admin/posts")
async def read_posts(last:str,limit:int = 100):
    return await utils.list_unmoderated_bottles(last,limit)

@app.post('/admin/moderate')
async def moderate(moderate_body: ModerateBody):
    return await utils.moderate_bottle(moderate_body.id,moderate_body.action)
app.mount("/admin", StaticFiles(directory="public"), name="public")

if __name__ == "__main__":
    bot.init_app(app)
    uvicorn.run(app,port=int(os.environ.get('PORT',8000)))    
    # 启动bot，注意，port端口号要和你的回调地址端口对上