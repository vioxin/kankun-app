import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from duckduckgo_search import DDGS  # 検索エンジンを使うためのツール
import random
import aiohttp  # APIを叩くためのツール
import urllib.parse  # 文字を安全なURLに変換するツール
from flask import Flask, request, jsonify # 追加：Webサーバー機能
from flask_cors import CORS # 追加：Webサイトとの通信許可ツール
from threading import Thread # 追加：ボットとWebサーバーを同時に動かすツール
import io

# ボットの初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 🌐 Web連携の設定
WEB_TARGET_CHANNEL_ID = 1325998165421195335
chat_history = [] # Webサイトに送るための会話履歴
user_coins = {}   # みんなのお財布

# ==========================================
# 🌐 Webサーバー（Flask）の設定
# ==========================================
# ==========================================
# 🌐 Webサーバー（Flask）の設定
# ==========================================
app = Flask(__name__)
CORS(app) 

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/api/messages', methods=['GET'])
def get_messages():
    return jsonify(chat_history)
# 🌟 追加：Discordアクティビティ用のゲーム画面を配信する窓口
@app.route('/quiz')
def serve_quiz():
    try:
        # 同じフォルダにある quiz.html を読み込んでWebブラウザ（Discord）に渡す
        with open('quiz.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "ゲームのファイルが見つかりません！quiz.htmlを同じフォルダに置いてください。"
# 🌟追加：Discordサーバーの「メンバー一覧」をWebに教える窓口
@app.route('/api/members', methods=['GET'])
def get_members():
    channel = bot.get_channel(WEB_TARGET_CHANNEL_ID)
    if not channel:
        return jsonify([])
    members = []
    # サーバー内の全員をチェックしてリストにする
    for member in channel.guild.members:
        if not member.bot: # ボット自身は除外する
            members.append({"id": str(member.id), "name": member.display_name})
    return jsonify(members)

# 🌟変更：テキストだけでなく「画像」と「メンション先」も受け取れるようにする
@app.route('/api/send', methods=['POST'])
def send_message():
    text = request.form.get('text', '')
    mention_id = request.form.get('mention_id', '')
    
    # 画像ファイルの処理
    image_file = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            image_bytes = file.read() # 画像を読み込む
            image_file = {'filename': file.filename, 'data': image_bytes}
            
    if text or image_file:
        asyncio.run_coroutine_threadsafe(send_to_discord(text, mention_id, image_file), bot.loop)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# ==========================================
# 🤖 ボットの基本イベント
# ==========================================

# ==========================================
# 🌟 メッセージデータの抽出（ファイル対応版）
# ==========================================
def extract_message_data(message):
    data = {
        "author": message.author.display_name,
        "content": message.content,
        "is_bot": message.author.bot,
        "interaction": None,
        "embeds": [],
        "attachments": [] # 🌟 追加：ファイルを入れる箱
    }
    
    if message.interaction:
        data["interaction"] = {
            "user": message.interaction.user.display_name,
            "name": message.interaction.name
        }
        
    for embed in message.embeds:
        embed_info = {}
        if embed.title: embed_info["title"] = embed.title
        if embed.description: embed_info["description"] = embed.description
        if embed.image and embed.image.url: embed_info["image"] = embed.image.url
        data["embeds"].append(embed_info)
        
    # 🌟 追加：添付ファイル（画像・その他のファイル）の情報を取得
    for attachment in message.attachments:
        att_info = {
            "url": attachment.url,
            "filename": attachment.filename,
            "content_type": attachment.content_type or "unknown" # これで画像かそれ以外かを見分けます
        }
        data["attachments"].append(att_info)
        
    return data

# ==========================================
# 🌟 Discordへの送信（Webからのコマンド対応版）
# ==========================================
async def send_to_discord(text, mention_id=None, image_file=None):
    channel = bot.get_channel(WEB_TARGET_CHANNEL_ID)
    if not channel:
        return

    # 🌟 追加：Webから特定のコマンド文字が送られたときの裏技処理
    if text == "/duck":
        async with aiohttp.ClientSession() as session:
            async with session.get('https://random-d.uk/api/v2/random') as resp:
                data = await resp.json()
                embed = discord.Embed(title="🦆 クワッ！ (Webからの召喚)", color=0xf1c40f)
                embed.set_image(url=data['url'])
                await channel.send(embed=embed)
        return # コマンドとして処理したので、ただの文字としては送らずに終了する

    if text == "/dog":
        async with aiohttp.ClientSession() as session:
            async with session.get('https://dog.ceo/api/breeds/image/random') as resp:
                data = await resp.json()
                embed = discord.Embed(color=0xe67e22)
                embed.set_image(url=data['message'])
                await channel.send(content="🐶 わん！ (Webからの召喚)", embed=embed)
        return

    # --- 以下は今までの通常の送信処理 ---
    content = ""
    if text:
        content += f"🌐 **[Webから]:** {text}"
        
    if mention_id:
        content += f" <@{mention_id}>"
        
    discord_file = discord.utils.MISSING
    if image_file:
        discord_file = discord.File(fp=io.BytesIO(image_file['data']), filename=image_file['filename'])
        
    await channel.send(content=content, file=discord_file)
@bot.event
async def on_message(message):
    if message.channel.id == WEB_TARGET_CHANNEL_ID:
        # 便利関数を使って詳細データを保存
        msg_data = extract_message_data(message)
        chat_history.append(msg_data)
        
        if len(chat_history) > 50:
            chat_history.pop(0)

    if message.author.bot:
        return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} 個のコマンドを同期しました！")
    except Exception as e:
        print(f"同期エラー: {e}")
        
    channel = bot.get_channel(WEB_TARGET_CHANNEL_ID)
    if channel:
        global chat_history
        chat_history.clear() 
        
        messages = [msg async for msg in channel.history(limit=50)]
        messages.reverse() 
        
        for msg in messages:
            # 起動時の履歴読み込みでも便利関数を使う
            msg_data = extract_message_data(msg)
            chat_history.append(msg_data)
            
        print("過去のメッセージの読み込みが完了しました！")
