# Author: Samuel Johnson
# Date: June 2021

# Imports
import os
import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands.errors import ConversionError, MissingRequiredArgument
import time
import datetime
import plotly.express as px
import pandas as pd

# Reads the bot token from file
with open("token.txt") as fp:
    TOKEN = fp.read().strip()

# Declare intents, needs members intent for getting members in call before starting the bot
intents = discord.Intents.default()
intents.members = True

# Creates the bot with prefix cs-
bot = Bot(command_prefix="cs-", intents=intents)


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

            # Make each of the users current in call "leave"
            for memberID in self.voiceChannel.voice_states:
                self.users[memberID].leaveTimes.append(time.time())

            # Iterate through all of the users and track their data
            for userID in self.users.keys():

                # Variable used to keep track of total time in call
                userTotal = 0
                # Iterate through the join and leave times for the user, and add them up
                for i in range(len(self.users[userID].joinTimes)):
                    # Simple (leave - join) times to get total time in call
                    userTotal += self.users[userID].leaveTimes[i] - \
                        self.users[userID].joinTimes[i]

                await ctx.send(f"{self.users[userID].user.name} participated for {userTotal} seconds")

            # Create the plotly chart and save it as ./images/temp.png
            createChart(self.users)

            embed = Embed()
            embed.title = "Here's a quick summary of the call"
            # an image in the same folder as the main bot file
            file = discord.File("images/temp.png")
            embed.set_image(url="attachment://images/temp.png")
            # filename and extension have to match (ex. "thisname.jpg" has to be "attachment://thisname.jpg")
            await ctx.send(embed=embed, file=file)

            # Get rid of the temp file after sending the message
            os.remove("images/temp.png")

            # Reset all of the variables for the cog
            self.voiceChannel = None
            self.textChannel = None
            self.users = {}

    @commands.command(name="check", brief="Reports the status of an active recording")
    async def check_command(self, ctx):
        if self.voiceChannel == None:  # Check for an active recording
            await ctx.send("There is no active recording")
        else:
            # Make each of the users current in call "leave"
            for memberID in self.voiceChannel.voice_states:
                self.users[memberID].leaveTimes.append(time.time())

            # Iterate through all of the users and track their data
            for userID in self.users.keys():

                # Variable used to keep track of total time in call
                userTotal = 0
                # Iterate through the join and leave times for the user, and add them up
                for i in range(len(self.users[userID].joinTimes)):
                    # Simple (leave - join) times to get total time in call
                    userTotal += self.users[userID].leaveTimes[i] - \
                        self.users[userID].joinTimes[i]

                await ctx.send(f"{self.users[userID].user.name} participated for {userTotal} seconds")

            # Remove all of the previous leave times that were added
            for memberID in self.voiceChannel.voice_states:
                self.users[memberID].leaveTimes.pop()


class UserStats:  # Class used by a list in the recording cog that details user stats
    def __init__(self, user: discord.Member) -> None:
        self.user = user  # user object to be added of discord abc class
        self.joinTimes = []  # Details any time the user joins the voice channel
        self.leaveTimes = []  # Details whenever this user has left the voice channel

    def __eq__(self, o: object) -> bool:
        return self.user.id == o.user.id


def createChart(users: dict):
    # Takes a user's join and leave times and returns a graph using plotly

    dictList = []

    # Iterate through all of the users
    for key in users:
        # Iterate through each of the time frames (join -> leave)
        for i in range(len(users[key].joinTimes)):
            # Create a dict usable by plotly
            statsDict = dict()
            statsDict["Task"] = users[key].user.name + str(i)
            # Format the timestamps to work with plotly
            statsDict["Start"] = datetime.datetime.fromtimestamp(
                users[key].joinTimes[i]).strftime('%Y-%m-%d %H:%M:%S')
            statsDict["Finish"] = datetime.datetime.fromtimestamp(
                users[key].leaveTimes[i]).strftime('%Y-%m-%d %H:%M:%S')
            statsDict["User"] = users[key].user.name

            dictList.append(statsDict)

    # Create hte data frame used by plotly
    df = pd.DataFrame([data for data in dictList])

    # Create the actual gantt chart
    fig = px.timeline(df, x_start="Start", x_end="Finish",
                      y="User", color="User")
    fig.show()

    # Export the image to a temp.png file
    fig.write_image("images/temp.png")
    fig.to_image(format="png", engine="kaleido")
    return


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

            # Prevent spam joining and leaving, must be at least [1 min] between last join/leave
            if activeCog.users[member.id].joinTimes[-1] - activeCog.users[member.id].leaveTimes[-1] < 60:
                activeCog.users[member.id].joinTimes.pop()
                activeCog.users[member.id].leaveTimes.pop()

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
            await activeCog.ctx.send(f"{activeCog.users[member.id].user.name} leaves: {time.ctime(activeCog.users[member.id].leaveTimes[-1])}")
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
