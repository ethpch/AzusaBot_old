import os
import re
import logging
from nonebot import permission as perm
from nonebot import Message as M
from nonebot import MessageSegment as MS
from AzusaBot import config
from Azusa.utils import Timer
from Azusa.data import groupdict, frienddict, SIGNAL
from Azusa.middleware import on_command, CommandGroup, on_websocket_connect, on_message, scheduled_job
from Azusa.exceptions import PixivError, InfoNotFoundError, RetryExhaustedError
from ._pixiv import pixiv_image


__plugin_name__ = 'P站插件'
__plugin_usage__ = 'P站相关功能实现，查询详细帮助请使用指令“pixiv帮助”'
_pixiv_instance = None
_timer = Timer()
logger = logging.getLogger('Azusa.pixiv')
pixiv_command = CommandGroup('pixiv', logger=logger, only_to_me=False, privileged=True)

@on_websocket_connect(logger=logger,
                      checkfunc=lambda event: _pixiv_instance is None,
                      wait_for=lambda : SIGNAL['coolq_directory'][1] == True)
async def init_pixiv_instance(event, bot):
    username = bot.config.PIXIV_USERNAME
    password = bot.config.PIXIV_PASSWORD
    proxy_url = bot.config.PIXIV_PROXY_URL
    imagepath = os.path.join(SIGNAL['coolq_directory'][0], 'data', 'image', 'pixiv') if SIGNAL['coolq_directory'][0] else ''
    global _pixiv_instance
    _pixiv_instance = pixiv_image(username, password, proxy_url, imagepath)
    _pixiv_instance.set_pagesize(20)

# 控制指令
# 控制R18与R18G
@pixiv_command.command('enabler18',
                       checkfunc=lambda session: _pixiv_instance is not None and \
                           session.event['message_type'] == 'group',
                       aliases=('允许R18'),
                       permission=perm.GROUP_ADMIN,
                       privileged=False)
