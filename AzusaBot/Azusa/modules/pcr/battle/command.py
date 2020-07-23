import logging
import os
import re
from asyncio import sleep
from datetime import datetime
from nonebot import permission as perm
from nonebot import Message as M
from nonebot import MessageSegment as MS
from Azusa.data import groupdict, SIGNAL
from Azusa.utils import convert_to_b64
from Azusa.middleware import CommandGroup, on_command, scheduled_job
from ._master import master

_clandict = {}
logger = logging.getLogger('Azusa.pcr')

pcr_battle_command = CommandGroup('pcr.battle', logger=logger, only_to_me=False, permission=perm.GROUP)

# 创建公会单位
@pcr_battle_command.command('createclan',
                            checkfunc=lambda session: not groupdict[session.self_id][session.event['group_id']]['mods_config']['pcr']['disable'],
                            aliases=('创建公会', '注册公会'),
                            only_to_me=True,
                            permission=perm.GROUP_OWNER)
async def createclan(session, bot):
    groupid = session.event['group_id']
    msg = M()
    if groupid in _clandict.keys():
        msg.append(MS.text('此群已经注册过公会了哦'))
    else:
        type = session.get('type', prompt='请输入公会服务器（国服、台服、日服）')
        botid = session.self_id
        _clandict[groupid] = master(botid, groupid, type)
        typedict = {'cn': '国服', 'tw': '台服', 'jp': '日服'}
        msg.append(MS.text(f'注册公会成功，使用{typedict[type]}数据进行boss血量上限以及分数倍率信息初始化，公会战管理组件可以使用'))
    await session.send(msg)

@createclan.args_parser
async def createclan_parser(session):
    stripped_args = session.current_arg_text.strip()
    if stripped_args:
        if re.search(r'[国Bb(cn)]服?', stripped_args):
            session.state['type'] = 'cn'
        elif re.search(r'[台(tw)]服?', stripped_args):
            session.state['type'] = 'tw'
        elif re.search(r'[日(jp)]服?', stripped_args):
            session.state['type'] = 'jp'
    else:
        session.state['type'] = 'tw'

# 删除公会单位
@pcr_battle_command.command('deleteclan',
                            checkfunc=lambda session: not groupdict[session.self_id][session.event['group_id']]['mods_config']['pcr']['disable'],
                            aliases=('删除公会', '解除注册公会'),
                            only_to_me=True,
                            permission=perm.GROUP_OWNER)
async def deleteclan(session, bot):
    groupid = session.event['group_id']
    msg = M()
    if groupid in _clandict.keys():
        _clandict.pop(groupid)
        msg.append(MS.text('删除公会成功'))
    else:
        msg.append(MS.text('此群未注册公会哦'))
    await session.send(msg)

# 用于检查消息类型与是否开启功能
def _check(session):
    return True if session.event['group_id'] in _clandict.keys() else False

# 开始新公会战
@pcr_battle_command.command('startBattle',
                            checkfunc=_check,
                            aliases=("开始公会战", "开始会战"),
                            only_to_me=True,
                            permission=perm.GROUP_ADMIN)
async def startBattle(session, bot):
    groupid = session.event['group_id']
    msg = M()
    totaldays = session.state['totaldays']
    daypassed = session.state['daypassed']
    if _clandict[groupid].callBattleStart(totaldays, daypassed):
        msg.append(MS.text('会战初始化完成！'))
        msg.append(MS.text(f'\n当前公会人数为：{_clandict[groupid].pnum}'))
    else:
        msg.append(MS.text('会战开启失败，请检查天数设置是否正确或者会战是否已开启。'))
    await session.send(msg)

@startBattle.args_parser
async def startBattle_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if len(paramList) >= 2:
            session.state['totaldays'] = int(paramList[0])
            session.state['daypassed'] = int(paramList[1])
        elif len(paramList) == 1:
            session.state['totaldays'] = int(paramList[0])
            session.state['daypassed'] = 0
        else:
            session.state['totaldays'] = 7
            session.state['daypassed'] = 0
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 结束公会战
@pcr_battle_command.command('endBattle',
                            checkfunc=_check,
                            aliases=("结束公会战", "结束会战"),
                            only_to_me=True,
                            permission=perm.GROUP_ADMIN)
async def endBattle(session, bot):
    groupid = session.event['group_id']
    msg = M()
    if _clandict[groupid].callBattleEnd():
        msg.append(MS.text("本期会战已结束，大家辛苦啦"))
    else:
        msg.append(MS.text('会战未开启哦'))
    await session.send(msg)

# 以下命令可在所有时期使用
# 注册入会
@pcr_battle_command.command('addplayer', checkfunc=_check, aliases=('注册', '加入公会', '入会'))
async def addplayer(session, bot):
    groupid = session.event['group_id']
    msg = M()
    id = session.state['id']
    if _clandict[groupid].is_player_exist(id):
        msg.append(MS.text('你已经注册过辣'))
    else:
        name = session.state['name']
        if _clandict[groupid].pnum >= 30:
            msg.append(MS.text('公会满员辣'))
        elif _clandict[groupid].callAddPlayer(id, name):
            msg.append(MS.text(f'玩家注册成功，你的昵称为{name}'))
        else: 
            msg.append(MS.text('昵称已被占用，请重新注册'))
    msg.append(MS.text(f'\n当前公会人数为： {_clandict[groupid].pnum}'))
    await session.send(msg, at_sender=True)

@addplayer.args_parser
async def addplayer_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    session.state['id'] = session.event['user_id']
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]
    else:
        session.state['name'] = session.event['sender']['card'] or session.event['sender']['nickname']
            

# 解除注册
@pcr_battle_command.command('delplayer', checkfunc=_check, aliases=('解除注册', '退出公会', '退会', '取消注册'))
async def delplayer(session, bot):
    groupid = session.event['group_id']
    msg = M()
    name = session.state["name"]
    if _clandict[groupid].callDelPlayer(name):
        msg.append(MS.text(f'玩家{name}解除注册成功'))
    else:
        msg.append(MS.text('不存在此玩家哦，请重新输入命令呢'))
    await session.send(msg, at_sender=True)
    await session.send(M(f'当前公会人数为： {_clandict[groupid].pnum}'))

@delplayer.args_parser
async def delplayer_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]
    else:
        id = session.event['user_id']
        if _clandict[groupid].is_player_exist(id):
            session.state['name'] = _clandict[groupid].getAlias(id)
        else:
            session.state['name'] = _clandict[groupid].reservedname

