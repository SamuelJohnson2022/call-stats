# Imports
import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands.errors import ConversionError, MissingRequiredArgument
import time

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


class RecordingCommands(commands.Cog):
    # Cog containing all commands used during recording for the bot after start
    def __init__(self, bot) -> None:
        super().__init__()
        # Initialized with a reference to the bot and the voice channel set to None
        self.bot = bot
        self.voiceChannel = None
        self.users = {}  # Dictionary to store user data with key being their discord ID
        self.ctx = None

    @commands.command(name="stop", brief="Stops any active recordings")
    async def stop_command(self, ctx):
        if self.voiceChannel == None:  # Check for an active recording
            await ctx.send("There is no active recording")
        else:
            await ctx.send(f"Stopped recording on channel: {self.voiceChannel}")
            # Reset all of the variables
            self.voiceChannel = None
            self.textChannel = None
            self.users = {}

    @commands.command(name="check", brief="Reports the status of an active recording")
    async def check_command(self, ctx):
        if self.voiceChannel == None:  # Check for an active recording
            await ctx.send("There is no active recording")
        else:
            await ctx.send("This does nothing yet")


class UserStats:  # Class used by a list in the recording cog that details user stats
    def __init__(self, user: discord.Member) -> None:
        self.user = user  # user object to be added of discord abc class
        self.joinTimes = []  # Details any time the user joins the voice channel
        self.leaveTimes = []  # Details whenever this user has left the voice channel

    def __eq__(self, o: object) -> bool:
        return self.user.id == o.user.id


@bot.command(name="start", brief="Starts recording on specified channel")
async def start_command(ctx, voiceChannel: ChannelConverter()):
    # Starts recording the channel stats
    activeCog = bot.get_cog("RecordingCommands")
    # Check if there already is a recording
    if activeCog.voiceChannel is not None:
        await ctx.send("There is already a recording in process")
    else:
        # If there is no recording, add the RecordingCog and send a message
        activeCog.voiceChannel = voiceChannel
        activeCog.ctx = ctx
        # Add any currently connected users to user list
        for memberID in voiceChannel.voice_states:
            # This get_member function doesnt work if user is in the voice channel before starting the bot
            activeCog.users[memberID] = UserStats(
                ctx.guild.get_member(memberID))
            activeCog.users[memberID].joinTimes.append(time.time())

        await ctx.send(f"Started recording on channel: {voiceChannel}!")


@ bot.listen("on_voice_state_update")  # Listener for voice activity
# Member is type discord.Member and before and after are type discord.VoiceState
async def call_activity(member, before, after):
    # First we check if its on the actively recorded channel
    activeCog = bot.get_cog("RecordingCommands")  # Get the recording cog

    # If there is no active recording, we can stop already
    if activeCog.voiceChannel == None:
        return

    # Check if it's the recorded channel when joining
    if after.channel == activeCog.voiceChannel and before.channel != activeCog.voiceChannel:

        # Check if the user is already in the list of users
        if member.id in activeCog.users:
            # Append their time to the joinTimes list for that user
            activeCog.users[member.id].joinTimes.append(time.time())
            # Temp debug output
            await activeCog.ctx.send(f"{activeCog.users[member.id].user.name} joins: {activeCog.users[member.id].joinTimes[-1]}")
        else:  # In case it is a new user
            # Add them to the users dictionary
            activeCog.users[member.id] = UserStats(member)
            # Append their time to the joinTimes list for that user
            activeCog.users[member.id].joinTimes.append(time.time())
            # Temp debug output
            await activeCog.ctx.send(f"{activeCog.users[member.id].user.name} joins: {activeCog.users[member.id].joinTimes[-1]}")

    # Check if it's the recorded channel when leaving
    elif before.channel == activeCog.voiceChannel and after.channel != activeCog.voiceChannel:
        if member.id in activeCog.users:  # This should always be the case
            if activeCog.users[member.id].user == None:
                # If the startup fails to find the member object, we can fill in here
                activeCog.users[member.id].user = member
            # Append their time to the leaveTimes list for that user
            activeCog.users[member.id].leaveTimes.append(time.time())
            # Temp debug output
            await activeCog.ctx.send(f"{activeCog.users[member.id].user.name} leaves: {activeCog.users[member.id].leaveTimes[-1]}")
        else:  # If somehow a user snuck in without being notices this will occur
            await activeCog.ctx.send("Something went wrong")

    # Otherwise this is not the right channel and we ignore


@ start_command.error  # Error message for failed start command
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


@ bot.listen("on_command_error")  # Error message if user tries bad command
async def warn_on_command_error(ctx, error):
    # Unwrapping the error cause because of how discord.py raises some of them
    error = error.__cause__ or error

    if isinstance(error, commands.CommandNotFound):
        # Direct the user to use the help command if they try a bad command
        await ctx.send("It seems that command doesnt exist. Try cs-help for a list of commands")

# Add the recording commands cog to the bot
bot.add_cog(RecordingCommands(bot))

# Start the bot
# Anything after this line will only be executed once the bot logs out
bot.run(TOKEN)
