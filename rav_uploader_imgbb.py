# rav_uploader_imgbb_reaction.py
import os
import aiohttp
from dotenv import load_dotenv
import discord
import base64
import asyncio
from aiohttp import web

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

# -------------------------------
# Minimal web server for Render
# -------------------------------
async def handle(request):
    return web.Response(text="Bot is running ✅")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("🌐 Web server running on port 10000")

# -------------------------------
# Discord client with web server
# -------------------------------
class MyClient(discord.Client):
    async def setup_hook(self):
        self.loop.create_task(start_web())

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != CHANNEL_ID:
            return

        if not message.attachments:
            return

        # Ask user to confirm upload
        confirm_msg = await message.reply("⚠️ React with ✅ within 30 seconds to confirm image upload.")
        await confirm_msg.add_reaction("✅")

        def check(reaction, user):
            return user == message.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id

        try:
            await self.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="❌ Upload cancelled (no confirmation).")
            return

        # User confirmed, proceed with upload
        await confirm_msg.edit(content="📤 Uploading your image(s)...")

        async with aiohttp.ClientSession() as session:
            urls = []
            for att in message.attachments:
                if att.content_type and "image" not in att.content_type:
                    continue

                img_bytes = await att.read()
                img_base64 = base64.b64encode(img_bytes).decode()

                data = {
                    "key": IMGBB_API_KEY,
                    "image": img_base64,
                    "name": att.filename
                }

                try:
                    async with session.post("https://api.imgbb.com/1/upload", data=data, timeout=60) as resp:
                        js = await resp.json()
                        if resp.status == 200 and js.get("success"):
                            urls.append(js["data"]["url"])
                        else:
                            urls.append(f"❌ Upload failed ({resp.status})")
                except Exception as e:
                    urls.append(f"❌ Upload failed ({e})")

            if urls:
                embed = discord.Embed(
                    title="📤 Image Uploaded Successfully!",
                    description=f"Here {'are' if len(urls) > 1 else 'is'} your image{'s' if len(urls) > 1 else ''}:",
                    color=discord.Color.green()
                )

                for idx, url in enumerate(urls, start=1):
                    embed.add_field(name=f"Image {idx}", value=url, inline=False)
                    if idx == 1:
                        embed.set_thumbnail(url=url)

                embed.set_footer(text=f"Uploaded by {message.author.display_name}")
                await message.reply(embed=embed)

# -------------------------------
# Start the bot
# -------------------------------
client = MyClient(intents=intents)
client.run(TOKEN)
