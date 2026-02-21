import discord
import os
import asyncio
import random
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ▼▼ 新しく追加：みんなの所持金を記録する「お財布（辞書）」
user_coins = {}

@client.event
async def on_ready():
    print(f'ログインしました: {client.user}')

@client.event
async def on_message(message):
    # ボット自身のメッセージには反応しない
    if message.author == client.user:
        return
    if message.contest == 'こんにちは':
        await message.channel.send('こんにちは。ぼくのなまえはかんくん。このサーバーの管理代理人だよ！今はまだ信頼がないからみんなのコインの数とスロットシステムの管理をしているんだ。!coinと入力したら自分のコインの数がわかるし、!slotって入力したら10コインでスロットを回せるよ！これからもよろしくね！')
    # 発言した人のIDを取得（これで誰のお財布か見分けます）
    user_id = message.author.id

    # 初めて発言した人には、初期資金として100コインをプレゼント！
    if user_id not in user_coins:
        user_coins[user_id] = 100

    # --------------------------------------------------
    # コマンド1：所持金の確認
    # --------------------------------------------------
    if message.content == '!coin':
        await message.channel.send(f'{message.author.mention} さんの現在の所持金は **{user_coins[user_id]} コイン** です！🪙')

    # --------------------------------------------------
    # コマンド2：お金稼ぎ（バイト）
    # --------------------------------------------------
    elif message.content == '!work':
        # 10〜50コインの間でランダムにもらえる
        reward = random.randint(10, 50)
        user_coins[user_id] += reward
        await message.channel.send(f'{message.author.mention} さんが働いて **{reward} コイン** ゲットしました！💼 (現在の所持金: {user_coins[user_id]} コイン)')

    # --------------------------------------------------
    # コマンド3：スロット（1回10コイン）
    # --------------------------------------------------
    elif message.content == '!slot':
        cost = 10  # スロット1回の値段
        prize = 100 # 大当たりの賞金

        # お金が足りるかチェック
        if user_coins[user_id] < cost:
            await message.channel.send(f'{message.author.mention} コインが足りません！（1回 {cost} コイン必要です）`!work` で稼いできてください！')
            return
        
        # コインを消費
        user_coins[user_id] -= cost
        
        fruits = ['🍎', '🍋', '🍒', '🍉', '🔔', '7️⃣']
        msg = await message.channel.send(f"{message.author.mention} 🎰 スロットを回しています... (残り {user_coins[user_id]} コイン)\n[ ぐる ] [ ぐる ] [ ぐる ]")
        
        # アニメーション部分
        for _ in range(3):
            await asyncio.sleep(0.5)
            res = [random.choice(fruits) for _ in range(3)]
            await msg.edit(content=f"{message.author.mention} 🎰 スロットを回しています...\n[ {res[0]} ] [ {res[1]} ] [ {res[2]} ]")
        
        # 最終結果
        await asyncio.sleep(0.7)
        final_res = [random.choice(fruits) for _ in range(3)]
        result_text = f"{message.author.mention} 🎰 **結果発表** 🎰\n[ {final_res[0]} ] [ {final_res[1]} ] [ {final_res[2]} ]\n"
        
        # 当たり判定（3つ揃ったら）
        if final_res[0] == final_res[1] == final_res[2]:
            user_coins[user_id] += prize
            result_text += f"🎉 **大当たり！！ {prize} コイン獲得！！** 🎉 (現在の所持金: {user_coins[user_id]} コイン)"
        else:
            result_text += "ざんねん...ハズレです。また挑戦してね！"
            
        await msg.edit(content=result_text)

# 起動処理
keep_alive()
token = os.getene('DISCORD_TOKEN') # もしくは os.getenv('DISCORD_TOKEN')
client.run(token)