async def enabler18(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18'] = True
    await session.send(M(f'群{groupid}已允许R18图像'))

@pixiv_command.command('disabler18',
                       checkfunc=lambda session: _pixiv_instance is not None and \
                           session.event['message_type'] == 'group',
                       aliases=('禁止R18'),
                       permission=perm.GROUP_ADMIN,
                       privileged=False)
async def disabler18(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18'] = False
    await session.send(M(f'群{groupid}已禁止R18图像'))

@pixiv_command.command('enabler18g',
                       checkfunc=lambda session: _pixiv_instance is not None and \
                           session.event['message_type'] == 'group',
                       aliases=('允许R18G'),
                       permission=perm.GROUP_ADMIN,
                       privileged=False)
async def enabler18g(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18g'] = True
    await session.send(M(f'群{groupid}已允许R18G图像'))

@pixiv_command.command('disabler18g',
                       checkfunc=lambda session: _pixiv_instance is not None and \
                           session.event['message_type'] == 'group',
                       aliases=('禁止R18G'),
                       permission=perm.GROUP_ADMIN,
                       privileged=False)
async def disabler18g(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18g'] = False
    await session.send(M(f'群{groupid}已禁止R18G图像'))

# 判断是否允许插件运行
async def _check(session) -> bool:
    if _pixiv_instance is None:
        return False
    if session.event['message_type'] == 'group':
        if groupdict[session.self_id][session.event['group_id']]['mods_config']['pixiv']['disable']:
            return False
    else:
        if session.event['sub_type'] == 'group':
            return True
        elif frienddict[session.self_id][session.event['user_id']]['mods_config']['pixiv']['disable']:
            return False
    return True

# 刷新登录token
async def refreshtoken():
    if _timer.run:
        if _timer.running:
            _timer.stop()
            # 两次执行时间间隔超过一小时则重新登录以刷新token
            if _timer.elapsed > 3600:
                await _pixiv_instance.login()
                logger.info('pixiv refresh token')
                _timer.reset()
            _timer.start()
    else:
        await _pixiv_instance.login()
        logger.info('pixiv first login')
        _timer.start()

# 获取R18与R18G权限值
async def _getperm(session) -> tuple:
    """ 获取r18与r18g权限 """
    if session.event['message_type'] == 'group':
        r18 = groupdict[session.self_id][session.event['group_id']]['mods_config']['pixiv']['allowr18']
        r18g = groupdict[session.self_id][session.event['group_id']]['mods_config']['pixiv']['allowr18g']
    else:
        if session.event['sub_type'] == 'group':
            r18 = r18g = True
        else:
            r18 = frienddict[session.self_id][session.event['user_id']]['mods_config']['pixiv']['allowr18']
            r18g = frienddict[session.self_id][session.event['user_id']]['mods_config']['pixiv']['allowr18g']
    return r18, r18g

# 通用函数
# pid参数解析器
async def common_pid_parser(session):
    """ pid参数解析器，获取一个pid参数 """
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        try:
            session.state['pid'] = int(paramList[0])
        except (IndexError, ValueError):
            pass
    elif not paramList:
        session.pause(M('请输入有效的pid'))
    else:
        try:
            session.state['pid'] = int(paramList[0])
        except ValueError:
            session.pause(M('参数必须是数字'))

# uid参数解析器
async def common_uid_parser(session):
    """ uid参数解析器，获取一个uid参数 """
    paramList = session.current_arg_text.strip().split(' ')
    if paramList[0] == '':
        paramList = []
    if session.is_first_run:
        try:
            session.state['uid'] = int(paramList[0])
        except (IndexError, ValueError):
            pass
    elif not paramList:
        session.pause(M('请输入有效的uid'))
    else:
        try:
            session.state['uid'] = int(paramList[0])
        except ValueError:
            session.pause(M('参数必须是数字'))

# 类型，页码，最低收藏数，原图与多图参数的解析器
re_page_object = re.compile(r'页\d+')
re_minbookmarks_object = re.compile(r'\d+收藏|收藏\d+')
async def common_type_page_minbookmarks_original_multiimage_parser(session):
    ''' 类型，页码，最低收藏数，原图与多图参数的解析器，获取页码、最低收藏数、原图与多图参数，默认值分别为1，False，False '''
    stripped_args = session.current_arg_text.strip()
    re_page = re_page_object.search(stripped_args)
    re_minbookmarks = re_minbookmarks_object.search(stripped_args)
    session.state['type'] = None if '全部' in stripped_args else 'manga' if '漫画' in stripped_args else 'illust'
    session.state['page'] = int(re_page.group(0)[1:]) if re_page else 1
    session.state['min_bookmarks'] = int(re_minbookmarks.group(0).replace('收藏', '')) if re_minbookmarks else 1
    session.state['original'] = True if '原图' in stripped_args else False
    session.state['multiimage'] = True if '多图' in stripped_args else False

# 通用多图片消息发送函数
async def common_multiimage_msgsender(session, pids: tuple, original: bool=False, multiimage: bool=False):
    '''
    通用多图片消息发送函数。
    参数：
        session
        pids: 图片pid组成的元组
        original: 是否使用原图
        multiimage: 是否使用多图
    '''
    if not pids:
        await session.send(M('未查询到信息'))
        return
    msg = M()
    msglimit = 20
    msgcurrent = 0
    useb64 = False if session.self_id == SIGNAL['MainQQ'] else True
    for illust in _pixiv_instance.getpics(pids, useb64):
        msgcurrent += illust['count'] if multiimage else 1
        if msgcurrent > msglimit:
            await session.send(msg)
            msgcurrent = illust['count'] if multiimage else 1
            msg.clear()
        msg.append(MS.text('-' * 20 + '\n'))
        msg.append(MS.text(f'作品名：{illust["title"]}\n'))
        msg.append(MS.text(f'PID：{illust["id"]}\n'))
        if SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'pro':
            files = illust['files']['original'] if original else illust['files']['large']
            multiimage = session.state['multiimage']
            if multiimage:
                for file in files:
                    msg.append(MS.image(file))
                    msg.append(MS.text('\n'))
            else:
                msg.append(MS.image(files[0]))
                msg.append(MS.text('\n'))
    if msg:
        await session.send(msg)

# 通用多用户消息发送函数
async def common_multiuser_msgsender(session, uids: tuple):
    """
    通用多用户消息发送函数。
    参数：
        session
        uids: 作者uid组成的元组
    """
    if not uids:
        await session.send(M('未查询到信息'))
        return
    msg = M()
    msglimit = 20
    msgcurrent = 0
    useb64 = False if session.self_id == SIGNAL['MainQQ'] else True
    for user in _pixiv_instance.getusers(uids, useb64):
        msgcurrent += 1
        if msgcurrent > msglimit:
            await session.send(msg)
            msgcurrent = 1
            msg.clear()
        msg.append(MS.text('-' * 20 + '\n'))
        msg.append(MS.text(f'用户名：{user["user"]["name"]}\n'))
        msg.append(MS.text(f'用户ID：{user["user"]["id"]}\n'))
    if msg:
        await session.send(msg)

# PID搜索
# PID搜索
@pixiv_command.command('pid_search_detail', checkfunc=_check, aliases=('PID搜索'))
async def pid_search_detail(session, bot):
    original = session.state['original']
    multiimage = session.state['multiimage']
    pid = session.get('pid', prompt='请输入想查询的PID')
    r18, r18g = await _getperm(session)
    useb64 = False if session.self_id == SIGNAL['MainQQ'] else True
    await session.send(M(f'开始搜索图片{pid}'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.illust_detail(pid, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        msg = M()
        for illust in _pixiv_instance.getpics(pids, useb64):
            msg.append(MS.text(f'作品名： {illust["title"]}\n'))
            msg.append(MS.text(f'作品ID： {illust["id"]}\n'))
            msg.append(MS.text(f'作品类型： {illust["type"]}\n'))
            msg.append(MS.text(f'作品页数： {illust["count"]}\n'))
            msg.append(MS.text(f'作品创作时间（JST）： {illust["time"]}\n'))
            msg.append(MS.text(f'作品标签： {"，".join([i["name"] + "（" + i["translated_name"] + "）" if i["translated_name"] is not None else i["name"] for i in illust["tags"]])}\n'))
            msg.append(MS.text(f'作者名： {illust["author_name"]}\n'))
            msg.append(MS.text(f'作者ID： {illust["author_id"]}\n'))
            msg.append(MS.text(f'阅览人数： {illust["views"]}\n'))
            msg.append(MS.text(f'收藏数： {illust["bookmarks"]}\n'))
            msg.append(MS.text(f'评论数： {illust["comments"]}\n'))
            if SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'pro':
                if ('R-18' in str(illust['tags']) or 'R18' in str(illust['tags'])) and not r18:
                    break
                elif ('R-18G' in str(illust['tags']) or 'R18G' in str(illust['tags'])) and not r18g:
                    break
                msglimit = 20
                msgcurrent = 0
                files = illust['files']['original'] if original else illust['files']['large']
                if multiimage:
                    for file in files:
                        msgcurrent += 1
                        if msgcurrent >= msglimit:
                            await session.send(msg)
                            msgcurrent = 1
                            msg.clear()
                        msg.append(MS.image(file))
                else:
                    msg.append(MS.image(files[0]))
        if msg:
            await session.send(msg)
    finally:
        await session.send(M(f'搜索图片{pid}完毕'))

@pid_search_detail.args_parser
async def pid_search_detail_parser(session):
    await common_pid_parser(session)
    if session.is_first_run:
        await common_type_page_minbookmarks_original_multiimage_parser(session)

# 评论区
@pixiv_command.command('pid_search_comment', checkfunc=_check, aliases=('PID搜索评论区'))
async def pid_search_comment(session, bot):
    pid = session.get('pid', prompt='请输入想查询的PID')
    await session.send(M(f'开始搜索作品{pid}的评论区'))
    try:
        await refreshtoken()
        comments = await _pixiv_instance.illust_comments(pid)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        msg = M()
        msglimit = 10
        msgcurrent = 0
        for comment in comments:
            msgcurrent += 1
            if msgcurrent > msglimit:
                await session.send(msg)
                msgcurrent = 1
                msg.clear()
            msg.append(MS.text(comment))
        if msg:
            await session.send(msg)
    finally:
        await session.send(M(f'搜索作品{pid}评论区完毕'))

@pid_search_comment.args_parser
async def pid_search_comment_parser(session):
    await common_pid_parser(session)

# 推荐与相关搜索
# 推荐
@pixiv_command.command('recommend', checkfunc=_check, aliases=('PIXIV推荐'))
async def recommend(session, bot):
    type = session.state['type']
    page = session.state['page']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    r18, r18g = await _getperm(session)
    await session.send(M('开始搜索推荐第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.illust_recommended(type=type, page=page, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids, original, multiimage)
    finally:
        await session.send(M('搜索推荐第{page}页完毕'))

@recommend.args_parser
async def recommend_parser(session):
    await common_type_page_minbookmarks_original_multiimage_parser(session)

# 作品相关搜索
@pixiv_command.command('pid_search_relate', checkfunc=_check, aliases=('PID搜索相关'))
async def pid_search_relate(session, bot):
    type = session.state['type']
    page = session.state['page']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    pid = session.get('pid', prompt='请输入想查询的PID')
    r18, r18g = await _getperm(session)
    await session.send(M(f'开始搜索作品{pid}相关图片第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.illust_related(pid=pid, type=type, page=page, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids, original, multiimage)
    finally:
        await session.send(M(f'搜索作品{pid}相关图片第{page}页完毕'))

@pid_search_relate.args_parser
async def pid_search_relate_parser(session):
    await common_pid_parser(session)
    if session.is_first_run:
        await common_type_page_minbookmarks_original_multiimage_parser(session)

# 关键词搜索
# 关键词通用查找函数
async def common_keywords_search(session, search_target: str):
    type = session.state['type']
    page = session.state['page']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    keywords = session.get('keywords', prompt='输入关键词')
    r18, r18g = await _getperm(session)
    await session.send(M(f'开始搜索关键词“{keywords}”第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.search_illust(keywords, type=type, page=page, search_target=search_target, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids, original, multiimage)
    finally:
        await session.send(M(f'搜索关键词“{keywords}”第{page}页完毕'))

# 关键词通用查找函数解析器
re_keywords_search_parser_object = re.compile(r'全部|漫画|插画|原图|多图|页\d+|\d+收藏|收藏\d+')
async def common_keywords_search_parser(session):
    stripped_args = session.current_arg_text.strip()
    stripped_args = re_keywords_search_parser_object.sub('', stripped_args).strip()
    if session.is_first_run:
        await common_type_page_minbookmarks_original_multiimage_parser(session)
        if stripped_args:
            session.state['keywords'] = stripped_args
    elif not stripped_args:
        session.pause(M('关键词不能为空'))
    else:
        session.state['keywords'] = stripped_args

@pixiv_command.command('keywords_search_partial', checkfunc=_check, aliases=('标签搜索'))
async def keywords_search_partial(session, bot):
    await common_keywords_search(session, search_target='partial_match_for_tags')

@keywords_search_partial.args_parser
async def keywords_search_partial_parser(session):
    await common_keywords_search_parser(session)

@pixiv_command.command('keywords_search_exact', checkfunc=_check, aliases=('精确标签搜索'))
async def keywords_search_exact(session, bot):
    await common_keywords_search(session, search_target='exact_match_for_tags')

@keywords_search_exact.args_parser
async def keywords_search_exact_parser(session):
    await common_keywords_search_parser(session)

@pixiv_command.command('keywords_search_title', checkfunc=_check, aliases=('标题搜索'))
async def keywords_search_title(session, bot):
    await common_keywords_search(session, search_target='title_and_caption')

@keywords_search_title.args_parser
async def keywords_search_title_parser(session):
    await common_keywords_search_parser(session)

# UID搜索
# 查询用户详细信息
@pixiv_command.command('uid_search_detail', checkfunc=_check, aliases=('UID搜索'))
async def uid_search_detail(session, bot):
    uid = session.get('uid', prompt='请输入想查询的UID')
    await session.send(M(f'开始搜索用户{uid}的详细信息'))
    try:
        await refreshtoken()
        uids = await _pixiv_instance.user_detail(uid)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        msg = M()
        useb64 = False if session.self_id == SIGNAL['MainQQ'] else True
        for user in _pixiv_instance.getusers(uids, useb64):
            msg.append(MS.text(f'用户名：{user["user"]["name"]}\n'))
            msg.append(MS.text(f'用户ID：{user["user"]["id"]}\n'))
            d = {
                'user': {
                    'profile_image': '用户头像' if 'profile_image' in user['user'].keys() else '',
                    'comment': '自我介绍' if 'comment' in user['user'].keys() else '',
                    },
                'profile': {
                    'webpage': '网站' if 'webpage' in user['profile'].keys() else '',
                    'gender': '性别' if 'gender' in user['profile'].keys() else '',
                    'job': '职业' if 'job' in user['profile'].keys() else '',
                    'region': '国家或地区' if 'region' in user['profile'].keys() else '',
                    'total_follow_users': '关注的人数' if 'total_follow_users' in user['profile'].keys() else '',
                    'total_mypixiv_users': '好P友人数' if 'total_mypixiv_users' in user['profile'].keys() else '',
                    'total_illusts': '创作插画数' if 'total_illusts' in user['profile'].keys() else '',
                    'total_manga': '创作漫画数' if 'total_manga' in user['profile'].keys() else '',
                    'total_novels': '创作小说数' if 'total_novels' in user['profile'].keys() else '',
                    'total_illust_bookmarks_public': '公开收藏作品数' if 'total_illust_bookmarks_public' in user['profile'].keys() else '',
                    'total_illust_series': '创作系列插画数' if 'total_illust_series' in user['profile'].keys() else '',
                    'total_novel_series': '创作系列漫画数' if 'total_novel_series' in user['profile'].keys() else '',
                    'background_image': '个人资料背景图' if 'background_image' in user['profile'].keys() else '',
                    'twitter_account': 'twitter帐号' if 'twitter_account' in user['profile'].keys() else '',
                    'twitter_url': 'twitter链接地址' if 'twitter_url' in user['profile'].keys() else '',
                    'pawoo_url': 'pawoo链接地址' if 'pawoo_url' in user['profile'].keys() else '',
                    },
                'workspace': {
                    'pc': '电脑' if 'pc' in user['workspace'].keys() else '',
                    'monitor': '显示器' if 'monitor' in user['workspace'].keys() else '',
                    'tool': '软件' if 'tool' in user['workspace'].keys() else '',
                    'scanner': '扫描仪' if 'scanner' in user['workspace'].keys() else '',
                    'tablet': '数位板' if 'tablet' in user['workspace'].keys() else '',
                    'mouse': '鼠标' if 'mouse' in user['workspace'].keys() else '',
                    'printer': '打印机' if 'printer' in user['workspace'].keys() else '',
                    'desktop': '桌子上的东西' if 'desktop' in user['workspace'].keys() else '',
                    'music': '绘图时听的音乐' if 'music' in user['workspace'].keys() else '',
                    'desk': '桌子' if 'desk' in user['workspace'].keys() else '',
                    'chair': '椅子' if 'chair' in user['workspace'].keys() else '',
                    'comment': '其他' if 'comment' in user['workspace'].keys() else '',
                    'workspace_image': '工作环境图' if 'workspace_image' in user['workspace'].keys() else '',
                    }
                }
            for k, v in d.items():
                for k1 in v.keys():
                    if user[k][k1]:
                        if 'image' not in k1:
                            msg.append(MS.text(f'{d[k][k1]}：{user[k][k1]}\n'))
                        elif 'image' in k1 and SIGNAL['RegisteredQQ'][session.self_id]['coolq_edition'] == 'pro':
                            msg.append(MS.text(f'{d[k][k1]}：'))
                            msg.append(MS.image(user[k][k1]))
                            msg.append(MS.text('\n'))
        await session.send(msg)
    finally:
        await session.send(M(f'搜索用户{uid}的详细信息完成'))

@uid_search_detail.args_parser
async def uid_search_detail_parser(session):
    await common_uid_parser(session)

# 用户作品列表
@pixiv_command.command('uid_search_illusts', checkfunc=_check, aliases=('UID搜索作品'))
async def uid_search_illusts(session, bot):
    type = session.state['type']
    page = session.state['page']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    uid = session.get('uid', prompt='请输入想查询的UID')
    r18, r18g = await _getperm(session)
    await session.send(M(f'开始搜索用户{uid}的作品第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.user_illusts(uid, type=type, page=page, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids, original, multiimage)
    finally:
        await session.send(M(f'搜索用户{uid}的作品第{page}页完毕'))

@uid_search_illusts.args_parser
async def uid_search_illusts_parser(session):
    await common_uid_parser(session)
    if session.is_first_run:
        await common_type_page_minbookmarks_original_multiimage_parser(session)

# 关注用户
@pixiv_command.command('uid_search_following', checkfunc=_check, aliases=('UID搜索关注'))
async def uid_search_following(session, bot):
    page = session.state['page']
    uid = session.get('uid', prompt='请输入想查询的UID')
    await session.send(M(f'开始搜索用户{uid}的关注用户第{page}页数据'))
    try:
        await refreshtoken()
        uids = await _pixiv_instance.user_following(uid, page)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiuser_msgsender(session, uids)
    finally:
        await session.send(M(f'搜索用户{uid}的关注用户第{page}页完毕'))

@uid_search_following.args_parser
async def uid_search_following_parser(session):
    await common_uid_parser(session)

# 好P友
@pixiv_command.command('uid_search_mypixiv', checkfunc=_check, aliases=('UID搜索好P友'))
async def uid_search_mypixiv(session, bot):
    page = session.state['page']
    uid = session.get('uid', prompt='请输入想查询的UID')
    await session.send(M(f'开始搜索用户{uid}的好P友第{page}页数据'))
    try:
        await refreshtoken()
        uids = await _pixiv_instance.user_mypixiv(uid, page)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiuser_msgsender(session, uids)
    finally:
        await session.send(M(f'搜索用户{uid}的好P友第{page}页完毕'))

@uid_search_mypixiv.args_parser
async def uid_search_mypixiv_parser(session):
    await common_pid_parser(session)

# 用户收藏作品
@pixiv_command.command('uid_search_bookmarks', checkfunc=_check, aliases=('UID搜索收藏'))
async def uid_search_bookmarks(session, bot):
    type = session.state['type']
    page = session.state['page']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    uid = session.get('uid', prompt='请输入想查询的UID')
    r18, r18g = await _getperm(session)
    await session.send(M(f'开始搜索用户{uid}的收藏作品第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.user_bookmarks_illust(uid, type=type, page=page, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids)
    finally:
        await session.send(M(f'搜索用户{uid}的收藏作品第{page}页完毕'))

@uid_search_bookmarks.args_parser
async def uid_search_bookmarks_parser(session):
    await common_uid_parser(session)
    if session.is_first_run:
        await common_type_page_minbookmarks_original_multiimage_parser(session)

# 榜单系列
# 通用排行函数
async def common_pixiv_rank(session, mode: str):
    commandname = session.event['raw_message'].split(' ')[0]
    page = session.state['page']
    date = session.state['date']
    minbookmarks = session.state['min_bookmarks']
    original = session.state['original']
    multiimage = session.state['multiimage']
    r18, r18g = await _getperm(session)
    await session.send(M(f'开始搜索{commandname}第{page}页数据'))
    try:
        await refreshtoken()
        pids = await _pixiv_instance.illust_ranking(mode=mode, page=page, date=date, min_bookmarks=minbookmarks, original_image=original, multiimage=multiimage, allowr18=r18, allowr18g=r18g)
    except InfoNotFoundError:
        await session.send(M('未查询到信息'))
    except PixivError as e:
        await session.send(M('插件出错'))
        raise e
    else:
        await common_multiimage_msgsender(session, pids)
    finally:
        await session.send(M(f'搜索{commandname}第{page}页数据完毕'))

# 通用排行函数解析器
re_rank_parser_object = re.compile(r'\d{4}-\d{2}-\d{2}')
async def common_pixiv_rank_parser(session):
    await common_type_page_minbookmarks_original_multiimage_parser(session)
    stripped_args = session.current_arg_text.strip()
    re_date = re_rank_parser_object.search(stripped_args)
    session.state['date'] = re_date.group(0) if re_date else None

@pixiv_command.command('rank_day', checkfunc=_check, aliases=('P站日榜'))
async def rank_day(session, bot):
    await common_pixiv_rank(session, mode='day')

@rank_day.args_parser
async def rank_day_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week', checkfunc=_check, aliases=('P站周榜'))
async def rank_week(session, bot):
    await common_pixiv_rank(session, mode='week')

@rank_week.args_parser
async def rank_week_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_month', checkfunc=_check, aliases=('P站月榜'))
async def rank_month(session, bot):
    await common_pixiv_rank(session, mode='month')

@rank_month.args_parser
async def rank_month_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_male', checkfunc=_check, aliases=('P站男性向日榜'))
async def rank_day_male(session, bot):
    await common_pixiv_rank(session, mode='day_male')

@rank_day_male.args_parser
async def rank_day_male_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_female', checkfunc=_check, aliases=('P站女性向日榜'))
async def rank_day_female(session, bot):
    await common_pixiv_rank(session, mode='day_female')

@rank_day_female.args_parser
async def rank_day_female_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_original', checkfunc=_check, aliases=('P站原创周榜'))
async def rank_week_original(session, bot):
    await common_pixiv_rank(session, mode='week_original')

@rank_week_original.args_parser
async def rank_week_original_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_rookie', checkfunc=_check, aliases=('P站新人周榜'))
async def rank_week_rookie(session, bot):
    await common_pixiv_rank(session, mode='week_rookie')

@rank_week_rookie.args_parser
async def rank_week_rookie_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_r18', checkfunc=_check, aliases=('P站R18日榜'))
async def rank_day_r18(session, bot):
    await common_pixiv_rank(session, mode='day_r18')

@rank_day_r18.args_parser
async def rank_day_r18_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_male_r18', checkfunc=_check, aliases=('P站R18男性向日榜'))
async def rank_day_male_r18(session, bot):
    await common_pixiv_rank(session, mode='day_male_r18')

@rank_day_male_r18.args_parser
async def rank_day_male_r18_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_female_r18', checkfunc=_check, aliases=('P站R18女性向日榜'))
async def rank_day_female_r18(session, bot):
    await common_pixiv_rank(session, mode='day_female_r18')

@rank_day_female_r18.args_parser
async def rank_day_female_r18_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_r18', checkfunc=_check, aliases=('P站R18周榜'))
async def rank_week_r18(session, bot):
    await common_pixiv_rank(session, mode='week_r18')

@rank_week_r18.args_parser
async def rank_week_r18_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_r18g', checkfunc=_check, aliases=('P站R18G周榜'))
async def rank_week_r18g(session, bot):
    await common_pixiv_rank(session, mode='week_r18g')

@rank_week_r18g.args_parser
async def rank_week_r18g_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_manga', checkfunc=_check, aliases=('P站漫画日榜'))
async def rank_day_manga(session, bot):
    await common_pixiv_rank(session, mode='day_manga')

@rank_day_manga.args_parser
async def rank_day_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_manga', checkfunc=_check, aliases=('P站漫画周榜'))
async def rank_week_manga(session, bot):
    await common_pixiv_rank(session, mode='week_manga')

@rank_week_manga.args_parser
async def rank_week_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_month_manga', checkfunc=_check, aliases=('P站漫画月榜'))
async def rank_month_manga(session, bot):
    await common_pixiv_rank(session, mode='month_manga')

@rank_month_manga.args_parser
async def rank_month_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_rookie_manga', checkfunc=_check, aliases=('P站新人漫画周榜'))
async def rank_week_rookie_manga(session, bot):
    await common_pixiv_rank(session, mode='week_rookie_manga')

@rank_week_rookie_manga.args_parser
async def rank_week_rookie_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_day_r18_manga', checkfunc=_check, aliases=('P站R18漫画日榜'))
async def rank_day_r18_manga(session, bot):
    await common_pixiv_rank(session, mode='day_r18_manga')

@rank_day_r18_manga.args_parser
async def rank_day_r18_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_r18_manga', checkfunc=_check, aliases=('P站R18漫画周榜'))
async def rank_week_r18_manga(session, bot):
    await common_pixiv_rank(session, mode='week_r18_manga')

@rank_week_r18_manga.args_parser
async def rank_week_r18_manga_parser(session):
    await common_pixiv_rank_parser(session)

@pixiv_command.command('rank_week_r18g_manga', checkfunc=_check, aliases=('P站R18G漫画周榜'))
async def rank_week_r18g_manga(session, bot):
    await common_pixiv_rank(session, mode='week_r18g_manga')

@rank_week_r18g_manga.args_parser
async def rank_week_r18g_manga_parser(session):
    await common_pixiv_rank_parser(session)

# 统计
@pixiv_command.command('statistics', checkfunc=_check, aliases=('PIXIV本地统计'))
async def statistics(session, bot):
    only_file_exist = False if '详细' in session.current_arg_text.strip() else True
    illusts_stat, users_stat = _pixiv_instance.statistics(only_file_exist)
    msg = M()
    msg.append(MS.text('*' * 20 + '\n'))
    msg.append(MS.text('图片统计：\n'))
    msg.append(MS.text(f'总数：{illusts_stat["total"]}\n'))
    tags_stat_limit = 20
    msg.append(MS.text(f'标签统计（仅显示占比最高的{tags_stat_limit}条）：\n'))
    msg.append(MS.text(f'总标签量：{len(illusts_stat["tags_stat"])}\n'))
    for i in range(tags_stat_limit):
        item = illusts_stat['tags_stat'][i]
        msg.append(MS.text(f'{i+1}：{item[0]}{"（" + item[1] + "）" if item[1] else ""}：总数{item[2]}，占比{item[3]}\n'))
    msg.append(MS.text('阅读量统计\n'))
    for k, v in illusts_stat['views_stat'].items():
        msg.append(MS.text(f'阅读量{k}：总数{v["total"]}，占比{v["rate"]}\n'))
    msg.append(MS.text('收藏量统计\n'))
    for k, v in illusts_stat['bookmarks_stat'].items():
        msg.append(MS.text(f'收藏量{k}：总数{v["total"]}，占比{v["rate"]}\n'))
    msg.append(MS.text('-' * 20 + '\n'))
    msg.append(MS.text('用户统计：\n'))
    msg.append(MS.text(f'总数：{users_stat["total"]}\n'))
    msg.append(MS.text('*' * 20 + '\n'))
    await session.send(msg)

# 清理缓存
@pixiv_command.command('clear_cache', aliases=('清理P站图片缓存'), permission=perm.SUPERUSER, privileged=False)
async def clear_cache(session, bot):
    _pixiv_instance.clear_cache()
    await session.send(M('清除P站图片缓存完成'))

# 随机图片
pattern0 = re.compile(r'([色涩瑟蛇铜]|社保?|射爆?)图来?$')
pattern00 = re.compile(r'(有没有|[要再多]?来一?[点份张]).*的?([色涩瑟蛇铜]|社保?|射爆?)图')
pattern01 = re.compile(r'.*的?([色涩瑟蛇铜]|社保?|射爆?)图来?')
pattern1 = re.compile(r'^不够([色涩瑟蛇铜大骚]|社保?|射爆?)$')
pattern2 = re.compile(r'^[要再多]?来一?[点份张].*([铜丝腿腋尻胸乳足]|屁股|大姐姐|奶子|奈子|萘子|莱莱|欧派)$')
pattern3 = re.compile(r'^[要再多]?来一?[点份张].*$')
@on_message(logger=logger,
            checkfunc=lambda event: SIGNAL['RegisteredQQ'][event['self_id']]['coolq_edition'] == 'pro' and _pixiv_instance is not None and \
                ((not groupdict[event['self_id']][event['group_id']]['mods_config']['pixiv']['disable']) if event['message_type'] == 'group' \
                else (True if event['sub_type'] == 'group' \
                else (not frienddict[event['self_id']][event['user_id']]['mods_config']['pixiv']['disable'])))
            )
async def random_image(event, bot):
    msg = event['raw_message']
    # 处理入口
    entry0 = pattern0.search(msg)
    entry1 = pattern1.search(msg)
    entry2 = pattern2.search(msg)
    entry3 = pattern3.search(msg)
    if entry0 or entry1 or entry2 or entry3:
        useb64 = False if event['self_id'] == SIGNAL['MainQQ'] else True
        if event['message_type'] == 'group':
            r18 = groupdict[event['self_id']][event['group_id']]['mods_config']['pixiv']['allowr18']
            r18g = groupdict[event['self_id']][event['group_id']]['mods_config']['pixiv']['allowr18g']
        else:
            if event['sub_type'] == 'group':
                r18 = r18g = True
            else:
                r18 = frienddict[event['self_id']][event['user_id']]['mods_config']['pixiv']['allowr18']
                r18g = frienddict[event['self_id']][event['user_id']]['mods_config']['pixiv']['allowr18g']
        if entry0:
            entry = 0
            if '铜图' in msg:
                tags = ('ロリ', '萝莉', 'loli')
                no_image_tips = '没萝莉了'
            else:
                re0 = pattern00.search(msg)
                re1 = pattern01.search(msg)
                if re0:
                    msg00 = re0.group(0)
                    msg01 = re.sub(r'有没有|[要再多]?来一?[点份张]|的?([色涩瑟蛇铜]|射爆?)图', '', msg00)
                    tags = (msg01,) if re0 and msg01 else tuple()
                elif re1:
                    msg10 = re1.group(0)
                    msg11 = re.sub(r'的?([色涩瑟蛇铜]|射爆?)图来?', '', msg10)
                    tags = (msg11,) if re1 and msg11 else tuple()
        elif entry1:
            entry = 1
            if '不够铜' in msg:
                tags = ('ロリ', '萝莉', 'loli')
                no_image_tips = '没萝莉了'
            elif '不够大' in msg:
                tags = ('おっぱい', '魅惑の谷間', '巨乳')
                no_image_tips = '没欧派了'
            else:
                tags = tuple()
        elif entry2:
            entry = 2
            if '铜' in msg:
                tags = ('ロリ', '萝莉', 'loli')
                no_image_tips = '没萝莉了'
            elif '丝' in msg:
                if '黑丝' in msg:
                    tags = ('黒ストッキング', '黒タイツ', '黒ニーソ')
                    no_image_tips = '没黑丝了'
                elif '白丝' in msg:
                    tags = ('白ストッキング', '白タイツ', '白ニーソ')
                    no_image_tips = '没白丝了'
                else:
                    tags = ('ストッキング', 'タイツ', 'ニーソ')
                    no_image_tips = '没丝袜了'
            elif '腿' in msg:
                tags = ('魅惑のふともも', 'ふともも')
                no_image_tips = '没腿了'
            elif '腋' in msg:
                tags = ('腋', '脇')
                no_image_tips = '没腋了'
            elif '尻' in msg or '屁股' in msg:
                tags = ('尻神様', 'ねじ込みたい尻', 'お尻')
                no_image_tips = '没尻了'
            elif '大姐姐' in msg:
                tags = ('むちむち', 'ぽっちゃり')
                no_image_tips = '没大姐姐了'
            elif re.search(r'[胸乳]|奶子|奈子|萘子|莱莱|欧派', msg):
                tags = ('おっぱい', '魅惑の谷間', '巨乳')
                no_image_tips = '没欧派了'
            elif '足' in msg:
                tags = ('裸足', '足裏', '足指')
                no_image_tips = '没足了'
            else:
                tags = tuple()
        elif entry3:
            entry = 3
            m = re.sub(r'[再多]?来一?[点份张]', '', msg)
            # 无后缀时使用无效tag以避免发出图片
            tags = (m,) if m else ('++++++++++++', )
        file, signal = await _pixiv_instance.random_image(tags=tags, allowr18=r18, allowr18g=r18g, useb64=useb64)
        if file:
            msg = M()
            if entry in (1, 2):
                if not signal:
                    msg.append(MS.text(no_image_tips + '，来点铜吧'))
            elif entry in (0, 3):
                if not signal:
                    return
            msg.append(MS.image(file))
            if msg:
                if event['message_type'] == 'group':
                    await bot.send_group_msg(self_id=event['self_id'], group_id=event['group_id'], message=msg)
                else:
                    await bot.send_private_msg(self_id=event['self_id'], user_id=event['user_id'], message=msg)
                return 1
        return 0

# 保存图库信息
@pixiv_command.command('pixivsave', aliases=('P站保存图库'), permission=perm.SUPERUSER, privileged=False,
                       checkfunc=lambda event: _pixiv_instance is not None)
async def pixivsave(session, bot):
    _pixiv_instance.psave()
    await session.send(M('pixiv图库保存完成'))

@scheduled_job(logger=logger, trigger='cron', day='*/3')
async def _pixivsave(bot):
    if _pixiv_instance is not None:
        _pixiv_instance.psave()
    return 1