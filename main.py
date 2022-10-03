import asyncio
import json
import keep_alive
import random
import discord
import youtube_dl
import os
import aiohttp

from math import ceil
from time import strftime
from time import gmtime
from discord.ext import commands 
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

LYRICS_URL = "https://some-random-api.ml/lyrics?title="

ytdl_format_options = {'format': 'bestaudio/best', 'noplaylist':'True','default_search': 'auto','quiet': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False,'source_address': '0.0.0.0'}

ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1     -reconnect_delay_max 5', 'options': '-vn'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

queue = {}
files = {}
length = {}
loops = {}
title = {}


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, ctx, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        if data['duration'] >= 4000:
            os.remove(str(filename))
            raise Exception('Duration')
        files[ctx.guild.id].append(str(filename))
        length[ctx.guild.id].append(data['duration'])
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class NoVoiceChannel(commands.CommandError):
    pass

class IncorrectVoiceChannel(commands.CommandError):
    pass  

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = queue
        self.files = files
        self.length = length
        self.title = title
        self.loops = loops
      
    @commands.command()
    async def lyrics(self, ctx, *, search=None):
        if search==None:
            try:
                player = self.title[ctx.guild.id][0]
            except:
                await ctx.send(":x: **Nothing is playing**")
                return

            name = str(player)

            await ctx.send(f'🔎 **Searching lyrics for:** `{player}`')
            async with aiohttp.request("GET", LYRICS_URL + name, headers={}) as r:
                if not 300 > r.status >= 200:
                    await ctx.send(":x: **lyrics could not be found**")
                    return

                data = await r.json()

                for i in range(ceil(len(data["lyrics"]) / 2048.0)):
                    part = data["lyrics"][i * 2048:min((i + 1) * 2048, len(data["lyrics"]))]
                    embed = discord.Embed(title=data["title"], description=part, colour=0xff00f6)
                    embed.set_thumbnail(url=data["thumbnail"]["genius"])
                    embed.set_author(name=data["author"])
                    await ctx.send(embed=embed)    
        else:
            return
    @commands.command()
    async def join(self, ctx):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            await ctx.send(f'↪️ **Moved to:** {ctx.author.voice.channel.mention}')
            return await ctx.voice_client.move_to(ctx.author.voice.channel)

        await ctx.author.voice.channel.connect()
        await ctx.send(f'↪️ **Joined in:** {ctx.author.voice.channel.mention}')

    @commands.command()
    async def remove(self, ctx, number):
        try:
            del (self.queue[ctx.guild.id][int(number)])
            del (self.length[ctx.guild.id][int(number)])
            del (self.title[ctx.guild.id][int(number)])
            await ctx.send(f':x: **Removed from queue:** `{number}`')
        except:
            await ctx.send(f':x: **Failed to remove from queue**')

    @commands.command()
    async def queue(self, ctx):
        if len(self.queue[ctx.guild.id]) > 1:
            counter = 0
            embed = discord.Embed(title=f"Queue for {ctx.guild.name} ", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.add_field(name="Now Playing:",
                            value=f'`{self.title[ctx.guild.id][0]}`  **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][0]))}**',
                            inline=False)
            embed.add_field(name="Up Next:",
                            value=f'1. `{self.title[ctx.guild.id][1]}`  **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][1]))}**',
                            inline=False)
            if len(self.queue[ctx.guild.id]) >= 2:
                for player in self.queue[ctx.guild.id]:
                    counter += 1
                    if (counter == 1) or (counter == 2):
                        pass
                    else:
                        embed.add_field(name="\n\u200b",
                                        value=f'{counter - 1}. `{self.title[ctx.guild.id][counter - 1]}` **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][self.queue[ctx.guild.id].index(player)]))}**',
                                        inline=False)
            else:
                await ctx.send(f':x: **Nothing in queue!**')
            await ctx.send(embed=embed)
        else:
            await ctx.send(f':x: **Nothing in queue!**')

    @commands.command()
    async def view(self, ctx):
        if len(self.queue[ctx.guild.id]) > 1:
            counter = 0
            embed = discord.Embed(title=f"Queue for {ctx.guild.name} ", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.add_field(name="Now Playing:",
                            value=f'`{self.title[ctx.guild.id][0]}`  **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][0]))}**',
                            inline=False)
            embed.add_field(name="Up Next:",
                            value=f'1. `{self.title[ctx.guild.id][1]}`  **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][1]))}**',
                            inline=False)
            if len(self.queue[ctx.guild.id]) >= 2:
                for player in self.queue[ctx.guild.id]:
                    counter += 1
                    if (counter == 1) or (counter == 2):
                        pass
                    else:
                        embed.add_field(name="\n\u200b",
                                        value=f'{counter - 1}. `{self.title[ctx.guild.id][counter - 1]}` **{strftime("%H:%M:%S", gmtime(self.length[ctx.guild.id][self.queue[ctx.guild.id].index(player)]))}**',
                                        inline=False)
            else:
                await ctx.send(f':x: **Nothing in queue!**')
            await ctx.send(embed=embed)
        else:
            await ctx.send(f':x: **Nothing in queue!**')

    @commands.command()
    async def forceplay(self, ctx, *, url=None):
        if url == None:
            await ctx.send(f':x: **Song is missing!**')
        await ctx.send(f'🔎 **Searching for:** `{url}`')

        with YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download = False)
        if 'entries' in info:
            # take first item from a playlist
            info = info['entries'][0]
        inf = info.get('title')
        URL = info['formats'][0]['url']
        print(inf)
        self.loops[ctx.guild.id] = []
        if len(self.queue[ctx.guild.id]) != 0:
            self.queue[ctx.guild.id].insert(1, url)
            self.length[ctx.guild.id].insert(1, info['duration'])
            self.title[ctx.guild.id].insert(1, info['title'])
            ctx.voice_client.stop()
        else:
            self.queue[ctx.guild.id].append(url)
            self.length[ctx.guild.id].append(info['duration'])
            self.title[ctx.guild.id].append(info['title'])
            ctx.voice_client.play(FFmpegPCMAudio(URL, **ffmpeg_options), after = lambda c: asyncio.run(Music.serverQueue(self, ctx, ctx.voice_client, ctx.message)))
        await ctx.send(f'🎶 **Now playing:** `{inf}`')    

    @commands.command()
    async def fp(self, ctx, *, url=None):
        if url == None:
            await ctx.send(f':x: **Song is missing!**')
        await ctx.send(f'🔎 **Searching for:** `{url}`')

        with YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download = False)
        if 'entries' in info:
            # take first item from a playlist
            info = info['entries'][0]
        inf = info.get('title')
        URL = info['formats'][0]['url']
        print(inf)
        self.loops[ctx.guild.id] = []
        if len(self.queue[ctx.guild.id]) != 0:
            self.queue[ctx.guild.id].insert(1, url)
            self.length[ctx.guild.id].insert(1, info['duration'])
            self.title[ctx.guild.id].insert(1, info['title'])
            ctx.voice_client.stop()
        else:
            self.queue[ctx.guild.id].append(url)
            self.length[ctx.guild.id].append(info['duration'])
            self.title[ctx.guild.id].append(info['title'])
            ctx.voice_client.play(FFmpegPCMAudio(URL, **ffmpeg_options), after = lambda c: asyncio.run(Music.serverQueue(self, ctx, ctx.voice_client, ctx.message)))
        await ctx.send(f'🎶 **Now playing:** `{inf}`')  

    @commands.command()
    async def shuffle(self, ctx, *, url=None):
        queue = self.queue[ctx.guild.id][0]
        length = self.length[ctx.guild.id][0]
        title = self.title[ctx.guild.id][0]
        del(self.queue[ctx.guild.id][0])
        del (self.length[ctx.guild.id][0])
        del (self.title[ctx.guild.id][0])
        mix = list(zip(self.queue[ctx.guild.id],self.length[ctx.guild.id],self.title[ctx.guild.id]))
        random.shuffle(mix)
        self.queue[ctx.guild.id], self.length[ctx.guild.id], self.title[ctx.guild.id] = zip(*mix)
        qAll = self.queue[ctx.guild.id]
        lAll = self.length[ctx.guild.id]
        fAll = self.title[ctx.guild.id]

        self.queue[ctx.guild.id] = []
        self.length[ctx.guild.id] = []
        self.title[ctx.guild.id] = []

        self.queue[ctx.guild.id].append(queue)
        self.length[ctx.guild.id].append(length)
        self.title[ctx.guild.id].append(title)

        for g in qAll:
            self.queue[ctx.guild.id].append(g)
        for l in lAll:
            self.length[ctx.guild.id].append(l)
        for f in fAll:
            self.title[ctx.guild.id].append(f)
        await ctx.send(f':ballot_box_with_check: **Shuffled**')

    @commands.command()
    async def p(self, ctx, *, url=None):
        await ctx.send(f'🔎 **Searching for:** `{url}`')

        with YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download = False)
        if 'entries' in info:
            # take first item from a playlist
            info = info['entries'][0]
        inf = info.get('title')
        URL = info['formats'][0]['url']
        print(inf)
        self.queue[ctx.guild.id].append(url)
        self.length[ctx.guild.id].append(info['duration'])
        self.title[ctx.guild.id].append(info['title'])
        if len(self.queue[ctx.guild.id]) <= 1:
            ctx.voice_client.play(FFmpegPCMAudio(URL, **ffmpeg_options), after = lambda c: asyncio.run(Music.serverQueue(self, ctx,ctx.voice_client, ctx.message)))
            await ctx.send(f'🎶 **Now playing:** `{inf}`')
        else:
            await ctx.send(f':ballot_box_with_check: **Added to queue:** `{inf}`')
            
    @commands.command()
    async def play(self, ctx, *, url=None):
        await ctx.send(f'🔎 **Searching for:** `{url}`')

        with YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download = False)
        if 'entries' in info:
            # take first item from a playlist
            info = info['entries'][0]
        inf = info.get('title')
        URL = info['formats'][0]['url']
        print(inf)
        self.queue[ctx.guild.id].append(url)
        self.length[ctx.guild.id].append(info['duration'])
        self.title[ctx.guild.id].append(info['title'])
        if len(self.queue[ctx.guild.id]) <= 1:
            ctx.voice_client.play(FFmpegPCMAudio(URL, **ffmpeg_options), after = lambda c: asyncio.run(Music.serverQueue(self, ctx, ctx.voice_client, ctx.message)))
            await ctx.send(f'🎶 **Now playing:** `{inf}`')
        else:
            await ctx.send(f':ballot_box_with_check: **Added to queue:** `{inf}`')

    async def myAfter(self, ctx, voice, message):
        coro = await Music.serverQueue(self, ctx, voice, message)
        loop = self.bot.loop
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            fut.result()
        except:
            # an error happened sending the message
            pass

    async def serverQueue(self, ctx, voice, message):
        if len(loops[ctx.guild.id]) == 0:
            try:
                del (queue[ctx.guild.id][0])
                del (length[ctx.guild.id][0])
                del (title[ctx.guild.id][0])
            except:
                pass
        if len(queue[ctx.guild.id]) != 0:
            with YoutubeDL(ytdl_format_options) as ydl:
              info = ydl.extract_info(queue[ctx.guild.id][0], download = False)
            if 'entries' in info:
                # take first item from a playlist
                info = info['entries'][0]
            URL = info['formats'][0]['url']
            voice.play(FFmpegPCMAudio(URL, **ffmpeg_options), after = lambda c: asyncio.run(Music.serverQueue(self, ctx, voice, message)))
            print('queue - ' + str(queue[ctx.guild.id][0]))
        else:
            print("Nothing in Queue!")

    @commands.command()
    async def clear(self, ctx):
        if len(self.queue[ctx.guild.id]) > 1:
            queue = self.queue[ctx.guild.id][0]
            length = self.length[ctx.guild.id][0]
            title = self.title[ctx.guild.id][0]
            self.queue[ctx.guild.id] = []
            self.length[ctx.guild.id] = []
            self.title[ctx.guild.id] = []
            self.queue[ctx.guild.id].append(queue)
            self.length[ctx.guild.id].append(length)
            self.title[ctx.guild.id].append(title)
            await ctx.send(f':fast_forward:️ **Queue cleared**')
        else:
            await ctx.send(f':x: **Nothing in queue!**')

    @commands.command()
    async def skip(self, ctx):
        if len(self.queue[ctx.guild.id]) == 0:
            await ctx.send(f':x:️ **Nothing to skip!**')
        else:
            self.loops[ctx.guild.id] = []
            ctx.voice_client.stop()
            await ctx.send(f':fast_forward:️ **Skipped**')

    @commands.command()
    async def now(self, ctx):
        if len(self.queue[ctx.guild.id]) >= 1:
            embed = discord.Embed(title=f"Queue for {ctx.guild.name} ", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.add_field(name="Now Playing:",
                            value=f'`{self.title[ctx.guild.id][0]}`', inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f':x:️ **Nothing is playing!**')

    @commands.command()
    async def pause(self, ctx):
        ctx.voice_client.pause()
        await ctx.send(f'⏸ **Paused**')

    @commands.command()
    async def stop(self, ctx):
        ctx.voice_client.pause()
        await ctx.send(f'⏸ **Paused**')

    @commands.command()
    async def resume(self, ctx):
        ctx.voice_client.resume()
        await ctx.send(f'⏯ **Resuming**')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Changed volume to **{volume}%**")

    @commands.command()
    async def loop(self, ctx):
      if len(self.loops[ctx.guild.id]) == 0:
          self.loops[ctx.guild.id].append(1)
          await ctx.send(f':repeat: **Loop activated**')
      else:
          self.loops[ctx.guild.id] = []
          await ctx.send(f':repeat: **Loop deactivated**')

    @commands.command()
    async def leave(self, ctx):
        self.queue[ctx.guild.id] = []
        self.length[ctx.guild.id] = []
        self.files[ctx.guild.id] = []
        self.loops[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send(f':x:️ **Disconnected from:** {ctx.author.voice.channel.mention}')

    @commands.command()
    async def cmd(self, ctx):
        embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                              url="https://www.Youtube.com")
        embed.set_author(name="Commands",
                         icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
        embed.add_field(name="Lyrics from current song:",
                        value="$lyrics", inline=True)
        embed.add_field(name="Play songs:",
                        value="$play (url or name)", inline=True)
        embed.add_field(name="Stop playing:",
                        value="$stop", inline=True)
        embed.add_field(name="Resume playing:",
                        value="$resume", inline=True)
        embed.add_field(name="Force playing:",
                        value="$forceplay (url or name)", inline=True)
        embed.add_field(name="Join your voicechannel:",
                        value="$join", inline=True)
        embed.add_field(name="Leave your voicechannel:",
                        value="$leave", inline=True)
        embed.add_field(name="See current Song:",
                        value="$now", inline=True)
        embed.add_field(name="See queue:",
                        value="$queue", inline=True)
        embed.add_field(name="Shuffle queue:",
                        value="$shuffle", inline=True)
        embed.add_field(name="clear queue:",
                        value="$clear", inline=True)
        embed.add_field(name="Remove from queue:",
                        value="$remove (number)", inline=True)
        embed.add_field(name="Skip current song:",
                        value="$skip", inline=True)
        embed.add_field(name="Change Volume:",
                        value="$volume (number)", inline=True)
        embed.add_field(name="Loop On/Off:",
                        value="$loop", inline=True)
        #embed.add_field(name="List of playlists:",
        #                value="$playlist", inline=True)
        #embed.add_field(name="Create Playlist:",
        #                value="$playlist add (playlist name)", inline=True)
        #embed.add_field(name="Remove Playlist:",
        #                value="$playlist remove (playlist name)", inline=True)
        #embed.add_field(name="View Playlist:",
        #                value="$playlist view (playlist name)", inline=True)
        #embed.add_field(name="Add song to Playlist:",
        #                value="$playlist addsong", inline=True)
        #embed.add_field(name="Play Playlist:",
        #                value="$playlist play (playlist name)", inline=True)

        await ctx.send(embed=embed)

    @commands.command()
    async def playlist(self, ctx, arg=None, name=None):
        server = ctx.guild.id
        if arg == None:
            with open('pl.txt', 'r') as f:
                users = json.load(f)

            try:
                users[str(server)]
            except:
                users[str(server)] = {}
            embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.set_author(name="Playlists",
                             icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
            counter = 0
            for playlist in users[str(server)]:
                counter += 1
                embed.add_field(name=f"{counter}. {playlist}",
                                value="\n\u200b", inline=True)
            if len(users[str(server)]) == 0:
                embed.add_field(name="\n\u200b",
                                value="**No playlist available**", inline=False)

            await ctx.send(embed=embed)

            with open('pl.txt', 'w') as f:
                json.dump(users, f)
        elif str(arg.lower()) == "add":
            if name == None:
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist add",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type desired playlist name**", inline=False)

                plMessage = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist add",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp = str(response.content)
                await response.delete()
            else:
                resp = str(name)
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlists",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Searching :mag_right:**", inline=False)

                plMessage = await ctx.send(embed=embed)

            with open('pl.txt', 'r') as f:
                users = json.load(f)

            users[str(server)][str(resp)] = ""

            embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.set_author(name="Playlists",
                             icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
            counter = 0
            for playlist in users[str(server)]:
                counter += 1
                embed.add_field(name=f"{counter}. {playlist}",
                                value="\n\u200b", inline=False)

            await plMessage.edit(embed=embed)

            with open('pl.txt', 'w') as f:
                json.dump(users, f)
        elif str(arg.lower()) == "remove":
            if name == None:
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist remove",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact playlist name**", inline=False)

                plMessage = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist remove",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp = str(response.content)
                await response.delete()
            else:
                resp = str(name)
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlists",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Searching :mag_right:**", inline=False)

                plMessage = await ctx.send(embed=embed)

            with open('pl.txt', 'r') as f:
                users = json.load(f)

            del (users[str(server)][str(resp)])

            embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.set_author(name="Playlists",
                             icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
            counter = 0
            for playlist in users[str(server)]:
                counter += 1
                embed.add_field(name=f"{counter}. {playlist}",
                                value="\n\u200b", inline=False)
            if len(users[str(server)]) == 0:
                embed.add_field(name="\n\u200b",
                                value="**No playlist available**", inline=False)

            await plMessage.edit(embed=embed)

            with open('pl.txt', 'w') as f:
                json.dump(users, f)
        elif str(arg.lower()) == "view":
            if name == None:
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist view",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact playlist name**", inline=False)

                plMessage = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist view",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp = str(response.content)
                await response.delete()
            else:
                resp = str(name)
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlists",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Searching :mag_right:**", inline=False)

                plMessage = await ctx.send(embed=embed)

            with open('pl.txt', 'r') as f:
                users = json.load(f)

            embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.set_author(name=f"Playlist: {resp}",
                             icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")

            if len(users[str(server)][str(resp)]) == 0:
                embed.add_field(name="\n\u200b",
                                value="**No songs available**", inline=False)
            else:
                counter = 0
                for song in users[str(server)][str(resp)].split("::"):
                    counter += 1
                    if counter < len(users[str(server)][str(resp)].split("::")):
                        embed.add_field(name="\n\u200b", value=f"{counter}. `{song}`", inline=False)

            await plMessage.edit(embed=embed)

        elif str(arg.lower()) == "addsong":
            if name == None:
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist addsong",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact playlist name**", inline=False)

                plMessage = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist addsong",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist addsong",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact songname or url**", inline=False)

                await plMessage.edit(embed=embed)

                try:
                    response2 = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist addsong",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp = str(response.content)
                await response.delete()
                resp2 = str(response2.content)
                await response2.delete()
            else:
                resp = str(name)
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlists",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Searching :mag_right:**", inline=False)

                plMessage = await ctx.send(embed=embed)

                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist addsong",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact songname or url**", inline=False)

                await plMessage.edit(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response2 = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist addsong",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp2 = str(response2.content)
                await response2.delete()

            with open('pl.txt', 'r') as f:
                users = json.load(f)

            player = await YTDLSource.from_url(ctx, str(resp2), loop=self.bot.loop, stream=True)

            users[str(server)][str(resp)] += f"{player.title}::"

            with open('pl.txt', 'w') as f:
                json.dump(users, f)

            embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                  url="https://www.Youtube.com")
            embed.set_author(name=f"Playlist: {resp}",
                             icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
            embed.add_field(name="\n\u200b",
                            value="**Added to Playlist**", inline=False)
            await plMessage.edit(embed=embed)
        
        elif str(arg.lower()) == "play":

            if name == None:
                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlist",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Type exact playlist name**", inline=False)

                plMessage = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author

                try:
                    response = await client.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                          url="https://www.Youtube.com")
                    embed.set_author(name="Playlist view",
                                     icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                    embed.add_field(name="\n\u200b",
                                    value="**You have taken too long**", inline=False)
                    return await plMessage.edit(embed=embed)

                resp = str(response.content)
                await response.delete()

                embed = discord.Embed(title=f"All-InOne-Music-Bot", colour=0xff00f6,
                                      url="https://www.Youtube.com")
                embed.set_author(name="Playlists",
                                 icon_url="https://icon-library.com/images/commands-icon/commands-icon-17.jpg")
                embed.add_field(name="\n\u200b",
                                value="**Searching :mag_right:**", inline=False)
            else:
                resp = str(name)

            with open('pl.txt', 'r') as f:
                users = json.load(f)

            if ctx.voice_client is None:
                if ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                else:
                    await ctx.send(":x: **Not connected to a voice channel!**")
                    return

            counter = 0
            for song in users[str(server)][str(resp)].split("::"):
                counter += 1
                if counter == 1:
                    player = await YTDLSource.from_url(ctx, song, loop=self.bot.loop, stream=False)
                    self.queue[ctx.guild.id].append(player)
                    await self.play(ctx)
                else:
                    if counter < len(users[str(server)][str(resp)].split("::")):
                        player = await YTDLSource.from_url(ctx, song, loop=self.bot.loop, stream=False)
                        self.queue[ctx.guild.id].append(player)
            await ctx.send(f":ballot_box_with_check: **Playlist added to queue:** `{resp}`")

    @play.before_invoke
    @loop.before_invoke
    @remove.before_invoke
    @skip.before_invoke
    @stop.before_invoke
    @resume.before_invoke
    @clear.before_invoke
    @pause.before_invoke
    @volume.before_invoke
    @leave.before_invoke
    @join.before_invoke
    @p.before_invoke
    @fp.before_invoke
    @forceplay.before_invoke
    @now.before_invoke
    @queue.before_invoke
    @playlist.before_invoke
    @view.before_invoke
    @shuffle.before_invoke
    async def ensure_voice(self, ctx):
        try:
            self.queue[ctx.guild.id]
        except:
            self.queue[ctx.guild.id] = []
            self.title[ctx.guild.id] = []
            self.files[ctx.guild.id] = []
            self.length[ctx.guild.id] = []
            self.loops[ctx.guild.id] = []


        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                raise NoVoiceChannel
                return
        else:
            if ctx.author.voice:
                if ctx.author.voice.channel == ctx.voice_client.channel:
                    pass
                else:
                    raise IncorrectVoiceChannel
                    return
            else:
                raise NoVoiceChannel
                return
              
client = commands.Bot(command_prefix=commands.when_mentioned_or("$"), description='Music Bot')              

@client.event
async def on_command_error(ctx, error):
    if isinstance(error,commands.MissingPermissions):
        embed = discord.Embed(title="Permission Denied.",
        description="You do not have the necessary permission for this command!",
        color=0xff00f6)
        await ctx.send(embed=embed)
    elif isinstance(error,commands.CommandNotFound):
        pass
    #elif isinstance(error,commands.CommandInvokeError):
        #return
        #await ctx.send(":x: **Unavailable!**")
    elif isinstance(error, NoVoiceChannel):
        await ctx.send(":x: **Not connected to a voice channel!**")
    elif isinstance(error, IncorrectVoiceChannel):
        await ctx.send(":x: **Not connected to the right voice channel!**")
    else:
        raise error

@client.event
async def on_ready():
    print("Logged in as: {}!".format(client.user.name))

client.add_cog(Music(client))
client.remove_command("help")
token = os.environ['Token']
 
keep_alive.keep_alive()

client.run(token)
