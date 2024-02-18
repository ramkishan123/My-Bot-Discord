import discord
from discord.ext import commands
from replit import db  # Import Replit database
from datetime import datetime, timedelta
import re

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

drop_active = False
disabled_channels = []  # List to store IDs of disabled channels
vouch_enabled_channels = set()  # Set to store IDs of channels where vouching is enabled
afk_users = {}  # Dictionary to store AFK users and their info

# Check if 'positive_vouches' and 'negative_vouches' keys exist in the database, if not create them
if 'positive_vouches' not in db:
    db['positive_vouches'] = {}  # Initialize positive vouches dictionary if not already present
if 'negative_vouches' not in db:
    db['negative_vouches'] = {}  # Initialize negative vouches dictionary if not already present


@bot.event
async def on_message(message):
    if message.channel.id not in disabled_channels:
        await bot.process_commands(
            message
        )  # Process commands if the channel is not disabled

    # Check if the message author is not a bot and if the message content matches the pattern for setting AFK
    if not message.author.bot:
        afk_pattern = re.compile(r'!afk (.+) (\d+[smh])')
        match = afk_pattern.match(message.content)
        if match:
            reason = match.group(1)
            time_str = match.group(2)
            await afk(message, reason, time_str)

        # Check if the message mentions any user
        if message.mentions:
            mentioned_users = message.mentions
            for user in mentioned_users:
                if user.id in afk_users:
                    await message.channel.send(f'{user.mention} is AFK: {afk_users[user.id]["reason"]} for {afk_users[user.id]["time_left"]} minutes.')
                    del afk_users[user.id]

    # Remove AFK status when user sends a message
    if message.author.id in afk_users:
        del afk_users[message.author.id]


async def afk(message, reason, time_str):
    global afk_users
    time = parse_time(time_str)
    if time is None:
        await message.channel.send("Invalid time format. Please use '10s', '10m', or '10h'.")
        return
    afk_time = datetime.utcnow() + timedelta(minutes=time)
    afk_users[message.author.id] = {'reason': reason, 'time': afk_time, 'time_left': time}
    await message.channel.send(f'{message.author.mention} is now AFK for "{reason}" for {time} minutes.')


def parse_time(time_str):
    try:
        amount = int(time_str[:-1])
        unit = time_str[-1]
        if unit == 's':
            return amount / 60  # Convert seconds to minutes
        elif unit == 'm':
            return amount
        elif unit == 'h':
            return amount * 60  # Convert hours to minutes
        else:
            return None
    except ValueError:
        return None


@bot.command()
async def afk(ctx, reason: str, time_str: str):
    await ctx.message.delete()  # Delete the command message
    await ctx.send(f'{ctx.author.mention} is now AFK for "{reason}" for {time_str}.')
    await ctx.author.edit(nick=f'[AFK] {ctx.author.display_name}')

    time = parse_time(time_str)
    if time is None:
        await ctx.send("Invalid time format. Please use '10s', '10m', or '10h'.")
        return
    afk_time = datetime.utcnow() + timedelta(minutes=time)
    afk_users[ctx.author.id] = {'reason': reason, 'time': afk_time, 'time_left': time}


@bot.command()
@commands.has_role('Owner')
async def ofdisable(ctx):
    if ctx.channel.id not in disabled_channels:
        disabled_channels.append(ctx.channel.id)  # Add the channel's ID to the list
        await ctx.send('**Commands have been disabled in this channel.**')
    else:
        await ctx.send('**Commands are already disabled in this channel.**')


@bot.command()
@commands.has_role('Owner')
async def startdrop(ctx):
    global drop_active
    if not drop_active:
        drop_active = True
        role = discord.utils.get(ctx.guild.roles,
                                 name="Owo Members")  # Get the role object
        if role is not None:  # If the role exists
            embed = discord.Embed()
            embed.set_image(
                url='https://media1.tenor.com/images/1528f134698db5d31680d3a18e755100/tenor.gif?itemid=1528f134698db5d31680d3a18e755100'
            )  # Direct link to the GIF
            await ctx.send(f'{role.mention}', embed=embed)  # Mention the role and send the GIF
        else:
            await ctx.send('**Role not found.**')
    else:
        await ctx.send('**A drop is already active. Please stop the current drop before starting a new one.**')


@bot.command()
@commands.has_role('Owner')
async def stopdrop(ctx):
    global drop_active
    if drop_active:
        drop_active = False
        await ctx.send('**DropStopped**')  # Send a text message
    else:
        await ctx.send('**No active drop to stop.**')


@bot.command()
async def slap(ctx, user: discord.Member):
    await ctx.send(f'{user.mention} got slapped! Ouch!')


@bot.command()
async def sorry(ctx, user: discord.Member, *, message):
    await ctx.send(f'Sorry, {user.mention}! {message}')


