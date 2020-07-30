# AzusaBot_old
旧AzusaBot项目。停止维护。

旧版缺陷：
> 使用内存存放所有数据，利用json做数据持久化。<br>
> 功能与QQ机器人框架`nonebot`强耦合，不能脱离其单独执行功能，丧失了接入其他机器人框架的可能性。<br>

新版计划：
> 完备的数据库支持。<br>
> 调整项目结构，让底层功能独立出来，机器人框架仅负责数据的发送与接收，从而使方便地接入其他机器人框架成为可能。<br>

## 简介
使用 [nonebot](https://github.com/nonebot/nonebot) 框架搭建的QQ机器人。

## 已实现的功能
> ### chat.group 群聊相关功能
>> 在群聊中探索吧<br>
> ### pcr.battle 公主连结公会战管理
>> #### 优点
>> Azusa的出刀仅有一个指令`出刀`，它能够自动统计尾刀与遗留时间刀，也提供撤回功能防止误报。<br>
>> 详尽的查询功能，查分（自己或他人），查排行（总分或单个boss分数），查boss状态，查挂树，查预约/剩余刀（有不同的模式，根据需要提供对应的参数），查已出刀的信息（有不同的模式，根据需要提供对应的参数）<br>
>> `作业`功能可以做到针对单个boss提交作业图片，也可以针对某一个阶段的全boss作业进行提交（感谢海雾鸽友会），同时提供对应的作业查询功能（有些许bug，疑似时间过长会失去缓存导致丢失个别作业图片，发生概率较低）<br>
>> `开始公会战` `设置最大血量` `设置分数倍率` `设置阶段转换`功能使得无须重启机器人就可以改变下一期会战参数，一次部署永久可用。<br>
>> 自动统计分数，1到5号boss分数以及总分均会统计，也可以统计战斗力。（分数统计使用公式“伤害*分数倍率”进行四舍五入后得到结果，会存在个位数的误差，没搞懂pcr到底怎么计算的）
>> #### 缺点
>> Azusa的会战管理要求精确到个位地汇报伤害。需要绝对的精确（撞刀时以机器人统计的剩余血量为准，pcr也是这么统计的），否则血量统计会出问题。可以使用`查询已出刀信息`指令来查找最近的出刀信息，与游戏内进行比对。<br>
>> #### 其他提示
>> 掉刀时伤害为0。<br>
>> 撞刀时以机器人统计的剩余血量为准，pcr也是这么统计的。<br>
>> 群友装死鱼拒不加入公会暂时无法处理。加入后可以使用`出刀`指令的第二模式为其代报。<br>
>> 下次公会战开启时，发生了人员变动，且前人未退会时，可以使用`查询昵称`功能与`解除注册`功能配合使其从公会中删除。<br>
>> 善用`会战帮助`。<br>
> ### pixiv P站相关功能
>> 权限控制，R18与R18G过滤器<br>
>> 详细的参数设置，指定类型、收藏数的搜索<br>

## 部署
假设你已经具有一定的代码基础，能够参阅文档自行安装环境，能够自行配置虚拟环境与安装依赖。<br>
本项目基于python3.7，3.7及以上版本可以使用。
> - 参考[cqhttp的安装文档](https://cqhttp.cc/docs/4.15/#/)安装好酷Q与cqhttp插件，首次运行酷Q。
> - 参考[cqhttp的配置文档](https://cqhttp.cc/docs/4.15/#/Configuration)配置好所需的信息。举例：
>> ```
>> {
>>   "$schema": "https://cqhttp.cc/config-schema.json",
>>   "ws_reverse_url": "ws://127.0.0.1:8080/ws/",
>>   "ws_reverse_reconnect_interval": 3000,
>>   "ws_reverse_reconnect_on_code_1000": true,
>>   "use_ws_reverse": true,
>>   "post_message_format": "string",
>>   "update_source": "global",
>>   "update_channel": "stable",
>>   "show_log_console": true,
>>   "log_level": "info"
>> }
>> ```
>> Docker环境下部署应当将`ws_reverse_url`的值修改为`ws://172.17.0.1:8080/ws/`
> - 使用git下载本项目<br>
> `git clone https://github.com/ethpch/AzusaBot_old.git`
> - 修改配置文件`AzusaBot/config_example.py`，尤其注意`HOST` `PORT`的值应当与cqhttp插件配置对应。特殊的，`HOST`可以配置`0.0.0.0`监听所有来源。修改完成后，将`config_example.py`改名为`config.py`。<br>
> - 创建虚拟环境并激活，下载依赖<br>
> ```
> virtualenv venv --python=python3.7
> source venv/bin/activate
> cd AzusaBot
> pip install -r requirements.txt
> ```
> - 运行Azusa<br>
> `python AzusaBot.py`

### 基本功能
> `echo` 手动复读<br>
> `dice` 骰子，骰点范围 1-100 ，群聊中 @其他人 可一起骰点<br>
> `查询插件状态` 查询当前的插件启用状态，对用户私聊与群聊有不同的表现。<br>
>> #### 以下功能为超级用户可以执行
>> `test`打印测试信息<br>
>> `datasave`保存所有数据<br>
>> `dataload`读取所有数据<br>
>> `resetmain`重置主要QQ，用于主QQ被封禁时，不需要重启机器人即可重新设置主QQ。<del>被封过很多次了，色图真好看，下次还敢</del> 必须要使用同一个酷Q客户端登录将要重置的主QQ<br>
>> `添加到用户黑名单 10000`将用户`10000`添加到用户黑名单<br>
>> `添加到群黑名单 10000`将群`10000`添加到群黑名单<br>
>> `删除用户黑名单 10000`将用户`10000`从用户黑名单删除<br>
>> `删除群黑名单 10000`将群`10000`从用户黑名单删除<br>
>> `查询黑名单`查询所有的黑名单信息<br>
>> `_exit`保存所有信息并退出机器人<br>

### 公主连结会战管理相关
#### 本机器人的会战管理思路为“出一刀报一刀”，要求精确伤害值，从而使提交伤害无需其他指令，尾刀等会由机器人自动管理。（特殊的，掉刀即0伤害）
工作流程：
> `会战帮助`查询帮助指令<br>
> 群主`@Bot 创建公会`将当前群注册为一个公会<br>
> `注册`加入当前群的公会<br>
> 管理员`@Bot 开始公会战`初始化一个公会战<br>
> `刀 123456`输出123456伤害，即报伤害123456<br>
> `（取消）预约 2`（取消）预约2号boss<br>
> `挂（下）树`挂（下）树<br>
> `查询boss`查询当前boss状态<br>
> `查询挂树`查询挂树的玩家<br>
> `查询剩余刀`查询所有未出完刀的玩家（依据参数不同会有不同的结果，查看全部功能）<br>
> `查询预约`查询所有预约（依据参数不同会有不同的结果，查看全部功能）<br>
> `作业`会战作业系统，查看全部功能<br>

全部功能：
> `会战帮助`查询帮助指令。<br>
> `@Bot创建公会 台服` 群主可执行。以台服数据初始化一个公会。具体数据可以在会战中修改。<br>
> `@Bot删除公会` 群主可执行。删除当前群注册公会。<br>
> `@Bot开始公会战 6 0` 群主及管理员可执行。以数据“总天数6天”“当前为会战前1天”为参数来初始化一个会战。默认值为 `7` `0`，即“总天数7天”“当前为会战前1天”。其他例子：`5` `-1`即“总天数5天”“当前为会战前2天”。<br>
> `@Bot结束公会战` 群主及管理员可执行。结束当前公会战，在项目根目录的`Azusa/data/pcr`文件夹下保存公会战分数统计的csv文件（可使用excel转为xlsx文件）。<br>
>
> `注册 PlayerA` 以PlayerA为昵称加入当前群注册公会。默认值为当前群名片。<br>
>> #### 如无特殊说明，以下功能所有第一个参数为`PlayerA`（玩家昵称）的命令默认值均为自己的昵称（即修改自己）。
>> `解除注册 PlayerA` 将昵称PlayerA的玩家退会。默认值为自己的昵称（`解除注册`将自己退会）。<br>
>> `改名 PlayerA PlayerB`将昵称PlayerA的玩家改名为PlayerB。<br>
>> `查分 PlayerA`查询昵称PlayerA的玩家的分数。<br>
>> `查询排行 1`查询1号boss的分数排行。无参数为查询总分排行（`查询排行`查询总分排行）。<br>
>> `修改战斗力 PlayerA 5`将昵称PlayerA的玩家的战斗力修改为5。<br>
>> `查询昵称 10000`查询QQ号为10000的玩家的昵称。<br>
>> `查询ID PlayerA`查询昵称为PlayerA的玩家的QQ号。<br>
>> `查询所有玩家`查询当前公会中的所有玩家昵称。<br>
>>
>> `出刀`依据参数不同，共有四种模式。
>>> `出刀 123456`自己对boss造成123456点伤害。<br>
>>> `出刀 PlayerA 123456`PlayerA对boss造成123456点伤害（为PlayerA代报）。<br>
>>> `出刀 3 4 123456`自己对3阶段的4号boss造成123456点伤害（漏报刀，不对当前boss产生影响）。<br>
>>> `出刀 PlayerA 3 4 123456`PlayerA对3阶段的4号boss造成123456点伤害（为PlayerA代报漏报刀）。<br>
>>>
>> `申请出刀 PlayerA`为昵称PlayerA的玩家申请出刀。启用此功能需要取消[这里](AzusaBot/Azusa/modules/pcr/battle/_master.py#L373-L376)的注释，否则不会阻止其他人申请出刀。<br>
>> `预约 PlayerA 2`为昵称为PlayerA的玩家预约2号boss。<br>
>> `取消预约 PlayerA 2`为昵称为PlayerA的玩家取消预约2号boss。<br>
>> `挂树 PlayerA`使昵称为PlayerA的玩家挂树。<br>
>> `下树 PlayerA`使昵称为PlayerA的玩家下树。<br>
>> `重置状态 PlayerA`仅管理员可执行，重置昵称PlayerA的玩家的状态（刀数，预约，挂树，尾刀）<br>
>> `调整boss 18 3 9000000`将当前boss调整为18周目，3号boss，9000000当前血量。<br>
>> `boss信息不正确`将当前boss信息设置为过时。仅能使用`出刀`的三参数与四参数模式。应当尽快使用`调整boss`更新boss信息。<br>
>> `设置最大血量 3 7000000 9000000 12000000 15000000 20000000`将3阶段的boss的最大血量分别设置为700w，900w，1200w，1500w，2000w。用于调整初始化参数。<br>
>> `设置分数倍率 3 2 2 2.4 2.4 2.6`将3阶段的boss的分数倍率分别设置为2，2，2.4，2.4，2.6。用于调整初始化参数。<br>
>> `设置阶段转换 1 4 11 35`将阶段转换的周数设置为1，4，11，35，即1周目进入1阶段，4周目进入2阶段，11周目进入3阶段，35周目进入4阶段。<br>
>> `@Bot撤回出刀`撤回上一刀。<br>
>> `查询已出刀信息`依据参数不同，共有4种模式。
>>> `查询已出刀信息 3`查询倒序第3刀的信息（X）。<br>
>>> `查询已出刀信息 1-3`查询倒序第1刀到倒序第3刀的信息（X-Y）。<br>
>>> `查询已出刀信息 正序 5`查询正序第5刀的信息（正序）。<br>
>>> `查询已出刀信息 3 PlayerA`查询昵称PlayerA的玩家倒序第3刀的信息（X Player）。<br>
>>>
>> `查询boss`查询boss信息。<br>
>> `查询挂树`查询挂树信息。<br>
>> `查询剩余刀`依据参数不同，共有3种模式。
>>> `查询剩余刀`查询所有的剩余刀信息。<br>
>>> `查询剩余刀 3`查询剩余3刀的玩家。<br>
>>> `查询剩余刀 PlayerA`查询昵称PlayerA的玩家剩余刀。<br>
>>>
>> `查询预约`依据参数不同，共有3种模式，类似于`查询剩余刀`。<br>
>> `查询公会总分`查询公会总分。<br>
>> `查询会战详细信息`查询当前会战详细信息，包括“期数”，“总时长”，“已进行天数”，“分数倍率信息”，“血量上限信息”，“阶段转换信息”。<br>
>> `作业`依据第一个参数的不同，共有3种模式。
>>> `作业 查询 3 1`查询3阶段1号boss的作业。特殊的，无boss序号参数时为全boss作业。<br>
>>> `作业 提交 3 1 [图片]`提交`[图片]`为3阶段1号boss的作业。特殊的，无boss序号参数时为全boss作业。<br>
>>> `作业 删除 [图片]`删除`[图片]`的作业。<br>
>>>
>>
>> `保存会战信息`仅超级用户可以使用，保存当前所有的会战信息。
>> `读取会战信息`仅超级用户可以使用，在会战未开启（已注册公会）时读取当前群保存的会战信息。
已知其他小bug：
> 尚未考虑国台日服时差区别，若要管理日服，应当在[这里](AzusaBot/Azusa/modules/pcr/battle/command.py#L1341) [这里](AzusaBot/Azusa/modules/pcr/battle/command.py#L1367) 以及[这里](AzusaBot/Azusa/modules/pcr/battle/command.py#L1393)的时间`hour`参数调整为正确的时间。新版本将会修正这个bug。

### pixiv相关
需要酷Q客户端为酷Q PRO，否则仅有文字信息。<br>
全部功能：
> `pixiv帮助`查询帮助指令。<br>
> `允许R18`仅管理员可执行，在当前群取消R18过滤器。<br>
> `禁止R18`仅管理员可执行，在当前群开启R18过滤器（默认开启）。<br>
> `允许R18G`群内仅管理员可执行，在当前群取消R18G过滤器。用户可单独执行，为当前用户取消R18G过滤器。在R18开启后才会生效。<br>
> `禁止R18G`仅管理员可执行，在当前群开启R18G过滤器（默认开启）。用户可单独执行，为当前用户启用R18G过滤器（默认开启）<br>
> `PID搜索评论区 12345678`搜索PID`12345678`的图片的评论区。<br>
> `UID搜索 12345678`搜索UID`12345678`用户的所有信息。<br>
> `UID搜索关注 12345678`搜索UID`12345678`用户的关注用户。<br>
> `UID搜索好P友 12345678`搜索UID`12345678`用户的好P友。<br>
> `用户搜索 关键词`以`关键词`为关键词搜索用户。<br>
> #### 如无特殊说明，以下功能均受到R18过滤器与R18G过滤器管制。
>> `PID搜索 12345678`搜索PID`12345678`的图片全部信息。R18与R18G过滤器生效时，将不输出R18与R18G图片，仅输出信息。<br>
>> #### 如无特殊说明，以下功能均含有`多图` `原图` `收藏x` `页x` `类型`五个参数，分别可以指定搜索一个PID下的所有图片，图片的原图，收藏数`x`以上的图片，第`x`页分页，作品类型（插画，漫画，全部）
>> `PID搜索相关 12345678`搜索PID`12345678`图片相关的所有图片。<br>
>> `PIXIV推荐`搜索推荐。<br>
>> #### 特别提醒：请如同使用P站搜索框那样使用搜索功能。例如，“-关键词”效果为排除该关键词的图片。同时，应当多加使用`收藏x`参数，否则会搜索到质量很差的图片。
>> `标签搜索 关键词`以关键词`关键词`进行模糊标签搜索，多关键词使用空格分离。<br>
>> `精确标签搜索 关键词`以关键词`关键词`进行精确标签搜索。不支持多关键词。<br>
>> `标题搜索 关键词`以关键词`关键词`进行标题搜索，多关键词使用空格分离。<br>
>> `UID搜索作品 12345678`搜索UID`12345678`用户的所有作品。<br>
>> `UID搜索收藏 12345678`搜索UID`12345678`用户的收藏作品。<br>
>> #### 榜单系列，如无特殊说明，以下功能额外含有一个`xxxx-xx-xx`日期参数，指定以`xxxx-xx-xx`日期开始搜索（例：2020-01-01）。
>>> `P站日榜`<br>
>>> `P站周榜`<br>
>>> `P站月榜`<br>
>>> `P站男性向日榜`<br>
>>> `P站女性向日榜`<br>
>>> `P站原创周榜`<br>
>>> `P站新人周榜`<br>
>>> `P站R18日榜`<br>
>>> `P站R18男性向日榜`<br>
>>> `P站R18女性向日榜`<br>
>>> `P站R18周榜`<br>
>>> `P站R18G周榜`<br>
>>> `P站漫画日榜`<br>
>>> `P站漫画周榜`<br>
>>> `P站漫画月榜`<br>
>>> `P站新人漫画周榜`<br>
>>> `P站R18漫画日榜`<br>
>>> `P站R18漫画周榜`<br>
>>> `P站R18G漫画周榜`<br>
>
> `PIXIV本地统计`统计图库中已下载图片的所有信息。带参数“详细”（`PIXIV本地统计 详细`）将统计图库所有信息。<br>
> `清理P站图片缓存`清空所有的图片缓存。<br>


### 友情链接
本人在pcr台服，去年9月入坑，在第一个公会呆到现在，说好的摸鱼公会几个月前摸着摸着进700了<del>现在都在300了</del>，那时候会长说要弄个机器人管理会战，不然总是撞刀，会长整天处理出刀顺序还有结束后副会抄分。找了点资料（yobot和hoshino）发现都不太符合咱们的需求，遂决定自己手撸一个能统分，查状态<del>以及其他会长指定功能</del>的机器人。<br>
自己仍在努力学习python，这里尤其感谢HoshinoBot在部分代码与架构方面给予的灵感。<br>
[yobot](https://github.com/pcrbot/yobot)<br>
[HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot)<br>

开源库nonebot，它是机器人框架。<br>
[nonebot](https://github.com/nonebot/nonebot)<br>
开源库pixivpy-async，它是pixiv模块的基本依赖。<br>
[pixivpy-async](https://github.com/Mikubill/pixivpy-async)<br>
