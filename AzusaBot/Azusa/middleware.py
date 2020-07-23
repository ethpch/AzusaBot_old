# 定义消息发送中间件。
import asyncio
from logging import Logger, getLogger
from datetime import datetime
from typing import Tuple, List, Dict, Callable, Union, Iterable
from functools import wraps
from collections import defaultdict
from aiocqhttp import Event
import nonebot
from nonebot import CommandSession, NoticeSession, RequestSession
from nonebot.typing import CommandName_T
from AzusaBot import config
from Azusa.log import debuglog
from Azusa.exceptions import *
from Azusa.exceptions import _PauseException, _FinishException

BLACKLIST = {
    'user': config.USER_BLACKLIST,
    'group': config.GROUP_BLACKLIST,
    }
BLACKLIST['user'].discard(0)
BLACKLIST['group'].discard(0)

bot = nonebot.get_bot()
_wait_for_maxtime = 30

_cooldown_functions = defaultdict(dict)

def on_command(name: Union[str, CommandName_T],
               *,
               logger: Logger,
               checkfunc: Callable[[CommandSession], bool] = None,
               wait_for: Callable[[], bool] = None,
               cooldown: int = 0,
               use_default_infolog: bool = True,
               aliases: Union[Iterable[str], str] = (),
               permission: int = nonebot.permission.EVERYBODY,
               only_to_me: bool = True,
               privileged: bool = False,
               shell_like: bool = False,
               **kwargs) -> Callable:
    """on_command装饰器。被装饰的函数应当接受两个参数session及bot。
    参数：
        name：命令名称。
        logger：日志器。
        checkfunc：检查是否应该工作的函数。函数执行返回True则执行功能，否则退出。
        wait_for: 等待函数。函数执行返回为True后再执行功能，否则等待1秒直到返回为True。
        cooldown：命令运行后的冷却时间。冷却时间内无法再次运行。
        use_default_infolog：是否使用默认info级别的日志记录。
        aliases：命令别名。
        permission：命令所需权限。
        only_to_me：是否仅响应私聊或者at机器人的指令。
        privileged：是否允许复数次执行。
        shell_like：是否是类shell指令。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(session: CommandSession):
            if session.event['user_id'] in BLACKLIST['user']:
                return
            if session.event['message_type'] == 'group' and session.event['group_id'] in BLACKLIST['group']:
                return
            if checkfunc is not None:
                if not ((await checkfunc(session) if asyncio.iscoroutinefunction(checkfunc) else checkfunc(session))):
                    return
            if wait_for is not None:
                count = 0
                while not ((await wait_for()) if asyncio.iscoroutinefunction(wait_for) else wait_for()):
                    await asyncio.sleep(1)
                    count += 1
                    if count >= _wait_for_maxtime:
                        raise WaitForTimeoutError
            funcname = func.__module__ + '.' + func.__name__
            if funcname in _cooldown_functions[session.self_id].keys():
                return
            try:
                await func(session, bot)
                if use_default_infolog:
                    if session.event['message_type'] == 'group':
                        logger.info(f'<Command> Group {session.event["group_id"]} user {session.event["user_id"]} call {funcname} successfully')
                    else:
                        logger.info(f'<Command> Private user {session.event["user_id"]} call {funcname} successfully')
            except (_PauseException, _FinishException, SwitchException) as e:
                raise e
            except Warning as w:
                logger.warning(f'<Command> Warning {type(w)} occured while {funcname} is running.')
            except (ApiNotAvailable, RetryExhaustedError) as a:
                logger.error(f'<Command> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Command> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Command> Error {type(e)} occured while {funcname} is running.')
            if cooldown > 0:
                if funcname not in _cooldown_functions[session.self_id]:
                    _cooldown_functions[session.self_id][funcname] = cooldown
        return nonebot.on_command(
            name,
            aliases=aliases,
            permission=permission,
            only_to_me=only_to_me,
            privileged=privileged,
            shell_like=shell_like,
            )(debuglog(logger)(wrapper))
    return deco

class CommandGroup(nonebot.CommandGroup):
    """重写command函数，使其响应重载的on_command装饰器。
    """
    def command(self, name: Union[str, CommandName_T], **kwargs) -> Callable:
        sub_name = (name,) if isinstance(name, str) else name
        name = self.basename + sub_name

        final_kwargs = self.base_kwargs.copy()
        final_kwargs.update(kwargs)
        return on_command(name, **final_kwargs)

def on_message(*event,
               logger: Logger,
               checkfunc: Callable[[Event], bool] = None,
               wait_for: Callable[[], bool] = None,
               cooldown: int = 0,
               use_default_infolog: bool = True,
               **kwargs) -> Callable:
    """on_message装饰器。被装饰的函数应当接受两个参数event及bot。
    编写规范：
        被装饰函数应当具有int返回值。返回值含义规定如下：
            0：执行成功，不进行消息操作。
            1：执行成功，进行消息操作。
    参数：
        logger：日志器。
        checkfunc：检查是否应该工作的函数。函数执行返回True则执行功能，否则退出。
        wait_for: 等待函数。函数执行返回为True后再执行功能，否则等待1秒直到返回为True。
        cooldown：命令运行后的冷却时间。冷却时间内无法再次运行。
        use_default_infolog：是否使用默认info级别的日志记录。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(event: Event):
            if event['user_id'] in BLACKLIST['user']:
                return
            if event['message_type'] == 'group' and event['group_id'] in BLACKLIST['group']:
                return
            if checkfunc is not None:
                if not ((await checkfunc(event) if asyncio.iscoroutinefunction(checkfunc) else checkfunc(event))):
                    return
            if wait_for is not None:
                count = 0
                while not ((await wait_for()) if asyncio.iscoroutinefunction(wait_for) else wait_for()):
                    await asyncio.sleep(1)
                    count += 1
                    if count >= _wait_for_maxtime:
                        raise WaitForTimeoutError
            funcname = func.__module__ + '.' + func.__name__
            if funcname in _cooldown_functions[event['self_id']].keys():
                return
            try:
                retcode = await func(event, bot)
                if use_default_infolog and retcode:
                    if event['message_type'] == 'group':
                        logger.info(f'<Message> Group {event["group_id"]} user {event["user_id"]} call {funcname} successfully')
                    else:
                        logger.info(f'<Message> Private user {event["user_id"]} call {funcname} successfully')
            except Warning as w:
                logger.warning(f'<Message> Warning {type(w)} occured while {funcname} is running.')
            except (ApiNotAvailable, RetryExhaustedError) as a:
                logger.error(f'<Message> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Message> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Message> Error {type(e)} occured while {funcname} is running.')
            if cooldown > 0:
                if funcname not in _cooldown_functions[event['self_id']]:
                    _cooldown_functions[event['self_id']][funcname] = cooldown
        return bot.on_message(*event)(debuglog(logger)(wrapper))
    return deco

