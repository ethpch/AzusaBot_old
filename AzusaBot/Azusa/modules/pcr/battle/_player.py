import logging
from copy import deepcopy
from Azusa.log import debuglog

logger = logging.getLogger('Azusa.pcr')

class player():
    """
    此类用于处理所有单个玩家相关的数据。
    """
    
    __scorebuff = {
        1: {1: 1.2, 2: 1.2, 3: 1.3, 4: 1.4, 5: 1.5,},
        2: {1: 1.6, 2: 1.6, 3: 1.8, 4: 1.9, 5: 2,},
        3: {1: 2, 2: 2, 3: 2.4, 4: 2.4, 5: 2.6,},
        4: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        5: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        }

    @debuglog(logger)
    def __init__(self):
        self.__player ={
            "Alias": "",
            "Damage": {
                "Stage1": {
                    "Boss1": 0,
                    "Boss2": 0,
                    "Boss3": 0,
                    "Boss4": 0,
                    "Boss5": 0,
                    "Total": 0,
                    },
                "Stage2": {
                    "Boss1": 0,
                    "Boss2": 0,
                    "Boss3": 0,
                    "Boss4": 0,
                    "Boss5": 0,
                    "Total": 0,
                    },
                "Stage3": {
                    "Boss1": 0,
                    "Boss2": 0,
                    "Boss3": 0,
                    "Boss4": 0,
                    "Boss5": 0,
                    "Total": 0,
                    },
                "Stage4": {
                    "Boss1": 0,
                    "Boss2": 0,
                    "Boss3": 0,
                    "Boss4": 0,
                    "Boss5": 0,
                    "Total": 0,
                    },
                'Stage5': {
                    "Boss1": 0,
                    "Boss2": 0,
                    "Boss3": 0,
                    "Boss4": 0,
                    "Boss5": 0,
                    "Total": 0,
                    },
                },
            "Score": {
                "Boss1": 0,
                "Boss2": 0,
                "Boss3": 0,
                "Boss4": 0,
                "Boss5": 0,
                "Total": 0,
                },
            "CombatEffectiveness": 0,
            "CombatEffectivenessRise": 0,
            "RemainingAttack": 3,
            "Suspension": False,
            "Knockout": [False, 0],
            "OrderedBoss": [],
            }
        self.__saveddata = []

    # 获取分数倍率
    @classmethod
    @debuglog(logger)
    def get_scorebuff(cls) -> dict:
        return cls.__scorebuff

    # 设置分数倍率
    @classmethod
    @debuglog(logger)
    def set_scorebuff(cls, stage: int, buff: dict) -> bool:
        if stage < 0 or stage > 5 or set(buff.keys()) != {1, 2, 3, 4, 5}:
            return False
        cls.__scorebuff[stage] = buff
        return True

    # 获取别名
    @property
    @debuglog(logger)
    def alias(self) -> str:
        return self.__player['Alias']

    # 设置别名
    @alias.setter
    @debuglog(logger)
    def alias(self, name: str):
        self.__player['Alias'] = name

    # 获取分数记录
    @property
    @debuglog(logger)
    def record(self) -> dict:
        d = {
            'Boss1Score': self.__player['Score']['Boss1'],
            'Boss2Score': self.__player['Score']['Boss2'],
            'Boss3Score': self.__player['Score']['Boss3'],
            'Boss4Score': self.__player['Score']['Boss4'],
            'Boss5Score': self.__player['Score']['Boss5'],
            'TotalScore': self.__player['Score']['Total'],
            'CombatEffectiveness': self.__player['CombatEffectiveness'],
            'CombatEffectivenessRise': self.__player['CombatEffectivenessRise'],
            }
        return d

    # 获取状态记录
    @property
    @debuglog(logger)
    def state(self) -> dict:
        d = {
            'RemainingAttack': self.__player['RemainingAttack'],
            'Suspension': self.__player['Suspension'],
            'Knockout': self.__player['Knockout'],
            'OrderedBoss': self.__player['OrderedBoss'],
            }
        return d

    # 获取所有属性，保存全部记录用
    @property
    @debuglog(logger)
    def alldata(self) -> dict:
        return self.__player

    # 设置所有属性，读取全部记录用
    @alldata.setter
    @debuglog(logger)
    def alldata(self, data: dict):
        self.__player = data

    # 设置战斗力
    @debuglog(logger)
    def setCE(self, ce: int) -> bool:
        if ce < self.__player['CombatEffectiveness']:
            return False
        self.__player['CombatEffectivenessRise'] = ce - self.__player['CombatEffectiveness']
        self.__player['CombatEffectiveness'] = ce
        return True

    # 设置挂树
    @debuglog(logger)
    def setSuspension(self, state: bool) -> bool:
        if state != self.__player['Suspension'] and self.__player['RemainingAttack'] > 0:
            self.__player['Suspension'] = state
            return True
        return False

    # 设置尾刀状态
    @debuglog(logger)
    def setKnockout(self, knockout: list):
        self.__player['Knockout'] = knockout

    # 设置预约boss
    @debuglog(logger)
    def setOrderedBoss(self, boss: int) -> bool:
        if len(self.__player['OrderedBoss']) < self.__player['RemainingAttack'] and boss not in self.__player['OrderedBoss']:
            self.__player['OrderedBoss'].append(boss)
            return True
        return False

    # 删除预约boss
    @debuglog(logger)
    def delOrderedBoss(self, boss: int) -> bool:
        try:
            self.__player['OrderedBoss'].remove(boss)
            return True
        except ValueError:
            return False

    # 重置分数记录
    @debuglog(logger)
    def initRecord(self):
        for stage in self.__player["Damage"].values():
            for k in stage.keys():
                stage[k] = 0
        self.__player["Score"] = {"Boss1": 0, "Boss2": 0, "Boss3": 0, "Boss4": 0, "Boss5": 0, "Total": 0,}

    # 重置状态记录
    @debuglog(logger)
    def initState(self):
        self.__player['RemainingAttack'] = 3
        self.__player['Suspension'] = False
        self.__player['Knockout'] = [False, 0]
        self.__player['OrderedBoss'].clear()
        self.initsaveddata()

    # 重置保存的玩家信息列表，防止撤回被滥用
    @debuglog(logger)
    def initsaveddata(self):
        self.__saveddata.clear()

    # 回滚操作
    @debuglog(logger)
    def rollback(self) -> bool:
        if self.__saveddata:
            self.__player = self.__saveddata.pop()
            return True
        return False

    # 攻击，返回值为-2表示当前无刀，返回值为-3表示正在挂树，返回值为0表示出刀成功，返回值为1表示当前刀击破boss，返回值为2表示出了尾刀剩余刀，返回值为3表示出了尾刀剩余刀且击破boss
    @debuglog(logger)
    def attack(self, stage: int, boss: int, dmg: int, knockout: list = [False, 0]) -> int:
        if self.__player['RemainingAttack'] <= 0:
            return -2
        if self.__player['Suspension']:
            return -3
        self.__saveddata.append(deepcopy(self.__player))
        score = round(dmg * self.__scorebuff[stage][boss])
        self.__player["Damage"][f'Stage{stage}'][f'Boss{boss}'] += dmg
        self.__player["Damage"][f'Stage{stage}']['Total'] += dmg
        self.__player["Score"][f'Boss{boss}'] += score
        self.__player["Score"]["Total"] += score
        self.delOrderedBoss(boss)
        if self.__player['Knockout'][0]:
            self.__player['RemainingAttack'] -= 1
            self.delOrderedBoss(self.__player['Knockout'][1])
            self.setKnockout([False, 0])
            if self.__player['RemainingAttack'] == 0:
                self.__player['OrderedBoss'].clear()
            if knockout[0]:
                return 3
            else:
                return 2
        elif knockout[0]:
            self.setKnockout(knockout)
            self.setOrderedBoss(knockout[1])
            return 1
        else:
            self.__player['RemainingAttack'] -= 1
            if self.__player['RemainingAttack'] == 0:
                self.__player['OrderedBoss'].clear()
            return 0
