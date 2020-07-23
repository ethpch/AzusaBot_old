import logging
from nonebot import permission as perm
from nonebot import Message as M
from Azusa.data import groupdict
from Azusa.middleware import on_command

logger = logging.getLogger('Azusa.pcr')

@on_command('disable_pcr',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('禁用pcr'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def disable_pcr(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pcr']['disable'] = True
    await session.send(M(f'已在群{groupid}禁用pcr模块'))
    logger.info(f'group {groupid} call Azusa.modules.pcr disable_pcr successfully')

@on_command('enable_pcr',
            logger=logger,
            checkfunc=lambda session: session.event['message_type'] == 'group',
            aliases=('启用pcr'),
            permission=perm.GROUP_ADMIN,
            only_to_me=False)
async def enable_pcr(session, bot):
    selfid = session.self_id
    groupid = session.event['group_id']
    groupdict[selfid][groupid]['mods_config']['pcr']['disable'] = False
    await session.send(M(f'已在群{groupid}启用pcr模块'))
    logger.info(f'group {groupid} call Azusa.modules.pcr disable_pcr successfully')