# ==========================================
# 💰 お金・ゲーム機能
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
    await interaction.response.send_message(f"🎰 スロットを回しています... (残り {user_coins[user_id]} コイン)\n[ ぐる ] [ ぐる ] [ ぐる ]")
    
    for _ in range(3):
        await asyncio.sleep(0.5)
        res = [random.choice(fruits) for _ in range(3)]
        await interaction.edit_original_response(content=f"🎰 スロットを回しています...\n[ {res[0]} ] [ {res[1]} ] [ {res[2]} ]")
    
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
# 🌐 外部API機能
# ==========================================
@bot.tree.command(name="ask", description="魔法の巻貝に質問します（Yes/Noで答えます）")
@app_commands.describe(question="巻貝に聞きたい質問")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://yesno.wtf/api') as resp:
            data = await resp.json()
            answer = data['answer'].upper()
            image_url = data['image']
            embed = discord.Embed(title=f"質問: {question}", description=f"**巻貝の答え: {answer}**", color=0x00ff00)
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="dog", description="可愛い犬の画像を召喚します")
async def dog(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://dog.ceo/api/breeds/image/random') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    image_url = data['message'] 
                    embed = discord.Embed(color=0xe67e22)
                    embed.set_image(url=image_url)
                    await interaction.followup.send(content="🐶 わん！", embed=embed)
                else:
                    await interaction.followup.send("🐶 画像が見つからなかったよ...")
    except Exception as e:
        print(f"Dogエラー: {e}")
        await interaction.followup.send("🐶 画像を引っ張ってくる途中で転んじゃった！")

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
    poke_id = random.randint(1, 1010)
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://pokeapi.co/api/v2/pokemon/{poke_id}') as resp:
            data = await resp.json()
            poke_name = data['name'].capitalize()
            image_url = data['sprites']['other']['official-artwork']['front_default']
            embed = discord.Embed(title=f"野生の {poke_name} が飛び出してきた！", color=0xff0000)
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="advice", description="ランダムなありがたい言葉（英語）を授けます")
async def advice(interaction: discord.Interaction):
    await interaction.response.defer()
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.adviceslip.com/advice', headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    advice_text = data['slip']['advice']
                    await interaction.followup.send(f"💬 **今日のアドバイス:**\n「{advice_text}」")
                else:
                    await interaction.followup.send("💬 賢者がお留守のようです...")
    except Exception as e:
        print(f"Adviceエラー: {e}")
        await interaction.followup.send("💬 失敗しました！もう一度試してね。")

