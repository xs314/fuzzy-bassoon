from villa import Bot
from villa.event import SendMessageEvent
from villa.store import get_app
import os
from fastapi import FastAPI
import uvicorn
import utils
from deta import Deta
import traceback
import time,requests
deta = Deta()
erres=deta.Base('err')


app = FastAPI()
bot = Bot(bot_id=os.environ.get('bot_id'), bot_secret=os.environ.get('bot_secret'), callback_url=os.environ.get('bot_callback'))
# 初始化Bot，填写你的bot_id、密钥以及回调地址endpoint
# 举例：若申请时提供的回调地址为https://域名/callback，这里的callback_url就填`/callback`

@bot.on_startswith("ping",prefix='/')
async def alive(event: SendMessageEvent):
    await event.send('pong')
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



#fastapi admintools
@app.get("/items")
async def read_item():
    return requests.get('https://bbs-api.miyoushe.com/vila/api/bot/platform/getAllEmoticons').json()

#vila listeners

if __name__ == "__main__":
    app=get_app()
    bot.init_app(app)
    uvicorn.run("__main__:app",port=int(os.environ.get('PORT',8000)),reload=True)    
    # 启动bot，注意，port端口号要和你的回调地址端口对上