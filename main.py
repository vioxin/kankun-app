import discord
from keep_alive import keep_alive
import os
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
@client.event
async def on_ready():
    print(f'ログインしました: {client.user}')
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == 'こんにちは':
        await message.channel.send('こんにちは！')
keep_alive()
token = os.environ['DISCORD_TOKEN']
client.run(token)
