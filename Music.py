import asyncio
import discord
from discord.ext import commands
if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

def __init__(self, client):
        self.client = client

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = ' {0.title} uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

class VoiceState:
    def __init__(self, client):
        self.current = None
        self.voice = None
        self.client = client
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.client.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.client.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.client.send_message(self.current.channel, 'Now playing' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()
class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, client):
        self.client = client
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.client)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.client.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.client.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.InvalidArgument:
            await self.client.say('This is not a voice channel...')
        except discord.ClientException:
            await self.client.say('Already in a voice channel...')
        else:
            await self.client.say('Joined.')

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the client to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.client.say('Are you sure you are in a channel?')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.client.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if success:
                await self.client.say("Loading the song please be patient..")
            elif not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.client.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 1.0
            entry = VoiceEntry(ctx.message, player)
            await self.client.say('Queued ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        """Allows you to pause the current-playing audio"""
        state = self.get_voice_state(ctx.message.server)
        player = state.player
        VoiceState.is_playing = False
        player.pause()
        #^^^actually pause audio stream

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int):
        """Sets the volume of the currently playing song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.client.say('Set the volume to {:.0%}'.format(player.volume))


    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx): 
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        player = state.player
        player.resume()
        VoiceState.is_playing = True

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(ctx.message.server)
        player = state.player
        player.stop()
        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
            await self.client.say("Cleared the queue and disconnected from voice channel ")
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester and DJ can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.client.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        voter_roles = ctx.message.author.roles

        if 'DJ' in [y.name.upper() for y in voter_roles]:
            await self.client.say('DJ skipped, skipping song...')
            state.skip()

        elif not 'DJ' in [y.name.upper() for y in voter_roles]:
            if voter == state.current.requester:
                await self.client.say('Requester requested skipping song...')
                state.skip()
            elif voter.id not in state.skip_votes:
                state.skip_votes.add(voter.id)
                total_votes = len(state.skip_votes)
                if total_votes >= 3:
                    await self.client.say('Skip vote passed, skipping song...')
                    state.skip()    
                else:
                    await self.client.say('Skip vote added, currently at [{}/3]'.format(total_votes))
            else:
                await self.client.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.client.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.client.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))
            
def setup(client):
    client.add_cog(Music(client))
    print('Music is loaded')
