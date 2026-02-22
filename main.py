import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from duckduckgo_search import DDGS  # 追加：検索エンジンを使うためのツール
import random
import aiohttp  # APIを叩くためのツール
from keep_alive import keep_alive
import urllib.parse  # 追加：文字を安全なURLに変換するツール
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

# ==========================================
# 🚀 さらに遊べる追加API機能
# ==========================================

@bot.tree.command(name="fake", description="この世に存在しない架空の人物プロフィールを生成します")
async def fake(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://randomuser.me/api/') as resp:
            data = await resp.json()
            user = data['results'][0]
            
            # データをわかりやすく取り出す
            name = f"{user['name']['first']} {user['name']['last']}"
            country = user['location']['country']
            age = user['dob']['age']
            picture = user['picture']['large']

            # かっこいいプロフィールカード（Embed）を作る
            embed = discord.Embed(title="🕵️ 架空の人物プロファイル", color=0x2b2d31)
            embed.add_field(name="名前", value=name, inline=True)
            embed.add_field(name="国籍", value=country, inline=True)
            embed.add_field(name="年齢", value=f"{age}歳", inline=True)
            embed.set_thumbnail(url=picture) # 右上に顔写真をセット
            
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="btc", description="現在のビットコイン価格（日本円）を調べます")
async def btc(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.coindesk.com/v1/bpi/currentprice/JPY.json') as resp:
            data = await resp.json()
            # 価格データを取り出して、見やすくカンマ区切りにする
            price = data['bpi']['JPY']['rate']
            
            await interaction.followup.send(f"📈 **現在のビットコイン価格:**\n1 BTC = **{price} 円** です！")

@bot.tree.command(name="weather", description="指定した都市の現在の天気を調べます")
@app_commands.describe(city="都市名（例: Tokyo, Osaka, London）")
async def weather(interaction: discord.Interaction, city: str):
    await interaction.response.defer()
    
    # wttr.in はURL自体が画像になる特殊な魔法のAPIです
    image_url = f"https://wttr.in/{city}_0tqp_lang=ja.png"
    
    embed = discord.Embed(title=f"🌦️ {city.capitalize()} のお天気", color=0x00ffff)
    embed.set_image(url=image_url)
    
    await interaction.followup.send(embed=embed)
# ==========================================
# 🧠 AIチャット機能（登録不要・完全無料！）
# ==========================================

@bot.tree.command(name="ai", description="AIに質問やお願いをします（例: おすすめのゲーム教えて！）")
@app_commands.describe(prompt="AIに話しかける内容")
async def ai_chat(interaction: discord.Interaction, prompt: str):
    # AIが考えるのには少し時間がかかるので「考え中...」状態にする
    await interaction.response.defer()
    
    # 日本語の質問をURLで使える形に変換する
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Pollinations.ai の無料テキスト生成APIを使用
    url = f"https://text.pollinations.ai/{encoded_prompt}"
    
    async with aiohttp.ClientSession() as session:
        # APIに質問を投げる
        async with session.get(url) as resp:
            if resp.status == 200:
                answer = await resp.text()
                
                # Discordは1回の送信が2000文字までなので、長すぎる場合はカットする対策
                if len(answer) > 1900:
                    answer = answer[:1900] + "\n\n(※長すぎるため途中でカットしました！)"
                
                # 見栄え良く返信する
                await interaction.followup.send(f"👤 **あなたの質問:** {prompt}\n\n🤖 **AIの回答:**\n{answer}")
            else:
                await interaction.followup.send("ごめんね、今AIがパンクしてて考えられないみたい...時間を置いて試してね！")
# ==========================================
# 🔍 インターネット検索機能
# ==========================================

@bot.tree.command(name="search", description="インターネットでキーワード検索をします")
@app_commands.describe(query="検索したいキーワード")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer() # 検索には少し時間がかかるので「考え中...」にする
    
    # 検索処理は少し重いので、ボットがフリーズしないように別の裏作業（スレッド）として実行します
    def do_search(q):
        with DDGS() as ddgs:
            # max_results=3 で、上位3件のサイトを取得
            return list(ddgs.text(q, region='wt-wt', safesearch='moderate', max_results=3))

    try:
        # 裏作業として検索を実行
        results = await asyncio.to_thread(do_search, query)
        
        if not results:
            await interaction.followup.send(f"「{query}」に関する情報は見つかりませんでした💦")
            return

        # 検索結果をかっこいいパネル（Embed）にまとめる
        embed = discord.Embed(title=f"🔍 「{query}」の検索結果", color=0x3498db)
        
        for res in results:
            # res['title'] がサイト名、res['body'] が説明文、res['href'] がURLです
            embed.add_field(
                name=res['title'], 
                value=f"{res['body']}\n[🔗リンクはこちら]({res['href']})", 
                inline=False
            )
            
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send("検索中にエラーが起きちゃいました...もう一度試してね！")
keep_alive()
token = os.getenv('DISCORD_TOKEN') # もしくは os.getenv('DISCORD_TOK
bot.run(token)