def on_notice(*event, logger: Logger, use_default_infolog: bool = True, **kwargs) -> Callable:
    """on_notice装饰器。被装饰的函数应当接受两个参数session及bot。
    参数：
        logger：日志器。
        use_default_infolog：是否使用默认info级别的日志记录。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(session: NoticeSession):
            funcname = func.__module__ + '.' + func.__name__
            try:
                await func(session, bot)
                if use_default_infolog:
                    logger.info(f'<Notice> Call function: {funcname}, notice information: {session.event}')
            except Warning as w:
                logger.warning(f'<Notice> Warning {type(w)} occured while {funcname} is running.')
            except ApiNotAvailable as a:
                logger.error(f'<Notice> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Notice> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Notice> Error {type(e)} occured while {funcname} is running.')
        return nonebot.on_notice(*event)(debuglog(logger)(wrapper))
    return deco

def on_request(*event, logger: Logger, use_default_infolog: bool = True, **kwargs) -> Callable:
    """on_request装饰器。被装饰的函数应当接受两个参数session及bot。
    参数：
        logger：日志器。
        use_default_infolog：是否使用默认info级别的日志记录。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(session: RequestSession):
            funcname = func.__module__ + '.' + func.__name__
            try:
                await func(session, bot)
                if use_default_infolog:
                    logger.info(f'<Request> Call function: {funcname}, request information: {session.event}')
            except Warning as w:
                logger.warning(f'<Request> Warning {type(w)} occured while {funcname} is running.')
            except ApiNotAvailable as a:
                logger.error(f'<Request> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Request> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Request> Error {type(e)} occured while {funcname} is running.')
        return nonebot.on_request(*event)(debuglog(logger)(wrapper))
    return deco

