from discord.ext.commands import Bot

with open("token.txt") as fp:
    TOKEN = fp.read().strip()

bot = Bot(command_prefix="cs-")

bot.run(TOKEN)
