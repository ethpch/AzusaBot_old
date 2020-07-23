import logging
from ast import literal_eval
from copy import deepcopy
from Azusa.log import debuglog

logger = logging.getLogger('Azusa.pcr')

class boss():
    '''
    此类用于处理所有boss相关的数据。
    主要处理当前boss信息，包括出刀等操作都是针对当前boss，额外负责各种数值检查工作。
    '''
    @debuglog(logger)
    def __init__(self):
        self.__boss = {
            'Round': 1,
            'Stage': 1,
            'Boss': 1,
            'CurrentHP': 6000000,
            }
        self.__stagechange = {1: 1, 2: 4, 3: 11, 4: 100, 5: 1000}
        self.__bossmaxhp = {
            1: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
            2: {1: 6000000, 2: 8000000, 3: 10000000, 4: 12000000, 5: 15000000},
            3: {1: 7000000, 2: 9000000, 3: 12000000, 4: 14000000, 5: 17000000},
            4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }
        self.__saveddata = []

    # 返回所有boss信息
    @property
    @debuglog(logger)
    def boss(self) -> dict:
        return self.__boss

    # 返回所有信息，保存文件用
    @property
    @debuglog(logger)
    def alldata(self) -> dict:
        d = {}
        d['boss'] = self.__boss
        d['stagechange'] = repr(self.__stagechange)
        d['maxhp'] = repr(self.__bossmaxhp)
        return d

    # 设置所有信息，读取文件用
    @alldata.setter
    @debuglog(logger)
    def alldata(self, data: dict):
        self.__boss = data['boss']
        self.__stagechange = literal_eval(data['stagechange'])
        self.__bossmaxhp = literal_eval(data['maxhp'])

    # 初始化信息
    @debuglog(logger)
    def initialize(self):
        self.__boss = {
            'Round': 1,
            'Stage': 1,
            'Boss': 1,
            'CurrentHP': 6000000,
            }
        self.initsaveddata()

    # 重置保存的boss信息列表，防止撤回被滥用
    @debuglog(logger)
    def initsaveddata(self):
        self.__saveddata.clear()

    # 获取最大血量
    @debuglog(logger)
    def getMAXHP(self) -> dict:
        return self.__bossmaxhp

    # 设置最大血量
    @debuglog(logger)
    def setMAXHP(self, stage: int, maxhp: dict) -> bool:
        if stage < 0 or stage > 5 or set(maxhp.keys()) != {1, 2, 3, 4, 5}:
            return False
        self.__bossmaxhp[stage] = maxhp
        return True

    # 设置阶段转换的周目，切换服务器用
    @debuglog(logger)
    def setStageChange(self, d: dict) -> bool:
        for i in d.keys():
            if not isinstance(i, int) or i < 0:
                return False
        self.__stagechange = d
        return True

    # 获取阶段转换的周目
    def getStageChange(self) -> dict:
        return self.__stagechange

    # 攻击，返回值为-1表示伤害值有误，为0表示正常出刀，为1表示为尾刀
    @debuglog(logger)
    def attack(self, dmg: int) -> int:
        if not self.validation(hp = dmg):
            return -1
        self.__saveddata.append(deepcopy(self.__boss))
        self.__boss['CurrentHP'] -= dmg
        if self.__boss['CurrentHP'] <= 0:
            self.__next_boss()
            return 1
        return 0

    # 调整boss信息
    @debuglog(logger)
    def adjust(self, round: int, boss: int, currenthp: int):
        if round < self.__stagechange[2]:
            stage = 1
        elif round < self.__stagechange[3]:
            stage = 2
        elif round < self.__stagechange[4]:
            stage = 3
        elif round < self.__stagechange[5]:
            stage = 4
        else:
            stage = 5
        if not self.validation(stage = stage, boss = boss, hp = currenthp):
            return False
        self.__boss['Round'] = round
        self.__boss['Stage'] = stage
        self.__boss['Boss'] = boss
        self.__boss['CurrentHP'] = currenthp
        return True

    # 回滚操作
    @debuglog(logger)
    def rollback(self) -> bool:
        if self.__saveddata:
            self.__boss = self.__saveddata.pop()
            return True
        return False

    # 下一个boss
    @debuglog(logger)
    def __next_boss(self):
        if self.__boss['Boss'] == 5:
            self.__boss['Boss'] = 1
            self.__boss['Round'] += 1
            if self.__boss['Round'] == self.__stagechange[1]:
                self.__boss['Stage'] = 1
            elif self.__boss['Round'] == self.__stagechange[2]:
                self.__boss['Stage'] = 2
            elif self.__boss['Round'] == self.__stagechange[3]:
                self.__boss['Stage'] = 3
            elif self.__boss['Round'] == self.__stagechange[4]:
                self.__boss['Stage'] = 4
            elif self.__boss['Round'] == self.__stagechange[5]:
                self.__boss['Stage'] = 5
        else:
            self.__boss['Boss'] += 1
        self.__boss['CurrentHP'] = self.__bossmaxhp[self.__boss['Stage']][self.__boss['Boss']]

    # 值验证
    @debuglog(logger)
    def validation(self, stage: int = None, boss: int = None, hp: int = None) -> bool:
        # 基本检查，仅检查失败时返回False
        if stage is not None:
            if stage < 1:
                return False
        if boss is not None:
            if boss < 1 or boss > 5:
                return False
        if hp is not None:
            if hp < 0:
                return False
        # 检查原则：优先检查参数较多的判断
        # 血量上限检查
        if stage and boss and hp:
            return True if hp <= self.__bossmaxhp[stage][boss] else False
        # 伤害值检查
        if hp:
            return True if hp <= self.__boss['CurrentHP'] else False
        # 基本检查成功，无其他检查时返回True
        return True
