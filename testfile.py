import discord
from discord.ext import commands
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import random
import os
from discord.utils import get

daily = 2000
support = 5176
fool = 987654

gamble_channels = 1093442747815448637, 1093443393385930772
ws_name = 'gamble'

content = lambda ctx: ctx.message.content
author = lambda ctx: ctx.message.author
channel = lambda ctx: ctx.message.channel.id
current_time = lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=9)

client = commands.Bot(command_prefix=">>", intents=discord.Intents.all())
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

url = "https://docs.google.com/spreadsheets/d/1G288YQemotpgNzet_HchHUaa8m7md1YSH38wldmCi0k/edit#gid=0"
grace = None


@client.event
async def on_ready():
    print("login: Garam Gamble")
    print(client.user.name)
    print(client.user.id)
    print("---------------")
    await client.change_presence(activity=discord.Game(name='IU-COIN', type=1))


async def get_spreadsheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name("garam-382904-9603060e0307.json", scope)
    auth = gspread.authorize(creds)

    if creds.access_token_expired:
        auth.login()

    try:
        worksheet = auth.open_by_url(url).worksheet(ws_name)
    except gspread.exceptions.APIError:
        for gamble_channel in gamble_channels:
            await client.get_channel(gamble_channel).send("API 호출 횟수에 제한이 걸렸습니다. 제발 진정하시고 잠시후 다시 시도해주세요.")
        return
    return worksheet


async def get_row(ws, user=None, mention=None):
    if user != None:
        mention = user.mention
    if not (mention.startswith('<@') and mention.endswith('>')):
        return -1
    if mention[2] != '!':
        mention = mention[:2] + '!' + mention[2:]
    try:
        return ws.find(mention).row
    except gspread.exceptions.CellNotFound:
        ###
        guild = await client.fetch_guild('1036216656797642812')
        member = await guild.fetch_member(user.id)

        ws.append_row([mention, '10000', member.nick])
        return ws.find(mention).row
    except gspread.exceptions.APIError:
        for gamble_channel in gamble_channels:
            await client.get_channel(gamble_channel).send("API 호출 횟수에 제한이 걸렸습니다. 제발 진정하시고 잠시후 다시 시도해주세요.")
        return -1


async def get_money(ws, user=None, mention=None):
    if user != None:
        row = await get_row(ws, user)
    else:
        row = await get_row(ws, mention=mention)
    if row == -1:
        return 0
    return int(ws.cell(row, 2).value)


async def redeemable(ws, user=None, mention=None):
    checkin_timedelta = datetime.timedelta(days=1, minutes=-5)
    if user != None:
        row = await get_row(ws, user)
    else:
        row = await get_row(ws, mention=mention)
    if row == -1:
        return False, checkin_timedelta
    ct = ws.cell(row, 4).value
    if ct:
        time = eval(ct)
        td = current_time() - time
        return td >= checkin_timedelta, checkin_timedelta - td
    else:
        return True, datetime.timedelta()


async def update_money(ws, money, user=None, mention=None, checkin=False):
    if user != None:
        row = await get_row(ws, user)
    else:
        row = await get_row(ws, mention=mention)
    if row == -1:
        return False
    ws.update_cell(row, 2, str(money))
    if checkin:
        ws.update_cell(row, 4, repr(current_time()))
    return 1


def change_maintenance_state(ws):
    if ws.cell(1, 1).value == 'under maintenance':
        ws.update_cell(1, 1, 'userid')
        return False
    else:
        ws.update_cell(1, 1, 'under maintenance')
        return True


def check_maintenance_state(ws):
    return ws.cell(1, 1).value == 'under maintenance'


@client.command()
async def 공사(message):
    commander = author(message)
    if "디코봇관리자" in map(lambda x: x.name, commander.roles):
        await message.channel.send('> ***공사중 PLEASE WAIT ***')
        return


@client.command()
async def 공사완료(message):
    commander = author(message)
    if "디코봇관리자" in map(lambda x: x.name, commander.roles):
        await message.channel.send('> ***공사완료! GOOD LUCK! ***')
        return


@client.command()
async def 시즌마감(message):
    commander = author(message)
    if "디코봇관리자" in map(lambda x: x.name, commander.roles):
        ws = await get_spreadsheet()
        ws.clear()
        ws.resize(rows=1, cols=4)
        await message.channel.send("시즌을 마감합니다. 겜블러 여러분 수고하셨어요.")
        return