@bot.tree.command(name="fake", description="この世に存在しない架空の人物プロフィールを生成します")
async def fake(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://randomuser.me/api/') as resp:
            data = await resp.json()
            user = data['results'][0]
            name = f"{user['name']['first']} {user['name']['last']}"
            country = user['location']['country']
            age = user['dob']['age']
            picture = user['picture']['large']
            embed = discord.Embed(title="🕵️ 架空の人物プロファイル", color=0x2b2d31)
            embed.add_field(name="名前", value=name, inline=True)
            embed.add_field(name="国籍", value=country, inline=True)
            embed.add_field(name="年齢", value=f"{age}歳", inline=True)
            embed.set_thumbnail(url=picture)
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="btc", description="現在のビットコイン価格（日本円）を調べます")
async def btc(interaction: discord.Interaction):
    await interaction.response.defer()
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=jpy'
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = data['bitcoin']['jpy']
                    formatted_price = f"{price:,}"
                    await interaction.followup.send(f"📈 **現在のビットコイン価格:**\n1 BTC = **{formatted_price} 円** です！")
                else:
                    await interaction.followup.send("📈 取引所のデータにアクセスできませんでした💦")
    except Exception as e:
        print(f"BTCエラー: {e}")
        await interaction.followup.send("📈 価格の取得に失敗しました。")

@bot.tree.command(name="weather", description="指定した都市の現在の天気を調べます")
@app_commands.describe(city="都市名（例: Tokyo, Osaka, London）")
async def weather(interaction: discord.Interaction, city: str):
    await interaction.response.defer()
    image_url = f"https://wttr.in/{city}_0tqp_lang=ja.png"
    embed = discord.Embed(title=f"🌦️ {city.capitalize()} のお天気", color=0x00ffff)
    embed.set_image(url=image_url)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ai", description="AIに質問やお願いをします")