# 改名
@pcr_battle_command.command('setalias', checkfunc=_check, aliases=('修改昵称', '改名', '修改名称'))
async def setalias(session, bot):
    groupid = session.event['group_id']
    msg = M()
    lastname = session.state['lastname']
    if not _clandict[groupid].is_player_exist(lastname):
        msg.append(MS.text(f'玩家{lastname}不存在，请使用注册命令注册玩家哦'))
    else:
        newname = session.get('newname', prompt='请输入想要的昵称哦')
        if lastname == newname:
            msg.append(MS.text('新旧昵称不要相同哦'))
        elif _clandict[groupid].callSetAlias(lastname, newname):
            msg.append(MS.text(f'昵称修改成功，{lastname}现在昵称为{newname}'))
        else:
            msg.append(MS.text('昵称已被占用，请重新修改呢'))
    await session.send(msg)

@setalias.args_parser
async def setalias_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        if len(paramList) >= 2:
            session.state['lastname'] = paramList[0]
            session.state['newname'] = paramList[1]
        elif len(paramList) == 1:
            session.state['newname'] = paramList[0]
        if 'lastname' not in session.state.keys():
            id = session.event["user_id"]
            if _clandict[groupid].is_player_exist(id):
                session.state['lastname'] = _clandict[groupid].getAlias(id)
            else:
                session.state['lastname'] = _clandict[groupid].reservedname
    elif not paramList:
        session.pause(M('请输入你想要的昵称哦'))
    else:
        session.state['newname'] = paramList[0]

# 查分
@pcr_battle_command.command('queryplayer', checkfunc=_check, aliases=('查分', '查询分数'))
async def queryplayer(session, bot):
    groupid = session.event['group_id']
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text("查询的玩家不存在哦"))
    else:
        data = _clandict[groupid].callPlayerRecord(name)
        msg.append(MS.text(f'玩家名：{name}，总计分数：{data["TotalScore"]}，一王分数：{data["Boss1Score"]}，二王分数：{data["Boss2Score"]}，三王分数：{data["Boss3Score"]}，四王分数：{data["Boss4Score"]}，五王分数：{data["Boss5Score"]}，战斗力：{data["CombatEffectiveness"]}，相比上次战斗力统计，战斗力提升{data["CombatEffectivenessRise"]}。'))
    await session.send(msg)

@queryplayer.args_parser
async def queryplayer_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]
    else:
        id = session.event["user_id"]
        if _clandict[groupid].is_player_exist(id):
            session.state['name'] = _clandict[groupid].getAlias(id)
        else:
            session.state['name'] = _clandict[groupid].reservedname
   
# 查询分数排行
@pcr_battle_command.command('rank', checkfunc=_check, aliases=('查询排行'))
async def rank(session, bot):
    groupid = session.event['group_id']
    msg = M()
    if 'boss' not in session.state.keys():
        rank = _clandict[groupid].rank()
        if not rank:
            msg.append(MS.text('公会中没有玩家'))
        else:
            msg.append(MS.text('公会内总分排名：\n'))
            for i in range(0, len(rank)):
                msg.append(MS.text(f'{i + 1}. {rank[i][0]}，{rank[i][1]}分\n'))
    else:
        boss = session.state['boss']
        rank = _clandict[groupid].rank(boss)
        if not rank:
            msg.append(MS.text(f'公会中没有人对{boss}号boss出刀'))
        else:
            bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
            msg.append(MS.text(f'公会内{bossnickname[boss]}分数排名：\n'))
            for i in range(0, len(rank)):
                msg.append(MS.text(f'{i + 1}. {rank[i][0]}，{rank[i][1]}分\n'))
    await session.send(msg)

@rank.args_parser
async def rank_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        try:
            session.state['boss'] = int(paramList[0])
        except ValueError:
            session.finish(M('输入值必须为数字。会话已结束，请重新执行命令。'))

# 设置战斗力
@pcr_battle_command.command('setce', checkfunc=_check, aliases=('设置战斗力', '修改战斗力'))
async def setce(session, bot):
    groupid = session.event['group_id']
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text("更改的玩家不存在哦"))
    else:
        ce = session.get('ce', prompt=f'请输入{name}的战斗力哦')
        if _clandict[groupid].callSetCE(name, ce):
            msg.append(MS.text(f"{name}的战斗力成功修改为{ce}"))
        else:
            msg.append(MS.text("战斗力是不会下降的哦"))
    await session.send(msg)

@setce.args_parser
async def setce_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            if len(paramList) >= 2:
                session.state['name'] = paramList[0]
                session.state['ce'] = int(paramList[1])
            elif len(paramList) == 1:
                session.state['ce'] = int(paramList[0])
            if 'name' not in session.state.keys():
                id = session.event["user_id"]
                if _clandict[groupid].is_player_exist(id):
                    session.state['name'] = _clandict[groupid].getAlias(id)
                else:
                    session.state['name'] = _clandict[groupid].reservedname
        elif not paramList:
            session.pause(M('请输入有效的战斗力数值哦'))
        else:
            session.state[session.current_key] = int(paramList[0])
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 查询玩家昵称
@pcr_battle_command.command('getAlias', checkfunc=_check, aliases=('查询昵称'))
async def getAlias(session, bot):
    groupid = session.event['group_id']
    msg = M()
    id = session.get('id', prompt='请输入查询对象的QQ号哦')
    if _clandict[groupid].is_player_exist(id):
        name = _clandict[groupid].getAlias(id)
        msg.append(MS.text(f'玩家ID{id}的昵称是{name}'))
    else:
        msg.append(MS.text('查询的玩家不存在哦'))
    await session.send(msg)

@getAlias.args_parser
async def getAlias_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            if paramList:
                session.state['id'] = int(paramList[0])
        elif not paramList:
            session.pause(M('请输入查询对象的QQ号哦'))
        else:
            session.state[session.current_key] = int(paramList[0])
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 查询玩家ID
@pcr_battle_command.command('getID', checkfunc=_check, aliases=('查询ID'))
async def getID(session, bot):
    groupid = session.event['group_id']
    msg = M()
    name = session.get('name', prompt='请输入查询对象的昵称哦')
    if _clandict[groupid].is_player_exist(name):
        id = _clandict[groupid].getID(name)
        msg.append(MS.text(f'玩家{name}的ID是{id}'))
    else:
        msg.append(MS.text('查询的玩家不存在哦'))
    await session.send(msg)

@getID.args_parser
async def getID_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        if paramList:
            session.state['name'] = paramList[0]
    elif not paramList:
        session.pause(M('请输入查询对象的昵称哦'))
    else:
        session.state[session.current_key] = paramList[0]

