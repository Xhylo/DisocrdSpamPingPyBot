import discord
from discord.ext import commands
import requests
import sys
from queue import Queue
from threading import Thread
from random import choice

if sys.platform == 'linux':
    import simplejson as json
else:
    import json

TOKEN = ''

channel_ids = [
    '879119135135645757',
    '879119146019848243',
    '879119156463677460'
]

client = commands.Bot(command_prefix=".", case_insensitive=False)

concurrent = 100
q = Queue(concurrent * 2)
def requestMaker():
    while True:
        requesting, url, headers, payload = q.get()
        try:
            # proxy = randomProxy('https')
            # r = requesting(url, data=json.dumps(payload), headers=headers, proxies=proxy, timeout=timeout)
            r = requesting(url, data=json.dumps(payload), headers=headers, timeout=5)
            if r.status_code == 429:
                r = r.json()
                if isinstance(r['retry_after'], int): # Discord will return all integer time if the retry after is less then 10 seconds which is in miliseconds.
                    r['retry_after'] /= 1000
                if r['retry_after'] > 5:
                    print(f'Rate limiting has been reached, and this request has been cancelled due to retry-after time is greater than 5 seconds: Wait {str(r["retry_after"])} more seconds.')
                    q.task_done()
                    continue
                print(f'Rate limiting has been reached: Wait {str(r["retry_after"])} more seconds.')
                q.put((requesting, url, headers, payload))
            elif 'code' in r:
                print('Request cancelled due to -> ' + r['message'])
        except json.decoder.JSONDecodeError:
            pass
        except requests.exceptions.ConnectTimeout:
            print(f'Reached maximum load time: timeout is')
            q.put((requesting, url, headers, payload))
        except Exception as e:
            print(f'Unexpected error: {str(e)}')

        q.task_done()

for i in range(concurrent):
    Thread(target=requestMaker, daemon=True).start()

def create_webhooks(MAX_WEBHOOK_COUNT: int) -> None:
    payload = {'name': 'Spammer'}
    headers = {'authorization': 'Bot ' + TOKEN, 'content-type': 'application/json'}
    channel_count = len(channel_ids)
    leftover = (MAX_WEBHOOK_COUNT % channel_count) + 1

    for channel_id in channel_ids:
        for i in range(int(50 / MAX_WEBHOOK_COUNT) + ((leftover := leftover - 1) > 0)):
            q.put((requests.post, f'https://discord.com/api/v8/channels/{channel_id}/webhooks', headers, payload))

@client.command()
async def ping(ctx):
    # get inputs
    webhooks = await ctx.guild.webhooks()
    print(webhooks)
    webhooks_length = len(webhooks)

    MAX_WEBHOOK_COUNT = 50 - webhooks_length

    if MAX_WEBHOOK_COUNT <= 50:
        create_webhooks(MAX_WEBHOOK_COUNT)

    webhooks = await ctx.guild.webhooks()
    
    _headers = {
        'content-type': 'application/json'
    }

    payload = {
        'username': 'LOL',
        'content': '@everyone',
        'avatar_url': None 
    }

    for i in range(50):
        q.put((requests.post, choice(webhooks).url, _headers, payload))

@client.event
async def on_ready():
    print('ready')


client.run(TOKEN)