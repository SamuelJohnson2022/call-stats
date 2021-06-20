import discord
from discord.ext import commands
from discord.ext.commands import Bot
from textwrap import dedent

# Just so our code doesn't look bad
from discord.ext.commands.errors import ConversionError

# Reads the bot token from file
with open("token.txt") as fp:
    TOKEN = fp.read().strip()

# Creates the bot with prefix cs-
bot = Bot(command_prefix="cs-")


class ChannelConverter(commands.Converter):
    # Class to convert user argument into discord usable channel names

    async def convert(self, ctx, argument):
        # check if channel exists
        if argument not in str(ctx.guild.voice_channels):
            # Raise a ValueError for a nonexistent channel
            raise ValueError("Not an existing voice channel")
        else:
            for chan in ctx.guild.voice_channels:  # Finds it in the channel list
                if argument == chan:
                    argument = chan  # Set the argument to be a channel variable

        return argument  # return the new channel object


class RecordingCog(commands.Cog):
    # Cog containing all commands used during recording for the bot after start
    # Intializes with the voiceChannel it started recording on
    def __init__(self, bot, voiceChannel) -> None:
        super().__init__()
        # Initialized with a reference to the bot and the voice channel the recording is on
        self.bot = bot
        self.voiceChannel = voiceChannel

    @commands.command(name="stop")
    async def stop_command(self, ctx):
        await ctx.send("Stopped recording on channel: %s." % str(self.voiceChannel))
        # Removes the cog for recording commands
        self.bot.remove_cog("RecordingCog")

    @commands.command(name="check")
    async def system_check_command(self, ctx):
        await ctx.send("This does nothing yet")


@bot.command(  # Simple response commmand
    name="hello", aliases=["hi", "hullo", "hey"], brief="Greet the bot!"
)
async def greet_back_command(ctx):
    await ctx.send(f"Howdy {ctx.author.display_name}!")


@bot.command(name="start")  # Starts recording the channel stats
async def start_command(ctx, voiceChannel: ChannelConverter()):
    # Enables the cog for commands used when recording stats
    cogCheck = bot.get_cog('RecordingCog')
    if cogCheck is not None:
        await ctx.send("There is already a recording in process")
    else:
        bot.add_cog(RecordingCog(bot, voiceChannel))
        await ctx.send("Started recording on channel: %s." % str(voiceChannel))


@start_command.error  # Error message for failed start command
async def start_error(ctx, error):
    # Unwrapping the error cause because of how discord.py raises some of them
    error = error.__cause__ or error
    if isinstance(error, ValueError):
        await ctx.send("That channel does not exist. (Remember to be case sensitive)")
    else:
        await ctx.send("Something went wrong.")


@bot.listen("on_command_error")
async def warn_on_command_cooldown(ctx, error):
    # Unwrapping the error cause because of how discord.py raises some of them
    error = error.__cause__ or error

    if isinstance(error, commands.CommandNotFound):
        if ctx.invoked_with == "stop":
            await ctx.send("There is no current recording active")
        else:
            await ctx.send("It seems that command doesnt exist, try cs-help")

# Never forget to leave this on the bottom of your code
# Anything after this line will only be executed once the bot logs out
bot.run(TOKEN)
