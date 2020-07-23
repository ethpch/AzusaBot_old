import logging
from nonebot import permission as perm
from nonebot import Message as M
from nonebot import MessageSegment as MS
from Azusa.data import frienddict, groupdict
from Azusa.middleware import on_command

logger = logging.getLogger('Azusa.help')


# 帮助指令，使用字典式查询
@on_command('pixivhelp',
            logger=logger,
            checkfunc=lambda session: not (groupdict[session.self_id][session.event['group_id']]['mods_config']['pixiv']['disable']
                                           if session.event['message_type'] == 'group' else (False if session.event['sub_type'] == 'group' \
                                               else frienddict[session.self_id][session.event['user_id']]['mods_config']['pixiv']['disable'])
                                           ),
            aliases=('pixiv帮助'),
            only_to_me=False)
async def pixivhelp(session, bot):
    msg = M()
    if session.is_first_run and 'page0' not in session.state.keys():
        tips = M()
        tips.append(MS.text("欢迎使用AzusaBot的pixiv插件。"))
        tips.append(MS.text('本插件所有指令名中字母均为英文大写，参数均以空格分割。\n'))
        tips.append(MS.text("-" * 10 + "\n目录：1.群r18管理指令，2.PID搜索，3.推荐，4.关键词搜索，5.UID搜索，6.榜单，7.统计信息，8.清理缓存。"))
        await session.send(tips)
    page0 = session.get('page0', prompt='请输入查询的页码哦')
    try:
        helpdict = {
            '1': {
                '0': '群r18管理指令：\n1.<禁用pixiv>，2.<启用pixiv>，3.<允许R18>，4.<禁止R18>，5.<允许R18G>，6.<禁止R18G>。',
                '1': '<禁用pixiv>：不接受参数。仅群主和管理员可执行。在本群禁用P站插件，不响应所有P站插件指令。',
                '2': '<启用pixiv>：不接受参数。仅群主和管理员可执行。在本群启用P站插件。默认为启用。',
                '3': '<允许R18>：不接受参数。仅群主和管理员可执行。允许在本群发送R18图像。',
                '4': '<禁止R18>：不接受参数。仅群主和管理员可执行。禁止在本群发送R18图像，所有R18图像将被过滤。特别的，<PID搜索>功能将输出除图片外的所有信息。默认为禁止。',
                '5': '<允许R18G>：不接受参数。仅群主和管理员可执行。允许在本群发送R18G图像，启用此项必须要先执行<允许R18>。',
                '6': '<禁止R18G>：不接受参数。仅群主和管理员可执行。禁止在本群发送R18G图像，所有R18G图像将被过滤。特别的，<PID搜索>功能将输出除图片外的所有信息。默认为禁止。',
                },
            '2': {
                '0': 'PID搜索：\n1.<PID搜索>，2.<PID搜索评论区>，3.<PID搜索相关>。',
                '1': '<PID搜索>：接受至少一个PID参数。可选参数为“多图”“原图”，“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图。输出ID为PID的图片的所有信息。\n' + '-' * 10 + '\n例：“PID搜索 12345678”，将输出ID为12345678的图片的所有信息。',
                '2': '<PID搜索评论区>：接受一个PID参数。输出ID为PID的图片的所有评论。\n' + '-' * 10 + '\n例：“PID评论区 12345678”，将输出ID为12345678的图片的所有评论。',
                '3': '<PID搜索相关>：接受至少一个PID参数。可选参数为“原图”“多图”“收藏x”“页x”。“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图，“收藏x”将指定输出作品的最小收藏数，“页x”将指定查找结果的页码。输出与ID为PID图片相关的所有图片。\n' + '-' * 10 + '\n例：“PID搜索相关 12345678”，将输出与ID为12345678的图片相关的所有图片。',                
                },
            '3': {
                '0': '推荐：\n1.<PIXIV推荐>。\n本系列指令全部拥有可选参数“多图”“原图”“收藏x”“页x”，“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图，“收藏x”将指定输出作品的最小收藏数，“页x”将指定查找结果的页码。',
                '1': '<PIXIV推荐>：接受可选参数。\n' + '-' * 10 + '\n例：“PIXIV推荐”，将输出推荐的所有图片。',
                },
            '4': {
                '0': '关键词搜索：\n1.<标签搜索>，2.<精确标签搜索>，3.<标题搜索>。\n本系列指令全部拥有可选参数“多图”“原图”“收藏x”“页x”，“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图，“收藏x”将指定输出作品的最小收藏数，“页x”将指定查找结果的页码。',
                '1': '<标签搜索>：接受至少一个关键字参数。输出以关键字搜索得到的所有图片。\n' + '-' * 10 + '\n例：“标签搜索 ロリ”，将输出以“ロリ”为关键字搜索得到的所有图片。',
                '2': '<精确标签搜索>：接受一个关键字参数。输出以关键字搜索得到的所有图片。因为禁止模糊匹配，所以应当使用最多一个关键词进行搜索。\n' + '-' * 10 + '\n例：“精确标签搜索 ロリ”，将输出以“ロリ”为关键字搜索得到的所有图片。',
                '3': '<标题搜索>：接受至少一个关键字参数。输出以关键字搜索得到的标题符合的所有图片。不推荐使用。\n' + '-' * 10 + '\n例：“标题搜索 ロリ”，将输出以“ロリ”为关键字搜索得到的所有标题含有“ロリ”的图片。',
                },
            '5': {
                '0': 'UID搜索：\n1.<UID搜索>，2.<UID搜索作品>，3.<UID搜索关注>，4.<UID搜索好P友>，5.<UID搜索收藏>。',
                '1': '<UID搜索>：接受一个UID参数。输出以UID搜索得到的用户信息。\n' + '-' * 10 + '\n例：“UID搜索 12345678”，将输出用户12345667的详细信息。',
                '2': '<UID搜索作品>：接受至少一个UID参数。可选参数为“多图”“原图”“收藏x”“页x”，“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图，“收藏x”将指定输出作品的最小收藏数，“页x”将指定查找结果的页码。输出以UID搜索得到的用户的所有作品。\n' + '-' * 10 + '\n例：“UID搜索作品 12345678”，输出用户12345678的所有作品。',
                '3': '<UID搜索关注>：接受一个UID参数。输出以UID搜索得到的用户的关注信息。\n' + '-' * 10 + '\n例：“UID搜索关注 12345678”，将输出用户12345678的关注的用户信息。',
                '4': '<UID搜索好P友>：接受一个UID参数。输出以UID搜索得到的用户的好P友信息\n' + '-' * 10 + '\n例：“UID搜索好P友 12345678”，将输出用户12345678的所有好P友信息。',
                '5': '<UID搜索收藏>：接受至少一个UID参数。可选参数为“多图”“原图”“收藏x”“页x”，“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图，“收藏x”将指定输出作品的最小收藏数，“页x”将指定查找结果的页码。输出以UID搜索得到的用户的所有收藏作品。\n' + '-' * 10 + '\n例：“UID搜索收藏 12345678”，输出用户12345678的所有收藏作品。',
                },
            '6': {
                '0': '榜单：\n1.<P站日榜>，2.<P站周榜>，3.<P站月榜>，4.<P站男性向日榜>，5.<P站女性向日榜>，6.<P站原创周榜>，7.<P站新人周榜>，8.<P站R18日榜>，9.<P站R18男性向日榜>，10.<P站R18女性向日榜>，11.<P站R18周榜>，12.<P站R18G周榜>，13.<P站漫画日榜>，14.<P站漫画周榜>，15.<P站漫画月榜>，16.<P站新人漫画周榜>，17.<P站R18漫画日榜>，18.<P站R18漫画周榜>，19.<P站R18G漫画周榜>。\n本系列指令全部拥有可选参数“页x”“xxxx-xx-xx”“多图”“原图”，“页x”参数将指定输出第x页内容，“xxxx-xx-xx”参数将指定以xxxx-xx-xx为日期的搜索（例：2020-01-01），“多图”参数将指定多图作品全部输出，“原图”参数将指定输出原图。',
                '1': '<P站日榜>：输出日排行榜。',
                '2': '<P站周榜>：输出周排行榜。',
                '3': '<P站月榜>：输出月排行榜。',
                '4': '<P站男性向日榜>：输出男性向日排行榜。',
                '5': '<P站女性向日榜>：输出女性向日排行榜。',
                '6': '<P站原创周榜>：输出原创周排行榜。',
                '7': '<P站新人周榜>：输出新人周排行榜。',
                '8': '<P站R18日榜>：输出R18日排行榜。',
                '9': '<P站R18男性向日榜>：输出R18男性向日排行榜。',
                '10': '<P站R18女性向日榜>：输出R18女性向日排行榜。',
                '11': '<P站R18周榜>：输出R18周排行榜。',
                '12': '<P站R18G周榜>：输出R18G周排行榜。',
                '13': '<P站漫画日榜>：输出漫画日排行榜。',
                '14': '<P站漫画周榜>：输出漫画周排行榜。',
                '15': '<P站漫画月榜>：输出漫画月排行榜。',
                '16': '<P站新人漫画周榜>：输出新人漫画周排行榜。',
                '17': '<P站R18漫画日榜>：输出R18漫画日排行榜。',
                '18': '<P站R18漫画周榜>：输出R18漫画周排行榜。',
                '19': '<P站R18G漫画周榜>：输出R18G漫画周排行榜。',
                },
            '7': {
                '0': '统计信息：\n1.<PIXIV本地统计>',
                '1': '<PIXIV本地统计>：可选一个参数“详细信息”。默认输出本地存在图片的图库统计信息，使用参数则输出全图库的统计信息。',
                },
            '8': {
                '0': '高权限指令：\n1.<清理P站图片缓存>。',
                '1': '<清理P站图片缓存>：不接受参数。清理所有P站图片缓存。',
                }
            }
        page1 = session.get('page1', prompt=helpdict[page0]['0'] + '\n查询详细参数与效果请输入命令序号。' + '\n输入“0”结束查询。')
        if page1 != '0':
            msg.append(MS.text(helpdict[page0][page1]))
        await session.send(msg)
    except KeyError:
        await session.send(M('页码不存在哦'))

@pixivhelp.args_parser
async def pixivhtlp_parser(session):
    selfid = session.self_id
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

@on_command('disable_pixiv',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('禁用pixiv'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def disable_pixiv(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['disable'] = True
    await session.send(M(f'已在群{groupid}禁用pixiv模块'))
    logger.info(f'group {groupid} call Azusa.modules.pixiv disable_pixiv successfully')

@on_command('enable_pixiv',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('启用pixiv'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def enable_pixiv(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['disable'] = False
    await session.send(M(f'已在群{groupid}启用pixiv模块'))
    logger.info(f'group {groupid} call Azusa.modules.pixiv enable_pixiv successfully')
