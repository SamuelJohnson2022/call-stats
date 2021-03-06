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
from PIL import Image
from io import BytesIO
import requests
import numpy as np
import scipy
import scipy.misc
import scipy.cluster
import binascii


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

    @commands.command(name="start", brief="Starts recording on specified channel")
    async def start_command(self, ctx, voiceChannel: ChannelConverter()):
        # Starts recording the channel stats
        # Check if there already is a recording
        if self.voiceChannel is not None:
            await ctx.send("There is already a recording in process")
        else:
            # If there is no recording, add the RecordingCog and send a message
            self.voiceChannel = voiceChannel
            self.ctx = ctx
            # Add any currently connected users to user list
            for memberID in voiceChannel.voice_states:
                # This get_member function only works with the members intent activated
                self.users[memberID] = UserStats(
                    ctx.guild.get_member(memberID))

                # Append the current time as the user's "join time"
                self.users[memberID].joinTimes.append(time.time())

            # Send a message so the user knows a recording has started
            await ctx.send(f"Started recording on: **{voiceChannel}**")

    @commands.command(name="stop", brief="Stops any active recordings")
    async def stop_command(self, ctx):
        if self.voiceChannel == None:  # Check for an active recording
            await ctx.send("There is no active recording")
        else:
            await ctx.send(f"Stopped recording on channel: **{self.voiceChannel}**")

            if len(self.users) == 0:
                await ctx.send("There was no activity during the recording period.")
                # Reset all of the variables for the cog
                self.voiceChannel = None
                self.textChannel = None
                self.users = {}
                return

            # Make each of the users current in call "leave"
            for memberID in self.voiceChannel.voice_states:
                self.users[memberID].leaveTimes.append(time.time())

            # Keeps track of user stats across the recording
            topUser = []
            topTime = 0
            activeUser = []
            mostJoins = 0

            # Iterate through all of the users and track their data
            for userID in self.users.keys():

                # Variable used to keep track of total time in call
                userTotal = 0
                # Iterate through the join and leave times for the user, and add them up
                for i in range(len(self.users[userID].joinTimes)):
                    # Simple (leave - join) times to get total time in call
                    userTotal += self.users[userID].leaveTimes[i] - \
                        self.users[userID].joinTimes[i]

                # Round the user total to the second to account for slight deviations
                userTotal = round(userTotal)
                # Check if this user's time is more than the current top
                if userTotal > topTime:
                    # Clear the previous list and add this user
                    topTime = userTotal
                    topUser.clear()
                    topUser.append(self.users[userID].user.name)
                elif userTotal == topTime:
                    # Just add this user to the end of the top list
                    topUser.append(self.users[userID].user.name)

                # Find out who joined and left the most
                userJoins = len(self.users[userID].joinTimes)
                if userJoins > mostJoins:
                    # Clear the previous list and add this user
                    mostJoins = userJoins
                    activeUser.clear()
                    activeUser.append(self.users[userID].user.name)
                elif userJoins == mostJoins:
                    # Just add this user to the end of the top list
                    activeUser.append(self.users[userID].user.name)

            # Create the plotly chart and save it as ./images/temp.png
            createChart(self.users)

            # Create an embed for sending summary message
            embed = Embed()
            embed.title = "Here's a quick summary of the call:"

            # Check if there is a tie for the top user
            if len(topUser) > 1:
                embed.add_field(
                    name="Longest Time in Call",
                    value=f"{', '.join(topUser)} stayed in the call the longest with \
                        {str(topTime) + ' seconds' if topTime < 120 else str(round(topTime/60)) + ' minutes'}.")
            else:  # With just one top user, just add in their name and time
                embed.add_field(
                    name="Longest Time in Call",
                    value=f"{topUser[0]} stayed in the call the longest with \
                        {str(topTime) + ' seconds' if topTime < 120 else str(round(topTime/60)) + ' minutes'}.")

            # See who the first user to join was
            firstTime = round(list(self.users.values())[0].joinTimes[0])
            # Long list comprehension that joins all users where they have a time equal to the first time
            firstList = [user.user.name for user in list(
                self.users.values()) if round(user.joinTimes[0]) == firstTime]

            # Create the embed field for the first user
            embed.add_field(
                name="First User in Call",
                value=f"{', '.join(firstList)} {'was' if len(firstList) == 1 else 'were'} \
                first in the call at {datetime.datetime.fromtimestamp(firstTime).strftime('%#I:%M %p')}.")

            # Find who joined and left the most
            if len(activeUser) > 1:
                embed.add_field(
                    name="Most Sporadic User",
                    value=f"{', '.join(activeUser)} had the most active times with {mostJoins}.")
            else:  # With just one top user, just add in their name and time
                embed.add_field(
                    name="Most Sporadic User",
                    value=f"{activeUser[0]} had the most active times with {mostJoins}.")

            # Find the chart image in the same folder as the main bot file
            file = discord.File("images/temp.png")
            embed.set_image(url="attachment://images/temp.png")
            # filename and extension have to match
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
            if len(self.users) == 0:
                await ctx.send("There was no activity during the recording period so far.")
                return
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

                await ctx.send(f"{self.users[userID].user.name} has participated for {round(userTotal)} seconds.")

            # Remove all of the previous leave times that were added
            for memberID in self.voiceChannel.voice_states:
                self.users[memberID].leaveTimes.pop()

    @ start_command.error  # Error message for failed start command
    async def start_error(self, ctx, error):
        # Unwrapping the error cause because of how discord.py raises some of them
        error = error.__cause__ or error
        if isinstance(error, ValueError):
            # Tell the user that the channel they specified was non-existant
            await ctx.send("That voice channel does not exist. (Remember to be case sensitive)")
        elif isinstance(error, MissingRequiredArgument):
            # Tell the user they need a channel name argument
            await ctx.send("Missing a name for the target voice channel")
        else:
            # Final case where the error is not covered by this handler
            await ctx.send("Something went wrong.")
            raise error


