import discord
from discord.ext import commands
from discord.ext.commands import Bot, AutoShardedBot, when_mentioned_or, CheckFailure
from discord.utils import get

import json
# MySQL
import pymysql, pymysqlpool
import pymysql.cursors
## regex
import re
## date/time handle
import datetime, time, timeago

from config import config

## ascii table
from terminaltables import AsciiTable

import sys, traceback

pymysqlpool.logger.setLevel('DEBUG')
myconfig = {
    'host': config.mysql.host,
    'user':config.mysql.user,
    'password':config.mysql.password,
    'database':config.mysql.db,
    'charset':'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit':True
    }

connPool = pymysqlpool.ConnectionPool(size=4, name='connPool', **myconfig)
conn = connPool.get_connection(timeout=5, retry_num=2)

token = config.discord.token
EMOJI_EXCHANGE = "\U0001F4B1"
EMOJI_ERROR = "\U0001F6D1"

bot_help_about = "About CMC Price Bot."
bot_help_invite = "Invite link of bot to your server."
bot_help_mcap = "Get marketcap of a coin or token."
bot_help_price = "Get various crypto price."
bot_help_donate = "Donate to support CMC Price Bot."

bot = AutoShardedBot(command_prefix=['.', 'cmc.', 'cmc!'], owner_id = config.discord.ownerID, case_insensitive=True)

# connPool 
def openConnection():
    global conn, connPool
    try:
        if conn is None:
            conn = connPool.get_connection(timeout=5, retry_num=2)
    except:
        print("ERROR: Unexpected error: Could not connect to MySql instance.")
        sys.exit()


@bot.event
async def on_ready():
    print("Hello, I am Pricing Bot!")
    print("Guilds: {}".format(len(bot.guilds)))
    print("Users: {}".format(sum([x.member_count for x in bot.guilds])))
    game = discord.Game(name="Crypto Price!")
    await bot.change_presence(status=discord.Status.online, activity=game)


@bot.event
async def on_guild_join(guild):
    botLogChan = bot.get_channel(id=config.discord.logChan)
    await botLogChan.send(f'Bot joins a new guild {guild.name} / {guild.id}. Total guilds: {len(bot.guilds)}.')
    return


@bot.event
async def on_guild_remove(guild):
    botLogChan = bot.get_channel(id=config.discord.logChan)
    await botLogChan.send(f'Bot was removed from guild {guild.name} / {guild.id}. Total guilds: {len(bot.guilds)}')
    return

@bot.event
async def on_message(message):
    # ignore .help in public
    if message.content.upper().startswith('.HELP') and isinstance(message.channel, discord.DMChannel) == False:
        await message.channel.send('Help command is available via Direct Message (DM) only.')
        return
    # Do not remove this, otherwise, command not working.
    ctx = await bot.get_context(message)
    await bot.invoke(ctx)


@bot.command(pass_context=True, name='about', help=bot_help_about)
async def about(ctx):
    invite_link = "https://discordapp.com/oauth2/authorize?client_id="+str(bot.user.id)+"&scope=bot"
    botdetails = discord.Embed(title='About Me', description='', colour=7047495)
    botdetails.add_field(name='My Github:', value='https://github.com/wrkzcoin/CMC-PriceBot', inline=False)
    botdetails.add_field(name='Invite Me:', value=f'{invite_link}', inline=False)
    botdetails.add_field(name='Servers I am in:', value=len(bot.guilds), inline=False)
    botdetails.add_field(name='Supported by:', value='WrkzCoin Community Team', inline=False)
    botdetails.add_field(name='Supported Server:', value='https://chat.wrkz.work', inline=False)
    botdetails.set_footer(text='Made in Python3.6+ with discord.py library!', icon_url='http://findicons.com/files/icons/2804/plex/512/python.png')
    botdetails.set_author(name=bot.user.name, icon_url=bot.user.avatar_url)
    try:
        await ctx.send(embed=botdetails)
    except Exception as e:
        await ctx.message.author.send(embed=botdetails)
        traceback.print_exc(file=sys.stdout)


@bot.command(pass_context=True, name='invite', aliases=['inviteme'], help=bot_help_invite)
async def invite(ctx):
    invite_link = "https://discordapp.com/oauth2/authorize?client_id="+str(bot.user.id)+"&scope=bot"
    await ctx.send('**[INVITE LINK]**\n\n'
                f'{invite_link}')


