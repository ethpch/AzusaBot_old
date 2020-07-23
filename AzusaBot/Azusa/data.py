# 定义主要数据结构
import logging
import os
import shutil
from collections import defaultdict
from nonebot.command import call_command
from AzusaBot import config
from Azusa.utils import storage
from Azusa.middleware import on_notice, on_websocket_connect

logger = logging.getLogger('Azusa.data')

groupdict = defaultdict(dict)
frienddict = defaultdict(dict)
SIGNAL = {
    'MainQQ': 0,
    'RegisteredQQ': defaultdict(dict),
    'coolq_directory': [config.CQROOT, False] if os.path.exists(os.path.join(config.CQROOT, 'CQA.exe')) \
        or os.path.exists(os.path.join(config.CQROOT, 'CQP.exe')) else ['', False],
    }

# 获取好友与群的详细信息
@on_websocket_connect(logger=logger)
async def data_initialize(event, bot):
    selfid = event['self_id']
    if selfid not in SIGNAL['RegisteredQQ'].keys():
        grouplist = await bot.get_group_list(self_id=selfid)
        for v in grouplist:
            member = await bot.get_group_member_list(self_id=selfid, group_id=v['group_id'])
            groupdict[selfid][v['group_id']] = {
                'member': {item['user_id']: {
                    'nickname': item['nickname'],
                    'card': item['card'],
                    'sex': item['sex'],
                    # 权限设置，群主为3，管理员为2，群员为1
                    'role': 3 if item['role'] == 'owner' else 2 if item['role'] == 'admin' else 1,
                    } for item in member},
                'mods_config': {},
                }
            # 默认启用所有插件
            for k in bot.config.LOAD_MODULES:
                if '.' not in k:
                    groupdict[selfid][v['group_id']]['mods_config'][k] = {
                        'disable': False,
                        }
                else:
                    prefix = k.split('.')[0]
                    groupdict[selfid][v['group_id']]['mods_config'][prefix] = {
                        'disable': False,
                        }
        privatelist = await bot.get_friend_list(self_id=selfid)
        for v in privatelist:
            frienddict[selfid][v['user_id']] = {
                'nickname': v['nickname'],
                'mods_config': {k: {
                    'disable': False,
                    } for k in bot.config.LOAD_MODULES},
                }
        # 设置pixiv插件的配置默认值
        if 'pixiv' in bot.config.LOAD_MODULES:
            for id in groupdict[selfid].keys():
                groupdict[selfid][id]['mods_config']['pixiv']['allowr18'] = False
                groupdict[selfid][id]['mods_config']['pixiv']['allowr18g'] = False
            for id in frienddict[selfid].keys():
                frienddict[selfid][id]['mods_config']['pixiv']['allowr18'] = True
                frienddict[selfid][id]['mods_config']['pixiv']['allowr18g'] = True
        # 尝试读取已保存的信息
        datastorage = storage.getStorageObj('mods_config_data')
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
        # 注册新QQ
        # 将第一个连接的酷Q设置为主要QQ
        if SIGNAL['MainQQ'] == 0:
            SIGNAL['MainQQ'] = selfid
        # 查找本机上的酷Q目录
        version_info = await bot.get_version_info(self_id=selfid)
        if SIGNAL['coolq_directory'][1] == False:
            # 简单校验config配置的CQROOT是否正确（依据coolq版本）
            if (os.path.exists(os.path.join(SIGNAL['coolq_directory'][0], 'CQA.exe')) and version_info['coolq_edition'] == 'air') or \
                (os.path.exists(os.path.join(SIGNAL['coolq_directory'][0], 'CQP.exe')) and version_info['coolq_edition'] == 'pro'):
                SIGNAL['coolq_directory'][1] = True
            else:
                SIGNAL['coolq_directory'] = ['', True]
            # 获取coolq路径
            if SIGNAL['coolq_directory'][0] == '':
                # 利用工作路径与coolq版本判断
                directory = version_info['coolq_directory']
                if (os.path.exists(os.path.join(directory, 'CQA.exe')) and version_info['coolq_edition'] == 'air') or \
                    (os.path.exists(os.path.join(directory, 'CQP.exe')) and version_info['coolq_edition'] == 'pro'):
                    SIGNAL['coolq_directory'][0] = directory
                # 若使用docker容器，则开始查找全系统文件以获取路径
                else:
                    # 仅对linux生效，受限于windows的硬盘分区
                    if os.name == 'posix':
                        paths = []
                        for path, dirs, files in os.walk('/'):
                            if ('CQA.exe' in files and version_info['coolq_edition'] == 'air') or \
                                ('CQP.exe' in files and version_info['coolq_edition'] == 'pro'):
                                paths.append(path)
                        # 本机存在一个coolq客户端时，设置路径
                        if len(paths) == 1:
                            SIGNAL['coolq_directory'][0] = paths[0]
                    # 其他情况下路径设置为空 ``''``
            # 冻结目录设置
            SIGNAL['coolq_directory'] = tuple(SIGNAL['coolq_directory'])
        SIGNAL['RegisteredQQ'][selfid] = {'coolq_edition': version_info['coolq_edition']}
        for superuser in bot.config.SUPERUSERS:
            await bot.send_private_msg(self_id=selfid, user_id=superuser, message='Azusa初始化成功')

# 更新详细信息
@on_notice('group_admin', 'group_decrease', 'group_increase', logger=logger)
async def data_update(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    member = await bot.get_group_member_list(self_id=selfid, group_id=groupid, no_cache=True)
    if groupid not in groupdict[selfid].keys():
        groupdict[selfid][groupid] = {}
    groupdict[selfid][groupid].update({
        'member': {item['user_id']: {
                'nickname': item['nickname'],
                'card': item['card'],
                'sex': item['sex'],
                'role': 3 if item['role'] == 'owner' else 2 if item['role'] == 'admin' else 1,
                } for item in member},
        })
    if 'mods_config' not in groupdict[selfid][groupid].keys():
        groupdict[selfid][groupid]['mods_config'] = {}
        for k in bot.config.LOAD_MODULES:
            if '.' not in k:
                groupdict[selfid][groupid]['mods_config'][k] = {
                    'disable': False,
                    }
            else:
                prefix = k.split('.')[0]
                groupdict[selfid][groupid]['mods_config'][prefix] = {
                    'disable': False,
                    }
        if 'pixiv' in bot.config.LOAD_MODULES:
            groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18'] = False
            groupdict[selfid][groupid]['mods_config']['pixiv']['allowr18g'] = False

# 释放资源
_is_resource_delivered = False
@on_websocket_connect(logger=logger,
                      checkfunc=lambda event: not _is_resource_delivered,
                      wait_for=lambda : SIGNAL['coolq_directory'][1] == True)
async def deliver_resource(event, bot):
    global _is_resource_deliver
    _is_resource_deliver = True
    _src = os.path.join(os.path.dirname(__file__), 'resources')
    _dst = os.path.join(SIGNAL['coolq_directory'][0], 'data', 'image')
    try:
        if not os.path.exists(_dst):
            os.mkdir(_dst)
        for path, dirs, files in os.walk(_src):
            for dir in dirs:
                if not os.path.exists(os.path.join(path.replace(_src, _dst), dir)):
                    os.mkdir(os.path.join(path.replace(_src, _dst), dir))
            for file in files:
                fullpath = os.path.join(path, file)
                target = fullpath.replace(_src, _dst)
                if not os.path.exists(target):
                    shutil.copyfile(fullpath, target)
    except FileNotFoundError as e:
        logger.exception('directory error')