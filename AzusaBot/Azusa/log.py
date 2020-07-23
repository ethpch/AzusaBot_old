# 定义日志系统。
import os
import logging
import functools
import asyncio
from AzusaBot import config

if not os.path.exists(os.path.join(os.path.dirname(__file__), 'log')):
    os.mkdir(os.path.join(os.path.dirname(__file__), 'log'))

def initLogConf():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard':  {
                'format': '%(asctime)s|%(name)s|%(levelname)s: %(message)s',
                },
            },
        'filters': {
            'standard': {
                '()': azusafilter,
                },
            },
        'handlers': {
            'default_handler': {
                'level': 'DEBUG',
                'formatter': 'standard',
                'filters': ['standard'],
                'class': 'logging.StreamHandler',
                },
            'debug_handler': {
                'level': 'DEBUG',
                'formatter': 'standard',
                'filters': ['standard'],
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 4,
                'filename': os.path.join(os.path.dirname(__file__), 'log', 'debug.log'),
                'encoding': 'utf-8',
                },
            'info_handler': {
                'level': 'INFO',
                'formatter': 'standard',
                'filters': ['standard'],
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 4,
                'filename': os.path.join(os.path.dirname(__file__), 'log', 'info.log'),
                'encoding': 'utf-8',
                },
            'warn_handler': {
                'level': 'WARN',
                'formatter': 'standard',
                'filters': ['standard'],
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 4,
                'filename': os.path.join(os.path.dirname(__file__), 'log', 'warnning.log'),
                'encoding': 'utf-8',
                },
            'error_handler': {
                'level': 'ERROR',
                'formatter': 'standard',
                'filters': ['standard'],
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 4,
                'filename': os.path.join(os.path.dirname(__file__), 'log', 'error.log'),
                'encoding': 'utf-8',
                },
            },
        'loggers': {
            'nonebot': {
                'handlers': ['default_handler', 'warn_handler', 'error_handler'],
                'level': 'DEBUG' if config.DEBUG else 'INFO',
                'propagate': False,
                },
            'Azusa': {
                'handlers': ['debug_handler', 'info_handler', 'warn_handler', 'error_handler'],
                'level': 'DEBUG' if config.DEBUG else 'INFO',
                }
            },
        })

class azusafilter(logging.Filter):
    def filter(self, record):
        return True if 'Azusa' in record.name or 'nonebot' in record.name else False

# debug日志的装饰器，监视程序运行顺序
def debuglog(logger: logging.Logger):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                logger.debug(f'function {func.__module__}.{func.__name__} start, with parameters tuple{args} and dict{kwargs}.')
                res = await func(*args, **kwargs)
                logger.debug(f'function {func.__module__}.{func.__name__} end.')
                return res
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                logger.debug(f'function {func.__module__}.{func.__name__} start, with parameters tuple{args} and dict{kwargs}.')
                res = func(*args, **kwargs)
                logger.debug(f'function {func.__module__}.{func.__name__} end.')
                return res
        return wrapper
    return decorator
