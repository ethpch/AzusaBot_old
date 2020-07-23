import logging
from ast import literal_eval
from datetime import datetime
from typing import Union
from bidict import namedbidict
from Azusa.log import debuglog
from Azusa.utils import Timer, storage
from Azusa.data import groupdict
from ._boss import boss
from ._player import player

logger = logging.getLogger('Azusa.pcr')

class master():
    @debuglog(logger)
    def __init__(self, botid: int, groupid: int, type: str='tw'):
        self.__botid = botid
        self.__groupid = groupid
        # 处理boss信息
        self.__boss = boss()
        # 处理所有玩家信息
        self.__playerdict = {}
        # 玩家名称与ID对应字典
        IDAndAlias = namedbidict('IDAndAlias', 'ID', 'Alias')
        self.__IDAndAliasDict = IDAndAlias()
        self.reservedname = 'UNDEFINED'
        self.__storage = storage.getStorageObj('pcr')
        self.__is_battle_active = False
        self.__is_current_boss = False
        self.__totaldays = 0
        self.__daypassed = 0
        self.__session = ''
        self.__solutions = {
            1: {0: [], 1: [], 2: [], 3: [], 4: [], 5: []},
            2: {0: [], 1: [], 2: [], 3: [], 4: [], 5: []},
            3: {0: [], 1: [], 2: [], 3: [], 4: [], 5: []},
            4: {0: [], 1: [], 2: [], 3: [], 4: [], 5: []},
            5: {0: [], 1: [], 2: [], 3: [], 4: [], 5: []},
            }
        # 已出刀的信息
        self.__lastattack = []
        # 已出刀数据格式
        #    {
        #    'name': self.reservedname,
        #    'boss': 0,
        #    'stage': 0,
        #    'dmg': 0,
        #    # 记录上一刀状态，实时刀或是漏报刀，0为实时1为漏报
        #    'type': 0,
        #    'playerstate': 0,
        #    'time': 2020-01-01 00:00:00
        #    }
        # 锁
        self.__lock = {
            'status': False,
            'player': self.reservedname,
            }
        # 计时器
        self.__timer = Timer()
        self.__timestamp = []
        # 初始化数据
        if type == 'cn':
            maxhp = {
                1: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                2: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                3: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }
            stagechange = {1: 1, 2: 2, 3: 100, 4: 1000, 5: 10000}
            scorebuff = {
                1: {1: 1, 2: 1, 3: 1.1, 4: 1.1, 5: 1.2,},
                2: {1: 1.2, 2: 1.2, 3: 1.5, 4: 1.7, 5: 2,},
                3: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }
        elif type == 'tw':
            maxhp = {
                1: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                2: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                3: {1: 7000000, 2: 9000000, 3: 13000000, 4: 15000000, 5: 20000000},
                4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }
            stagechange = {1: 1, 2: 4, 3: 11, 4: 1000, 5: 10000}
            scorebuff = {
                1: {1: 1.2, 2: 1.2, 3: 1.3, 4: 1.4, 5: 1.5},
                2: {1: 1.6, 2: 1.6, 3: 1.8, 4: 1.9, 5: 2},
                3: {1: 2, 2: 2, 3: 2.4, 4: 2.4, 5: 2.6},
                4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }
        elif type == 'jp':
            maxhp = {
                1: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                2: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
                3: {1: 7000000, 2: 9000000, 3: 13000000, 4: 15000000, 5: 20000000},
                4: {1: 15000000, 2: 16000000, 3: 18000000, 4: 19000000, 5: 20000000},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                   }
            stagechange = {1: 1, 2: 4, 3: 11, 4: 35, 5: 10000}
            scorebuff = {
                1: {1: 1.2, 2: 1.2, 3: 1.3, 4: 1.4, 5: 1.5},
                2: {1: 1.6, 2: 1.6, 3: 1.8, 4: 1.9, 5: 2},
                3: {1: 2, 2: 2, 3: 2.4, 4: 2.4, 5: 2.6},
                4: {1: 3.5, 2: 3.5, 3: 3.7, 4: 3.8, 5: 4},
                5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }
        else:
            raise ValueError('wrong clan type')
        for k, v in maxhp.items():
            self.__boss.setMAXHP(k, v)
        self.__boss.setStageChange(stagechange)
        for k, v in scorebuff.items():
            player.set_scorebuff(k, v)

    @property
    @debuglog(logger)
    def botid(self) -> int:
        return self.__botid

    # 获取当前会战执行的年月，以10日为每月界限，即当月开启会战的时间最早不早于当月10日
    @staticmethod
    @debuglog(logger)
    def get_session() -> str:
        year = datetime.now().year
        month = datetime.now().month
        day = datetime.now().day
        if day < 10:
            if month == 1:
                year = year - 1
                month = 12
            else:
                month = month - 1
        return f'{year}-{month}'

    # 开启公会战
    @debuglog(logger)
    def callBattleStart(self, totaldays: int=7, daypassed: int=0) -> bool:
        """
        开启公会战。
        参数：
            totaldays：会战总持续时长，默认设置为7
            daypassed：已进行的天数，默认为0（提前一天），若提前两天开启会战则将该值设置为-1，即提前天数相对于1的补数
        """
        if self.__is_battle_active:
            return False
        if daypassed > totaldays:
            return False
        self.__is_battle_active = True
        self.__session = self.get_session()
        self.__totaldays = totaldays
        self.__daypassed = daypassed
        self.callInitAllData()
        self.__is_current_boss = True
        self.__lastattack.clear()
        if not self.__timer.running:
            self.__timer.start()
        self.__timer.reset()
        self.__timestamp = [0]
        for stage in self.__solutions.keys():
            for boss in self.__solutions[stage].keys():
                self.__solutions[stage][boss].clear()
        return True

    # 结束公会战
    @debuglog(logger)
    def callBattleEnd(self) -> bool:
        """
        结束公会战。
        结束时自动保存结算结果。
        """
        if not self.__is_battle_active:
            return False
        self.__is_battle_active = False
        self.callSaveResult()
        if self.__timer.running:
            self.__timer.stop()
        return True

    # 添加玩家
    @debuglog(logger)
    def callAddPlayer(self, id: int, name: str) -> bool:
        """
        添加新玩家进入公会。
        参数：
            id：玩家的QQ号
            name：玩家的昵称
        返回值：
            返回一个bool值，代表添加是否成功
        """
        if self.is_player_exist(id) or self.is_player_exist(name) or name == self.reservedname or self.pnum >= 30:
            return False
        self.__playerdict[id] = player()
        self.__playerdict[id].alias = name
        self.__IDAndAliasDict[id] = name
        return True

    # 删除玩家
    @debuglog(logger)
    def callDelPlayer(self, name: str) -> bool:
        """
        从公会内删除玩家。
        参数：
            name：玩家的昵称
        返回值：
            返回一个bool值，代表删除是否成功
        """
        if self.is_player_exist(name):
            id = self.getID(name)
            self.__playerdict.pop(id)
            self.__IDAndAliasDict.pop(id)
            return True
        return False

    # 查询公会内总人数
    @property
    @debuglog(logger)
    def pnum(self) -> int:
        """
        查询公会内总人数。
        返回值：
            返回一个int值，代表公会内的总人数
        """
        return len(self.__IDAndAliasDict)

    # 设置昵称，即修改玩家昵称
    @debuglog(logger)
    def callSetAlias(self, lastname: str, newname: str) -> bool:
        """
        修改玩家昵称。
        参数：
            lastname：玩家旧昵称
            newname：玩家新昵称
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if not self.is_player_exist(lastname) or self.is_player_exist(newname):
            return False
        self.__playerdict[self.getID(lastname)].alias = newname
        self.__IDAndAliasDict[self.getID(lastname)] = newname
        return True

    # 设置战斗力
    @debuglog(logger)
    def callSetCE(self, name: str, ce: int) -> bool:
        """
        设置玩家战斗力。
        参数：
            name：玩家昵称
            ce：战斗力数值
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if self.is_player_exist(name):
            if self.__playerdict[self.getID(name)].setCE(ce):
                return True
        return False

    # 设置挂树
    @debuglog(logger)
    def callSetSuspension(self, name: str, state: bool) -> bool:
        """
        设置玩家挂树状态。
        参数：
            name：玩家昵称
            state：玩家状态
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if self.is_player_exist(name):
            if self.__playerdict[self.getID(name)].setSuspension(state):
                self.__lock['status'] = False
                self.__lock['id'] = 0
                self.__lock['player'] = self.reservedname
                return True
        return False

    # 设置预约
    @debuglog(logger)
    def callSetOrderedBoss(self, name: str, boss: int) -> bool:
        """
        设置玩家预约boss。
        参数：
            name：玩家昵称
            boss：要预约的boss序号
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if self.is_player_exist(name) and self.__boss.validation(boss = boss):
            if self.__playerdict[self.getID(name)].setOrderedBoss(boss):
                return True
        return False

    # 取消预约
    @debuglog(logger)
    def callCancelOrderedBoss(self, name: str, boss: int) -> bool:
        """
        设置玩家预约boss。
        参数：
            name：玩家昵称
            boss：要取消预约的boss序号
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if self.is_player_exist(name) and self.__boss.validation(boss = boss):
            if self.__playerdict[self.getID(name)].delOrderedBoss(boss):
                return True
        return False

    # 申请出刀
    @debuglog(logger)
    def callSetLock(self, name: str) -> int:
        """
        申请出刀。
        参数:
            name: 玩家昵称
        返回值：
            返回一个int值，意义如下：
                0: 申请成功
                -1: 申请失败，有人已经申请
                -2: 申请失败，玩家无剩余刀
                -3: 申请失败，玩家不存在
        """
        if self.is_player_exist(name):
            if self.__playerdict[self.getID(name)].state['RemainingAttack'] > 0:
                if not self.__lock['status']:
                    self.__lock['status'] = True
                    self.__lock['player'] = name
                    return 0
                else:
                    return -1
            else:
                return -2
        else:
            return -3

    # 攻击boss，出刀
    @debuglog(logger)
    def callAttack(self, name: str, stage: int=None, boss: int=None, dmg: int=0):
        """
        攻击一次boss。
        参数：
            name：玩家昵称
            stage：boss阶段数
            boss：boss序号
            dmg：伤害值
        返回值：
            返回一个int值。意义如下：
                -1：伤害值有误
                -2：玩家当前无刀
                -3：玩家当前正在挂树
                -4: 尚未申请出刀
                -5: 有人正在出刀
                -6: 玩家不存在
                0：出刀成功
                1：出刀成功，且玩家击杀了boss（进入尾刀状态）
                2：出刀成功，且玩家出的是尾刀剩余时间（退出尾刀状态）
                3：出刀成功，且玩家出的是尾刀剩余时间并且击杀了boss（退出尾刀状态）
        """
        if not self.is_player_exist(name):
            return -6
        if self.__is_current_boss == False or (stage and boss and dmg):
            if self.__boss.validation(stage = stage, boss = boss, hp = dmg):
                playerstate = self.__playerdict[self.getID(name)].attack(stage, boss, dmg)
                d = {'name': name, 'stage': stage, 'boss': boss, 'dmg': dmg, 'type': 1, 'playerstate': playerstate, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                self.__lastattack.append(d)
            else:
                return -1
        else:
            # 启用出刀锁请取消注释以下四行，反之请注释以下四行
            #if not self.__lock['status']:
            #    return -4
            #if name != self.__lock['player']:
            #    return -5
            stage = self.__boss.boss['Stage']
            boss = self.__boss.boss['Boss']
            d = {'name': name, 'stage': stage, 'boss': boss, 'dmg': dmg, 'type': 0, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            bossstate = self.__boss.attack(dmg)
            if bossstate == -1:
                return -1
            elif bossstate == 0:
                knockout = [False, 0]
            elif bossstate == 1:
                knockout = [True, boss]
                for v in self.__playerdict.values():
                    v.setSuspension(False)
            playerstate = self.__playerdict[self.getID(name)].attack(stage, boss, dmg, knockout)
            if playerstate < 0:
                self.__boss.rollback()
            else:
                d['playerstate'] = playerstate
                self.__lastattack.append(d)
            if playerstate == 1 or playerstate == 3:
                if self.__timer.running:
                    self.__timer.stop()
                self.__timer.start()
                self.__timestamp.append(self.__timer.elapsed)
        self.__lock['status'] = False
        self.__lock['id'] = 0
        self.__lock['player'] = self.reservedname
        return playerstate

    # 撤回出刀
    @debuglog(logger)
    def callRollback(self) -> bool:
        """
        撤回出刀。
        """
        if self.__lastattack:
            if self.__lastattack[-1]['type'] == 0:
                if self.__playerdict[self.getID(self.__lastattack[-1]['name'])].rollback() and self.__boss.rollback():
                    if self.__lastattack[-1]['playerstate'] == 1 or self.__lastattack[-1]['playerstate'] == 3:
                        self.__timestamp.pop()
                    self.__lastattack.pop()
                    return True
            elif self.__lastattack[-1]['type'] == 1:
                if self.__playerdict[self.getID(self.__lastattack[-1]['name'])].rollback():
                    self.__lastattack.pop()
                    return True
        return False

    # 调整boss状态
    @debuglog(logger)
    def callAdjustBoss(self, round: int, boss: int, currenthp: int) -> bool:
        """
        调整boss状态。
        在有人漏报，误报的情况下使用。
        参数：
            round：boss周数
            boss：boss序号
            currenthp：boss当前血量
        返回值：
            返回一个bool值，代表修改是否成功
        """
        if self.__boss.adjust(round, boss, currenthp):
            self.__is_current_boss = True
            for v in self.__playerdict.values():
                    v.setSuspension(False)
            return True
        return False

    # 设置boss血量最大值
    @debuglog(logger)
    def callSetMAXHP(self, stage: int, boss1: int, boss2: int, boss3: int, boss4: int, boss5: int):
        """
        设置各个阶段boss血量最大值。
        参数：
            stage：需要修改血量上限的boss阶段
            boss1：1号boss的血量上限
            boss2：2号boss的血量上限
            boss3：3号boss的血量上限
            boss4：4号boss的血量上限
            boss5：5号boss的血量上限
        """
        maxhp = {1: boss1, 2: boss2, 3: boss3, 4: boss4, 5: boss5}
        self.__boss.setMAXHP(stage, maxhp)

    # 设置boss分数倍率
    @debuglog(logger)
    def callSetScorebuff(self, stage: int, boss1: int, boss2: int, boss3: int, boss4: int, boss5: int):
        """
        设置各个阶段boss的分数倍率。
        参数：
            stage：需要修改分数倍率的boss阶段
            boss1：1号boss的分数倍率
            boss2：2号boss的分数倍率
            boss3：3号boss的分数倍率
            boss4：4号boss的分数倍率
            boss5：5号boss的分数倍率
        """
        scorebuff = {1: boss1, 2: boss2, 3: boss3, 4: boss4, 5: boss5}
        player.set_scorebuff(stage, scorebuff)

    # 设置boss阶段切换的周目
    @debuglog(logger)
    def callSetStagechange(self, round: list):
        """
        设置boss阶段切换时的周目。
        参数：
            round：一个列表，数据分别为从一周目一阶开始的切换周目，例如“1，4，11，35”将周目切换设定为1周1阶段，4周2阶段，11周3阶段，35周4阶段。
        """
        d = {}
        for i in range(5):
            d[i + 1] = round[i] if i < len(round) else pow(10, i)
        self.__boss.setStageChange(d)

    # 查询正在出刀的玩家
    @property
    @debuglog(logger)
    def callGetLock(self) -> dict:
        return self.__lock

    # 查询玩家记录
    @debuglog(logger)
    def callPlayerRecord(self, name: str) -> dict:
        """
        查询玩家记录。
        返回值：
            返回一个字典，字段说明如下：
                Boss1Score：一王总分
                Boss2Score：二王总分
                Boss3Score：三王总分
                Boss4Score：四王总分
                Boss5Score：五王总分
                TotalScore：总分
                CombatEffectiveness：战斗力
                CombatEffectivenessRise：战斗力提升值
        """
        return self.__playerdict[self.getID(name)].record

    # 查询boss状态
    @property
    @debuglog(logger)
    def boss(self) -> dict:
        """
        查询boss状态。
        返回值：
            返回一个字典，字段说明如下：
                Round：boss周数
                Stage：boss阶段
                Boss：boss序号
                CurrentHP：boss当前血量
        """
        return self.__boss.boss

    # 查询挂树信息
    @property
    @debuglog(logger)
    def suspension(self) -> tuple:
        """
        查询挂树信息。
        返回值：
            返回一个元组，元组内元素为：
                所有挂树的玩家的昵称
        """
        return tuple([v.alias for v in self.__playerdict.values() if v.state['Suspension']])

    # 查询尾刀信息
    @property
    @debuglog(logger)
    def knockout(self) -> tuple:
        """
        查询尾刀信息。
        返回值：
            返回一个元组，元组内元素为：
                由（玩家昵称，尾刀所出的boss）组成的元组
        """
        return tuple([(v.alias, v.state['Knockout'][1]) for v in self.__playerdict.values() if v.state['Knockout'][0]])

    # 查询剩余刀信息
    @debuglog(logger)
    def remainingattack(self, p: Union[int, str]=None) -> tuple:
        """
        查询剩余刀信息。
        参数：
            p：可以为int值也可以为str值，说明如下：
                为int值时：p代表boss序号
                为str值时：p代表玩家昵称
        返回值：
            依据参数的不同，存在三种情况：
                无参数时：返回由所有（玩家昵称，（玩家剩余刀数））组成的元组
                参数为int值时：返回由所有剩余刀数为p的玩家昵称组成的元组
                参数为str值时：返回由昵称为p玩家剩余刀数
        """
        if p is None:
            return tuple([(v.alias, v.state['RemainingAttack']) for v in self.__playerdict.values() if v.state['RemainingAttack'] > 0])
        elif isinstance(p, int):
            return tuple([v.alias for v in self.__playerdict.values() if v.state['RemainingAttack'] == p])
        elif isinstance(p, str):
            return self.__playerdict[self.getID(p)].state['RemainingAttack']

    # 查询已出刀信息
    @debuglog(logger)
    def lastattack(self, name: str=None, index: tuple=(1,), reverse: bool=False) -> tuple:
        """
        查询已出刀信息。
        返回值：
            返回一个字典，字段说明如下：
                name：玩家昵称
                stage：出刀阶段
                boss：boss序号
                dmg：伤害值
                type：出刀类型（0为实时刀，1为补报刀）
                playerstate：出刀信息（0为正常出刀，1为出尾刀，2为尾刀遗留时间，3为遗留时间击破）
                time：出刀时间
        """
        lastattack = self.__lastattack if name is None else [i for i in self.__lastattack if i['name'] == name]
        for i in index:
            if i < 1 or i > len(lastattack):
                raise IndexError
        if reverse:
            if len(index) == 1:
                return lastattack[index[0] - 1:index[0]], len(self.__lastattack)
            elif len(index) == 2:
                return lastattack[index[0] - 1:index[1]], len(self.__lastattack)
        else:
            if len(index) == 1:
                if ~index[0] + 2 >= 0:
                    return lastattack[~index[0] + 1:], len(self.__lastattack)
                else:
                    return lastattack[~index[0] + 1:~index[0] + 2], len(self.__lastattack)
            elif len(index) == 2:
                if ~index[0] + 2 >= 0:
                    return lastattack[~index[1] + 1:], len(lastattack)
                else:
                    return lastattack[~index[1] + 1:~index[0] + 2], len(self.__lastattack)

    # 查询预约刀信息
    @debuglog(logger)
    def orderedboss(self, p: Union[int, str]=None) -> tuple:
        """
        查询预约刀信息。
        参数：
            p：可以为int值也可以为str值，说明如下：
                为int值时：p代表boss序号
                为str值时：p代表玩家昵称
        返回值：
            依据参数的不同，存在三种情况：
                无参数时：返回由所有（玩家昵称，（所有玩家预约的boss））组成的元组
                参数为int值时：返回由所有预约了该boss的玩家昵称组成的元组
                参数为str值时：返回由该玩家预约的所有boss序号组成的元组
        """
        if p is None:
            return tuple([(v.alias, tuple([i for i in v.state['OrderedBoss']])) for v in self.__playerdict.values() if v.state['OrderedBoss']])
        elif isinstance(p, int):
            return tuple([v.alias for v in self.__playerdict.values() if p in v.state['OrderedBoss']])
        elif isinstance(p, str):
            if self.is_player_exist(p):
                return tuple(self.__playerdict[self.getID(p)].state['OrderedBoss'])

    # 查询排行
    @debuglog(logger)
    def rank(self, boss: int=None) -> tuple:
        """
        查询排行信息。
        参数：
            boss：要查询的boss序号
        返回值：
            返回一个元组，依据参数是否存在，有两种情况：
                参数存在时：返回由所有（玩家昵称，玩家对该boss分数）组成的，并且按分数降序排序的元组
                参数不存在时：返回由所有（玩家昵称，玩家总分）组成的，并且按分数降序排序的元组
        """
        if boss is not None:
            if self.__boss.validation(boss=boss):
                return tuple(sorted([(v.alias, v.record[f'Boss{boss}Score']) for v in self.__playerdict.values() if v.record[f'Boss{boss}Score'] > 0], key=lambda i: i[1], reverse=True))
        else:
            return tuple(sorted([(v.alias, v.record['TotalScore']) for v in self.__playerdict.values() if v.record[f'TotalScore'] > 0], key=lambda i: i[1], reverse=True))

    # 查询公会总分
    @property
    @debuglog(logger)
    def clantotalscore(self) -> int:
        """
        查询公会总分。
        返回值：
            返回一个int值，代表公会的总分
        """
        return sum([v.record['TotalScore'] for v in self.__playerdict.values()])

    # 查询会战作业
    @debuglog(logger)
    def callQuerySolutions(self, stage: int=3, boss: int=0) -> tuple:
        """
        查询会战作业。
        参数：
            stage：作业阶段
            boss：作业boss序号
        返回值：
            一个元组，由作业文件名组成
        """
        try:
            return tuple(self.__solutions[stage][boss])
        except KeyError:
            pass

    # 提交会战作业
    @debuglog(logger)
    def callSubmitSolutions(self, stage: int=3, boss: int=0, path: tuple=None) -> bool:
        try:
            if path:
                self.__solutions[stage][boss].extend(path)
            return True
        except KeyError:
            return False

    # 删除会战作业
    @debuglog(logger)
    def callDeleteSolutions(self, path: tuple=None):
        for i in path:
            for stage in self.__solutions.keys():
                for boss in self.__solutions[stage].keys():
                    try:
                        self.__solutions[stage][boss].remove(i)
                    except ValueError:
                        pass

    # 查询所有玩家
    @property
    @debuglog(logger)
    def allplayer(self) -> tuple:
        """
        查询所有玩家。
        返回值：
            返回一个元组，元组由公会内所有玩家的昵称组成
        """
        return tuple([v for v in self.__IDAndAliasDict.values()])

    # 查询会战经过的天数
    @property
    @debuglog(logger)
    def daypassed(self) -> int:
        """
        查询会战经过的天数。
        返回值：
            返回一个int值，代表会战经过的天数
        """
        return self.__daypassed

    # 查询会战总天数
    @property
    @debuglog(logger)
    def totaldays(self) -> int:
        """
        查询会战总天数。
        返回值：
            返回一个int值，代表会战的总天数
        """
        return self.__totaldays

    # 查询会战所有信息
    @property
    @debuglog(logger)
    def battleinfo(self) -> dict:
        """
        查询会战所有信息。
        返回值：
            返回一个字典，字段说明如下：
                session：str，当前会战期数，格式为“XXXX-XX”，分别代表年月
                totaldays：int，会战持续时长
                daypassed：int，会战已进行时长，可能小于1，代表当前为会战前（1-daypassed）天，会战未正式开启
                scorebuff：dict，boss分数倍率的字典
                maxhp：dict，boss血量上限的字典
                stagechange：dict，boss阶段转换的字典
        """
        d = {}
        d['session'] = self.__session
        d['totaldays'] = self.__totaldays
        d['daypassed'] = self.__daypassed
        d['scorebuff'] = {k: v for k, v in player.get_scorebuff().items() if v[1]}
        d['maxhp'] = {k: v for k, v in self.__boss.getMAXHP().items() if v[1]}
        d['stagechange'] = {k: v for k, v in self.__boss.getStageChange().items() if v % 10}
        return d

    # 查询计时器的时间
    @property
    @debuglog(logger)
    def timepassed(self) -> int:
        """
        查询计时器的时间。
        返回值：
            返回一个int值，代表计时器的时间（秒）
        """
        if len(self.__timestamp) >= 2:
            return self.__timestamp[-1] - self.__timestamp[-2]
    
    # 查询是否是当前boss
    @property
    @debuglog(logger)
    def is_current_boss(self) -> bool:
        """
        查询是否是当前boss。
        返回值：
            返回一个bool值，代表是否是当前boss
        """
        return self.__is_current_boss

    # 查询会战是否开启
    @property
    @debuglog(logger)
    def is_battle_active(self) -> bool:
        """
        查询会战是否开启。
        返回值：
            返回一个bool值，代表会战是否开启
        """
        return self.__is_battle_active

    # 重置每日状态
    @debuglog(logger)
    def callInitDaily(self) -> bool:
        """
        重置每日状态。
        返回值：
            会战开启时返回True，否则返回False。
        """
        if not self.is_battle_active:
            return False
        self.__boss.initsaveddata()
        for v in self.__playerdict.values():
            v.initState()
        self.__daypassed += 1
        if self.__daypassed == 1:
            self.callInitAllData()
            if self.__timer.running:
                self.__timer.stop()
            self.__timer.start()
            self.__timer.reset()
            self.__timestamp = [0]
        return True

    # 重置所有记录
    @debuglog(logger)
    def callInitAllData(self):
        """
        重置所有记录，包括boss状态，所有玩家分数，所有玩家状态，不包括设定好的boss血量上限以及boss分数倍率
        """
        self.__boss.initialize()
        for v in self.__playerdict.values():
            v.initState()
            v.initRecord()

    # 重置玩家状态
    @debuglog(logger)
    def callInitState(self, name: str) -> bool:
        """
        重置玩家状态。
        参数：
            name：玩家名称
        返回值：
            返回一个bool值，代表是否重置成功
        """
        if self.is_player_exist(name):
            self.__playerdict[self.getID(name)].initState()
            return True
        return False

    # 保存所有信息，谨慎更改此方法
    @debuglog(logger)
    def callSaveAllData(self):
        """
        保存所有信息到文件。
        """
        d = {}
        d['boss'] = self.__boss.alldata
        d['playerdict'] = {}
        for k, v in self.__playerdict.items():
            d['playerdict'][k] = v.alldata
        d['scorebuff'] = repr(player.get_scorebuff())
        d['is_battle_active'] = self.__is_battle_active
        d['is_current_boss'] = self.__is_current_boss
        d['totaldays'] = self.__totaldays
        d['daypassed'] = self.__daypassed
        d['session'] = self.__session
        d['lastattack'] = self.__lastattack
        d['solutions'] = repr(self.__solutions)
        return self.__storage.save(f'{self.__groupid}_alldata', d)

    # 读取所有信息，谨慎更改此方法
    @debuglog(logger)
    def callLoadAllData(self):
        """
        从文件中读取所有信息。
        """
        d = self.__storage.load(f'{self.__groupid}_alldata')
        self.__boss.alldata = d['boss']
        for k, v in d['playerdict'].items():
            self.__playerdict[int(k)] = player()
            self.__playerdict[int(k)].alldata = v
        scorebuff = literal_eval(d['scorebuff'])
        for k, v in scorebuff.items():
            player.set_scorebuff(k, v)
        IDAndAlias = namedbidict('IDAndAlias', 'ID', 'Alias')
        self.__IDAndAliasDict = IDAndAlias()
        for k, v in self.__playerdict.items():
            self.__IDAndAliasDict[k] = v.alias
        self.__is_battle_active = d['is_battle_active']
        self.__is_current_boss = d['is_current_boss']
        self.__totaldays = d['totaldays']
        self.__daypassed = d['daypassed']
        self.__session = d['session']
        self.__lastattack = d['lastattack']
        self.__solutions = literal_eval(d['solutions'])

    # 保存会战结果
    @debuglog(logger)
    def callSaveResult(self):
        """
        保存会战结果，将输出csv文件。
        """
        d = {}
        for r in self.__playerdict.values():
            d[r.alias] = r.record
        matrix = []
        for i in d.values():
            keys = ['name'] + [k for k in i.keys()]
            break
        matrix.append(keys)
        for k, v in d.items():
            l = [k]
            for i in v.keys():
                for j in keys[1:]:
                    if i == j:
                        l.append(v[i])
            matrix.append(l)
        return self.__storage.save_to_csv(f'{self.__groupid}-Battle-{self.__session}', matrix)

    # 查询玩家ID
    @debuglog(logger)
    def getID(self, name: str) -> int:
        """
        依据昵称查询玩家ID。
        参数：
            name：玩家昵称
        返回值：
            返回一个int值，代表玩家ID
        """
        return self.__IDAndAliasDict.ID_for[name] if self.is_player_exist(name) else None

    # 查询玩家昵称
    @debuglog(logger)
    def getAlias(self, id: int) -> str:
        """
        依据ID查询玩家昵称。
        参数：
            id：玩家ID
        返回值：
            返回一个str值，代表玩家昵称
        """
        return self.__IDAndAliasDict.Alias_for[id] if self.is_player_exist(id) else None

    # 查询玩家是否存在
    @debuglog(logger)
    def is_player_exist(self, param: Union[int, str]) -> bool:
        """
        查询玩家是否存在于公会中。
        参数：
            param：可以为int值也可以为str值，说明如下：
                参数为int值时：param代表玩家ID
                参数为str值时：param代表玩家昵称
        返回值：
            返回一个bool值，代表玩家是否存在于公会中
        """
        return True if param in self.__IDAndAliasDict.keys() or param in self.__IDAndAliasDict.values() else False
