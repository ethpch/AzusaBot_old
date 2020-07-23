# AzusaBot应当处理的所有异常
from aiocqhttp.exceptions import ApiNotAvailable, ActionFailed
from nonebot.command import _PauseException, _FinishException, SwitchException
from pixivpy_async.error import PixivError, RetryExhaustedError

# MIDDLEWARE中等待函数超时时引发的异常
class WaitForTimeoutError(Exception):
    pass

# PIXIV插件未找到信息时引发的异常
class InfoNotFoundError(PixivError):
    pass
