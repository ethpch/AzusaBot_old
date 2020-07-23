import logging
from nonebot import permission as perm
from nonebot import Message as M
from Azusa.data import groupdict
from Azusa.middleware import on_command

logger = logging.getLogger('Azusa.chat')

@on_command('disable_chat',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('禁用chat'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def disable_chat(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['chat']['disable'] = True
    await session.send(M(f'已在群{groupid}禁用chat模块'))
    logger.info(f'group {groupid} call Azusa.modules.chat disable_chat successfully')

@on_command('enable_chat',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('启用chat'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def enable_chat(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['chat']['disable'] = False
    await session.send(M(f'已在群{groupid}启用chat模块'))
    logger.info(f'group {groupid} call Azusa.modules.chat disable_chat successfully')