class UserStats:  # Class used by a list in the recording cog that details user stats
    def __init__(self, user: discord.Member) -> None:
        self.user = user  # user object to be added of discord Member class
        self.joinTimes = []  # Details any time the user joins the voice channel
        self.leaveTimes = []  # Details whenever this user has left the voice channel

    # Used when iterating over the dictionary of UserStats objects
    def __eq__(self, o: object) -> bool:
        return self.user.id == o.user.id


def createChart(users: dict):
    # Takes a user's join and leave times and returns a graph using plotly

    # List used to store user dictionaries and color dict is used to store their colors
    dictList = []
    urlDict = dict()
    colorDict = dict()
    # Iterate through all of the users
    for key in users:

        # If the user doesnt have an avatar, find the color of their default avatar
        if users[key].user.avatar == None:
            # Get the discriminator key
            userKey = int(users[key].user.discriminator) % 5

            response1 = requests.get(users[key].user.default_avatar_url)
            # Plotly didnt like normal urls for the default avatars, so we open it with PIL
            urlDict[users[key].user.name] = Image.open(
                BytesIO(response1.content))

            # Discord assigns these 5 colors as the default for each person using their discriminator (#1234)
            colorList = ['#7289da', '#747f8d', '#43b581', '#faa61a', '#f04747']
            colorDict[users[key].user.name] = colorList[userKey]

        # Otherwise, find the dominant color of the user avatar
        else:
            # Get the url of the user avatar
            urlDict[users[key].user.name] = str(users[key].user.avatar_url)
            response = requests.get(users[key].user.avatar_url)
            # Find the dominant color of their avatar  using clusters - credit Peter Hansen on Stack Overflow
            with Image.open(BytesIO(response.content)) as im:
                im = im.resize((150, 150))      # optional, to reduce time
                ar = np.asarray(im)
                shape = ar.shape
                ar = ar.reshape(np.product(
                    shape[:2]), shape[2]).astype(float)

                codes, dist = scipy.cluster.vq.kmeans(ar, 5)

                vecs, dist = scipy.cluster.vq.vq(
                    ar, codes)         # assign codes
                counts, bins = np.histogram(
                    vecs, len(codes))    # count occurrences

                # find most frequent
                index_max = np.argmax(counts)
                peak = codes[index_max]
                colour = binascii.hexlify(bytearray(int(c)
                                                    for c in peak)).decode('ascii')
                colorDict[users[key].user.name] = ("#" + str(colour))

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

    # Create the pandas data frame used by plotly
    df = pd.DataFrame([data for data in dictList])

    # Create the actual gantt chart
    fig = px.timeline(df, x_start="Start", x_end="Finish",
                      y="User", color="User", color_discrete_map=colorDict)
    # Styling Changes
    fig.update_layout(plot_bgcolor="rgb(54,57,62)",
                      paper_bgcolor="rgb(54,57,62)",
                      font=dict(color="#fff", size=20),
                      width=1500)
    fig.update_yaxes(showticklabels=False, title=None)
    fig.update_xaxes(tickformat="%-I:%M %p")

    # Add the image axis markers
    for key2 in urlDict:
        # Add images
        fig.add_layout_image(
            dict(
                source=urlDict[key2],
                x=0,
                y=key2
            ))

    # Update the figure with these images
    fig.update_layout_images(dict(
        xref="paper",
        yref="y",
        sizex=0.5,
        sizey=0.5,
        xanchor="center",
        yanchor="middle"
    ))

    # Export the image to a temp.png file
    fig.write_image("images/temp.png")
    fig.to_image(format="png", engine="kaleido")
    return


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

            # Prevent spam joining and leaving, must be at least [30 s] between last join/leave
            if activeCog.users[member.id].joinTimes[-1] - activeCog.users[member.id].leaveTimes[-1] < 30:
                activeCog.users[member.id].joinTimes.pop()
                activeCog.users[member.id].leaveTimes.pop()

        else:  # In case it is a new user
            # Add them to the users dictionary
            activeCog.users[member.id] = UserStats(member)
            # Append their time to the joinTimes list for that user
            activeCog.users[member.id].joinTimes.append(time.time())

    # Check if it's the recorded channel when leaving
    elif before.channel == activeCog.voiceChannel and after.channel != activeCog.voiceChannel:
        if member.id in activeCog.users:  # This should always be the case
            if activeCog.users[member.id].user == None:
                # If the startup fails to find the member object, we can fill in here
                activeCog.users[member.id].user = member
            # Append their time to the leaveTimes list for that user
            activeCog.users[member.id].leaveTimes.append(time.time())
        else:  # If somehow a user snuck in without being notices this will occur
            await activeCog.ctx.send("Something went wrong")

    # Otherwise this is not the right channel and we ignore


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
