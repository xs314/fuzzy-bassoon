from villa import Bot
from villa.event import SendMessageEvent
import os
from fastapi import FastAPI
import uvicorn
import utils
from deta import Deta
import traceback
import time
deta = Deta()
erres=deta.Base('err')


app = FastAPI()
bot = Bot(bot_id=os.environ.get('bot_id'), bot_secret=os.environ.get('bot_secret'), callback_url=os.environ.get('bot_callback'))
# 初始化Bot，填写你的bot_id、密钥以及回调地址endpoint
# 举例：若申请时提供的回调地址为https://域名/callback，这里的callback_url就填`/callback`

@bot.on_startswith("/ping")
async def ___(event: SendMessageEvent):

    await event.send('pong',mention_sender=True)
    a=await bot.get_member(event.villa_id,event.from_user_id)
    print(a)

@bot.on_startswith("/扔漂流瓶")
async def _(event: SendMessageEvent):        
    msg = await utils.put_bottle(event)
    await event.send(msg,mention_sender=True,quote_message=True)

    # 一个简单的处理函数，向你的Bot发送包含`hello`关键词的消息，它将会回复你`world`！

@bot.on_startswith("/捡漂流瓶")
async def __(event: SendMessageEvent):

    msg = await utils.random_bottle()
    await event.send(msg,mention_sender=True)



#fastapi admintools
@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}

#vila listeners

if __name__ == "__main__":
    bot.init_app(app)
    uvicorn.run(app,port=int(os.environ.get('PORT',8000)),log_level="debug")    
    # 启动bot，注意，port端口号要和你的回调地址端口对上