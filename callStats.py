import discord
from discord.ext.commands import Bot
from textwrap import dedent

# Just so our code doesn't look bad
from discord.ext.commands.errors import ConversionError

# Reads the bot token from file
with open("token.txt") as fp:
    TOKEN = fp.read().strip()

# Creates the bot
bot = Bot(command_prefix="cs-")

# Class to convert user argument into discord usable channel names


class channelConverter(discord.ext.commands.Converter):

    async def convert(self, ctx, argument):
        # check if channel does not exist
        if argument not in str(ctx.guild.voice_channels):
            # Raise an error for a nonexistent channel
            raise ValueError("Not an existing voice channel")
        else:
            for chan in ctx.guild.voice_channels:  # Finds it in the channel list
                if argument == chan:
                    argument = chan  # Set the argument to be a channel variable

        return argument  # return the new channel object


@bot.command(name="start")  # Starts recording the channel stats
async def start_command(ctx, voiceChannel: channelConverter()):
    await ctx.send("Started recording on channel - %s." % str(voiceChannel))


@start_command.error  # Error message for failed start command
async def start_error(ctx, error):
    await ctx.send("That channel does not exist. (Remember to be case sensitive)")


@bot.command(
    name="hello", aliases=["hi", "hullo", "hey"], brief="Greet the bot!"
)
async def greet_back_command(ctx):
    await ctx.send(f"Howdy {ctx.author.display_name}!")


# Never forget to leave this on the bottom of your code
# Anything after this line will only be executed once the bot logs out
bot.run(TOKEN)