def on_websocket_connect(*,
                         logger: Logger,
                         checkfunc: Callable[[CommandSession], bool] = None,
                         wait_for: Callable[[], bool] = None,
                         use_default_infolog: bool = True,
                         **kwargs) -> Callable:
    """on_websocket_connect装饰器。被装饰的函数应当接受两个参数event及bot。
    参数：
        logger：日志器。
        checkfunc：检查是否应该工作的函数。函数执行返回True则执行功能，否则退出。
        wait_for: 等待函数。函数执行返回为True后再执行功能，否则等待1秒直到返回为True。
        use_default_infolog：是否使用默认info级别的日志记录。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(event: Event):
            if checkfunc is not None:
                if not ((await checkfunc(event) if asyncio.iscoroutinefunction(checkfunc) else checkfunc(event))):
                    return
            if wait_for is not None:
                count = 0
                while not ((await wait_for()) if asyncio.iscoroutinefunction(wait_for) else wait_for()):
                    await asyncio.sleep(1)
                    count += 1
                    if count >= _wait_for_maxtime:
                        raise WaitForTimeoutError
            funcname = func.__module__ + '.' + func.__name__
            try:
                await func(event, bot)
                if use_default_infolog:
                    logger.info(f'<Connect> Call function: {funcname}, connect information: {event}')
            except Warning as w:
                logger.warning(f'<Connect> Warning {type(w)} occured while {funcname} is running.')
            except ApiNotAvailable as a:
                logger.error(f'<Connect> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Scheduler> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Connect> Error {type(e)} occured while {funcname} is running.')
        return nonebot.on_websocket_connect(debuglog(logger)(wrapper))
    return deco

def scheduled_job(logger: Logger,
                  trigger: str,
                  *,
                  args: Union[list, tuple]=[bot],
                  kwargs: dict=None,
                  wait_for: Callable[[], bool] = None,
                  use_default_infolog: bool = True,
                  **trigger_args) -> Callable:
    """scheduler.scheduled_job装饰器。被装饰函数接受``args``和``kwargs``内的参数，默认为bot。
    编写规范：
        被装饰函数应当具有int返回值。返回值含义规定如下：
            0：执行成功，不进行有效操作。
            1：执行成功，进行有效操作。
    参数：
        logger：日志器。
        trigger：触发器，可选``date``, ``interval``, ``cron``。
        args：要传递的参数。
        kwargs：要传递的参数。
        wait_for: 等待函数。函数执行返回为True后再执行功能，否则等待1秒直到返回为True。
        use_default_infolog：是否使用默认info级别的日志记录。
        **trigger_args：触发器参数。
    """
    def deco(func) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if wait_for is not None:
                count = 0
                while not ((await wait_for()) if asyncio.iscoroutinefunction(wait_for) else wait_for()):
                    await asyncio.sleep(1)
                    count += 1
                    if count >= _wait_for_maxtime:
                        raise WaitForTimeoutError
            funcname = func.__module__ + '.' + func.__name__
            try:
                retcode = await func(*args, **kwargs)
                if use_default_infolog and retcode:
                    logger.info(f'<Scheduler> Azusa call {funcname} successfully')
            except Warning as w:
                logger.warning(f'<Scheduler> Warning {type(w)} occured while {funcname} is running.')
            except ApiNotAvailable as a:
                logger.error(f'<Scheduler> Error {type(a)} occured while {funcname} is running.')
            except ActionFailed as a:
                logger.error(f'<Scheduler> Error {type(a)} occured while {funcname} is running, retcode = {a.retcode}.')
            except Exception as e:
                logger.exception(f'<Scheduler> Error {type(e)} occured while {funcname} is running.')
        return nonebot.scheduler.scheduled_job(trigger, args, kwargs, **trigger_args)(debuglog(logger)(wrapper))
    return deco

_cooldown_manager_is_running = False
@on_websocket_connect(logger=getLogger('Azusa'),
                      checkfunc=lambda event: not _cooldown_manager_is_running,
                      use_default_infolog=False)
async def CooldownManager(*args, **kwargs):
    global _cooldown_manager_is_running
    _cooldown_manager_is_running = True
    count = 0
    while True:
        if count % 3600 == 0:
            getLogger('Azusa').info(f'<CooldownManager> CooldownManager is already working for {count // 3600} hours.')
        try:
            await asyncio.sleep(1)
            count += 1
        except asyncio.futures.CancelledError:
            pass
        for id in _cooldown_functions.keys():
            will_to_pop = []
            for func in _cooldown_functions[id].keys():
                _cooldown_functions[id][func] -= 1
                if _cooldown_functions[id][func] <= 0:
                    will_to_pop.append(func)
            for func in will_to_pop:
                _cooldown_functions[id].pop(func)