@bot.command()
async def vouch(ctx, user: discord.Member):
    global vouch_enabled_channels
    if ctx.channel.id in vouch_enabled_channels:
        if user.id != ctx.author.id:  # Check if the user trying to vouch is not the same as the user being vouched for
            if str(user.id) in db['positive_vouches']:
                db['positive_vouches'][str(user.id)] += 1
            else:
                db['positive_vouches'][str(user.id)] = 1
            await ctx.send(
                f'{ctx.author.mention} vouched for {user.mention}! Vouch successful!'
            )
        else:
            await ctx.send("You can't vouch for yourself!")
    else:
        await ctx.send("Vouching is not enabled in this channel.")


@bot.command()
async def profile(ctx, user: discord.Member):
    global vouch_enabled_channels
    if ctx.channel.id in vouch_enabled_channels:
        positive_vouches = db['positive_vouches'].get(str(user.id), 0)
        negative_vouches = db['negative_vouches'].get(str(user.id), 0)
        await ctx.send(
            f'```md\n({user})\n# Positive Vouches➕: {positive_vouches}\n# Negative Vouches➖: {negative_vouches}\n```'
        )
    else:
        await ctx.send("Vouching is not enabled in this channel.")


@bot.command()
async def bad(ctx, user: discord.Member):
    global vouch_enabled_channels
    if ctx.channel.id in vouch_enabled_channels:
        if user.id != ctx.author.id:  # Check if the user trying to give a bad vouch is not the same as the user being vouched for
            if str(user.id) in db['negative_vouches']:
                db['negative_vouches'][str(user.id)] += 1
            else:
                db['negative_vouches'][str(user.id)] = 1
            await ctx.send(
                f'{ctx.author.mention} gave {user.mention} a bad vouch! Vouch successful!'
            )
        else:
            await ctx.send("You can't give yourself a bad vouch!")
    else:
        await ctx.send("Vouching is not enabled in this channel.")


@bot.command()
@commands.has_role('Owner')
async def resetall(ctx, user: discord.Member):
    global vouch_enabled_channels
    if ctx.channel.id in vouch_enabled_channels:
        str_user_id = str(user.id)
        if str_user_id in db['positive_vouches']:
            del db['positive_vouches'][str_user_id]
        if str_user_id in db['negative_vouches']:
            del db['negative_vouches'][str_user_id]
        await ctx.send(f'All vouches for {user.mention} have been reset.')
    else:
        await ctx.send("Vouching is not enabled in this channel.")


@bot.command()
@commands.has_role('Owner')
async def warn(ctx, user: discord.Member, *, message):
    if user == bot.user:
        await ctx.send("You can't warn the bot.")
        return

    await ctx.send(
        f'{user.mention} has been warned by {ctx.author.display_name} for "{message}".'
    )


@bot.command()
async def bot_help(ctx):
    command_list = [f"{command.name}" for command in bot.commands]
    await ctx.send("Available commands: " + ", ".join(command_list))


@bot.command()
@commands.has_role('Owner')
async def vouchenable(ctx):
    global vouch_enabled_channels
    if ctx.channel.id not in vouch_enabled_channels:
        vouch_enabled_channels.add(ctx.channel.id)
        await ctx.send('**Vouching has been enabled in this channel.**')
    else:
        await ctx.send('**Vouching is already enabled in this channel.**')


@bot.command()
@commands.has_role('Owner')
async def vouchdisable(ctx):
    global vouch_enabled_channels
    if ctx.channel.id in vouch_enabled_channels:
        vouch_enabled_channels.remove(ctx.channel.id)
        await ctx.send('**Vouching has been disabled in this channel.**')
    else:
        await ctx.send('**Vouching is already disabled in this channel.**')


@bot.command()
@commands.has_role('Owner')
async def welcomeadd(ctx):
    db['welcome_channel'] = ctx.channel.id
    db['welcome_image'] = 'https://t3.ftcdn.net/jpg/02/20/14/38/360_F_220143804_fc4xRygvJ8bn8JPQumtHJieDN4ORNyjs.jpg'
    await ctx.send('Welcome message enabled! 🎉')


@bot.command()
@commands.has_role('Owner')
async def ping(ctx, user: discord.Member, count: int):
    if count > 5:
        await ctx.send("You can only ping a user a maximum of 5 times.")
        return

    for _ in range(count):
        await user.send("You've been pinged!")

    await ctx.send(f"Successfully pinged {user.mention} {count} times!")


@bot.command()
async def ofmc(ctx):
    members = ctx.guild.members
    bot_list = [member.name for member in members if member.bot]
    member_list = [member.name for member in members if not member.bot]
    await ctx.send(f"**Bots**: {', '.join(bot_list)}\n**Members**: {', '.join(member_list)}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def nuke(ctx):
    """Clear all messages in the current channel."""
    await ctx.channel.purge(limit=None)

    # Create an embed with the message
    embed = discord.Embed(description="Channel nuked!", color=discord.Color.dark_red())
    embed.set_author(name=f"Nuked By {ctx.author.name}", icon_url=ctx.author.avatar_url)  

    # Send the embed
    await ctx.send(embed=embed)


# Run the bot
bot.run('MTIwNTQ5NTgzMTE1MTc3MTY3OA.GpPz2G.ai0L18X4aVms4uvhJjWa6-Q95Xb76CBngQ9jfU')