@app_commands.describe(prompt="AIに話しかける内容")
async def ai_chat(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/{encoded_prompt}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                answer = await resp.text()
                if len(answer) > 1900:
                    answer = answer[:1900] + "\n\n(※長すぎるため途中でカットしました！)"
                await interaction.followup.send(f"👤 **あなたの質問:** {prompt}\n\n🤖 **AIの回答:**\n{answer}")
            else:
                await interaction.followup.send("ごめんね、今AIがパンクしてて考えられないみたい...")

@bot.tree.command(name="search", description="Wikipediaでキーワードを検索します")
@app_commands.describe(query="検索したいキーワード")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    url = f"https://ja.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=3&format=json"
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    titles = data[1]
                    links = data[3] 
                    if not titles:
                        await interaction.followup.send(f"「{query}」に関する情報は見つかりませんでした💦")
                        return
                    embed = discord.Embed(title=f"🔍 「{query}」の検索結果", color=0x3498db)
                    for i in range(len(titles)):
                        embed.add_field(name=titles[i], value=f"[🔗記事を読む]({links[i]})", inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("検索サーバーが混雑しているみたいです...")
    except Exception as e:
        print(f"Searchエラー: {e}")
        await interaction.followup.send("検索中にエラーが起きちゃいました...")

@bot.tree.command(name="music", description="iTunesで曲を検索して表示します")
@app_commands.describe(query="曲名やアーティスト名")
async def music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&country=jp&media=music&limit=1"
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['resultCount'] == 0:
                        await interaction.followup.send(f"🎧 「{query}」は見つからなかったよ...")
                        return
                    track = data['results'][0]
                    artist_name = track.get('artistName', '不明なアーティスト')
                    track_name = track.get('trackName', '不明な曲')
                    artwork_url = track.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                    preview_url = track.get('previewUrl', '')
                    embed = discord.Embed(title=f"🎵 {track_name}", description=f"アーティスト: **{artist_name}**", color=0xff2d55)
                    embed.set_thumbnail(url=artwork_url)
                    if preview_url:
                        embed.add_field(name="試聴", value=f"[▶️ 30秒試聴する]({preview_url})")
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("🎧 Appleのサーバーに繋がらなかったみたい！")
    except Exception as e:
        print(f"Musicエラー: {e}")
        await interaction.followup.send("🎧 検索中にエラーが起きちゃいました！")

@bot.tree.command(name="qr", description="URLや文字からQRコードを作成します")
@app_commands.describe(text="QRコードにしたい文字やURL")
async def qr(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    safe_text = urllib.parse.quote(text)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={safe_text}"
    embed = discord.Embed(title="📱 QRコードを作成しました！", color=0xffffff)
    embed.set_image(url=qr_url)
    embed.set_footer(text=f"内容: {text}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="nasa", description="NASAが公開している「今日の宇宙画像」を表示します")
async def nasa(interaction: discord.Interaction):
    await interaction.response.defer()
    url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    title = data.get('title', '無題')
                    image_url = data.get('url', '')
                    embed = discord.Embed(title=f"🌌 {title}", color=0x0b3d91)
                    embed.set_image(url=image_url)
                    embed.set_footer(text="Provided by NASA API")
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("🌌 NASAの通信基地からの応答がありません！")
    except Exception as e:
        print(f"NASAエラー: {e}")
        await interaction.followup.send("🌌 宇宙の彼方と通信中にエラーが発生しました。")

@bot.tree.command(name="translate", description="外国語を日本語に自動翻訳します")
@app_commands.describe(text="翻訳したい文章")
async def translate(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=Autodetect|ja"
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated_text = data['responseData']['translatedText']
                    embed = discord.Embed(title="🌐 翻訳結果", color=0x4285F4)
                    embed.add_field(name="元の文章", value=text, inline=False)
                    embed.add_field(name="日本語", value=translated_text, inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("🌐 翻訳サーバーが少し混み合っているみたいです！")
    except Exception as e:
        print(f"Translateエラー: {e}")
        await interaction.followup.send("🌐 翻訳中にエラーが発生しました💦")

@bot.tree.command(name="mc", description="マイクラサーバーの現在の状態を調べます")
@app_commands.describe(address="サーバーアドレス")
async def mc(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    url = f"https://api.mcsrvstat.us/2/{urllib.parse.quote(address)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('online'):
                        players_online = data['players']['online']
                        players_max = data['players']['max']
                        version = data.get('version', '不明')
                        embed = discord.Embed(title=f"⛏️ {address} の状態", color=0x2ecc71)
                        embed.add_field(name="ステータス", value="🟢 オンライン", inline=True)
                        embed.add_field(name="プレイヤー数", value=f"{players_online} / {players_max} 人", inline=True)
                        embed.add_field(name="バージョン", value=version, inline=True)
                    else:
                        embed = discord.Embed(title=f"⛏️ {address} の状態", color=0xe74c3c)
                        embed.add_field(name="ステータス", value="🔴 オフライン", inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("⛏️ APIサーバーに応答がありませんでした。")
    except Exception as e:
        print(f"MCエラー: {e}")
        await interaction.followup.send("⛏️ サーバー情報の取得に失敗しました。")

@bot.tree.command(name="zip", description="郵便番号から日本の住所を検索します")
@app_commands.describe(zipcode="ハイフンなしの7桁")
async def zipcode(interaction: discord.Interaction, zipcode: str):
    await interaction.response.defer()
    url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={urllib.parse.quote(zipcode)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['status'] == 200 and data['results']:
                        result = data['results'][0]
                        address = f"{result['address1']}{result['address2']}{result['address3']}"
                        kana = f"{result['kana1']} {result['kana2']} {result['kana3']}"
                        embed = discord.Embed(title="📮 住所検索結果", color=0xf39c12)
                        embed.add_field(name="郵便番号", value=f"〒{zipcode}", inline=False)
                        embed.add_field(name="住所", value=address, inline=False)
                        embed.add_field(name="フリガナ", value=kana, inline=False)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"📮 「{zipcode}」の住所は見つかりませんでした！")
                else:
                    await interaction.followup.send("📮 検索サーバーがお休みのようです。")
    except Exception as e:
        print(f"Zipエラー: {e}")
        await interaction.followup.send("📮 住所の検索中にエラーが発生しました。")

@bot.tree.command(name="yesno", description="AIがあなたの悩みに「Yes」か「No」で白黒つけます")
@app_commands.describe(question="迷っていること")
async def yesno(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://yesno.wtf/api', timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data['answer'].upper()
                    gif_url = data['image']
                    embed = discord.Embed(title=f"🤔 質問: {question}", color=0x9b59b6)
                    embed.add_field(name="お告げ", value=f"**{answer}!!!**", inline=False)
                    embed.set_image(url=gif_url)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("🤔 宇宙の意志が読み取れませんでした...")
    except Exception as e:
        print(f"YesNoエラー: {e}")
        await interaction.followup.send("🤔 占い中に水晶玉が割れました！")

@bot.tree.command(name="duck", description="なぜかアヒルの画像を召喚します")
async def duck(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://random-d.uk/api/v2/random', timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    image_url = data['url']
                    embed = discord.Embed(title="🦆 クワッ！", color=0xf1c40f)
                    embed.set_image(url=image_url)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("🦆 アヒルは池に帰りました。")
    except Exception as e:
        print(f"Duckエラー: {e}")
        await interaction.followup.send("🦆 アヒルが転びました。")

@bot.tree.command(name="trivia", description="誰の役にも立たない「世界の無駄知識」を披露します")
async def trivia(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://uselessfacts.jsph.pl/api/v2/facts/random?language=en', timeout=5) as resp:
                if resp.status == 200:
                    fact_data = await resp.json()
                    english_fact = fact_data['text']
                    trans_url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(english_fact)}&langpair=en|ja"
                    headers = {"User-Agent": "MyDiscordBot/1.0"}
                    async with session.get(trans_url, headers=headers, timeout=5) as trans_resp:
                        if trans_resp.status == 200:
                            trans_data = await trans_resp.json()
                            japanese_fact = trans_data['responseData']['translatedText']
                            embed = discord.Embed(title="🧠 今日の無駄知識", description=japanese_fact, color=0xe67e22)
                            embed.set_footer(text=f"原文: {english_fact}")
                            await interaction.followup.send(embed=embed)
                        else:
                            await interaction.followup.send("🧠 翻訳に失敗しちゃいました...")
                else:
                    await interaction.followup.send("🧠 知識を忘れました...")
    except Exception as e:
        print(f"Triviaエラー: {e}")
        await interaction.followup.send("🧠 脳細胞がショートしました！")

# ==========================================
# 🚀 実行部分（FlaskとBotの同時起動）
# ==========================================
if __name__ == "__main__":
    # Flask(Webサーバー)を裏で起動
    Thread(target=run_flask).start()
    
    # トークンを取得してBotを起動
    token = os.getenv('DISCORD_TOKEN')
    bot.run(token)