@client.command()
async def 출석(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return
    user = author(message)
    redeem, time_remain = await redeemable(ws, user)
    if redeem:
        money = await get_money(ws, user)
        if await update_money(ws, money + daily, user, checkin=True):
            await message.channel.send(
                "{}\n:cherry_blossom:좋은 하루되세용!:cherry_blossom: \n현재 잔고 : {}G".format(user.mention, money + daily))
            return
    await message.channel.send(
        "{} 출석체크는 24시간에 한번만 가능합니다.\n남은 시간 : 약 {}시간 {}분".format(user.mention, time_remain.seconds // 3600,
                                                               time_remain.seconds % 3600 // 60))


@client.command()
async def 재난지원금(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return
    user = author(message)
    money = await get_money(ws, user)
    if money == 0:
        if await update_money(ws, money + support, user, checkin=False):
            await message.channel.send("{}\n재난지원금 입금 완료!\n현재 잔고 : {}G".format(user.mention, money + support))
            return
    else:
        await message.channel.send("재난지원금은 0원일때만 신청할수있습니다.")
        return



@client.command()
async def 확인(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return
    user = author(message)
    money = await get_money(ws, user)
    await message.channel.send("{}\n잔고:{}G".format(user.mention, money))


         
@client.command()
async def 송금(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return
    sender = author(message)
    money = await get_money(ws, sender)
    msg = content(message)
    com, rcv, send, *rest = msg.split()

    if not send.isnumeric():
        await message.channel.send("{} 송금 금액은 정수여야 합니다.".format(sender.mention))
        return

    if money < int(send):
        await message.channel.send("{} 송금 금액은 소지 금액을 넘어설 수 없습니다. 현재 소지 금액: {}G".format(sender.mention, money))
        return

    rcv_mon = await get_money(ws, mention=rcv)
    await update_money(ws, rcv_mon + int(send), mention=rcv)
    await update_money(ws, money - int(send), sender)

    await message.channel.send(
        "송금 완료: {} -> {}\n보낸 사람 잔고: {}G\n받는 사람 잔고: {}G".format(sender.mention, rcv, money - int(send),
                                                               rcv_mon + int(send)))



@client.command()
async def 동전(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("Hey, Calm Down~")
        return
    user = author(message)
    msg = content(message)
    com, choice, bet, *rest = msg.split()

    if choice not in ('앞', '뒤'):
        await message.channel.send("{} 앞 또는 뒤만 선택할 수 있습니다.".format(user.mention))
        return

    if not bet.isnumeric():
        await message.channel.send("{} 베팅 금액은 자연수여야 합니다.".format(user.mention))
        return

    bet = int(bet)
    if bet == 0:
        await message.channel.send("{} 베팅 금액은 자연수여야 합니다.".format(user.mention))
        return

    money = await get_money(ws, user)
    if (bet, money) != (1, 0) and bet > money:
        await message.channel.send("{} 베팅 금액은 소지 금액을 넘어설 수 없습니다. 현재 소지 금액: {}G".format(user.mention, money))
        return

    msg = "{}\n예측:{}\n동전:".format(user.mention, choice)

    result = random.choice(['앞', '뒤'])
    msg += result + '\n'

    if result == choice:
        msg += ':white_check_mark: 성공!\n'
        money += bet
    else:
        msg += ':x: 실패...\n'
        if money == 0:
            money = 1
        money -= bet

    await update_money(ws, money, user)
    msg += '현재 잔고: {}G'.format(money)

    await message.channel.send(msg)


@client.command()
async def 순위(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return
    user = author(message)
    money = await get_money(ws, user)

    moneys = [*sorted(map(lambda x: int(x) if x.isnumeric() else -1, ws.col_values(2)), reverse=True)]
    rank = moneys.index(money) + 1
    same = moneys.count(money)
    await message.channel.send("{}\n현재 {}위(동순위 {}명)".format(user.mention, rank, same))


@client.command()
async def 랭킹(message):
    if message.channel.id not in gamble_channels: return
    ws = await get_spreadsheet()
    if check_maintenance_state(ws):
        await message.channel.send("진정하시라고요.")
        return

    list_rank_name = ws.col_values(1)
    list_rank_money = ws.col_values(2)
    list_rank = zip(list_rank_name, list_rank_money)
    list_rank = sorted(list_rank, key=lambda x: int(x[1]), reverse=True)

    text_message = ""
    cur_rank = 1
    same_rank_count = 0

    for i in range(2, len(list_rank) if len(list_rank) < 12 else 12):
        if list_rank[i - 1][1] == list_rank[i][1]:
            cur_rank -= 1
            text_message += ("\n공동 {}위: {}, 현재 잔고: {}G".format(cur_rank, list_rank[i][0], list_rank[i][1]))
            same_rank_count += 1
            cur_rank += 1
        else:
            cur_rank += same_rank_count
            text_message += ("\n현재 {}위: {}, 현재 잔고: {}G".format(cur_rank, list_rank[i][0], list_rank[i][1]))
            cur_rank += 1
            same_rank_count = 0

    await message.channel.send(text_message)


@client.command()
async def 겜블(message):
    if message.channel.id not in gamble_channels: return
    embed = discord.Embed(title="gamble bot", description="도박 봇입니다.", color=0xeee657)
    embed.add_field(name=">>출석\n", value="2000G를 받습니다. 23시간 55분에 한 번만 사용할 수 있습니다.\n", inline=False)
    embed.add_field(name=">>확인\n", value="자신의 소지 G를 확인합니다.\n", inline=False)
    #embed.add_field(name=">>송금 (멘션) (금액)\n", value="멘션한 사람에게 언급된 금액을 송금합니다.\n", inline=False)
    embed.add_field(name=">>동전 [앞/뒤] (금액)\n",
                    value="G를 걸고, 동전을 던집니다. 맞추면 두 배로 돌려받고, 틀리면 돌려받지 못합니다.\n0G를 소지중이라면 1G를 걸어 성공시 1G를 받을 수 있습니다.",
                    inline=False)
    embed.add_field(name=">>순위\n", value="자신의 순위와 동순위인 사람 수를 알려줍니다.\n", inline=False)
    embed.add_field(name=">>랭킹\n", value="10위까지 랭킹을 알려줍니다.\n", inline=False)
    await message.send(embed=embed)



access_token = os.environ["BOT_TOKEN"]
client.run(access_token)
