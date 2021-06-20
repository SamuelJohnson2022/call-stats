import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from textwrap import dedent

# Just so our code doesn't look bad
from discord.ext.commands.errors import ConversionError, MissingRequiredArgument

# Reads the bot token from file
with open("token.txt") as fp:
    TOKEN = fp.read().strip()

# Creates the bot with prefix cs-
bot = Bot(command_prefix="cs-")


class ChannelConverter(commands.Converter):
    # Class to convert user argument into discord usable channel names

    async def convert(self, ctx, argument):
        # check if channel exists
        for channel in ctx.guild.voice_channels:  # Finds it in the channel list
            if argument == channel.name:
                argument = channel  # Set the argument to be a channel variable
        if isinstance(argument, discord.VoiceChannel):  # See if the argument has been set
            # Return the new channel object
            return argument
        else:
            # return the new channel object
            raise ValueError("Not an existing voice channel")


class RecordingCog(commands.Cog):
    # Cog containing all commands used during recording for the bot after start
    # Intializes with the voiceChannel it started recording on
    def __init__(self, bot, voiceChannel) -> None:
        super().__init__()
        # Initialized with a reference to the bot and the voice channel the recording is on
        self.bot = bot
        self.voiceChannel = voiceChannel

    @commands.command(name="stop", brief="Stops any active recordings")
    async def stop_command(self, ctx):
        await ctx.send("Stopped recording on channel: %s." % str(self.voiceChannel))
        # Removes the cog for recording commands
        self.bot.remove_cog("RecordingCog")

    @commands.command(name="check", brief="Reports the status of an active recording")
    async def system_check_command(self, ctx):
        await ctx.send("This does nothing yet")


# Starts recording the channel stats
@bot.command(name="start", brief="Starts recording on specified channel")
async def start_command(ctx, voiceChannel: ChannelConverter()):
    # Enables the cog for commands used when recording stats
    cogCheck = bot.get_cog('RecordingCog')

    # Check if there already is a recording
    if cogCheck is not None:
        await ctx.send("There is already a recording in process")
    else:
        # If there is no recording, add the RecordingCog and send a message
        bot.add_cog(RecordingCog(bot, voiceChannel))
        await ctx.send(f"Howdy {str(voiceChannel)}!")


@start_command.error  # Error message for failed start command
async def start_error(ctx, error):
    # Unwrapping the error cause because of how discord.py raises some of them
    error = error.__cause__ or error
    if isinstance(error, ValueError):
        # Tell the user that the channel they specified was non-existant
        await ctx.send("That channel does not exist. (Remember to be case sensitive)")
    elif isinstance(error, MissingRequiredArgument):
        # Tell the user they need a channel name argument
        await ctx.send("Missing a name for the target channel")
    else:
        # Final case where the error is not covered by this handler
        await ctx.send("Something went wrong.")
        raise error


@bot.listen("on_command_error")
async def warn_on_command_cooldown(ctx, error):
    # Unwrapping the error cause because of how discord.py raises some of them
    error = error.__cause__ or error

    if isinstance(error, commands.CommandNotFound):
        if ctx.invoked_with == "stop":
            # Tell the user that there is no active recording
            await ctx.send("There is no current recording active")
        else:
            # Direct the user to use the help command if they try a bad command
            await ctx.send("It seems that command doesnt exist, try cs-help")

# Never forget to leave this on the bottom of your code
# Anything after this line will only be executed once the bot logs out
bot.run(TOKEN)