# 查询所有玩家
@pcr_battle_command.command('getAllPlayer', checkfunc=_check, aliases=('查询所有玩家'))
async def getAllPlayer(session, bot):
    groupid = session.event['group_id']
    msg = M()
    msg.append(MS.text(f'当前公会人数为：{_clandict[groupid].pnum}。'))
    allplayer = _clandict[groupid].allplayer
    if allplayer:
        msg.append(MS.text('\n公会内玩家有：' + '，'.join(allplayer) + '。'))
    await session.send(msg)

# 以下命令仅能在会战期间使用
# 编辑此部分应当在命令执行前检查当前公会对象的is_battle_active值
# 调整boss信息，用于有人漏报时的修正
@pcr_battle_command.command('bossadjust', checkfunc=_check, aliases=('调整boss', '校正boss'), permission=perm.GROUP_ADMIN)
async def bossadjust(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    round = session.get('round', prompt='请输入boss周目：')
    boss = session.get('boss', prompt='请输入几号boss')
    hp = session.get('hp', prompt='请输入当前血量')
    if _clandict[groupid].callAdjustBoss(round , boss, hp):
        bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
        await session.send(M(f'boss信息校正完成，当前为{round}周目的{bossnickname[boss]}，剩余{hp}血。'))
        qqlist = [_clandict[groupid].getID(name) for name in _clandict[groupid].orderedboss(boss)]
        if qqlist:
            msg.append(MS.text(f'到{bossnickname[boss]}啦，'))
            for qq in qqlist:
                msg.append(MS.at(qq))
            msg.append(MS.text('该出刀啦'))
    else:
        msg.append(MS.text('参数不合法哦，请检查参数是否正确呢，尤其注意是否调整过阶段转换、血量上限哦。\n会话已结束，请重新执行命令。'))
    await session.send(msg)

@bossadjust.args_parser
async def bossadjust_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            l = len(paramList)
            if l >= 1:
                session.state["round"] = int(paramList[0])
            if l >= 2:
                session.state["boss"] = int(paramList[1])
            if l >= 3:
                session.state["hp"] = int(paramList[2])
        elif not paramList:
            session.pause(M('请输入有效参数哦'))
        else:
            session.state[session.current_key] = int(paramList[0])
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 攻击boss，出刀
@pcr_battle_command.command('attack', checkfunc=_check, aliases=('出刀', '报刀', '刀'))
async def attack(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    msg_sus = M()
    msg_ord = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text('报刀玩家不存在哦'))
    else:
        attackingboss = _clandict[groupid].boss['Boss']
        if _clandict[groupid].is_current_boss and len(session.state) <= 2:
            dmg = session.get('dmg', prompt='请输入伤害值哦')
            suspension_qq_list = [_clandict[groupid].getID(name) for name in _clandict[groupid].suspension]
            state = _clandict[groupid].callAttack(name, dmg=dmg)
        else:
            stage = session.get('stage', prompt='请输入boss阶段哦')
            boss = session.get('boss', prompt='请输入boss序号哦')
            dmg = session.get('dmg', prompt='请输入伤害值哦')
            state = _clandict[groupid].callAttack(name, stage, boss, dmg)
        if state == 0:
            msg.append(MS.text(f'玩家{name}出刀成功，'))
            if 'boss' in vars():
                bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
                msg.append(MS.text(f'对{stage}阶段的{bossnickname[boss]}造成{dmg}点伤害。'))
            else:
                bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
                bossinfo = _clandict[groupid].boss
                msg.append(MS.text(f'对当前boss造成{dmg}点伤害。\n当前boss为{bossinfo["Round"]}周目，{bossinfo["Stage"]}阶段的{bossnickname[bossinfo["Boss"]]}，剩余{bossinfo["CurrentHP"]}血。'))
        elif state == -1:
            msg.append(MS.text('请检查伤害值是否合法，或者boss信息是否正确呢。\n'))
            msg.append(MS.text('boss信息不正确，请使用“boss信息不正确”指令修改boss状态，或者使用“调整boss 周数 序号 血量”指令修改boss信息哦'))
        elif state == -2:
            msg.append(MS.text(f'{name}已经没有刀啦，不可以乱出啦'))
        elif state == -3:
            msg.append(MS.text(f'{name}正在挂树，不可以乱出哦'))
        elif state == -4:
            msg.append(MS.text(f'玩家{name}尚未申请出刀，请先申请出刀'))
        elif state == -5:
            lock = _clandict[groupid].callGetLock
            msg.append(MS.text(f'当前玩家{lock["player"]}正在出刀'))
        elif state == -6:
            msg.append(MS.text(f'玩家{name}不存在，请重新报刀'))
        elif state == 1:
            bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
            bossinfo = _clandict[groupid].boss
            msg.append(MS.text(f'玩家{name}出刀成功，对当前{bossnickname[attackingboss]}造成{dmg}点伤害并击破，已自动预约下一轮{bossnickname[attackingboss]}。'))
            tsec = _clandict[groupid].timepassed
            if tsec:
                hour = int(tsec // 3600)
                minute = int(tsec % 3600 // 60)
                second = int(tsec % 60)
                msg.append(MS.text(f'\n上一个boss共存活了{hour}小时{minute}分{second}秒。'))
            msg.append(MS.text(f'\n当前boss为{bossinfo["Round"]}周目，{bossinfo["Stage"]}阶段的{bossnickname[bossinfo["Boss"]]}，剩余{bossinfo["CurrentHP"]}血。'))
            if suspension_qq_list:
                for qq in suspension_qq_list:
                    msg_sus.append(MS.at(qq))
                msg_sus.append(MS.text('，可以下树了哦'))
            orderedboss_qq_list = [_clandict[groupid].getID(name) for name in _clandict[groupid].orderedboss(bossinfo['Boss'])]
            if orderedboss_qq_list:
                msg_ord.append(MS.text(f'到{bossnickname[_clandict[groupid].boss["Boss"]]}啦，'))
                for qq in orderedboss_qq_list:
                    msg_ord.append(MS.at(qq))
                msg_ord.append(MS.text('，该出刀啦'))
        elif state == 2:
            bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
            bossinfo = _clandict[groupid].boss
            msg.append(MS.text(f'玩家{name}出尾刀剩余刀成功，对当前boss造成{dmg}点伤害，并取消了尾刀预约。\n当前boss为{bossinfo["Round"]}周目，{bossinfo["Stage"]}阶段的{bossnickname[bossinfo["Boss"]]}，剩余{bossinfo["CurrentHP"]}血。'))
        elif state == 3:
            bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
            bossinfo = _clandict[groupid].boss
            msg.append(MS.text(f'玩家{name}出尾刀剩余刀成功，对当前boss造成{dmg}点伤害并击破，取消了尾刀预约。'))
            tsec = _clandict[groupid].timepassed
            if tsec:
                hour = int(tsec // 3600)
                minute = int(tsec % 3600 // 60)
                second = int(tsec % 60)
                msg.append(MS.text(f'\n上一个boss共存活了{hour}小时{minute}分{second}秒。'))
            msg.append(MS.text(f'\n当前boss为{bossinfo["Round"]}周目，{bossinfo["Stage"]}阶段的{bossnickname[bossinfo["Boss"]]}，剩余{bossinfo["CurrentHP"]}血。'))
            if suspension_qq_list:
                for qq in suspension_qq_list:
                    msg_sus.append(MS.at(qq))
                msg_sus.append(MS.text('，可以下树了哦'))
            orderedboss_qq_list = [_clandict[groupid].getID(name) for name in _clandict[groupid].orderedboss(bossinfo['Boss'])]
            if orderedboss_qq_list:
                msg_ord.append(MS.text(f'到{bossnickname[_clandict[groupid].boss["Boss"]]}啦，'))
                for qq in orderedboss_qq_list:
                    msg_ord.append(MS.at(qq))
                msg_ord.append(MS.text('，该出刀啦'))
    await session.send(msg)
    if msg_sus:
        await session.send(msg_sus)
    if msg_ord:
        await session.send(msg_ord)

@attack.args_parser
async def attack_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            if len(paramList) >= 4:
                session.state["name"] = paramList[0]
                session.state["stage"] = int(paramList[1])
                session.state["boss"] = int(paramList[2])
                session.state["dmg"] = int(paramList[3])
            elif len(paramList) == 3:
                session.state["stage"] = int(paramList[0])
                session.state["boss"] = int(paramList[1])
                session.state["dmg"] = int(paramList[2])
            elif len(paramList) == 2:
                session.state['name'] = paramList[0]
                session.state['dmg'] = int(paramList[1])
            elif len(paramList) == 1:
                session.state["dmg"] = int(paramList[0])
            if 'name' not in session.state.keys():
                id = session.event['user_id']
                if _clandict[groupid].is_player_exist(id):
                    session.state['name'] = _clandict[groupid].getAlias(id)
                else:
                    session.state['name'] = _clandict[groupid].reservedname
        elif not paramList:
            session.pause(M('请输入有效参数哦'))
        else:
            session.state[session.current_key] = int(paramList[0])
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 申请出刀
@pcr_battle_command.command('lock', checkfunc=_check, aliases=('申请出刀'))
async def lock(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text(f'玩家{name}不存在，请使用注册命令注册玩家哦'))
    elif _clandict[groupid].is_current_boss:
        state = _clandict[groupid].callSetLock(name)
        if state == 0:
            msg.append(MS.text(f'玩家{name}申请出刀成功。'))
        else:
            msg.append(MS.text(f'玩家{name}申请出刀失败，'))
            if state == -1:
                lock = _clandict[groupid].callGetLock
                msg.append(MS.text(f'当前玩家{lock["player"]}正在出刀。'))
            elif state == -2:
                msg.append(MS.text(f'当前玩家{name}已无剩余刀。'))
            elif state == -3:
                msg.append(MS.text(f'玩家{name}不存在，请先注册。'))
    else:
        msg.append(MS.text('当前boss信息已过时，申请出刀功能失效，请尽快调整boss信息'))
    await session.send(msg)

@lock.args_parser
async def lock_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]
    else:
        id = session.event["user_id"]
        if _clandict[groupid].is_player_exist(id):
            session.state['name'] = _clandict[groupid].getAlias(id)
        else:
            session.state['name'] = _clandict[groupid].reservedname

# 预约boss，预约刀
@pcr_battle_command.command('orderedboss', checkfunc=_check, aliases=('预约刀', '预约'))
async def orderedboss(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text(f'玩家{name}不存在，请使用注册命令注册玩家哦'))
    elif _clandict[groupid].is_current_boss:
        boss = session.get('boss', prompt='请输入你想要预约的boss序号哦')
        validboss = []
        invalidboss = []
        tips = ''
        for i in boss:
            if _clandict[groupid].callSetOrderedBoss(name, i):
                validboss.append(str(i))
            else:
                invalidboss.append(str(i))
        if validboss:
            msg.append(MS.text(f'玩家{name}预约{"，".join(validboss)}号boss成功。\n'))
        if invalidboss:
            msg.append(MS.text(f'玩家{name}预约{"，".join(invalidboss)}号boss失败，请注意是否预约了重复boss或者输入了错误的boss序号或者预约了超出剩余刀数的boss。\n'))
        orderedboss = _clandict[groupid].orderedboss(name)
        if not orderedboss:
            msg.append(MS.text(f'玩家{name}没有预约boss。'))
        else:
            bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
            msg.append(MS.text(f'玩家{name}预约了{"，".join([bossnickname[i] for i in orderedboss])}。'))
    else:
        msg.append(MS.text('当前boss信息已过时，预约功能失效，请尽快调整boss信息'))
    await session.send(msg)

@orderedboss.args_parser
async def orderedboss_parser(session):
    await common_orderedboss_parser(session)

# 取消预约boss，取消预约
@pcr_battle_command.command('cancelorderedboss', checkfunc=_check, aliases=('取消预约'))
async def cancelorderedboss(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text(f'玩家{name}不存在，请使用注册命令注册玩家哦'))
    else:
        boss = session.get('boss', prompt='请输入你想要取消预约的boss序号哦')
        validboss = []
        invalidboss = []
        for i in boss:
            if _clandict[groupid].callCancelOrderedBoss(name, i):
                validboss.append(str(i))
            else:
                invalidboss.append(str(i))
        if validboss:
            msg.append(MS.text(f'玩家{name}取消预约{"，".join(validboss)}号boss成功。\n'))
        if invalidboss:
            msg.append(MS.text(f'玩家{name}取消预约{"，".join(invalidboss)}号boss失败，请注意是否取消了未预约的boss。'))
    await session.send(msg)

@cancelorderedboss.args_parser
async def cancelorderedboss_parser(session):
    await common_orderedboss_parser(session)

async def common_orderedboss_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        if paramList:
            try:
                int(paramList[0])
                session.state['boss'] = [int(i) for i in paramList]
            except ValueError:
                session.state['name'] = paramList[0]
                try:
                    session.state['boss'] = [int(i) for i in paramList[1:]]
                except ValueError:
                    session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))
        if 'name' not in session.state.keys():
            id = session.event["user_id"]
            if _clandict[groupid].is_player_exist(id):
                session.state['name'] = _clandict[groupid].getAlias(id)
            else:
                session.state['name'] = _clandict[groupid].reservedname
    elif not paramList:
        session.pause(M('请输入有效的boss序号哦'))
    else:
        try:
            session.state['boss'] = [int(i) for i in paramList]
        except ValueError:
            session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 设置挂树
@pcr_battle_command.command('setsuspensiontrue', checkfunc=_check, aliases=('挂树', '上树'))
async def setsuspensiontrue(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text(f'玩家{name}不存在，请使用注册命令注册玩家哦'))
    elif _clandict[groupid].is_current_boss:
        if _clandict[groupid].callSetSuspension(name, True):
            msg.append(MS.text(f'玩家{name}已挂树，进行到下一个boss时将收到通知。'))
            if SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'pro':
                if session.self_id == SIGNAL['MainQQ']:
                    msg.append(MS.image(os.path.join('pcr', 'suspension.jpg')))
                else:
                    realpath = os.path.join(bot.config.resources, 'pcr', 'suspension.jpg')
                    msg.append(MS.image(convert_to_b64(realpath)))
        else:
            msg.append(MS.text(f'玩家{name}已经在挂树,或者无剩余刀了哦'))
    else:
        msg.append(MS.text('当前boss信息过时，挂树功能失效，请尽快调整boss信息'))
    await session.send(msg)

@setsuspensiontrue.args_parser
async def setsuspensiontrue_parser(session):
    await common_suspension_parser(session)

# 取消挂树
@pcr_battle_command.command('setsuspensionfalse', checkfunc=_check, aliases=('取消挂树', '下树'))
async def setsuspensionfalse(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if not _clandict[groupid].is_player_exist(name):
        msg.append(MS.text(f'玩家{name}不存在，请使用注册命令注册玩家哦'))
    else:
        if _clandict[groupid].callSetSuspension(name, False):
            msg.append(MS.text(f'玩家{name}已下树。'))
        else:
            msg.append(MS.text(f'玩家{name}不在挂树状态哦'))
    await session.send(msg)

@setsuspensionfalse.args_parser
async def setsuspensionfalse_parser(session):
    await common_suspension_parser(session)

async def common_suspension_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]
    else:
        id = session.event["user_id"]
        if _clandict[groupid].is_player_exist(id):
            session.state['name'] = _clandict[groupid].getAlias(id)
        else:
            session.state['name'] = _clandict[groupid].reservedname

# 设置各阶段boss最大HP值
@pcr_battle_command.command('setMAXHP', checkfunc=_check, aliases=('设置最大血量'), permission=perm.GROUP_ADMIN)
async def setMAXHP(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    stage = session.get('stage', prompt='请输入阶段')
    maxhp = session.get('maxhp', prompt='请依次输入五个boss的血量')
    _clandict[groupid].callSetMAXHP(stage, maxhp[0], maxhp[1], maxhp[2], maxhp[3], maxhp[4])
    msg.append(MS.text(f'{stage}阶段boss血量最大值设置为：一王：{maxhp[0]}，二王：{maxhp[1]}，三王：{maxhp[2]}，四王：{maxhp[3]}，五王：{maxhp[4]}。请注意调整各阶段boss分数倍率哦'))
    await session.send(msg)

@setMAXHP.args_parser
async def setMAXHP_parser(session):
    if not _check(session):
        return
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            if paramList:
                session.state['stage'] = int(paramList.pop(0))
                if len(paramList) == 5:
                    session.state['maxhp'] = [int(i) for i in paramList[:5]]
        elif not paramList:
            session.pause('请输入有效的参数哦')
        else:
            if session.current_key == 'stage':
                session.state['stage'] = int(paramList.pop(0))
            elif session.current_key == 'maxhp':
                if len(paramList) == 5:
                    session.state['maxhp'] = [int(i) for i in paramList[:5]]
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 设置各阶段分数倍率
@pcr_battle_command.command('setScorebuff', checkfunc=_check, aliases=('设置分数倍率'), permission=perm.GROUP_ADMIN)
async def setScorebuff(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    stage = session.get('stage', prompt='请输入阶段')
    buff = session.get('buff', prompt='请依次输入五个boss的分数倍率')
    _clandict[groupid].callSetScorebuff(stage, buff[0], buff[1], buff[2], buff[3], buff[4])
    msg.append(MS.text(f'{stage}阶段的boss分数倍率依次设置为：一王：{buff[0]}，二王：{buff[1]}，三王：{buff[2]}，四王：{buff[3]}，五王：{buff[4]}。'))
    await session.send(msg)

@setScorebuff.args_parser
async def setScorebuff_parser(session):
    if not _check(session):
        return
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if session.is_first_run:
            if paramList:
                session.state['stage'] = int(paramList.pop(0))
                if len(paramList) == 5:
                    session.state['buff'] = [float(i) for i in paramList[:5]]
        elif not paramList:
            session.pause('请输入有效的参数哦')
        else:
            if session.current_key == 'stage':
                session.state['stage'] = int(paramList.pop(0))
            elif session.current_key == 'buff':
                if len(paramList) == 5:
                    session.state['buff'] = [float(i) for i in paramList[:5]]
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 设置各阶段转换的周数
@pcr_battle_command.command('setStagechange', checkfunc=_check, aliases=('设置阶段转换'), permission=perm.GROUP_ADMIN)
async def setStagechange(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    data = session.get('data', prompt='请输入阶段切换的周数')
    _clandict[groupid].callSetStagechange(data)
    msg.append(MS.text(f'阶段转换周数依次设置为：{"，".join([str(i) for i in data])}，请注意调整各阶段boss血量与分数倍率哦'))
    await session.send(msg)

@setStagechange.args_parser
async def setScorebuff_parser(session):
    if not _check(session):
        return
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    try:
        if paramList:
            session.state['data'] = [int(i) for i in paramList]
        else:
            session.pause('请输入有效的参数哦')
    except ValueError:
        session.finish(M('参数必须是数字。会话已结束，请重新执行命令。'))

# 查询boss信息
@pcr_battle_command.command('bossinfo', checkfunc=_check, aliases=('查询BOSS', '查询Boss', '查询boss'))
async def bossinfo(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    if _clandict[groupid].is_current_boss:
        round = _clandict[groupid].boss["Round"]
        stage = _clandict[groupid].boss["Stage"]
        boss = _clandict[groupid].boss["Boss"]
        hp = _clandict[groupid].boss["CurrentHP"]
        bossnickname = {1: "一王", 2: "二王", 3: "三王", 4: "四王", 5: "五王"}
        msg.append(MS.text(f'当前是{round}周目，{stage}阶段的{bossnickname[boss]}，剩余{hp}血。'))
    else:
        msg.append(MS.text('当前boss信息不正确，请使用“调整boss”命令调整boss数值哦'))
    await session.send(msg)

# 查询挂树信息
@pcr_battle_command.command('suspension', checkfunc=_check, aliases=('查询挂树'))
async def suspension(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    suspension = _clandict[groupid].suspension
    if not suspension:
        msg.append(MS.text('当前没有玩家挂树'))
    else:
        msg.append(MS.text(f'当前共有{len(suspension)}人正在挂树：{"，".join(suspension)}。'))
    await session.send(msg)

# 查询未出完刀
@pcr_battle_command.command('remainingattack', checkfunc=_check, aliases=('查询剩余刀'))
async def remainingattack(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    if 'p' not in session.state.keys():
        reatk = _clandict[groupid].remainingattack()
        if not reatk:
            msg.append(MS.text('当前全体玩家已出完刀'))
        else:
            tips = []
            msg.append(MS.text(f'当前有{len(reatk)}人还有刀未出：'))
            for i in reatk:
                tips.append(f'玩家{i[0]}，剩余{i[1]}刀')
            msg.append(MS.text('；'.join(tips) + '。'))
            if SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'pro':
                if session.self_id == SIGNAL['MainQQ']:
                    msg.append(MS.image(os.path.join('pcr', 'urgeattack.jpg')))
                else:
                    realpath = os.path.join(bot.config.resources, 'pcr', 'urgeattack.jpg')
                    msg.append(MS.image(convert_to_b64(realpath)))
    else:
        p = session.state['p']
        if isinstance(p, int):
            reatk = _clandict[groupid].remainingattack(p)
            if not reatk:
                msg.append(MS.text(f'当前没有玩家剩余{p}刀'))
            else:
                msg.append(MS.text(f'当前剩余{p}刀的玩家共有{len(reatk)}人：{"，".join(reatk)}。'))
        elif isinstance(p, str):
            if _clandict[groupid].is_player_exist(p):
                reatk = _clandict[groupid].remainingattack(p)
                msg.append(MS.text(f'玩家{p}剩余{reatk}刀。'))
            else:
                msg.append(MS.text(f'玩家{p}不存在，请重新查询。'))
    await session.send(msg)

@remainingattack.args_parser
async def remainingattack_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        try:
            session.state['p'] = int(paramList[0])
        except ValueError:
            session.state['p'] = paramList[0]

# 查询预约刀
@pcr_battle_command.command('getorderedboss', checkfunc=_check, aliases=('查询预约刀', '查询预约'))
async def getorderedboss(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    if 'p' not in session.state.keys():
        orderedboss = _clandict[groupid].orderedboss()
        if not orderedboss:
            msg.append(MS.text('当前没有预约刀哦'))
        else:
            tips = ''
            bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
            msg.append(MS.text(f'当前有{len(orderedboss)}人正在预约：'))
            for i in orderedboss:
                tips += f'玩家{i[0]}预约了{"，".join([bossnickname[boss] for boss in i[1]])}；'
            tips = tips[:-1] + '。'
            msg.append(MS.text(tips))
    else:
        p = session.state['p']
        if isinstance(p, int):
            orderedboss = _clandict[groupid].orderedboss(p)
            if not orderedboss:
                msg.append(MS.text(f'当前没有玩家预约{p}号boss'))
            else:
                msg.append(MS.text(f'当前预约了{p}号boss的玩家共有{len(orderedboss)}人：{"，".join(orderedboss)}。'))
        elif isinstance(p, str):
            if _clandict[groupid].is_player_exist(p):
                bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
                orderedboss = _clandict[groupid].orderedboss(p)
                if not orderedboss:
                    msg.append(MS.text(f'玩家{p}没有预约boss。'))
                else:
                    msg.append(MS.text(f'玩家{p}预约了{"，".join([bossnickname[i] for i in orderedboss])}。'))
            else:
                msg.append(MS.text(f'玩家{p}不存在，请重新查询。'))
    await session.send(msg)

@getorderedboss.args_parser
async def getorderedboss_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        try:
            session.state['p'] = int(paramList[0])
        except ValueError:
            session.state['p'] = paramList[0]

# 查询公会总分
@pcr_battle_command.command('totalscore', checkfunc=_check, aliases=('查询公会总分'))
async def totalscore(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    score = _clandict[groupid].clantotalscore
    await session.send(M(f'当前公会总分为：{score}'))

# 查询已出刀
@pcr_battle_command.command('lastattack', checkfunc=_check, aliases=('查询已出刀信息'))
async def lastattack(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.state['name']
    if name and not _clandict[groupid].is_player_exist(name):
        await session.send(M(f'玩家{name}不存在，请重新查询'))
        return
    index = session.state['index']
    reverse = session.state['reverse']
    try:
        atk = _clandict[groupid].lastattack(name=name, index=index, reverse=reverse)
        msg.append(MS.text(f'当前共保存有{atk[1]}条出刀数据。\n'))
        bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
        typename = {0: '实时刀', 1: '漏报刀'}
        statename = {0: '正常出刀', 1: '尾刀', 2: '尾刀遗留时间', 3: '尾刀遗留时间击破'}
        if len(index) == 1:
            if reverse:
                msg.append(MS.text(f'{"玩家" + name + "的" if name else ""}正序第{index[0]}个出刀的信息：\n'))
            else:
                msg.append(MS.text(f'{"玩家" + name + "的" if name else ""}倒序第{index[0]}个出刀的信息：\n'))
        else:
            if reverse:
                msg.append(MS.text(f'{"玩家" + name + "的" if name else ""}正序第{index[0]}到正序第{index[1]}个出刀的信息：\n'))
            else:
                msg.append(MS.text(f'{"玩家" + name + "的" if name else ""}倒序第{index[1]}到倒序第{index[0]}个出刀的信息：\n'))
        for i in atk[0]:
            msg.append(MS.text(f'玩家：{i["name"]}，出刀时间：{i["time"]}，出刀类型：{typename[i["type"]]}、{statename[i["playerstate"]]}，对{i["stage"]}阶段的{bossnickname[i["boss"]]}造成了{i["dmg"]}点伤害。\n'))
    except IndexError:
        if reverse:
            msg.append(MS.text(f'未记录{"玩家" + name + "的" if name else ""}正序第{index[0] if len(index) == 1 else str(index[0]) + "到正序第" + str(index[1])}刀的信息哦'))
        else:
            msg.append(MS.text(f'未记录{"玩家" + name + "的" if name else ""}倒序第{index[0] if len(index) == 1 else str(index[1]) + "到倒序第" + str(index[0])}刀的信息哦'))
    await session.send(msg)

@lastattack.args_parser
async def lastattack_parser(session):
    if not _check(session):
        return
    stripped_args = session.current_arg_text.strip()
    if stripped_args:
        re_index_object = re.compile(r'\d+(-\d+)?')
        re_index = re_index_object.search(stripped_args)
        session.state['index'] = tuple([int(i) for i in re_index.group(0).split('-')]) if re_index else (1,)
        if len(session.state['index']) > 1:
            if session.state['index'][0] > session.state['index'][1]:
                session.finish(M('前一个数必须小于后一个数。会话已结束，请重新执行命令。'))
        session.state['reverse'] = True if re.search(r'正向(排序)?|正序', stripped_args) else False
        name_args = re_index_object.sub('', stripped_args).strip()
        session.state['name'] = name_args if name_args else None
    else:
        session.state['name'] = None
        session.state['index'] = (1,)
        session.state['reverse'] = False

# 作业提交，删除与查询
@pcr_battle_command.command('solutions', checkfunc=_check, aliases=('作业'))
async def solutions(session, bot):
    if  SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'air' or SIGNAL['coolq_directory'][0] == '':
        return
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    type = session.get('type', prompt='请输入操作类型（提交、删除、查询）')
    if type == 'submit':
        stage = session.get('stage', prompt='请输入作业阶段')
        boss = session.get('boss', prompt='请输入作业对应的boss')
        path = session.get('path', prompt='请发送作业图片')
        if _clandict[groupid].callSubmitSolutions(stage, boss, path):
            msg.append(MS.text(f'已成功添加进阶段{stage}，{str(boss) + "号" if boss else "全"}boss的作业'))
        else:
            msg.append(MS.text('添加失败，请检查阶段数和boss序号是否正确'))
    elif type == 'delete':
        path = session.get('path', prompt='请发送作业图片')
        _clandict[groupid].callDeleteSolutions(path)
        msg.append(MS.text('成功删除作业'))
    elif type == 'query':
        stage = session.get('stage', prompt='请输入作业阶段')
        boss = session.get('boss', prompt='请输入作业对应的boss')
        solutions = _clandict[groupid].callQuerySolutions(stage, boss)
        if solutions:
            msg.append(MS.text(f'已查询到{stage}阶段{str(boss) + "号" if boss else "全"}boss的作业如下：'))
            for image in solutions:
                if session.self_id == SIGNAL['MainQQ']:
                    msg.append(MS.image(image))
                else:
                    realpath = os.path.join(SIGNAL['coolq_directory'][0], 'data', 'image', image)
                    msg.append(MS.image(convert_to_b64(realpath)))
        else:
            msg.append(MS.text('查询不到信息'))
    await session.send(msg)

@solutions.args_parser
async def solutions_parser(session):
    if not _check(session):
        return
    paramList = session.current_arg_text.strip().split(' ')
    imageList = [i['data']['file'] for i in session.event['message'] if i['type'] == 'image']
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        if imageList:
            session.state['path'] = tuple(imageList)
        session.state['retry'] = 1
        try:
            if paramList[0] == '提交':
                session.state['type'] = 'submit'
            elif paramList[0] == '删除':
                session.state['type'] = 'delete'
            elif paramList[0] == '查询':
                session.state['type'] = 'query'
            else:
                session.finish(M('必须输入有效的操作类型。会话已结束，请重新输入命令。'))
            session.state['stage'] = int(paramList[1])
        except (ValueError, IndexError):
            pass
        try:
            session.state['boss'] = int(paramList[2])
        except IndexError:
            session.state['boss'] = 0
        except ValueError:
            pass
    elif session.current_key == 'path':
        if session.state['retry'] > 3:
            session.finish(M('重试次数过多，已关闭会话。请重新执行命令。'))
        if not imageList:
            session.state['retry'] += 1
            session.pause(M('请给出一张图片'))
        session.state['path'] = tuple(imageList)
    elif not paramList:
        session.pause(M('请输入有效的参数'))
    else:
        if session.current_key == 'type':
            if paramList[0] == '提交':
                session.state['type'] = 'submit'
            elif paramList[0] == '删除':
                session.state['type'] = 'delete'
            elif paramList[0] == '查询':
                session.state['type'] = 'query'
            else:
                session.finish(M('必须输入有效的操作类型。会话已结束，请重新输入命令。'))
        elif session.current_key == 'stage' or session.current_key == 'boss':
            try:
                session.state[session.current_key] = int(paramList[0])
            except ValueError:
                session.finish(M('阶段参数与序号参数必须是数字。会话已结束，请重新输入命令。'))

# 查询会战信息
@pcr_battle_command.command('battleinfo', checkfunc=_check, aliases=('查询会战详细信息'))
async def battleinfo(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    info = _clandict[groupid].battleinfo
    msg.append(MS.text(f'当前会战的详细信息：\n'))
    msg.append(MS.text(f'期数：{info["session"]}\n'))
    msg.append(MS.text(f'总时长：{info["totaldays"]}天\n'))
    if info['daypassed'] < 1:
        msg.append(MS.text(f'已进行天数：会战前{1 - info["daypassed"]}天\n'))
    else:
        msg.append(MS.text(f'已进行天数：会战中第{info["daypassed"]}天\n'))
    bossnickname = {1: '一王', 2: '二王', 3: '三王', 4: '四王', 5: '五王'}
    msg.append(MS.text('分数倍率信息：\n'))
    for k, v in info['scorebuff'].items():
        msg.append(MS.text(f'阶段{k}：'))
        msg.append(MS.text('；'.join([f'{bossnickname[x]}：{y}倍' for x, y in v.items()])))
        msg.append(MS.text('\n'))
    msg.append(MS.text('阶段转换信息：\n'))
    for k, v in info['stagechange'].items():
        msg.append(MS.text(f'阶段{k}：{v}周目\n'))
    msg.append(MS.text('血量上限信息：\n'))
    for k, v in info['maxhp'].items():
        msg.append(MS.text(f'阶段{k}：'))
        msg.append(MS.text('；'.join([f'{bossnickname[x]}：{y}血' for x, y in v.items()])))
        msg.append(MS.text('\n'))
    await session.send(msg)

# 撤回出刀，用于错误出刀
@pcr_battle_command.command('rollback', checkfunc=_check, aliases=('撤回出刀'), only_to_me=True)
async def rollback(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    if _clandict[groupid].callRollback():
        msg.append(MS.text('撤回成功，对boss伤害以及玩家分数已回退'))
    else:
        msg.append(MS.text('没有保存的信息啦，不可以继续撤回了哦'))
    await session.send(msg)

# 手动重置玩家状态
@pcr_battle_command.command('initattack', checkfunc=_check, aliases=('重置状态'), permission=perm.GROUP_ADMIN)
async def initattack(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    msg = M()
    name = session.get('name', prompt='请输入重置对象的昵称哦')
    if _clandict[groupid].callInitState(name):
        msg.append(MS.text(f'玩家{name}状态重置成功，已重置玩家刀数、清空所有预约。'))
    else:
        msg.append(MS.text('重置的玩家不存在哦'))
    await session.send(msg)

@initattack.args_parser
async def initattack_parser(session):
    if not _check(session):
        return
    groupid = session.event['group_id']
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if paramList:
        session.state['name'] = paramList[0]

# 手动设置提示boss信息不正确
@pcr_battle_command.command('bossinfoerror', checkfunc=_check, aliases=('boss信息不正确'))
async def bossinfoerror(session, bot):
    groupid = session.event['group_id']
    if not _clandict[groupid].is_battle_active:
        await session.send(M("现在无法使用该功能哦"))
        return
    _clandict[groupid].is_current_boss = False
    await session.send(M('请尽快使用“调整boss 周数 序号 血量”命令调整boss数值哦'))

# 以下命令为调试用命令，防止出现意外错误需要调试时关闭程序后丢失信息。
# 保存会战信息，必须在会战已开启时使用
@pcr_battle_command.command('udsave', aliases=('保存会战信息'), permission=perm.SUPERUSER)
async def udsave(session, bot):
    msg = M()
    for groupid in _clandict.keys():
        if not _clandict[groupid].is_battle_active:
            msg.append(MS.text(f'注册群：{groupid}，请在会战开启后使用该功能\n'))
        else:
            filename = _clandict[groupid].callSaveAllData()
            msg.append(MS.text(f'注册群：{groupid}，会战信息文件{filename}已保存\n'))
    await session.send(msg)

# 读取会战信息，必须在会战未开启时使用
@pcr_battle_command.command('udload', aliases=('读取会战信息'), permission=perm.SUPERUSER)
async def udload(session, bot):
    msg = M()
    for groupid in _clandict.keys():
        if _clandict[groupid].is_battle_active:
            msg.append(MS.text(f'注册群：{groupid}，请在会战未开启时使用该功能\n'))
        else:
            try:
                _clandict[groupid].callLoadAllData()
                msg.append(MS.text(f'注册群：{groupid}，已读取保存的会战信息\n'))
            except KeyError:
                msg.append(MS.text(f'注册群：{groupid}，读取保存的会战信息失败，可能不存在会战信息\n'))
    await session.send(msg)

# 以下是定时任务
# 每日5点自动刷新所有人状态
@scheduled_job(logger=logger, trigger='cron', hour = 5)
async def initdaily(bot):
    count = 0
    for groupid in _clandict.keys():
        if _clandict[groupid].is_battle_active:
            msg = M()
            reatk = _clandict[groupid].remainingattack()
            if reatk:
                msg.append(MS.text(f'前一天有{len(reatk)}人还有刀未出：'))
                tips = []
                for i in reatk:
                    tips.append(f'玩家{i[0]}，剩余{i[1]}刀')
                msg.append(MS.text('；'.join(tips) + '。'))
            _clandict[groupid].callInitDaily()
            _clandict[groupid].callSaveAllData()
            if _clandict[groupid].daypassed < 1:
                leadtime = 1 - _clandict[groupid].daypassed
                await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=M(f'新的一天到来啦，这是会战前第{leadtime}天呢'))
            else:
                await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=M(f'新的一天到来啦，这是会战第{_clandict[groupid].daypassed}天呢'))
                if msg and _clandict[groupid].daypassed > 1:
                    await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=msg)
            count += 1
    return 1 if count > 0 else 0

# 每日23点30分自动提醒所有未出刀的人
@scheduled_job(logger=logger, trigger='cron', hour = 23, minute = 30)
async def reatkwarn(bot):
    count = 0
    for groupid in _clandict.keys():
        if _clandict[groupid].is_battle_active and _clandict[groupid].daypassed > 0:
            reatk_qq_list = [_clandict[groupid].getID(reatk[0]) for reatk in _clandict[groupid].remainingattack()]
            msg = M()
            if reatk_qq_list:
                for qq in reatk_qq_list:
                    msg.append(MS.at(qq))
                msg.append(MS.text('，快出刀啦'))
            if msg:
                msg = M(f'已经{datetime.now().hour}点{datetime.now().minute}分了，').extend(msg)
                if SIGNAL['RegisteredQQ'][_clandict[groupid].botid]['coolq_edition'] == 'pro':
                    if _clandict[groupid].botid == SIGNAL['MainQQ'] and SIGNAL['coolq_directory'][0]:
                        msg.append(MS.image(os.path.join('pcr', 'urgeattack.jpg')))
                    else:
                        realpath = os.path.join(bot.config.resources, 'pcr', 'urgeattack.jpg')
                        msg.append(MS.image(convert_to_b64(realpath)))
            else:
                msg = M(f'已经{datetime.now().hour}点{datetime.now().minute}分啦，今天所有刀已出，值得表扬')
            await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=msg)
            count += 1
    return 1 if count > 0 else 0

# 会战结束日0点自动提醒报剩余刀，0点10分结束上报
@scheduled_job(logger=logger, trigger='cron', hour = 0)
async def lastdayautostop(bot):
    count = 0
    for groupid in _clandict.keys():
        if _clandict[groupid].is_battle_active:
            if _clandict[groupid].daypassed >= _clandict[groupid].totaldays:
                reatk = _clandict[groupid].remainingattack()
                if reatk:
                    msg = M()
                    msg.append(MS.text(f'当前有{len(reatk)}人还有刀未上报：'))
                    tips = []
                    for i in reatk:
                        tips.append(f'玩家{i[0]}，剩余{i[1]}刀')
                    msg.append(MS.text('；'.join(tips) + '。\n'))
                    msg.append(MS.text('会战已结束，请在10分钟内上报分数。'))
                    await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=msg)
                    await sleep(10 * 60)
                _clandict[groupid].callBattleEnd()
                await bot.send_group_msg(self_id=_clandict[groupid].botid, group_id=groupid, message=M(f'已经到了会战第{_clandict[groupid].totaldays}天0点啦，会战已经结束。大家辛苦啦！'))
                count += 1
    return 1 if count > 0 else 0