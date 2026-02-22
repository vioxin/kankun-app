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

@bot.tree.command(name="dog", description="可愛い犬の画像を召喚します")
async def dog(interaction: discord.Interaction):
    await interaction.response.defer() # 考え中...にする
    
    try:
        async with aiohttp.ClientSession() as session:
            # 安定している Dog API に変更！
            async with session.get('https://dog.ceo/api/breeds/image/random') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Dog API は 'message' の中に画像のURLが入っています
                    image_url = data['message'] 
                    
                    embed = discord.Embed(color=0xe67e22)
                    embed.set_image(url=image_url)
                    await interaction.followup.send(content="🐶 わん！", embed=embed)
                else:
                    await interaction.followup.send("🐶 今みんなお散歩中で、画像が見つからなかったよ...")
                    
    except Exception as e:
        # 万が一エラーが起きてもフリーズさせないためのお守り
        print(f"Dogエラー: {e}")
        await interaction.followup.send("🐶 画像を引っ張ってくる途中で転んじゃった！もう一度試してね。")

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
    headers = {"User-Agent": "Mozilla/5.0"} # 一般のブラウザのフリをする
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
        await interaction.followup.send("💬 言葉を思い出すのに失敗しました！もう一度試してね。")
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
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            # 制限が緩いCoinGeckoのAPIに変更
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
        await interaction.followup.send("📈 価格の取得に失敗しました。後でもう一度試してね！")

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
@bot.tree.command(name="search", description="Wikipediaでキーワードを検索します")
@app_commands.describe(query="検索したいキーワード")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    # Wikipediaの検索APIを使用
    url = f"https://ja.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=3&format=json"
    # 「私は怪しいロボットじゃありません」という身分証
    headers = {"User-Agent": "MyDiscordBot/1.0"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    titles = data[1] # 見つかった記事のタイトル一覧
                    links = data[3]  # 記事のURL一覧
                    
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
        await interaction.followup.send("検索中にエラーが起きちゃいました...もう一度試してね！")
# ==========================================
# 🎵 エンタメ＆便利API機能
# ==========================================

@bot.tree.command(name="music", description="iTunesで曲を検索してジャケットと試聴リンクを表示します")
@app_commands.describe(query="曲名やアーティスト名")
async def music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    # Apple(iTunes)の検索API（日本のストアを指定）
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
                        
                    # 最初の1件のデータを取り出す
                    track = data['results'][0]
                    artist_name = track.get('artistName', '不明なアーティスト')
                    track_name = track.get('trackName', '不明な曲')
                    # 画質を良くするため、URLの 100x100 を 300x300 に書き換える小技
                    artwork_url = track.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                    preview_url = track.get('previewUrl', '')
                    
                    embed = discord.Embed(title=f"🎵 {track_name}", description=f"アーティスト: **{artist_name}**", color=0xff2d55)
                    embed.set_thumbnail(url=artwork_url)
                    if preview_url:
                        embed.add_field(name="試聴", value=f"[▶️ 30秒試聴する（ブラウザが開きます）]({preview_url})")
                        
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
    
    # 入力された文字をURL用に変換
    safe_text = urllib.parse.quote(text)
    # QRコード生成APIのURL（URL自体が画像になります）
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={safe_text}"
    
    embed = discord.Embed(title="📱 QRコードを作成しました！", color=0xffffff)
    embed.set_image(url=qr_url)
    embed.set_footer(text=f"内容: {text}")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="nasa", description="NASAが公開している「今日の宇宙画像」を表示します")
async def nasa(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # NASA公式API（DEMO_KEYで無料で使えます）
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
# ==========================================
# 🌐 外部サービス連携機能（翻訳・マイクラ・実用ツール）
# ==========================================

@bot.tree.command(name="translate", description="外国語を日本語に自動翻訳します")
@app_commands.describe(text="翻訳したい文章")
async def translate(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    
    # MyMemory API: Autodetect(自動判定) から ja(日本語) へ翻訳
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

@bot.tree.command(name="mc", description="マイクラサーバーの現在の状態（人数など）を調べます")
@app_commands.describe(address="サーバーアドレス (例: mc.hypixel.net)")
async def mc(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    
    # Minecraft Server Status API (Java版)
    url = f"https://api.mcsrvstat.us/2/{urllib.parse.quote(address)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # サーバーがオンラインかどうかチェック
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
                        embed.add_field(name="ステータス", value="🔴 オフライン（または存在しません）", inline=False)
                        
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("⛏️ APIサーバーに応答がありませんでした。")
    except Exception as e:
        print(f"MCエラー: {e}")
        await interaction.followup.send("⛏️ サーバー情報の取得に失敗しました。")

@bot.tree.command(name="zip", description="郵便番号から日本の住所を検索します")
@app_commands.describe(zipcode="ハイフンなしの7桁の数字（例: 1000001）")
async def zipcode(interaction: discord.Interaction, zipcode: str):
    await interaction.response.defer()
    
    # 郵便番号検索API (ZipCloud)
    url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={urllib.parse.quote(zipcode)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # エラーメッセージがないか、結果が存在するかチェック
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
                        await interaction.followup.send(f"📮 「{zipcode}」の住所は見つかりませんでした！数字が間違っていないか確認してね。")
                else:
                    await interaction.followup.send("📮 検索サーバーがお休みのようです。")
    except Exception as e:
        print(f"Zipエラー: {e}")
        await interaction.followup.send("📮 住所の検索中にエラーが発生しました。")
# ==========================================
# 🤪 おふざけ＆ネタ機能
# ==========================================

@bot.tree.command(name="yesno", description="AIがあなたの悩みに「Yes」か「No」で白黒つけます")
@app_commands.describe(question="迷っていること（例: ガチャ引くべき？）")
async def yesno(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            # YES/NOとGIF画像を返してくれるAPI
            async with session.get('https://yesno.wtf/api', timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data['answer'].upper() # yesをYESに大文字化
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
            # アヒル専用API
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
            # 1. まず英語の無駄知識を取得する
            async with session.get('https://uselessfacts.jsph.pl/api/v2/facts/random?language=en', timeout=5) as resp:
                if resp.status == 200:
                    fact_data = await resp.json()
                    english_fact = fact_data['text']
                    
                    # 2. それをMyMemory APIに投げて日本語に翻訳する（APIの連携技！）
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
keep_alive()
token = os.getenv('DISCORD_TOKEN') # もしくは os.getenv('DISCORD_TOK
bot.run(token)
