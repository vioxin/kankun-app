import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import random
import aiohttp  # APIを叩くためのツール
from keep_alive import keep_alive

# ボットの初期設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# みんなのお財布
user_coins = {}

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    # スラッシュコマンドをDiscordサーバーに同期（登録）する
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} 個のコマンドを同期しました！")
    except Exception as e:
        print(f"同期エラー: {e}")

# ==========================================
# 💰 お金・ゲーム機能（スラッシュコマンド版）
# ==========================================

@bot.tree.command(name="coin", description="現在の所持金を確認します")
async def coin(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in user_coins:
        user_coins[user_id] = 100
    await interaction.response.send_message(f'{interaction.user.mention} さんの所持金は **{user_coins[user_id]} コイン** です！🪙')

@bot.tree.command(name="work", description="働いてコインを稼ぎます")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in user_coins:
        user_coins[user_id] = 100
        
    reward = random.randint(10, 50)
    user_coins[user_id] += reward
    await interaction.response.send_message(f'💼 働いて **{reward} コイン** ゲットしました！(合計: {user_coins[user_id]} コイン)')

@bot.tree.command(name="slot", description="1回10コインでスロットを回します")
async def slot(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in user_coins:
        user_coins[user_id] = 100
        
    cost = 10
    if user_coins[user_id] < cost:
        await interaction.response.send_message("コインが足りません！ `/work` で稼いできてください！", ephemeral=True)
        return

    user_coins[user_id] -= cost
    fruits = ['🍎', '🍋', '🍒', '🍉', '🔔', '7️⃣']
    
    # 最初のメッセージを送信
    await interaction.response.send_message(f"🎰 スロットを回しています... (残り {user_coins[user_id]} コイン)\n[ ぐる ] [ ぐる ] [ ぐる ]")
    
    # アニメーション
    for _ in range(3):
        await asyncio.sleep(0.5)
        res = [random.choice(fruits) for _ in range(3)]
        # interaction.edit_original_response でメッセージを更新
        await interaction.edit_original_response(content=f"🎰 スロットを回しています...\n[ {res[0]} ] [ {res[1]} ] [ {res[2]} ]")
    
    # 最終結果
    await asyncio.sleep(0.7)
    final_res = [random.choice(fruits) for _ in range(3)]
    result_text = f"🎰 **結果発表** 🎰\n[ {final_res[0]} ] [ {final_res[1]} ] [ {final_res[2]} ]\n"
    
    if final_res[0] == final_res[1] == final_res[2]:
        user_coins[user_id] += 100
        result_text += f"🎉 **大当たり！！ 100 コイン獲得！！** 🎉 (合計: {user_coins[user_id]} コイン)"
    else:
        result_text += "ざんねん...ハズレです。"
        
    await interaction.edit_original_response(content=result_text)

# ==========================================
# 🌐 外部API機能（スラッシュコマンド版）
# ==========================================

@bot.tree.command(name="ask", description="魔法の巻貝に質問します（Yes/Noで答えます）")
@app_commands.describe(question="巻貝に聞きたい質問")
async def ask(interaction: discord.Interaction, question: str):
    # APIの返事を待つ間、Discord側で「考え中...」と表示させるおまじない
    await interaction.response.defer()
    
    async with aiohttp.ClientSession() as session:
        async with session.get('https://yesno.wtf/api') as resp:
            data = await resp.json()
            answer = data['answer'].upper()
            image_url = data['image']
            
            # 見栄えを良くするためにEmbed（埋め込み枠）を使う
            embed = discord.Embed(title=f"質問: {question}", description=f"**巻貝の答え: {answer}**", color=0x00ff00)
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="dog", description="可愛い柴犬の画像を召喚します")
async def dog(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('http://shibe.online/api/shibes?count=1') as resp:
            data = await resp.json()
            image_url = data[0]
            await interaction.followup.send(content="🐶 わん！", file=None, embed=discord.Embed().set_image(url=image_url))

@bot.tree.command(name="cat", description="可愛いネコちゃんの画像を召喚します")
async def cat(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.thecatapi.com/v1/images/search') as resp:
            data = await resp.json()
            image_url = data[0]['url']
            await interaction.followup.send(content="🐱 にゃーん！", embed=discord.Embed().set_image(url=image_url))

@bot.tree.command(name="poke", description="ランダムなポケモンを召喚します")
async def poke(interaction: discord.Interaction):
    await interaction.response.defer()
    # ポケモンは現在1000種類以上いるので、1〜1010の中からランダムに選ぶ
    poke_id = random.randint(1, 1010)
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pokeapi.co/api/v2/pokemon/{poke_id}') as resp:
            data = await resp.json()
            poke_name = data['name'].capitalize()
            # 公式アートワークの画像URL
            image_url = data['sprites']['other']['official-artwork']['front_default']
            
            embed = discord.Embed(title=f"野生の {poke_name} が飛び出してきた！", color=0xff0000)
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="advice", description="ランダムなありがたい言葉（英語）を授けます")
async def advice(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.adviceslip.com/advice') as resp:
            data = await resp.json()
            advice_text = data['slip']['advice']
            await interaction.followup.send(f"💬 **今日のアドバイス:**\n「{advice_text}」")


keep_alive()
token = os.getenv('DISCORD_TOKEN') # もしくは os.getenv('DISCORD_TOK
bot.run(token)
