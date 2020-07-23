# 定义常用指令
import sys
import logging
import random
import asyncio
from nonebot import get_loaded_plugins
from nonebot import permission as perm
from nonebot.command import CommandManager, call_command
from nonebot import Message as M
from nonebot import MessageSegment as MS
from Azusa.data import frienddict, groupdict, SIGNAL
from Azusa.utils import storage
from Azusa.middleware import on_command, BLACKLIST

logger = logging.getLogger('Azusa.common')

# 总帮助指令
@on_command('help', logger=logger, aliases=('帮助'), only_to_me=False)
async def help(session, bot):
    plugins = list(filter(lambda p: p.name, get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    if not arg:
        msg = M()
        msg.append(MS.text('欢迎使用AzusaBot！\n'))
        msg.append(MS.text('Azusa现在启用的模块有：' + '，'.join(i for i in bot.config.LOAD_MODULES) + '\n'))
        msg.append(MS.text('群主及管理员可控制群聊中插件的开关。使用指令“disable_<模块名>”（例：disable_chat）可在本群禁用对应模块的功能。\n'))
        msg.append(MS.text('Azusa现在启用的功能有：' + '，'.join(p.name for p in plugins) + '\n'))
        msg.append(MS.text('查询详细帮助请使用指令“帮助 <功能名>”（例：“帮助 公主连结公会战”）\n'))
        msg.append(MS.text('常用功能（无法禁用）：\n'))
        msg.append(MS.text('手动复读<echo>。复读参数。例：“echo ABC”，复读ABC。\n'))
        msg.append(MS.text('骰子<dice/骰子>。为自己及at到的人(群聊)进行随机骰点。\n'))
        if session.event['user_id'] in bot.config.SUPERUSERS:
            msg.append(MS.text('测试指令<test>。仅superuser可以使用。\n'))
            msg.append(MS.text('数据保存<datasave>。仅superuser可以使用。执行所有的save命令，额外保存群与好友的模块控制开关信息。\n'))
            msg.append(MS.text('数据读取<dataload>。仅superuser可以使用。执行所有的load命令。额外读取群与好友的模块控制开关信息，会覆盖现有信息。\n'))
            msg.append(MS.text('重置主要QQ<resetmain/重置主QQ>。仅superuser可以使用。确保在主QQ无法登录（封禁等）且不用重启Azusa的情况下重新设置主QQ。\n'))
            msg.append(MS.text('设置用户黑名单<set_user_blacklist/添加到用户黑名单>。仅superuser可以使用。将用户添加到黑名单。\n'))
            msg.append(MS.text('设置群黑名单<set_group_blacklist/添加到群黑名单>。仅superuser可以使用。将群添加到黑名单。\n'))
            msg.append(MS.text('取消用户黑名单<del_user_blacklist/删除用户黑名单>。仅superuser可以使用。将用户从黑名单中删除。\n'))
            msg.append(MS.text('取消群黑名单<del_group_blacklist/删除群黑名单>。仅superuser可以使用。将群从黑名单中删除。\n'))
            msg.append(MS.text('查询黑名单<query_blacklist/查询黑名单>。仅superuser可以使用。查询黑名单内容。\n'))
            msg.append(MS.text('退出机器人<_exit>。仅superuser可以使用。退出机器人并保存所有信息。'))
        await session.send(msg)
        return
    for p in plugins:
        if p.name.lower() == arg:
            await session.send(M(p.usage))

# 测试指令
@on_command('test', logger=logger, cooldown=5, only_to_me=False, permission=perm.SUPERUSER)
async def test(session, bot):
    await session.send(M(str(session.event)))

# 手动复读
@on_command('echo', logger=logger, only_to_me=False)
async def echo(session, bot):
    msg = M(session.current_arg_text.strip())
    await session.send(msg)

# 骰子，为所有at的人进行随机骰点
@on_command('dice', logger=logger, aliases=('骰子'), only_to_me=False, permission=perm.GROUP)
async def dice(session, bot):
    selfid = session.self_id
    msgat = []
    for msg in session.event['message']:
        if msg['type'] == 'at' and msg['data']['qq'] != 'all':
            msgat.append(int(msg['data']['qq']))
    msg = M()
    if session.event['message_type'] == 'group':
        msg.append(MS.text(f'{session.event["sender"]["card"] or session.event["sender"]["nickname"]}掷出了{random.randint(1, 100)}点'))
    else:
        msg.append(MS.text(f'{session.event["sender"]["nickname"]}掷出了{random.randint(1, 100)}点'))
    for i in msgat:
        alias = groupdict[selfid][session.event['group_id']]['member'][i]['card'] or groupdict[selfid][session.event['group_id']]['member'][i]['nickname']
        msg.append(MS.text(f'\n{alias}掷出了{random.randint(1, 100)}点'))
    await session.send(msg)

# 数据保存与读取
datastorage = storage.getStorageObj('mods_config_data')
# 数据保存
@on_command('datasave', logger=logger, only_to_me=False, permission=perm.SUPERUSER)
async def datasave(session, bot):
    selfid = session.self_id
    for cmd in CommandManager().commands:
        if 'datasave' not in cmd and 'save' in repr(cmd):
            await call_command(bot, session.event, cmd)
    try:
        mods_config = {}
        for selfid in groupdict.keys():
            mods_config[str(selfid)] = {
                'group': {k: v['mods_config'] for k, v in groupdict[selfid].items()},
                'private': {k: v['mods_config'] for k, v in frienddict[selfid].items()},
                }
        datastorage.save('data', mods_config)
        await session.send(M('所有信息保存完成'))
    except Exception as e:
        await session.send(M('保存出现错误，请检查日志'))
        raise e

# 数据读取
@on_command('dataload', logger=logger, only_to_me=False, permission=perm.SUPERUSER)
async def dataload(session, bot):
    selfid = session.self_id
    for cmd in CommandManager().commands:
        if 'dataload' not in cmd and 'load' in repr(cmd):
            await call_command(bot, session.event, cmd)
    mods_config = datastorage.load('data')
    for k in groupdict[selfid].keys():
        try:
            groupdict[selfid][k]['mods_config'].update(mods_config[str(selfid)]['group'][str(k)])
        except KeyError:
            pass
    for k in frienddict[selfid].keys():
        try:
            frienddict[selfid][k]['mods_config'].update(mods_config[str(selfid)]['private'][str(k)])
        except KeyError:
            pass
    await session.send(M('所有信息读取完成'))

# 重置主QQ，确保在主QQ无法登录（封禁等）且不用重启Azusa的情况下重新设置主QQ（因为不会重新寻找cool目录，所以必须使用同一个客户端，否则会出现难以预料的错误）
@on_command('resetmain', logger=logger, aliases=('重置主QQ'), only_to_me=False, permission=perm.SUPERUSER)
async def resetmain(session, bot):
    selfid = session.self_id
    SIGNAL['MainQQ'] = selfid
    await session.send(M(f'重置主要QQ为{selfid}'))

# 设置黑名单
@on_command('set_user_blacklist', logger=logger, aliases=('添加到用户黑名单'), only_to_me=False, permission=perm.SUPERUSER)
async def set_user_blacklist(session, bot):
    ids = await get_id(session)
    BLACKLIST['user'].update(ids)
    await session.send(M(f'将{"，".join([str(i) for i in ids])}添加到用户黑名单。'))

@on_command('set_group_blacklist', logger=logger, aliases=('添加到群黑名单'), only_to_me=False, permission=perm.SUPERUSER)
async def set_group_blacklist(session, bot):
    ids = await get_id(session)
    BLACKLIST['group'].update(ids)
    await session.send(M(f'将{"，".join([str(i) for i in ids])}添加到群聊黑名单。'))

# 取消黑名单
@on_command('del_user_blacklist', logger=logger, aliases=('删除用户黑名单'), only_to_me=False, permission=perm.SUPERUSER)
async def del_user_blacklist(session, bot):
    ids = await get_id(session)
    for id in ids:
        BLACKLIST['user'].discard(id)
    await session.send(M(f'将{"，".join([str(i) for i in ids])}从用户黑名单移除。'))

@on_command('del_group_blacklist', logger=logger, aliases=('删除群黑名单'), only_to_me=False, permission=perm.SUPERUSER)
async def del_group_blacklist(session, bot):
    ids = await get_id(session)
    for id in ids:
        BLACKLIST['group'].discard(id)
    await session.send(M(f'将{"，".join([str(i) for i in ids])}从群黑名单移除。'))

async def get_id(session):
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    ids = []
    for i in paramList:
        try:
            ids.append(int(i))
        except ValueError:
            pass
    return tuple(ids)

# 查询黑名单
@on_command('query_blacklist', logger=logger, aliases=('查询黑名单'), only_to_me=False, permission=perm.SUPERUSER)
async def query_blacklist(session, bot):
    msg = M()
    if BLACKLIST['user']:
        msg.append(MS.text(f'用户黑名单：{"，".join([str(i) for i in BLACKLIST["user"]])}。\n'))
    if BLACKLIST['group']:
        msg.append(MS.text(f'群黑名单：{"，".join([str(i) for i in BLACKLIST["group"]])}。'))
    await session.send(msg)

# 退出机器人程序
@on_command('_exit', logger=logger, permission=perm.SUPERUSER)
async def exit(session, bot):
    await session.send(M('Azusa即将退出...'))
    try:
        sys.exit()
    finally:
        await call_command(bot, session.event, 'datasave')
