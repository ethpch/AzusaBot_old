from nonebot.default_config import *

SUPERUSERS = {272386063}
NICKNAME = {'Azusa', '梓', '小梓', '梓酱'}
COMMAND_START = {'', '!', '！'}

# 反向代理地址与端口，与CQHTTP插件配置相对应
HOST = '127.0.0.1'
PORT = 8080

# 生产环境下关闭DEBUG模式可以提高性能
DEBUG = False

# 选择要启用的功能，功能名前加“#”表示禁用
LOAD_MODULES = [
    'chat',
    'pcr',
    'pixiv',
    # 允许单独装载子系统的特定功能，每一级模块或包应当用“.”隔开，例：
    # 'chat.group',
    # 'pcr.battle'
    # 不建议装载子系统后继续装载子系统的子系统。
    ]

# 不响应消息的QQ号
USER_BLACKLIST = {0}
# 不响应消息的群号
GROUP_BLACKLIST = {0}

# 酷Q根目录，即CQA.exe或CQP.exe所在的目录。可选设置。
# Windows需要使用转义'\'， 例如“D:\\path\\to\\coolq”
# Linux使用绝对地址即可，例如“/path/to/coolq”
# docker环境下，仅linux下且仅存在一个coolq客户端时会使用自动查找。
# 建议设置此项。
CQROOT = ''

# Pixiv帐号，现在Pixiv必须登录后使用，OAuth鉴权失败是无法使用的。
PIXIV_USERNAME = ''
PIXIV_PASSWORD = ''
# Pixiv代理地址，中国境内的用户建议按如下提示建立一个cloudflare worker，也可使用自己的境外网站添加一个Javascript进行代理
#Tips: How to create a proxy for Pixiv api? Just comment out all infomation in a CloudFlare worker and throw the following code into it.
#----------------------------
#    addEventListener("fetch", e => {
#        let t = e.request, d = new URL(t.url);
#        d.hostname = (t.url.includes("auth/token") ? "oauth.secure" : "app-api") + ".pixiv.net";
#        e.respondWith(fetch(d, {body: t.body, headers: t.headers, method: t.method}))
#    });
#----------------------------
PIXIV_PROXY_URL = ''