@bot.command(pass_context=True, name='donate', help=bot_help_donate)
async def donate(ctx):
    invite_link = "https://discordapp.com/oauth2/authorize?client_id="+str(bot.user.id)+"&scope=bot"
    donatelist = discord.Embed(title='Support Me', description='', colour=7047495)
    donatelist.add_field(name='BTC:', value=config.donate.btc, inline=False)
    donatelist.add_field(name='LTC:', value=config.donate.ltc, inline=False)
    donatelist.add_field(name='DOGE:', value=config.donate.doge, inline=False)
    donatelist.add_field(name='BCH:', value=config.donate.bch, inline=False)
    donatelist.add_field(name='DASH:', value=config.donate.dash, inline=False)
    donatelist.add_field(name='XMR:', value=config.donate.xmr, inline=False)
    donatelist.add_field(name='WRKZ:', value=config.donate.wrkz, inline=False)
    donatelist.set_author(name=bot.user.name, icon_url=bot.user.avatar_url)
    try:
        await ctx.send(embed=donatelist)
        return
    except Exception as e:
        await ctx.message.author.send(embed=donatelist)
        traceback.print_exc(file=sys.stdout)


@bot.command(pass_context=True, help=bot_help_price)
async def price(ctx, *args):
    PriceQ = (' '.join(args)).split()
    message = "Internal Error."
    if len(PriceQ) == 1:
        # Only ticker accepted
        if not re.match('^[a-zA-Z0-9]+$', PriceQ[0]):
            message = 'Invalid ticker.'
            await ctx.message.add_reaction(EMOJI_ERROR)  
        if (ValueInUSD(1, PriceQ[0]) == ''):
            message = 'Invalid ticker.'
            await ctx.message.add_reaction(EMOJI_ERROR) 
        if (PriceQ[0].upper() == 'LIST'):
            message = PriceMon_List(str(ctx.message.author.id))
        elif (PriceQ[0].lower() == 'delall' or PriceQ[0].lower() == 'del-all'):
            message = PriceMon_DelAll(str(ctx.message.author.id))
        else:
            message = ValueInUSD(1, PriceQ[0])
        await ctx.send(message)
        return
    elif len(PriceQ) == 2:
        # Only ticker accepted sample 10 btc, 15.2 btc
        # price 10.0 btc
        # .price del xmr
        if not re.match('^[a-zA-Z0-9]+$', PriceQ[1]):
            message = 'Invalid ticker.'
            await ctx.message.add_reaction(EMOJI_ERROR) 
        # check if valid number
        if PriceQ[0].lower() != "del" and PriceQ[0].lower() != "delall" and PriceQ[0].lower() != "del-all":
            amount = None
            PriceQ[0] = PriceQ[0].replace(",", "")
            try:
                amount = int(PriceQ[0])
            except ValueError:
                message = 'Invalid given number.'
                pass
            try:
                amount = float(PriceQ[0])
            except ValueError:
                message = 'Invalid given number.'

            if amount is None:
                await ctx.send(message)
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

            if (ValueInUSD(amount, PriceQ[1]) == ''):
                message = 'Invalid ticker.'
                await ctx.message.add_reaction(EMOJI_ERROR)
            else:
                message = ValueInUSD(amount, PriceQ[1])
        elif (PriceQ[0].lower() == "del"):
            if (PriceMon_CheckExist(str(ctx.message.author.id), PriceQ[1].upper()) == True):
                msg = PriceMon_Del(str(ctx.message.author.id), PriceQ[1].upper())
            else:
                msg = '`{} is not in your monitoring list.`'.format(PriceQ[1].upper())
                await ctx.message.add_reaction(EMOJI_ERROR)
            message = msg
        await ctx.send(message)
        return
    elif (len(PriceQ) == 3):
        # .price xmr in btc
        # .price add 10 xmr
        if not re.match('^[a-zA-Z0-9]+$', PriceQ[0]) or not re.match('^[a-zA-Z0-9]+$', PriceQ[2]):
            message = 'Invalid ticker pair(s).'
            await ctx.message.add_reaction(EMOJI_ERROR)
        if PriceQ[1].lower() != "in":
            # in or number only
            PriceQ[1] = PriceQ[1].replace(",", "")
            try:
                amount = int(PriceQ[1])
            except ValueError:
                pass
            try:
                amount = float(PriceQ[1])
            except ValueError:
                message = 'Invalid syntax .price OR given number.'
                await ctx.message.add_reaction(EMOJI_ERROR)

        if PriceQ[1].lower() == "in":
            ### A1 / B1 or A2 / B2
            tmpA1 = ValueCmcUSD(PriceQ[0])
            tmpA2 = ValueGeckoUSD(PriceQ[0])

            tmpB1 = ValueCmcUSD(PriceQ[2])
            tmpB2 = ValueGeckoUSD(PriceQ[2])
            MsgPrice = ''
            #print(float(tmpA1 / tmpB1))
            #print(float(tmpA2 / tmpB2))
            if any(x is None for x in [tmpA1, tmpB1]):
                MsgPrice = MsgPrice
            else:
                totalValue = float(tmpA1 / tmpB1)
                MsgPrice = MsgPrice + '`1 {} = {:,.8f}{} from Coinmarketcap`\n'.format(PriceQ[0].upper(), totalValue, PriceQ[2].upper())
            if (any(x is None for x in [tmpA2, tmpB2])):
                MsgPrice = MsgPrice
            else:
                totalValue = float(tmpA2 / tmpB2)
                MsgPrice = MsgPrice + '`1 {} = {:,.8f}{} from Coingecko`'.format(PriceQ[0].upper(), totalValue, PriceQ[2].upper())
            if (MsgPrice == ''):
                MsgPrice = '`No result found pair {} and {}`'.format(PriceQ[0].upper(), PriceQ[2].upper())
                await ctx.message.add_reaction(EMOJI_ERROR)
            message = MsgPrice
            await ctx.send(message)
            return
        if PriceQ[0].lower() == "add":
            # .price add 10 xmr
            try:
                amount = int(PriceQ[1])
            except ValueError:
                pass
            try:
                amount = float(PriceQ[1])
            except ValueError:
                message = 'Invalid given number.'
                await ctx.message.add_reaction(EMOJI_ERROR)
            UnitPriceCmc = ValueCmcUSD(PriceQ[2])
            UnitPriceGecko = ValueGeckoUSD(PriceQ[2])
            if UnitPriceCmc is None and UnitPriceGecko is None:
                message = '`Ticker not found in marketcap for {}`'.format(PriceQ[2].upper())
            else:
                if UnitPriceCmc is None:
                    UnitPriceCmc = 0
                if UnitPriceGecko is None:
                    UnitPriceGecko = 0
                # let's insert
                if PriceMon_CheckExist(str(ctx.message.author.id), PriceQ[2].upper()) == True:
                    message = '`Please delete {} first in your monitoring list.`'.format(PriceQ[2].upper())
                    await ctx.message.add_reaction(EMOJI_ERROR)
                else:
                    if amount < 0.001:
                        message = '`The amount {} {} is too small.`'.format(amount, PriceQ[2].upper())
                        await ctx.message.add_reaction(EMOJI_ERROR)
                    else:
                        countList = PriceMon_CountRecord(str(ctx.message.author.id))
                        if countList >= 16:
                            message = '`You currently have {countList} record in your monitoring list. Delete some please.`'
                            await ctx.message.add_reaction(EMOJI_ERROR)
                        else:
                            msg = PriceMon_Add(str(ctx.message.author.id), PriceQ[2].upper(), amount, UnitPriceCmc, UnitPriceGecko)
                            message = msg 
            await ctx.send(message)
            return
    elif (len(PriceQ) == 4):
        if (PriceQ[2].lower() != "in"):
            message = 'Invalid syntax .price.'
        else:
            if not re.match('^[a-zA-Z0-9]+$', PriceQ[1]):
                message = 'Invalid ticker.'
                await ctx.message.add_reaction(EMOJI_ERROR)
            if not re.match('^[a-zA-Z0-9]+$', PriceQ[3]):
                message = 'Invalid ticker.'
                await ctx.message.add_reaction(EMOJI_ERROR)
            # check if valid number
            PriceQ[0] = PriceQ[0].replace(",", "")
            try:
                amount = int(PriceQ[0])
            except ValueError:
                pass
            try:
                amount = float(PriceQ[0])
            except ValueError:
                message = 'Invalid given number.'
                await ctx.message.add_reaction(EMOJI_ERROR)

            tmpA1 = ValueCmcUSD(PriceQ[1])
            tmpA2 = ValueGeckoUSD(PriceQ[1])

            tmpB1 = ValueCmcUSD(PriceQ[3])
            tmpB2 = ValueGeckoUSD(PriceQ[3])

            MsgPrice = ''
            #print(any(x is None for x in [tmpA1, tmpB1]))
            #print(any(x is None for x in [tmpA2, tmpB2]))
            if (any(x is None for x in [tmpA1, tmpB1])):
                MsgPrice = MsgPrice
            else:
                totalValue = float(float(amount) * tmpA1 / tmpB1)
                #print(totalValue)
                MsgPrice = MsgPrice + '`{} {} = {:,.8f}{} from Coinmarketcap`\n'.format(amount, PriceQ[1].upper(), totalValue, PriceQ[3].upper())
            if (any(x is None for x in [tmpA2, tmpB2])):
                MsgPrice = MsgPrice
            else:
                totalValue = float(float(amount) * tmpA2 / tmpB2)
                #print(totalValue)
                MsgPrice = MsgPrice + '`{} {} = {:,.8f}{} from Coingecko`'.format(amount, PriceQ[1].upper(), totalValue, PriceQ[3].upper())

            if (MsgPrice == ''):
                message = '`No result found pair {} and {}`'.format(PriceQ[1].upper(), PriceQ[3].upper())
                await ctx.message.add_reaction(EMOJI_ERROR)
            else:
                message = MsgPrice
        await ctx.send(message)
        return


