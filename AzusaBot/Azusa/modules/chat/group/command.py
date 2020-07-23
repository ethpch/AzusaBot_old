import logging
import asyncio
import re
import random
from nonebot import Message as M
from nonebot import MessageSegment as MS
from Azusa.data import groupdict
from Azusa.utils import Timer
from Azusa.middleware import on_message

logger = logging.getLogger('Azusa.chat')

# 需要管理员及以上权限的功能
@on_message('group',
            logger=logger,
            checkfunc=lambda event: (not groupdict[event['self_id']][event['group_id']]['mods_config']['chat']['disable']) and \
                groupdict[event['self_id']][event['group_id']]['member'][event['self_id']]['role'] >= 2
            ) 
async def admin_only_func(event, bot):
    count = 0
    # 正式的消息处理
    selfid = event['self_id']
    senderid = event['user_id']
    groupid = event['group_id']
    # 分割文本信息，at信息，图片信息等等
    allmsg = event['message']
    msgtext = []
    msgat = []
    for msg in allmsg:
        if msg['type'] == 'text':
            msgtext.append(msg['data']['text'])
        elif msg['type'] == 'at' and msg['data']['qq'] != 'all':
            msgat.append(int(msg['data']['qq']))
        elif msg['type'] == 'image':
            pass
    msg = M()
    # “一带一路”功能，允许一个群成员选择另一个群成员一起被禁言，时长控制为1-9分钟
    msgtextstr = ''.join(msgtext)
    if '一带一路' in msgtextstr and msgat:
        if groupdict[selfid][groupid]['member'][selfid]['role'] <= groupdict[selfid][groupid]['member'][senderid]['role']:
            msg.append(MS.text('权限狗无法参与（请自裁'))
        else:
            if len(msgat) > 1:
                msg.append(MS.text('是不是太贪心了呢'))
            elif senderid == msgat[0]:
                msg.append(MS.text('你成功促进了自己的经济发展'))
            elif groupdict[selfid][groupid]['member'][selfid]['role'] > groupdict[selfid][groupid]['member'][msgat[0]]['role']:
                msg.append(MS.text('你成功带动了'))
                msg.append(MS.at(msgat[0]))
                msg.append(MS.text('的经济发展'))
                await bot.set_group_ban(self_id=selfid, group_id=groupid, user_id=msgat[0], duration=random.randint(1, 9) * 60)
            else:
                msg.append(MS.text('没有符合帮扶政策的群员，你将独享'))
            await bot.set_group_ban(self_id=selfid, group_id=groupid, user_id=senderid, duration=random.randint(1, 9) * 60)
        if msg:
            await bot.send_group_msg(self_id=selfid, group_id=groupid, message=msg)
        count += 1
    # “抽奖”功能，允许一个群成员禁言自己，娱乐用，时长控制为1-9分钟
    if re.match(r'.*抽.*奖.*', msgtextstr):
        if groupdict[selfid][groupid]['member'][selfid]['role'] <= groupdict[selfid][groupid]['member'][senderid]['role']:
            msg.append(MS.text('权限狗无法参与（请自裁'))
        # “大抽奖”功能，抽奖升级版，时长控制为4-8小时
        elif re.match(r'.*[大带(da)].*抽.*奖.*', msgtextstr):
            await bot.set_group_ban(self_id=selfid, group_id=groupid, user_id=senderid, duration=random.randint(240, 480) * 60)
        else:
            await bot.set_group_ban(self_id=selfid, group_id=groupid, user_id=senderid, duration=random.randint(1, 9) * 60)
        if msg:
            await bot.send_group_msg(self_id=selfid, group_id=groupid, message=msg)
        count += 1
    return 1 if count > 0 else 0

# 随机复读
_repeat = {}
_repeatcooldown = 1200.0

@on_message('group',
            logger=logger,
            checkfunc=lambda event: not groupdict[event['self_id']][event['group_id']]['mods_config']['chat']['disable'])
async def randomrepeat(event, bot):
    count = 0
    selfid = event['self_id']
    groupid = event['group_id']
    global _repeat
    if groupid not in _repeat.keys():
        _repeat[groupid] = {
            'recentmsg': '',
            'repeatcount': 0,
            'probabilitygain': 0,
            'timer': Timer(),
            }
        _repeat[groupid]['timer'].start()
        _repeat[groupid]['timer'].elapsed = _repeatcooldown
    try:
        rawmsg = event['raw_message']
        if rawmsg == _repeat[groupid]['recentmsg']:
            _repeat[groupid]['repeatcount'] += 1
            _repeat[groupid]['probabilitygain'] += 1
        else:
            _repeat[groupid]['recentmsg'] = rawmsg
            _repeat[groupid]['repeatcount'] = 1
            _repeat[groupid]['probabilitygain'] = 1
        # 群复读次数达到三次时允许复读
        if _repeat[groupid]['repeatcount'] >= 3:
            rdm = random.randint(1, 100)
            # 复读几率，几率为20+复读次数*5，即最大16次复读内必定触发一次复读
            if rdm <= 20 + _repeat[groupid]['probabilitygain'] * 5:
                _repeat[groupid]['probabilitygain'] = 1
                # 延时复读，几率为30%
                if random.randint(1, 100) <= 30:
                    await asyncio.sleep(random.randint(10, 30))
                await bot.send_group_msg(self_id=selfid, group_id=groupid, message=rawmsg)
                count += 1
        # 20分钟内有一次机会允许复读
        _repeat[groupid]['timer'].stop()
        _repeat[groupid]['timer'].start()
        if _repeat[groupid]['timer'].elapsed >= _repeatcooldown:
            rdm = random.randint(1, 100)
            # 复读几率为 (上一次触发此功能的时间整除100)%，即最大10000秒必定触发一次复读
            if rdm <= _repeat[groupid]['timer'].elapsed // 100:
                _repeat[groupid]['timer'].reset()
                # 延时复读，几率为30%
                if random.randint(1, 100) <= 30:
                    await asyncio.sleep(random.randint(10, 30))
                await bot.send_group_msg(self_id=selfid, group_id = groupid, message = rawmsg)
                count += 1
        return 1 if count > 0 else 0
    except KeyError:
        _repeat.clear()
