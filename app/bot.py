import discord, os, asyncio
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="UR LoL"))


# Load all cogs
def load_extensions():
    print("Loading cogs...")
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Successfully loaded cogs.{filename[:-3]}')
            except Exception as e:
                print(f'Error loading cogs.{filename[:-3]}: {e}')


async def main():
    async with bot:
        load_extensions()
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())