@bot.command(pass_context=True, help=bot_help_mcap)
async def mcap(ctx, ticker: str):
    global conn
    if not re.match('^[a-zA-Z0-9]+$', ticker.strip()):
        message = 'Invalid ticker.'
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(message)
        return
    else:
        try:
            openConnection()
            message = "Unknown error."
            with conn.cursor() as cursor:
            # Read a single record
                sql = "SELECT * FROM `cmc_v2` WHERE `symbol`=%s ORDER BY `id` DESC LIMIT 1"
                cursor.execute(sql, (ticker.strip().upper(),))
                result = cursor.fetchone()

                if result is None:
                    message = '`We can not find ticker {} in Coinmarketcap`'.format(ticker.upper())
                    await ctx.message.add_reaction(EMOJI_ERROR)
                else:
                    await ctx.message.add_reaction(EMOJI_EXCHANGE)
                    name = result['name']
                    ticker = result['symbol']
                    price = result['priceUSD']
                    update = datetime.datetime.strptime(result['last_updated'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                    ago = timeago.format(update, datetime.datetime.utcnow())

                    if result['volume_24hUSD'] is None:
                        volume24h = " - "
                    else:
                        volume24h = str('{:,.2f}'.format(result['volume_24hUSD']))

                    if result['total_supply'] is None:
                        totalsupply = " - "
                    else:
                        totalsupply = str('{:,.2f}'.format(result['total_supply']))

                    if result['circulating_supply'] is None:
                        circulatingsupply = " - "
                        supplycap = " - "
                    else:
                        circulatingsupply = str('{:,.2f}'.format(result['circulating_supply']))
                        supplycap = str('{:,.2f}'.format(result['circulating_supply'] * price))

                    if result['max_supply'] is None:
                        maxsupply = " - "
                    else:
                        maxsupply = str('{:,.2f}'.format(result['max_supply']))
                    #print(result)
                    if float(price) > 0.01:
                        message = """ ```
{} - 1{}= {:,.4f}USD
Ranking:            {}
Circulating supply: {}{}
Market cap:         {}USD
Total supply:       {}{}
Max. supply:        {}{}
Volume 24h:         {}USD
Updated {}``` """.format(name, ticker, price, 
                         result['cmc_rank'], circulatingsupply, ticker, supplycap, 
                         totalsupply, ticker, maxsupply, ticker, volume24h, ago)
                    else:
                        message = """ ```
{} - 1{}= {:,.8f}USD
Ranking:            {}
Circulating supply: {}{}
Market cap:         {}USD
Total supply:       {}{}
Max. supply:        {}{}
Volume 24h:         {}USD
Updated {}``` """.format(name, ticker, price, 
                         result['cmc_rank'], circulatingsupply, ticker, supplycap, 
                         totalsupply, ticker, maxsupply, ticker, volume24h, ago)
            await ctx.send(message)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def ValueInUSD(amount, ticker) -> str:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `cmc_v2` WHERE `symbol`=%s ORDER BY `id` DESC LIMIT 1"
            cursor.execute(sql, (ticker.upper(),))
            result = cursor.fetchone()

            #coingecko
            sql = "SELECT * FROM `coingecko_v2` WHERE `symbol`=%s ORDER BY `id` DESC LIMIT 1"
            cursor.execute(sql, (ticker.lower(),))
            result2 = cursor.fetchone()

            if (result is None) and (result2 is None):
                return '`We can not find ticker {} in Coinmarketcap`'.format(ticker.upper())
            else:
                if result:
                    name = result['name']
                    ticker = result['symbol'].upper()
                    price = result['priceUSD']
                    totalValue = amount * price
                    if (float(totalValue) > 0.01):
                        totalValue = '{:,.4f}'.format(float(totalValue))
                    else:
                        totalValue = '{:,.8f}'.format(float(totalValue))
                    update = datetime.datetime.strptime(result['last_updated'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                    ago = timeago.format(update, datetime.datetime.utcnow())

                if result2 is not None:				
                    name2 = result2['name']
                    ticker2 = result2['symbol'].upper()
                    price2 = result2['marketprice_USD']
                    totalValue2 = amount * price2
                    if (float(totalValue2) > 0.01):
                        totalValue2 = '{:,.4f}'.format(float(totalValue2))
                    else:
                        totalValue2 = '{:,.8f}'.format(float(totalValue2))
                    update2 = datetime.datetime.strptime(result2['last_updated'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                    ago2 = timeago.format(update2, datetime.datetime.utcnow())

                MsgPrice = ''
                if result:
                    MsgPrice = MsgPrice + '`{}{} = {}USD. Updated {} from Coinmarketcap`\n'.format(amount, ticker, totalValue, ago)
                if result2:
                    MsgPrice = MsgPrice + '`{}{} = {}USD. Updated {} from Coingecko`'.format(amount, ticker2, totalValue2, ago2)
                return MsgPrice
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def ValueCmcUSD(ticker) -> float:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `cmc_v2` WHERE `symbol`=%s ORDER BY `id` DESC LIMIT 1"
            cursor.execute(sql, (ticker.upper(),))
            result = cursor.fetchone()
            if result is None:
                return None
            else:
                return float(result['priceUSD'])
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def ValueCmcUSDList():
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `cmc_v2` WHERE id IN (SELECT MAX(id) FROM `cmc_v2` GROUP BY symbol)"
            number_of_rows  = cursor.execute(sql,)
            result = cursor.fetchall()
            if result is None:
                return None
            else:
                res = {}
                for row in result:
                    if (row['priceUSD'] is not None):
                        res[row['symbol'].upper()] = row['priceUSD']
                        res['last_updated'] = row['last_updated']
                return res
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def ValueGeckoUSD(ticker) -> float:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `coingecko_v2` WHERE `symbol`=%s ORDER BY `id` DESC LIMIT 1"
            cursor.execute(sql, (ticker.lower(),))
            result = cursor.fetchone()
            if result is None:
                return None
            else:
                return float(result['marketprice_USD'])
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def ValueGeckoUSDList():
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `coingecko_v2` WHERE id IN (SELECT MAX(id) FROM `coingecko_v2` GROUP BY symbol)"
            number_of_rows  = cursor.execute(sql,)
            result = cursor.fetchall()
            if result is None:
                return None
            else:
                res = {}
                for row in result:
                    if (row['marketprice_USD'] is not None):
                        res[row['symbol'].upper()] = row['marketprice_USD']
                        res['last_updated'] = row['last_updated']
                return res
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def PriceMon_Del(discordID, symbol) -> str:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "DELETE FROM `PriceMonUser_v1` WHERE `discordID`=%s AND `symbol`=%s"
            cursor.execute(sql, (discordID, str(symbol).upper(),))
            conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return str('`OK, deleted {}!`\n'.format(symbol.upper()))


def PriceMon_DelAll(discordID) -> str:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "DELETE FROM `PriceMonUser_v1` WHERE `discordID`=%s"
            cursor.execute(sql, (discordID,))
            conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return str('`OK, deleted all monitoring list from you!`\n')


def PriceMon_CheckExist(discordID, symbol):
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `PriceMonUser_v1` WHERE `discordID`=%s AND `symbol`=%s"
            cursor.execute(sql, (discordID, symbol.upper(),))
            ExistSymbol = cursor.fetchone()
            if ExistSymbol is None:
                return False
            else:
                return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def PriceMon_CountRecord(discordID) -> int:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `PriceMonUser_v1` WHERE `discordID`=%s"
            number_of_rows = cursor.execute(sql, (discordID,))
            return number_of_rows
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def PriceMon_Add(discordID, symbol, amount, UnitPriceCmc, UnitPriceGecko) -> str:
    global conn
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            current_Date = int(datetime.datetime.now().timestamp())
            sql = "INSERT INTO PriceMonUser_v1 (`discordID`, `symbol`, `amount`, `priceUSD_cmc`, `priceUSD_coingecko`, `added_date`) VALUES (%s, %s, %s, %s, %s, %s)"
            affected_count = cursor.execute(sql, (discordID, symbol.upper(), amount, UnitPriceCmc, UnitPriceGecko, current_Date,))
            conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return str('`Inserted {} {} to your monitoring list.`'.format(amount, symbol.upper()))


def PriceMon_List(discordID) -> str:
    global conn
    SumFund = float(0)
    table_data = [
        ['No.', 'Ticker', 'Balance', 'Value(USD)']
    ]
    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT * FROM `PriceMonUser_v1` WHERE `discordID`=%s ORDER BY `symbol` ASC LIMIT 50"
            number_of_rows = cursor.execute(sql, (discordID,))
            i = 0
            while True:
                row = cursor.fetchone()
                if row == None:
                    break
                #print(row)
                i += 1

                if (row['priceUSD_cmc'] is None) and (row['priceUSD_coingecko'] is None):
                    SubPrice = 0
                else:
                    if row['amount'] is None:
                        row['amount'] = 0
                    else:
                        if (min(row['priceUSD_cmc'], row['priceUSD_coingecko']) == 0):
                            SubPrice = row['amount'] * (max(row['priceUSD_cmc'], row['priceUSD_coingecko']))
                        else:
                            SubPrice = row['amount'] * (min(row['priceUSD_cmc'], row['priceUSD_coingecko']))
                SumFund = SumFund + float(SubPrice)
                SubPrice = '{:,.6f}'.format(SubPrice)
                table_data.append([i, row['symbol'].upper(), '{:,.4f}'.format(row['amount']), SubPrice])
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    if i == 0:
        return '`You don\'t have any tracking coins.`'
    else:
        table = AsciiTable(table_data)
        return '`'+table.table+'`\n`Your tracking coin(s) values in USD: '+'{:,.2f}'.format(SumFund)+' USD`'


def PriceMon_update_rate():
    global conn
    UnitPriceCmc = {}
    UnitPriceGecko = {}
    UnitPriceCmc = ValueCmcUSDList()
    UnitPriceGecko = ValueGeckoUSDList()

    try:
        openConnection()
        with conn.cursor() as cursor:
        # Read a single record
            sql = "SELECT DISTINCT `symbol` FROM `PriceMonUser_v1`"
            number_of_rows = cursor.execute(sql,)
            result = cursor.fetchall()
            for row in result:
                if (row['symbol'] not in UnitPriceCmc):
                    UnitPriceCmc[row['symbol']] = 0
                if (row['symbol'] not in UnitPriceGecko):
                    UnitPriceGecko[row['symbol']] = 0
                sql = "UPDATE `PriceMonUser_v1` SET `priceUSD_cmc`=%s, `priceUSD_coingecko`=%s, `last_update`=%s WHERE `symbol`=%s"
                cursor.execute(sql, (UnitPriceCmc[row['symbol']], UnitPriceGecko[row['symbol']], datetime.datetime.utcnow(), row['symbol'],))
                conn.commit()
                print('Records updated unit price list {}...'.format(row['symbol']))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def update_rate_inMonList():
## Let bot update rate every 60 seconds
    while not bot.is_closed:
        await asyncio.sleep(30)
        PriceMon_update_rate()
        await asyncio.sleep(60)

# start bot
bot.loop.create_task(update_rate_inMonList())
bot.run(token)
