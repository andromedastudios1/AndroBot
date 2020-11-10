import discord
from discord import TextChannel
import sys
import os
import praw
import random
import requests
from discord.ext import commands
from discord import Game, Embed
from discord.voice_client import VoiceClient
import asyncio as asyncio
import time
from discord.ext.tasks import loop

client = commands.AutoShardedBot(command_prefix= '?')
startup_extensions = ["Music"]

if __name__ == "__main__":
  for extension in startup_extensions:
    try:
      client.load_extension(extension)
    except Exception as e:
      exc = '{}: {}'.format(type(e).__name__, e)
      raise SystemExit('Failed to load extension {}\n{}'.format(extension, exc))
      

token = os.environ['DiscordKey']
reddit_token = os.environ['RedditKey']


reddit = praw.Reddit(client_id='ZOkK-ZCFJpcWCQ', client_secret=reddit_token, user_agent='CardNightBot by AsyncSGD', username='androstudios')
def createRandomSortedList(num, start = 1, end = 100): 
    arr = [] 
    tmp = random.randint(start, end) 
      
    for x in range(num): 
          
        while tmp in arr: 
            tmp = random.randint(start, end) 
              
        arr.append(tmp) 
          
    arr.sort() 
      
    return arr 


@client.event
async def on_ready():
  global cache
  global cache_funny
  cache = [i for i in reddit.subreddit('memes').new() if not i.stickied]
  cache_funny = [i for i in reddit.subreddit('funny').new() if not i.stickied]
  print('Logged in as: ' + str(client.user.name) + ' ' + str(client.user.id))
  activity = discord.Game(name='?help | ' + str(len(client.guilds)) + ' guilds')
  await client.change_presence(activity=activity)
class Main_Commands():
  def __init__(self,client):
    self.client=client

@loop(seconds=150)
async def refreshCache():
  cache = [i for i in reddit.subreddit('memes').new() if not i.stickied]
  cache_funny = [i for i in reddit.subreddit('funny').new() if not i.stickied]

@client.command()
async def ping(ctx): 
  await ctx.send('Pong!')

@client.command()
async def clear(ctx, amount=0):
  if (amount == 0):
    await ctx.send("Please specify how many messages are to be deleted.")
  else:
    try:
      await ctx.channel.purge(limit=amount)
    except discord.errors.Forbidden:
      await ctx.send("Bot does not have neccessary permissions to delete messages.")

@client.command()
async def meme(ctx, numMemes=None):
  """Sends a number of memes to a channel."""
  if numMemes == None:
    selectedpostnum = random.randint(1,100)
    selectedpost = cache[selectedpostnum]
    await ctx.send("Here is a random meme: ", embed=discord.Embed(title="Random meme").set_image(url=selectedpost.url))
  else:
    try:
      if (int(numMemes) > 20 or int(numMemes) < 1):
        await ctx.send("Please provide a reasonable number of memes")
        return
    except:
      await ctx.send("Please provide a reasonable number of memes")
      return
    else: 
      x = int(numMemes)
      randomlist = createRandomSortedList(x)
      for i in randomlist:
        selectedpost = cache[i]
        await ctx.send("Here is a random meme: ", embed=discord.Embed(title="Random meme").set_image(url=selectedpost.url))
@client.command()
async def funny(ctx, numMemes=None):
  """Sends a number of posts from r/funny to a channel."""
  if numMemes == None:
    selectedpostnum = random.randint(1,100)
    selectedpost = cache_funny[selectedpostnum]
    await ctx.send("Here is a post from r/funny: ", embed=discord.Embed(title="r/funny").set_image(url=selectedpost.url))
  else:
    try:
      if (int(numMemes) > 20 or int(numMemes) < 1):
        await ctx.send("Please provide a reasonable number of funny posts to send")
        return
    except:
      await ctx.send("Please provide a reasonable number of funny posts")
      return
    else: 
      x = int(numMemes)
      randomlist = createRandomSortedList(x)
      for i in randomlist:
        selectedpost = cache_funny[i]
        await ctx.send("Here is a post from r/funny: ", embed=discord.Embed(title="r/funny").set_image(url=selectedpost.url))
refreshCache.start()
client.run(token)
