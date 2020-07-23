from os import path, sep
import logging
import nonebot

from Azusa.log import initLogConf


def init(config) -> nonebot.NoneBot:
    nonebot.init(config)
    initLogConf()
    logging.getLogger('Azusa').info('<Init> Azusa initializes successfully.')
    bot = nonebot.get_bot()
    bot.config.resources = path.join(path.dirname(__file__), 'resources')
    import Azusa.common
    import Azusa.data
    for mod in config.LOAD_MODULES:
        if '.' in mod:
            t = sep.join(mod.split('.'))
        else:
            t = mod
        nonebot.load_plugins(
            path.join(path.dirname(__file__), 'modules', t),
            f'Azusa.modules.{mod}'
            )
    return bot
