﻿import logging
from nonebot import Message as M
from nonebot import MessageSegment as MS
from Azusa.log import debuglog
from Azusa.data import groupdict
from Azusa.middleware import on_command
from .command import *

__plugin_name__ = '公主连结公会战'
__plugin_usage__ = '公主连结公会战管理。查询详细帮助请使用指令 “会战帮助”。'

logger = logging.getLogger('Azusa.help')

# 帮助指令，使用字典式查询
# 本插件共有35条指令
@on_command('clanbattlehelp',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group' and \
                not groupdict[session.self_id][session.event['group_id']]['mods_config']['pcr']['disable'],
            aliases=('会战帮助'),
            only_to_me=False)
async def clanbattlehelp(session, bot):
    msg = M()
    if session.is_first_run and 'page0' not in session.state.keys():
        tips = M()
        tips.append(MS.text("欢迎使用AzusaBot的公主连结会战管理插件。"))
        tips.append(MS.text('本插件仅可在群聊中生效。所有指令均以空格分割；@代表需要at机器人才能执行；/代表其前后的指令均可执行且为同一效果（别名）；执行成功的指令一定会收到文字提示。\n'))
        tips.append(MS.text("-" * 10 + "\n目录：1.会战管理指令，2.公会指令（所有时期可用），3.会战限定指令（仅会战期间可用）。4.调试用指令（仅su可执行）。"))
        await session.send(tips)
    page0 = session.get('page0', prompt='请输入查询的页码哦')
    try:
        helpdict = {
            '1': {
                '0': '会战管理指令：\n1.<@创建公会/注册公会>，2.<@删除公会/解除注册公会>，3.<@开始公会战/开始会战>，4.<@结束公会战/结束会战>。',
                '1': '<@创建公会/注册公会>：可选1个参数。仅群主可执行。可选参数为“国服（B服、b服、cn服），台服（tw服），日服（jp服）”，未设置参数则默认为台服。将当前群注册为使用公会战插件的公会，公会战指令有效，使用服务器类型初始化会战数据（各阶段boss血量上限以及各阶段boss分数倍率信息，允许使用指令<设置最大血量><设置分数倍率>进行修改）。\n'+ '-' * 10 + '\n例：“创建公会 cn服”，创建一个类型为国服的公会。\n例：“创建公会”，创建一个类型为台服的公会。',
                '2': '<@删除公会/解除注册公会>：不接受参数。仅群主可执行。将当前群从使用公会战插件的公会中去除，公会战指令无效。',
                '3': '<@开始公会战/开始会战>：可选0，1，2个参数。仅群主和管理员可执行。参数依次为“会战总天数”、“会战已进行天数”，默认设置为“7”，“0”。允许使用会战限定指令，立即重置所有会战数据，并且会战进行到第1天时会自动重置所有会战数据。\n'+ '-' * 10 + '\n例：“@开始公会战”，开始为期7天的公会战，当前为会战前1天，命令执行后第2天时正式记录分数，第8天时自动结束。\n例：“@开始公会战 6 -1”，开始为期6天的公会战，当前为会战前2天，命令执行后第3天时正式记录分数，第8天时自动结束。',
                '4': '<@结束公会战/结束会战>：不接受参数。仅群主和管理员可执行。执行后结束当期会战，保存玩家分数并且禁止使用会战限定指令。由于已存在自动结束功能，不推荐使用此指令。',
                },
            '2': {
                '0': '公会指令：\n1.<注册/加入公会/入会>，2.<解除注册/退出公会/退会>，3.<修改昵称/改名/修改名称>，4.<查分/查询分数>，5.<查询排行>，6.<设置战斗力/修改战斗力>，7.<查询昵称>，8.<查询ID>，9.<查询所有玩家>。',
                '1': '<注册/加入公会/入会>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为群名片。向公会内注册新玩家，以昵称为自己的名称。\n' + '-' * 10 + '\n例：“注册”，以QQ昵称作为自己的名称注册。\n例：“注册 AAA”，以AAA作为自己的名称注册。',
                '2': '<解除注册/退出公会/退会>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为自己的名称。删除公会内以昵称为名称的玩家。\n' + '-' * 10 + '\n例：“解除注册”， 删除自己。\n例：“解除注册 AAA”，删除公会内名为AAA的玩家。',
                '3': '<修改昵称/改名/修改名称>：可选1，2个参数。参数依次为“旧昵称”、“新昵称”，“旧昵称”默认设置为公会内自己的名称。必须接受新昵称参数。将旧昵称的玩家的名称修改为新昵称。\n' + '-' * 10 + '\n例：“改名 AAA”，将自己的名称修改为AAA。\n例：“改名 AAA BBB”，将名称AAA的玩家的名称修改为BBB。',
                '4': '<查分/查询分数>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为公会内自己的名称。查询名称为昵称的玩家的分数。\n' + '-' * 10 + '\n例：“查分”，查询自己的分数。\n例:“查分 AAA”，查询名称为AAA的玩家的分数。',
                '5': '<查询排行>：可选0，1个参数。无参数时返回所有玩家的总分排行信息。带一个参数时，该参数为boss序号，返回所有玩家对该boss的分数排行信息。\n' + '-' * 10 + '\n例：“查询排行”，返回所有玩家总分排行信息。\n例：“查询排行 5”，返回所有玩家五王分数排行信息。',
                '6': '<设置战斗力/修改战斗力>：可选1，2个参数。参数依次为“昵称”，“战斗力数值”，“昵称”默认设置为公会内自己的名称。将名称为昵称的玩家的战斗力设置为战斗力数值。\n' + '-' * 10 + '\n例：“修改战斗力 5”，将自己的战斗力设置为5。\n例：“修改战斗力 AAA 5”，将名称为AAA的玩家的战斗力修改为5。',
                '7': '<查询昵称>：必选1个参数。参数为“QQ号”。查询以QQ号为内部ID的玩家的名称。',
                '8': '<查询ID>：必选1个参数。参数为“昵称”。查询以昵称为名称的玩家的QQ号。',
                '9': '<查询所有玩家>：不接受参数。查询公会内所有注册玩家的名称。',
                },
            '3': {
                '0': '会战限定指令：\n1.<出刀/刀/报刀>，2.<申请出刀>，3.<预约刀/预约>，4.<取消预约>，5.<挂树/上树>，6.<取消挂树/下树>，7.<重置状态>，8.<调整boss/校正boss>，9.<boss信息不正确>，10.<设置最大血量>，11.<设置分数倍率>，12.<设置阶段转换>，13.<@撤回出刀>，14.<查询已出刀信息>，15.<查询BOSS/查询Boss/查询boss>，16.<查询挂树>，17.<查询剩余刀>，18.<查询预约刀/查询预约>，19.<查询公会总分>，20.<查询会战信息>，21.<作业>。',
                '1': '<出刀/刀/报刀>：可选1，2，3，4个参数。带1或2个参数时，参数依次为“昵称”、“伤害值”，“昵称”默认设置为公会内自己的名称，执行后名称为昵称的玩家对当前boss造成伤害值的伤害。带3或4个参数时，参数依次为“昵称”、“阶段”、“boss序号”、“伤害值”，“昵称”默认设置为公会内自己的名称，执行后名称为昵称的玩家对阶段的阶段的boss序号的boss造成伤害值的伤害，此时伤害不计入当前boss数值。\n' + '-' * 15 + '\n例：“刀 10”，自己对当前boss造成10点伤害。\n例：“刀 AAA 10”，玩家AAA对当前boss造成10点伤害。\n例：“刀 3 4 20”，自己对三阶段四号boss造成20点伤害且当前boss信息不变。\n例：“刀 AAA 3 4 20”，玩家AAA对三阶段四号boss造成20点伤害且当前boss信息不变。',
                '2': '<申请出刀>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为公会内自己的名称。为名称为昵称的玩家申请出刀，可使用正常出刀指令。\n' + '-' * 10 + '\n例：“申请出刀”，为自己申请出刀。\n例：“申请出刀 AAA”，为玩家AAA申请出刀。',
                '3': '<预约刀/预约>：可选随意长度的参数。若第一个参数不是数字，则将其设置为“昵称”，并将其后所有参数作为boss序号传入；否则“昵称”默认设置为公会内自己的名称，并将所有参数作为boss序号传入。执行后为名称为昵称的玩家预约所有boss序号的boss。\n' + '-' * 10 + '\n例：“预约 2 3”，为自己预约2号3号boss。\n例：“预约 AAA 1”，为玩家AAA预约1号boss。',
                '4': '<取消预约>：可选随意长度的参数。若第一个参数不是数字，则将其设置为“昵称”，并将其后所有参数作为boss序号传入；否则“昵称”默认设置为公会内自己的名称，并将所有参数作为boss序号传入。执行后为名称为昵称的玩家取消预约所有boss序号的boss。\n' + '-' * 10 + '\n例：“取消预约 2 3”，为自己取消预约2号3号boss。\n例：“取消预约 AAA 1”，为玩家AAA取消预约1号boss。',
                '5': '<挂树/上树>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为公会内自己的名称。将名称为昵称的玩家设置为挂树状态。\n' + '-' * 10 + '\n例：“挂树”，为自己设置挂树。\n例：“挂树 AAA”，将名称为AAA的玩家设置挂树。',
                '6': '<取消挂树/下树>：可选0，1个参数。参数为“昵称”，“昵称”默认设置为公会内自己的名称。将名称为昵称的玩家取消挂树状态。当boss击破时所有挂树状态的玩家自动下树，不建议使用此指令。\n' + '-' * 10 + '\n例：“下树”，为自己取消挂树。\n例：“下树 AAA”，将名称为AAA的玩家取消挂树。',
                '7': '<重置状态>：可选0，1个参数。仅群主或管理员可执行。参数为“昵称”，“昵称”默认设置为公会内自己的名称。将名称为昵称的玩家的状态重置，包括剩余刀数，预约boss信息，挂树信息，尾刀信息。\n' + '-' * 10 + '\n例：“重置状态”，重置自己的状态。\n例：“重置状态 AAA”，重置名称为AAA的玩家的状态。',
                '8': '<调整boss/校正boss>：必选3个参数。仅群主或管理员可执行。参数依次为“周数”，“序号”，“当前血量”。将当前boss信息设置为周数的周目，序号的boss，当前血量的血量。\n' + '-' * 10 + '\n例：“调整boss 22 4 6800000”，将当前boss设置为22周目的4号boss且血量为6800000。',
                '9': '<boss信息不正确>：不接受参数。将当前boss信息设置为过时。此时出刀必须带3或4个参数，并且不再统计boss信息，预约刀、挂树将自动失效。',
                '10': '<设置最大血量>：必选6个参数。仅群主或管理员可执行。参数依次为boss阶段、boss1至boss5的血量上限。\n' + '-' * 10 + '\n例：“设置最大血量 3 7000000 9000000 12000000 14000000 17000000”，将三阶段五个boss的血量上限依次设置为7000000，9000000，12000000，14000000，17000000。',
                '11': '<设置分数倍率>：必选6个参数。仅群主或管理员可执行。参数依次为boss阶段、boss1至boss5的分数倍率。\n' + '-' * 10 + '\n例：“设置分数倍率 3 2 2 2.4 2.4 2.6”，将三阶段五个boss的分数倍率依次设置为2，2，2.4，2.4，2.6。',
                '12': '<设置阶段转换>：可选1个以上参数。仅群主或管理员可执行。参数依次为进入第1，第2，...，第n阶段的周数。\n' + '-' * 10 + '\n例：“设置阶段转换 1 4 11 35”，将阶段转换设置为第1周目进入第1阶段，第4周目进入第2阶段，第11周目进入第3阶段，第35周目进入第4阶段。',
                '13': '<@撤回出刀>：不接受参数。回滚所有信息至上一个出刀之前。用于报错刀修正。对任意形式的出刀均有效。将会保存Azusa从开始公会战（或读取会战信息）之后的所有出刀信息。每日五点清空。',
                '14': '<查询已出刀信息>：可选1，2，3个参数。可选参数为“正序”，“X（-Y）”，“昵称”。查询已出刀的信息，带有“正序”参数则按从前往后出刀的顺序查询，否则按从后往前的顺序查询。单独“X”参数查询第X条数据，“X-Y”参数查询第X到第Y条数据，Y必须大于X，此参数默认设置为“1”。“昵称”参数指定查询玩家昵称为“昵称”的出刀信息。\n' + '-' * 10 + '\n例：“查询已出刀信息”，查询倒序第一刀（前一刀）的出刀信息。\n例：“查询已出刀信息 3”，查询倒序第三刀（前第三刀）的出刀信息。\n例：“查询已出刀信息 4-7”，查询倒序第四到第七刀（前第七到第四刀）的所有出刀信息。\n例：“查询已出刀信息 正序 5”，查询正序第五刀的出刀信息。\n例：“查询已出刀信息 ABC”，查询昵称为“ABC”的玩家的出刀信息。',
                '15': '<查询BOSS/查询Boss/查询boss>：不接受参数。查询当前boss信息。',
                '16': '<查询挂树>：不接受参数。查询当前挂树信息。',
                '17': '<查询剩余刀>：可选0，1个参数。无参数时返回所有剩余刀数大于0的玩家的剩余刀信息。带一个参数时，若该参数为数字，则参数为剩余刀数，返回所有剩余刀数为参数的玩家名单；否则参数为玩家名称，返回该玩家的剩余刀数。\n' + '-' * 10 + '\n例：“查询剩余刀”，返回所有剩余刀数大于0的玩家的剩余刀信息。\n例：“查询剩余刀 3”，返回所有剩余刀数为3的玩家名单。\n例：“查询剩余刀 AAA”，返回玩家AAA的剩余刀数。',
                '18': '<查询预约刀/查询预约>：可选0，1个参数。无参数时返回所有玩家的挂树信息。带一个参数时，若该参数为数字，则参数为boss序号，返回所有预约了该boss的玩家名单；否则参数为玩家名称，返回该玩家的预约信息。\n' + '-' * 10 + '\n例：“查询预约”，返回所有玩家预约信息。\n例：“查询预约 5”，返回所有预约了五王的玩家名单。\n例：“查询预约 AAA”，返回玩家AAA的预约信息。',
                '19': '<查询公会总分>：不接受参数。查询当前公会的战斗总分。',
                '20': '<查询会战详细信息>：不接受参数。返回当前会战信息，包括期数（年月），总时长，已进行天数，所有boss血量上限设置以及所有boss分数倍率设置。',
                '21': '<作业>：可选参数。必选第一个参数“提交”或“删除”或“查询”，若为提交则可选2，3个参数“阶段”“图片”（此时提交为所有boss作业）或“阶段”“boss序号”“图片”（此时提交为指定boss作业），“删除”则必选1个参数“图片”，“查询”则可选1，2个参数“阶段”（查询指定阶段所有boss作业）或“阶段”“boss序号”（查询指定阶段指定boss作业）。依据参数不同操作作业系统。\n' + '-' * 10 + '\n例：“作业 提交 3 【图片】”，将图片保存为阶段3的全boss的作业。\n例：“作业 提交 3 1 【图片】”，将图片保存为阶段3的1号boss的作业。\n例：“作业 删除 【图片】”，将图片从作业库中删除。\n例：“作业 查询 3”，查询阶段3的全boss作业。\n例：“作业 查询 3 1”，查询阶段3的1号boss的作业。',
                },
            '4': {
                '0': '调试用指令：\n1.<@保存会战信息>，2.<@读取会战信息>。',
                '1': '<@保存会战信息>：不接受参数。高权限指令。执行后将所有注册使用公会战插件的群聊的会战信息保存为文件。',
                '2': '<@读取会战信息>：不接受参数。高权限指令。执行后从文件中读入会战信息。',
                },
            }
        page1 = session.get('page1', prompt=helpdict[page0]['0'] + '\n查询详细参数与效果请输入命令序号。' + '\n输入“0”结束查询。')
        if page1 != '0':
            msg.append(MS.text(helpdict[page0][page1]))
        await session.send(msg)
    except KeyError:
        await session.send(M('页码不存在哦'))

@clanbattlehelp.args_parser
async def clanbattlehtlp_parser(session):
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        if paramList:
            session.state['page0'] = paramList.pop(0)
            if paramList:
                session.state['page1'] = paramList.pop(0)
    elif not paramList:
        session.pause('请输入有效的序号')
    else:
        session.state[session.current_key] = paramList.pop(0)
