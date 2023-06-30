from hertavilla import MessageChain, SendMessageEvent, VillaBot, run
import os
bot = VillaBot(
os.environ.get('bot_id'), os.environ.get('bot_secret'), os.environ.get('bot_callback')
)


@bot.startswith("/")  # 注册一个消息匹配器，匹配前缀为 / 的消息
async def _(event: SendMessageEvent, bot: VillaBot):
    message = event.message
    if str(message[1]) == "/hello":
        chain = MessageChain()
        chain.append("world")
        await bot.send(event.villa_id, event.room_id, chain)


run(bot,port=int(os.environ.get('PORT',8080)))  # 运行 bot
