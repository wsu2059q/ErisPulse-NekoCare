import random
import time
from typing import Optional, Dict, Any, Tuple

import aiohttp

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command, message

DECAY_RATE = 3
CRITICAL_TIMEOUT = 86400
RESCUE_COST = 50
FOSTER_COST_PER_DAY = 5
FOSTER_MAX_DAYS = 7

SHOP_ITEMS = {
    "小鱼干": {
        "price": 8,
        "desc": "恢复15点饱食度",
        "type": "consumable",
        "effect": {"fullness": 15},
    },
    "猫粮罐头": {
        "price": 15,
        "desc": "恢复25点饱食度",
        "type": "consumable",
        "effect": {"fullness": 25},
    },
    "高级猫粮": {
        "price": 35,
        "desc": "恢复50点饱食度",
        "type": "consumable",
        "effect": {"fullness": 50},
    },
    "豪华猫宴": {
        "price": 60,
        "desc": "恢复80点饱食度",
        "type": "consumable",
        "effect": {"fullness": 80},
    },
    "亲密度糖果": {
        "price": 40,
        "desc": "亲密度+10",
        "type": "consumable",
        "effect": {"intimacy": 10},
    },
    "猫薄荷": {
        "price": 25,
        "desc": "亲密度+5 饱食度+10",
        "type": "consumable",
        "effect": {"intimacy": 5, "fullness": 10},
    },
    "体力药水": {
        "price": 30,
        "desc": "体力+15",
        "type": "consumable",
        "effect": {"hp_boost": 15},
    },
    "金币加成卡": {
        "price": 80,
        "desc": "下次打工收益翻倍",
        "type": "buff",
        "buff": "work_double",
    },
    "幸运铃铛": {
        "price": 60,
        "desc": "下次抓猫成功率+25%",
        "type": "buff",
        "buff": "catch_boost",
    },
    "急救包": {
        "price": 100,
        "desc": "免费急救一次",
        "type": "buff",
        "buff": "free_rescue",
    },
}

SHOP_ITEM_LIST = list(SHOP_ITEMS.keys())

DEATH_TITLES = {"starve": "饿死大王", "overwork": "劳累过度"}
ABANDON_TITLE = "弃养者"

ALL_TITLES = {
    "death": ["饿死大王", "劳累过度"],
    "punish": ["弃养者"],
    "achievement": [
        "打工狂魔",
        "捕猫达人",
        "神医再世",
        "富可敌国",
        "好主人",
        "理财圣手",
        "止盈大师",
        "富贵险求",
        "果断梭哈",
        "千金散尽",
        "散尽家财",
        "负债累累",
        "佛系玩家",
        "欧皇附体",
        "非酋酋长",
        "驭猫达人",
    ],
    "cute": ["萌系可爱", "软萌可爱", "软萌喵系", "萌态万千", "人间可爱", "盛世美颜"],
    "rich": ["清丽多金", "俊朗多金"],
}

EDU_LEVELS = {
    0: {"name": "无学历", "cost": 0},
    1: {"name": "喵喵小学", "cost": 0},
    2: {"name": "喵喵初中", "cost": 80},
    3: {"name": "喵喵高中", "cost": 200},
    4: {"name": "猫大专", "cost": 500},
    5: {"name": "猫大学", "cost": 1200},
    6: {"name": "猫研究生院", "cost": 3000},
}

EDU_STUDY_TIME = {1: 1800, 2: 3600, 3: 5400, 4: 7200, 5: 10800, 6: 21600}

JOBS = {
    0: [
        {
            "name": "捡瓶子",
            "earn_min": 5,
            "earn_max": 15,
            "nrg_min": 5,
            "nrg_max": 10,
            "stat": "hp",
        },
        {
            "name": "扫大街",
            "earn_min": 8,
            "earn_max": 18,
            "nrg_min": 5,
            "nrg_max": 10,
            "stat": "hp",
        },
        {
            "name": "街边卖小鱼干",
            "earn_min": 6,
            "earn_max": 22,
            "nrg_min": 5,
            "nrg_max": 10,
            "stat": "cha",
        },
    ],
    1: [
        {
            "name": "送鱼外卖",
            "earn_min": 10,
            "earn_max": 28,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "hp",
        },
        {
            "name": "猫砂厂打工",
            "earn_min": 12,
            "earn_max": 25,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
        {
            "name": "搬运猫粮",
            "earn_min": 12,
            "earn_max": 30,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
    ],
    2: [
        {
            "name": "便利店员",
            "earn_min": 15,
            "earn_max": 38,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "cha",
        },
        {
            "name": "保安",
            "earn_min": 18,
            "earn_max": 42,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
        {
            "name": "宠物店助手",
            "earn_min": 16,
            "earn_max": 35,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "cha",
        },
    ],
    3: [
        {
            "name": "喵喵快递员",
            "earn_min": 20,
            "earn_max": 52,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
        {
            "name": "猫咖服务员",
            "earn_min": 22,
            "earn_max": 48,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "cha",
        },
        {
            "name": "汽修猫",
            "earn_min": 25,
            "earn_max": 58,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
    ],
    4: [
        {
            "name": "宠物医生助理",
            "earn_min": 28,
            "earn_max": 62,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "int",
        },
        {
            "name": "喵喵银行柜员",
            "earn_min": 30,
            "earn_max": 65,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "cha",
        },
        {
            "name": "程序员",
            "earn_min": 32,
            "earn_max": 72,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
    ],
    5: [
        {
            "name": "猫学校教师",
            "earn_min": 40,
            "earn_max": 92,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
        {
            "name": "金融分析师",
            "earn_min": 45,
            "earn_max": 98,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
        {
            "name": "设计师",
            "earn_min": 42,
            "earn_max": 88,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "cha",
        },
        {
            "name": "工程师",
            "earn_min": 44,
            "earn_max": 95,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
    ],
    6: [
        {
            "name": "猫教授",
            "earn_min": 60,
            "earn_max": 130,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "int",
        },
        {
            "name": "基金经理",
            "earn_min": 65,
            "earn_max": 140,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "int",
        },
        {
            "name": "猫猫研究院研究员",
            "earn_min": 60,
            "earn_max": 128,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "int",
        },
        {
            "name": "城市规划猫",
            "earn_min": 65,
            "earn_max": 138,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "int",
        },
        {
            "name": "企业高管",
            "earn_min": 70,
            "earn_max": 155,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "cha",
        },
    ],
}

HIDDEN_JOBS = [
    {
        "name": "赏金猎猫",
        "earn_min": 50,
        "earn_max": 120,
        "nrg_min": 15,
        "nrg_max": 25,
        "req_cha": 60,
        "req_rep": 20,
        "stat": "cha",
    },
    {
        "name": "黑市中介",
        "earn_min": 40,
        "earn_max": 100,
        "nrg_min": 12,
        "nrg_max": 20,
        "req_rep": -30,
        "stat": "cha",
    },
    {
        "name": "猫窝设计师",
        "earn_min": 60,
        "earn_max": 130,
        "nrg_min": 12,
        "nrg_max": 20,
        "req_int": 60,
        "req_cha": 50,
        "stat": "cha",
    },
]

STOCK_LIST = ["喵粮股", "猫砂股", "猫薄荷股", "鱼干公司", "猫爬架集团", "罐头科技"]

STOCK_BASE_PRICES = {
    "喵粮股": 100,
    "猫砂股": 50,
    "猫薄荷股": 200,
    "鱼干公司": 150,
    "猫爬架集团": 80,
    "罐头科技": 300,
}

BANK_INTEREST_REGULAR = 0.03
BANK_INTEREST_FIXED = 0.08
BANK_FIXED_TERM = 86400
BANK_FIXED_PENALTY = 0.2
BANK_MAX_DEPOSIT = 10000
BANK_MAX_LOAN_RATE = 0.1
BANK_LOAN_CAP_RATIO = 2.0
BANK_LOAN_CAP_ABSOLUTE = 5000

ROB_COOLDOWN = 3600
SIGNIN_BASE = 20
SIGNIN_STREAK_BONUS = 10

SIGNIN_TYPES = {
    "signin": {"label": "签到", "coins": 20, "intimacy": 0},
    "morning": {"label": "早安", "coins": 8, "intimacy": 2},
    "noon": {"label": "午安", "coins": 8, "intimacy": 2},
    "night": {"label": "晚安", "coins": 8, "intimacy": 2},
}

INVESTMENTS = [
    {
        "name": "稳健基金",
        "cost": 100,
        "profit_min": 8,
        "profit_max": 20,
        "fail_rate": 0.02,
    },
    {
        "name": "债券理财",
        "cost": 300,
        "profit_min": 25,
        "profit_max": 70,
        "fail_rate": 0.05,
    },
    {
        "name": "风险投资",
        "cost": 500,
        "profit_min": 50,
        "profit_max": 250,
        "fail_rate": 0.12,
    },
    {
        "name": "运气投资",
        "cost": 1000,
        "profit_min": 200,
        "profit_max": 1200,
        "fail_rate": 0.25,
    },
]

NPC_CATS = [
    "橘座",
    "布偶妹妹",
    "三花大姐",
    "黑猫警长",
    "暹罗少爷",
    "狸花老哥",
    "奶牛仔",
    "英短胖虎",
    "美短小花",
    "无毛猫王",
    "波斯公主",
    "缅因大佬",
    "折耳弟弟",
    "加菲吃货",
    "狮子猫侠",
]

ROB_NPC_LOOT = {"min": 10, "max": 50}

BLACKMARKET_ITEMS = {
    "棒球棍": {
        "price": 80,
        "desc": "抢劫便利店/加油站必备",
        "type": "tool",
        "tool_tag": "melee",
    },
    "黑丝头套": {
        "price": 120,
        "desc": "遮挡面孔，降低被捕风险",
        "type": "tool",
        "tool_tag": "disguise",
    },
    "炸药": {
        "price": 200,
        "desc": "抢劫银行/珠宝店必备",
        "type": "tool",
        "tool_tag": "explosive",
    },
    "银行密码": {
        "price": 300,
        "desc": "抢劫银行必备 (一次性)",
        "type": "tool",
        "tool_tag": "bank_code",
    },
    "钻机": {
        "price": 250,
        "desc": "抢劫珠宝店必备",
        "type": "tool",
        "tool_tag": "drill",
    },
    "撬棍": {
        "price": 60,
        "desc": "撬开ATM机/便利店后门",
        "type": "tool",
        "tool_tag": "pry_bar",
    },
    "逃跑工具": {
        "price": 150,
        "desc": "逃跑更快，降低被捕率",
        "type": "tool",
        "tool_tag": "getaway",
    },
}

BLACKMARKET_ITEM_LIST = list(BLACKMARKET_ITEMS.keys())

ROB_TARGETS = {
    "便利店": {
        "require": ["melee"],
        "optional": ["disguise", "getaway"],
        "loot_min": 30,
        "loot_max": 100,
        "base_success": 65,
        "police_base": 10,
        "cooldown": 1800,
        "rep_loss": 5,
    },
    "加油站": {
        "require": ["melee"],
        "optional": ["disguise", "getaway"],
        "loot_min": 40,
        "loot_max": 120,
        "base_success": 60,
        "police_base": 12,
        "cooldown": 1800,
        "rep_loss": 6,
    },
    "ATM机": {
        "require": ["pry_bar"],
        "optional": ["disguise", "getaway"],
        "loot_min": 50,
        "loot_max": 200,
        "base_success": 50,
        "police_base": 15,
        "cooldown": 3600,
        "rep_loss": 8,
    },
    "珠宝店": {
        "require": ["drill"],
        "optional": ["disguise", "explosive", "getaway"],
        "loot_min": 200,
        "loot_max": 600,
        "base_success": 40,
        "police_base": 20,
        "cooldown": 7200,
        "rep_loss": 12,
    },
    "银行": {
        "require": ["bank_code", "explosive"],
        "optional": ["disguise", "getaway"],
        "loot_min": 500,
        "loot_max": 2000,
        "base_success": 30,
        "police_base": 25,
        "cooldown": 14400,
        "rep_loss": 15,
    },
}

ROB_TARGET_LIST = list(ROB_TARGETS.keys())

INVEST_TITLE_ACHIEVEMENTS = {
    "invest_profit_500": ("理财圣手", "累计理财净赚500金币"),
    "invest_profit_2000": ("止盈大师", "累计理财净赚2000金币"),
    "invest_profit_5000": ("富贵险求", "累计理财净赚5000金币"),
    "invest_total_10": ("果断梭哈", "累计投资10次"),
}

HELP_TEXT = (
    "喵喵世界 · 游戏指南\n\n"
    "你领养一只小猫，在喵喵城生活。\n"
    "上学、打工、存钱、投资，目标是成为富猫!\n\n"
    "--- 命令列表 ---\n"
    "/猫猫 - 主菜单 (领养/交互式)\n"
    "/猫猫状态 - 查看猫猫状态\n"
    "/猫猫喂食 - 喂食/互动\n"
    "/猫猫打工 - 打工/捡瓶子/捉虫/打劫\n"
    "/猫猫银行 - 存款/贷款/股票/理财\n"
    "/猫猫学习 - 学习深造\n"
    "/猫猫背包 - 背包/商城\n"
    "/猫图 - 随机猫图\n"
    "/喵榜 - 排行榜\n\n"
    "--- 每日签到 ---\n"
    "消息中包含「早安/午安/晚安/签到」自动触发奖励\n"
    "无需命令，直接说话就行!\n"
    "签到: 每天领一次金币 (连续签到奖励更多!)\n"
    "早安/午安/晚安: 各领一次，得少量金币+亲密度\n"
    "全部完成额外奖励!\n\n"
    "--- 教育系统 ---\n"
    "学历: 喵喵小学→初中→高中→大专→大学→研究生院\n"
    "认真学习: 进度+25 智力+1~3 (推荐!)\n"
    "正常学习: 进度+15\n"
    "摸鱼: 进度+5 魅力+1~2 (偶尔扣智力)\n"
    "进度满100%且学费充足自动毕业，解锁更高薪工作!\n"
    "注意: 学费不足时不消耗冷却时间!\n\n"
    "--- 赚钱方式 ---\n"
    "打工: 每级学历解锁不同岗位，共25+种职业\n"
    "属性>=60对应工作额外加成15%收益\n"
    "捡瓶子: 10分钟冷却，零门槛小额收入\n"
    "捉虫子: 10分钟冷却，高智力有稀有虫!\n"
    "打劫野外NPC: 低风险，15分钟冷却\n"
    "抓猫打工: @目标，中等风险，1小时冷却\n"
    "抢劫地点: 需要黑市工具 (便利店/加油站/ATM/珠宝店/银行)\n"
    "黑市: 购买棒球棍/头套/炸药/密码/钻机/撬棍/逃跑车\n\n"
    "--- 喵喵银行 ---\n"
    "活期: 3%日息，随存随取\n"
    "定期: 8%日息，锁24h，提前取扣20%违约金\n"
    "贷款: 额度=500x学历，利息上限为本金的2倍(最高5000)\n"
    "股票: 6只股票实时波动，低买高卖\n"
    "理财: 4档风险(稳健基金2%/债券5%/风险投资12%/运气投资25%)\n\n"
    "--- 生存系统 ---\n"
    "饱食度会随时间下降(3点/小时)\n"
    "饱食度归0进入危急状态，24h不救则饿死\n"
    "体力耗尽无法打劫，记得休息!\n\n"
    "--- 头衔系统 ---\n"
    "萌系: 萌系可爱/软萌可爱/软萌喵系/萌态万千/人间可爱/盛世美颜\n"
    "多金: 清丽多金/俊朗多金/富可敌国\n"
    "理财: 理财圣手/止盈大师/富贵险求/果断梭哈\n"
    "破产: 千金散尽/散尽家财/负债累累\n"
    "趣味: 佛系玩家/欧皇附体/非酋酋长/驭猫达人\n"
    "负面: 弃养者/饿死大王/劳累过度\n\n"
    "--- 小贴士 ---\n"
    "1. 每天签到+问候白拿金币!\n"
    "2. 捡瓶子/捉虫子零门槛赚零花钱\n"
    "3. 先上学提升学历 → 解锁高薪工作\n"
    "4. 打工赚到的钱存银行吃利息\n"
    "5. 适当炒股/理财加速致富\n"
    "6. 贷款利息有上限，不会失控\n"
    "7. 别忘了每天喂猫猫!\n\n"
    "!!! 注意 !!!\n"
    "弃养猫猫: 扣50%金币(最低200)、学历清零、属性重置、银行清空\n"
    "猫猫死亡: 扣30%金币(最低100)、体力-40、声望-15\n"
    "重新领养: 扣33%金币、学历清零、属性重置、银行清空"
)

CARD_THEMES = {
    "menu": {
        "accent": "#D4D4AA",
        "bg": "#FFFFFF",
        "header_color": "#2C2C2C",
        "tag_bg": "#E8E8D0",
        "border": "#E0E0E0",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
    "status": {
        "accent": "#9775fa",
        "bg": "#FFFFFF",
        "header_color": "#6741d9",
        "tag_bg": "#F3F0FF",
        "border": "#E0E0E0",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
    "success": {
        "accent": "#2E7D32",
        "bg": "#E8F5E9",
        "header_color": "#2E7D32",
        "tag_bg": "#C8E6C9",
        "border": "#C8E6C9",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
    "warning": {
        "accent": "#E65100",
        "bg": "#FFF9DB",
        "header_color": "#E65100",
        "tag_bg": "#FFF3CD",
        "border": "#FFE0B2",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
    "danger": {
        "accent": "#C62828",
        "bg": "#FFEBEE",
        "header_color": "#C62828",
        "tag_bg": "#FFCDD2",
        "border": "#FFCDD2",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
    "death": {
        "accent": "#adb5bd",
        "bg": "#2d2d3a",
        "header_color": "#dee2e6",
        "tag_bg": "rgba(134,142,150,0.25)",
        "border": "#404040",
        "text": "#dee2e6",
        "text_sub": "#adb5bd",
    },
    "info": {
        "accent": "#1971c2",
        "bg": "#FFFFFF",
        "header_color": "#1971c2",
        "tag_bg": "#E3F2FD",
        "border": "#BBDEFB",
        "text": "#2C2C2C",
        "text_sub": "#666666",
    },
}

_FONT = (
    "font-family:'Inter',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;"
)


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("NekoCare")
        self.config = self._load_config()
        self._timed_out_users: set = set()
        self.image_categories = {
            "neko": "https://nekos.best/api/v2/neko",
            "hug": "https://nekos.best/api/v2/hug",
            "pat": "https://nekos.best/api/v2/pat",
            "cuddle": "https://nekos.best/api/v2/cuddle",
            "kiss": "https://nekos.best/api/v2/kiss",
            "bite": "https://nekos.best/api/v2/bite",
            "slap": "https://nekos.best/api/v2/slap",
            "kick": "https://nekos.best/api/v2/kick",
            "blush": "https://nekos.best/api/v2/blush",
            "smile": "https://nekos.best/api/v2/smile",
            "wave": "https://nekos.best/api/v2/wave",
            "happy": "https://nekos.best/api/v2/happy",
            "dance": "https://nekos.best/api/v2/dance",
            "cry": "https://nekos.best/api/v2/cry",
            "sleep": "https://nekos.best/api/v2/sleep",
        }

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy

        return ModuleLoadStrategy(lazy_load=False, priority=0)

    async def on_load(self, event):
        @command("猫猫", help="猫猫养成主菜单")
        async def menu_cmd(cmd_event):
            await self._handle_main_menu(cmd_event)

        @command("猫猫状态", help="查看猫猫状态")
        async def status_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            cat_data, status = self._apply_hunger_decay(user_id)
            if not cat_data:
                await self._send_reply(cmd_event, "你还没有猫猫呢~去 /猫猫 领养一只吧!")
                return
            await self._handle_status(cmd_event, cat_data, user_id)

        @command("猫猫喂食", help="喂食/互动")
        async def feed_cmd(cmd_event):
            await self._cmd_ensure_alive(cmd_event, self._handle_feed_menu)

        @command("猫猫打工", help="打工赚钱")
        async def work_cmd(cmd_event):
            await self._cmd_ensure_alive(cmd_event, self._handle_earn_menu)

        @command("猫猫银行", help="喵喵银行")
        async def bank_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            await self._handle_bank(cmd_event, user_id)

        @command("猫猫学习", help="学习深造")
        async def study_cmd(cmd_event):
            await self._cmd_ensure_alive(cmd_event, self._handle_study)

        @command("猫猫背包", help="背包/商城")
        async def bag_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            await self._handle_bag_menu(cmd_event, user_id)

        @command("猫图", help="随机猫图")
        async def cat_image_cmd(cmd_event):
            categories = list(self.image_categories.keys())
            category = random.choice(categories)
            url = await self._fetch_image(category)
            if url:
                await self._send_reply(cmd_event, "随机猫图", image_url=url)
            else:
                await self._send_reply(cmd_event, "获取图片失败~", card_type="danger")

        @command("喵榜", help="查看排行榜")
        async def leaderboard_cmd(cmd_event):
            await self._handle_leaderboard(cmd_event)

        @command("喵喵帮助", help="喵喵世界游戏指南")
        async def help_cmd(cmd_event):
            await self._send_reply(cmd_event, HELP_TEXT, card_type="info")

        @message.on_message()
        async def greeting_handler(msg_event):
            text = msg_event.get_text().strip()
            if not text:
                return
            keyword_map = {
                "早安": "morning",
                "午安": "noon",
                "晚安": "night",
                "签到": "signin",
            }
            for keyword, key in keyword_map.items():
                if keyword in text:
                    user_id = msg_event.get_user_id()
                    self._register_user(user_id, msg_event.get_user_nickname() or "")
                    cat_data = self._get_cat(user_id)
                    if key == "signin":
                        await self._handle_signin(msg_event, user_id, cat_data)
                    else:
                        await self._quick_greeting(msg_event, key)
                    return

        self.logger.info("NekoCare 模块加载成功")

    async def on_unload(self, event):
        self.logger.info("NekoCare 模块已卸载")

    async def _cmd_ensure_alive(self, event, handler):
        user_id = event.get_user_id()
        self._register_user(user_id, event.get_user_nickname() or "")
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~去 /猫猫 领养一只吧!")
            return
        if status == "dead":
            await self._send_dead_message(event, cat_data)
            return
        if status == "critical":
            await self._send_critical_message(event, cat_data)
            return
        if status == "fostered":
            await self._send_reply(event, "猫猫正在寄养中~用 /猫猫 接它回家")
            return
        await handler(event, user_id)

    # =============================================================
    #  菜单处理
    # =============================================================

    async def _wait_choice(
        self,
        event,
        timeout=60,
        choices: list = None,
        expect: str = None,
        min_val: int = None,
        max_val: int = None,
    ):
        user_id = event.get_user_id()
        max_fail = 3
        fail_count = 0
        while True:
            reply = await event.wait_reply(timeout=timeout)
            if not reply:
                self._timed_out_users.add(user_id)
                return None
            text = reply.get_text().strip()
            if not text:
                continue

            if choices is not None:
                if text in choices:
                    return text
                fail_count += 1
                if fail_count >= max_fail:
                    self._timed_out_users.add(user_id)
                    return None
                continue

            if expect == "int":
                try:
                    val = int(text)
                except ValueError:
                    fail_count += 1
                    if fail_count >= max_fail:
                        self._timed_out_users.add(user_id)
                        return None
                    continue
                if min_val is not None and val < min_val:
                    fail_count += 1
                    if fail_count >= max_fail:
                        self._timed_out_users.add(user_id)
                        return None
                    continue
                if max_val is not None and val > max_val:
                    fail_count += 1
                    if fail_count >= max_fail:
                        self._timed_out_users.add(user_id)
                        return None
                    continue
                return val

            return text

    async def _handle_main_menu(self, event):
        user_id = event.get_user_id()
        self._timed_out_users.discard(user_id)
        self._register_user(user_id, event.get_user_nickname() or "")

        while True:
            if user_id in self._timed_out_users:
                break

            cat_data, status = self._apply_hunger_decay(user_id)
            coins = self._get_coins(user_id)

            if not cat_data or status == "dead":
                if cat_data is not None and status == "dead":
                    death_title = DEATH_TITLES.get(
                        cat_data.get("death_cause", "starve"), "???"
                    )
                    header = f"[{cat_data['name']}] 已去喵星...\n头衔: {death_title}"
                else:
                    header = "欢迎来到喵喵城!\n这里有很多等待领养的小猫猫~"

                menu = f"{header}\n\n1. 领养一只小猫猫\n0. 退出"
                await self._send_reply(event, menu)

                choice = await self._wait_choice(event, choices=["0", "1"])
                if choice is None or choice == "0":
                    break
                await self._handle_adopt(event)
                continue

            elif status == "fostered":
                foster_days = self._get_foster_days(cat_data)
                foster_cost = self._calc_foster_cost(cat_data)
                menu = (
                    f"[{cat_data['name']}] 正在寄养中  金币:{coins}\n\n"
                    f"寄养天数: {foster_days}天 | 费用: {foster_cost}金币\n"
                    f"(接回时结算，最多寄养{FOSTER_MAX_DAYS}天)\n\n"
                    f"1. 接回家 ({foster_cost}金币)\n"
                    f"2. 查看状态\n"
                    f"3. 背包/商城\n"
                    f"0. 退出"
                )
                await self._send_reply(event, menu)

                choice = await self._wait_choice(event, choices=["0", "1", "2", "3"])
                if choice is None or choice == "0":
                    break
                if choice == "1":
                    await self._handle_unfoster(event, user_id, cat_data)
                elif choice == "2":
                    await self._handle_status(event, cat_data, user_id)
                elif choice == "3":
                    await self._handle_bag_menu(event, user_id)

            else:
                fullness = cat_data["fullness"]
                fl, fc = self._get_stat_style("fullness", fullness)
                edu_name = EDU_LEVELS[self._get_edu(user_id)]["name"]
                attrs = self._get_attrs(user_id)
                attr_line = f"智:{attrs['int']} 体:{attrs['hp']} 魅:{attrs['cha']} 声:{attrs['rep']}"
                menu = (
                    f"[{cat_data['name']}] 作为铲屎官，今天做什么呢?\n\n"
                    f"饱食度: {fl}  金币:{coins}  学历:{edu_name}\n"
                    f"{attr_line}\n\n"
                    f"1. 查看状态\n"
                    f"2. 喂食/互动\n"
                    f"3. 赚钱\n"
                    f"4. 喵喵银行\n"
                    f"5. 学习深造\n"
                    f"6. 背包/商城\n"
                    f"7. 其他\n"
                    f"0. 退出\n\n"
                    f"快捷命令: /猫猫状态 /猫猫喂食 /猫猫打工\n"
                    f"  /猫猫银行 /猫猫学习 /猫猫背包"
                )
                await self._send_reply(event, menu)

                choice = await self._wait_choice(
                    event,
                    choices=["0", "1", "2", "3", "4", "5", "6", "7"],
                )
                if choice is None or choice == "0":
                    break
                if choice == "1":
                    await self._handle_status(event, cat_data, user_id)
                elif choice == "2":
                    await self._handle_feed_menu(event, user_id)
                elif choice == "3":
                    await self._handle_earn_menu(event, user_id, cat_data)
                elif choice == "4":
                    await self._handle_bank(event, user_id)
                elif choice == "5":
                    await self._handle_study(event, user_id)
                elif choice == "6":
                    await self._handle_bag_menu(event, user_id)
                elif choice == "7":
                    await self._handle_other_menu(event, user_id, cat_data)

        explicit_exit = user_id not in self._timed_out_users
        self._timed_out_users.discard(user_id)

        if explicit_exit:
            nickname = event.get_user_nickname() or user_id
            cat_data_exit = self._get_cat(user_id)
            if cat_data_exit:
                exit_msg = (
                    f"[{cat_data_exit['name']}] 在等你回来哦~\n{nickname}，下次再来玩~"
                )
            else:
                exit_msg = f"{nickname}，快去领养一只小猫猫吧~"
            await self._send_reply(event, exit_msg, card_type="info", force_new=True)

    async def _handle_feed_menu(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return
            cat_data, status = self._apply_hunger_decay(user_id)
            if not cat_data or status != "alive":
                if status == "dead" and cat_data is not None:
                    await self._send_dead_message(event, cat_data)
                elif status == "critical" and cat_data is not None:
                    await self._send_critical_message(event, cat_data)
                return

            now = time.time()
            today_start = int(time.strftime("%Y%m%d", time.localtime(now)))
            last_feed_day = int(
                time.strftime("%Y%m%d", time.localtime(cat_data.get("last_feed", 0)))
            )
            if today_start != last_feed_day:
                cat_data["feed_count"] = 0
                self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            feed_left = 5 - cat_data["feed_count"]
            fl, _ = self._get_stat_style("fullness", cat_data["fullness"])
            menu = (
                f"喂食 / 互动\n\n"
                f"饱食度: {fl}\n\n"
                f"1. 喂食 (今日剩余{feed_left}次)\n"
                f"2. 贴贴\n"
                f"3. 摸摸\n"
                f"0. 返回"
            )
            await self._send_reply(event, menu)

            choice = await self._wait_choice(event, choices=["0", "1", "2", "3"])
            if choice is None or choice == "0":
                return
            if choice == "1":
                await self._do_feed(event, user_id, cat_data)
            elif choice == "2":
                await self._do_cuddle(event, user_id, cat_data)
            elif choice == "3":
                await self._do_pat(event, user_id, cat_data)

    async def _handle_earn_menu(self, event, user_id, cat_data=None):
        while True:
            if user_id in self._timed_out_users:
                return
            now = time.time()
            last_work = self._get_work_cooldown(user_id)
            work_ready = (now - last_work) >= 1800
            last_catch = self._get_catch_cooldown(user_id)
            catch_ready = (now - last_catch) >= 3600
            last_rob = self._get_rob_cooldown(user_id)
            rob_ready = (now - last_rob) >= ROB_COOLDOWN
            last_scavenge = self._get_scavenge_cooldown(user_id)
            scavenge_ready = (now - last_scavenge) >= 600

            wr = "✓" if work_ready else f"{int((1800 - (now - last_work)) // 60) + 1}分"
            cr = (
                "✓"
                if catch_ready
                else f"{int((3600 - (now - last_catch)) // 60) + 1}分"
            )
            rr = (
                "✓"
                if rob_ready
                else f"{int((ROB_COOLDOWN - (now - last_rob)) // 60) + 1}分"
            )
            sr = (
                "✓"
                if scavenge_ready
                else f"{int((600 - (now - last_scavenge)) // 60) + 1}分"
            )

            menu = (
                f"赚钱\n\n"
                f"1. 打工 ({wr})\n"
                f"2. 抓猫打工 ({cr})\n"
                f"3. 打劫 ({rr})\n"
                f"4. 捡瓶子 ({sr})\n"
                f"5. 摸鱼捉虫 ({sr})\n"
                f"0. 返回"
            )
            await self._send_reply(event, menu)

            choice = await self._wait_choice(
                event, choices=["0", "1", "2", "3", "4", "5"]
            )
            if choice is None or choice == "0":
                return
            elif choice == "1":
                await self._handle_work(event, user_id)
            elif choice == "2":
                await self._handle_catch(event, user_id)
            elif choice == "3":
                await self._handle_rob(event, user_id)
            elif choice == "4":
                await self._handle_scavenge(event, user_id)
            elif choice == "5":
                await self._handle_bugcatch(event, user_id)

    async def _quick_greeting(self, event, key: str):
        user_id = event.get_user_id()
        self._register_user(user_id, event.get_user_nickname() or "")
        now = time.time()
        today = time.strftime("%Y%m%d", time.localtime(now))
        signin_data = self._get_signin_data(user_id)
        if signin_data.get("last_date") != today:
            signin_data["streak"] = signin_data.get("streak", 0) + 1
            signin_data["last_date"] = today
            signin_data["today"] = {}
            self._set_signin_data(user_id, signin_data)

        today_done = signin_data.get("today", {})
        if today_done.get(key, False):
            return

        info = SIGNIN_TYPES[key]
        self._add_coins(user_id, info["coins"])

        cat_data = self._get_cat(user_id)
        ig = 0
        if cat_data and cat_data.get("status") == "alive":
            ig = info["intimacy"]
            cat_data["intimacy"] = min(100, cat_data["intimacy"] + ig)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        today_done[key] = True
        signin_data["today"] = today_done
        self._set_signin_data(user_id, signin_data)

        has_cat = cat_data is not None
        if has_cat:
            cat_name = cat_data["name"]
        else:
            cat_name = None

        nickname = event.get_user_nickname() or user_id

        if key == "morning":
            greetings = [f"早安呀~", f"早上好!", f"新的一天开始啦!"]
        elif key == "noon":
            greetings = [f"午安~", f"中午好!", f"吃午饭了吗?"]
        else:
            greetings = [f"晚安~", f"晚安好梦!", f"早点休息哦~"]

        greet = random.choice(greetings)
        reward_text = f"+{info['coins']}金币"
        if ig > 0:
            reward_text += f" +{ig}亲密度"

        if has_cat:
            text = f"{greet}\n\n[{cat_name}]向你{info['label']}\n{reward_text}"
        else:
            text = (
                f"{greet}\n\n"
                f"{nickname}，{info['label']}!\n"
                f"{reward_text}\n\n"
                f"你还没有猫猫哦，试试 /猫猫 领养一只吧~"
            )

        img_key = "wave"
        if key == "morning":
            img_key = "smile"
        elif key == "night":
            img_key = "sleep"

        url = await self._fetch_image(img_key)
        await self._send_reply(
            event, text, image_url=url, card_type="success", force_new=True
        )

    async def _handle_signin(self, event, user_id, cat_data):
        now = time.time()
        today = time.strftime("%Y%m%d", time.localtime(now))
        signin_data = self._get_signin_data(user_id)
        streak = signin_data.get("streak", 0)
        last_date = signin_data.get("last_date", "")

        if last_date != today:
            streak += 1
            signin_data["streak"] = streak
            signin_data["last_date"] = today
            signin_data["today"] = {}
            self._set_signin_data(user_id, signin_data)

        today_done = signin_data.get("today", {})
        key = "signin"

        if today_done.get(key, False):
            await self._send_reply(
                event, "今天已经签过啦~明天再来!", card_type="warning", force_new=True
            )
            return

        bonus = SIGNIN_BASE + (streak - 1) * SIGNIN_STREAK_BONUS
        self._add_coins(user_id, bonus)
        today_done[key] = True
        signin_data["today"] = today_done
        self._set_signin_data(user_id, signin_data)

        all_keys = list(SIGNIN_TYPES.keys())
        all_done = all(today_done.get(k, False) for k in all_keys)
        extra = 0
        if all_done:
            extra = streak * 2
            self._add_coins(user_id, extra)

        nickname = event.get_user_nickname() or user_id
        has_cat = cat_data is not None and cat_data.get("status") == "alive"

        text = f"签到成功! 第{streak}天连续签到\n+{bonus}金币"
        if extra > 0:
            text += f"\n今日全部完成! 额外+{extra}金币"
        if has_cat:
            text += f"\n\n[{cat_data['name']}] 在等你回来哦~"
        else:
            text += f"\n\n{nickname}，你还没有猫猫，试试 /猫猫 领养一只吧~"

        url = await self._fetch_image("happy")
        await self._send_reply(
            event, text, image_url=url, card_type="success", force_new=True
        )

    async def _handle_other_menu(self, event, user_id, cat_data):
        while True:
            if user_id in self._timed_out_users:
                return
            active_title = self._get_active_title(user_id)
            title_text = f" [{active_title}]" if active_title else ""
            menu = (
                f"其他\n"
                f"当前猫猫: [{cat_data['name']}]{title_text}\n\n"
                "1. 寄养猫猫\n"
                "2. 改名\n"
                "3. 查看/设置头衔\n"
                "4. 弃养猫猫\n"
                "0. 返回"
            )
            await self._send_reply(event, menu)

            choice = await self._wait_choice(event, choices=["0", "1", "2", "3", "4"])
            if choice is None or choice == "0":
                return
            elif choice == "1":
                await self._handle_foster(event, user_id, cat_data)
            elif choice == "2":
                await self._handle_rename(event, user_id, cat_data)
            elif choice == "3":
                await self._handle_titles(event, user_id)
            elif choice == "4":
                if await self._handle_abandon(event, user_id, cat_data):
                    return
            menu = "其他\n\n1. 寄养猫猫\n2. 改名/头衔\n3. 弃养猫猫\n0. 返回"
            await self._send_reply(event, menu)

            choice = await self._wait_choice(event, choices=["0", "1", "2", "3"])
            if choice is None or choice == "0":
                return
            elif choice == "1":
                await self._handle_foster(event, user_id, cat_data)
            elif choice == "2":
                await self._handle_rename(event, user_id, cat_data)
            elif choice == "3":
                if await self._handle_abandon(event, user_id, cat_data):
                    return

    async def _handle_scavenge(self, event, user_id, cat_data=None):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status != "alive":
            await self._send_reply(event, "猫猫状态不对，无法外出~")
            return

        now = time.time()
        last = self._get_scavenge_cooldown(user_id)
        remaining = 600 - (now - last)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫刚捡完，{m}分钟后再来~")
            return

        attrs = self._get_attrs(user_id)
        finds = [
            ("几个空瓶子", random.randint(2, 8)),
            ("一张旧报纸", random.randint(1, 3)),
            ("别人掉的硬币", random.randint(3, 12)),
            ("一个好看的石头", random.randint(2, 6)),
            ("一罐过期的猫粮", random.randint(1, 4)),
            ("一只手套", random.randint(1, 5)),
        ]
        if attrs["cha"] >= 30:
            finds.append(("一张钞票", random.randint(8, 20)))
        if attrs["cha"] >= 60:
            finds.append(("一个红包!", random.randint(15, 35)))

        item_name, coins = random.choice(finds)
        cat_data["fullness"] = max(0, cat_data["fullness"] - random.randint(1, 3))
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self._add_coins(user_id, coins)
        self._set_scavenge_cooldown(user_id)
        self._mod_attr(user_id, "hp", -random.randint(1, 3))

        url = await self._fetch_image("happy")
        msgs = [
            f"[{cat_data['name']}] 在路边捡到了【{item_name}】!\n卖了 {coins} 金币~",
            f"[{cat_data['name']}] 叼回了【{item_name}】!\n换了 {coins} 金币!",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _handle_bugcatch(self, event, user_id, cat_data=None):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status != "alive":
            await self._send_reply(event, "猫猫状态不对~")
            return

        now = time.time()
        last = self._get_scavenge_cooldown(user_id)
        remaining = 600 - (now - last)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫刚玩完，{m}分钟后再来~")
            return

        attrs = self._get_attrs(user_id)
        bugs = [
            ("一只蝴蝶", random.randint(1, 5)),
            ("一只蚂蚱", random.randint(1, 4)),
            ("一只蜻蜓", random.randint(2, 6)),
            ("一条毛毛虫", random.randint(0, 3)),
            ("一只甲虫", random.randint(2, 5)),
        ]
        if attrs["int"] >= 30:
            bugs.append(("一只漂亮的瓢虫", random.randint(5, 12)))
        if attrs["int"] >= 60:
            bugs.append(("一只罕见的萤火虫!", random.randint(10, 25)))

        caught = random.choice(bugs)
        bug_name, coins = caught
        cat_data["fullness"] = max(0, cat_data["fullness"] - random.randint(1, 2))
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self._add_coins(user_id, coins)
        self._set_scavenge_cooldown(user_id)
        self._mod_attr(user_id, "int", random.randint(0, 1))
        self._mod_attr(user_id, "hp", -random.randint(1, 2))

        url = await self._fetch_image("happy")
        msgs = [
            f"[{cat_data['name']}] 捉到了【{bug_name}】!\n卖了 {coins} 金币~",
            f"[{cat_data['name']}] 扑腾半天抓到【{bug_name}】!\n赚了 {coins} 金币!",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _handle_bag_menu(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return
            coins = self._get_coins(user_id)
            bag_text = self._build_bag_display(user_id, coins)

            actions = "\n1.使用道具  2.前往商城  3.查看增益  4.查看头衔\n0. 返回"
            full = f"{bag_text}{actions}"
            await self._send_reply(event, full)

            choice = await self._wait_choice(event, choices=["0", "1", "2", "3", "4"])
            if choice is None or choice == "0":
                return
            if choice == "1":
                await self._handle_use_item(event, user_id)
            elif choice == "2":
                await self._handle_shop_menu(event, user_id)
            elif choice == "3":
                await self._show_buffs(event, user_id)
            elif choice == "4":
                await self._handle_titles(event, user_id)

    async def _handle_shop_menu(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return
            coins = self._get_coins(user_id)
            shop_text = self._build_shop_display(coins)
            shop_text += "\n输入编号购买 | 0 返回"
            await self._send_reply(event, shop_text)

            choice = await self._wait_choice(
                event, expect="int", min_val=0, max_val=len(SHOP_ITEM_LIST)
            )
            if choice is None or choice == 0:
                return
            idx = choice - 1
            await self._do_buy(event, user_id, SHOP_ITEM_LIST[idx])

    async def _handle_use_item(self, event, user_id):
        inventory = self._get_inventory(user_id)
        coins = self._get_coins(user_id)

        available = []
        for i, name in enumerate(SHOP_ITEM_LIST):
            count = inventory.get(name, 0)
            if count > 0:
                item = SHOP_ITEMS[name]
                available.append((i + 1, name, count, item))

        has_tools = False
        tool_lines = []
        for name in BLACKMARKET_ITEM_LIST:
            count = inventory.get(name, 0)
            if count > 0:
                has_tools = True
                item = BLACKMARKET_ITEMS[name]
                tool_lines.append(f"  {name}  x{count}  {item['desc']}")

        if not available and not has_tools:
            await self._send_reply(event, "背包空空如也~去商城逛逛吧!")
            return

        lines = [f"使用道具  金币:{coins}\n"]
        for idx, name, count, item in available:
            lines.append(f"{idx}. {name}  x{count}  {item['desc']}")
        if has_tools:
            lines.append("\n--- 作案工具 (用于抢劫) ---")
            lines.extend(tool_lines)
        lines.append("\n输入编号使用 | 0 返回")
        await self._send_reply(event, "\n".join(lines))

        choice = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(available)
        )
        if choice is None or choice == 0:
            return

        selected_idx = choice

        for idx, name, count, item in available:
            if idx == selected_idx:
                cat_data, status = self._apply_hunger_decay(user_id)

                if item["type"] == "consumable":
                    if not cat_data:
                        await self._send_reply(event, "你还没有猫猫，无法使用此道具")
                        return
                    if status == "dead":
                        await self._send_dead_message(event, cat_data)
                        return
                    if status == "fostered":
                        await self._send_reply(event, "猫猫正在寄养中，无法使用此道具")
                        return

                    await self._send_reply(
                        event, f"使用几个【{name}】? (1-{count})，输入数量:"
                    )
                    qty = await self._wait_choice(
                        event, expect="int", min_val=1, max_val=count
                    )
                    if qty is None:
                        return

                    effect = item["effect"]
                    total_fullness_gain = effect.get("fullness", 0) * qty
                    total_intimacy_gain = effect.get("intimacy", 0) * qty

                    if "fullness" in effect:
                        cat_data["fullness"] = min(
                            100, cat_data["fullness"] + total_fullness_gain
                        )
                    if "intimacy" in effect:
                        cat_data["intimacy"] = min(
                            100, cat_data["intimacy"] + total_intimacy_gain
                        )
                    if "hp_boost" in effect:
                        self._mod_attr(user_id, "hp", effect["hp_boost"] * qty)

                    if status == "critical" and cat_data["fullness"] > 0:
                        cat_data["status"] = "alive"
                        cat_data["critical_since"] = 0
                        cat_data["last_decay"] = time.time()

                    self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
                    self._remove_inventory(user_id, name, qty)

                    fl, _ = self._get_stat_style("fullness", cat_data["fullness"])
                    il, _ = self._get_stat_style("intimacy", cat_data["intimacy"])

                    parts = []
                    if total_fullness_gain:
                        parts.append(f"饱食度+{total_fullness_gain}")
                    if total_intimacy_gain:
                        parts.append(f"亲密度+{total_intimacy_gain}")
                    if "hp_boost" in effect:
                        parts.append(f"体力+{effect['hp_boost'] * qty}")

                    status_line = f"当前状态: 饱食度 {cat_data['fullness']}/100 亲密度 {cat_data['intimacy']}/100"
                    url = await self._fetch_image("happy")
                    await self._send_reply(
                        event,
                        f"使用了【{name}】x{qty}! {', '.join(parts)}\n{status_line}",
                        image_url=url,
                        card_type="success",
                    )

                elif item["type"] == "buff":
                    buffs = self._get_buffs(user_id)
                    buffs[item["buff"]] = True
                    self._set_buffs(user_id, buffs)
                    self._remove_inventory(user_id, name, 1)

                    url = await self._fetch_image("neko")
                    await self._send_reply(
                        event,
                        f"使用了【{name}】! 增益已激活。",
                        image_url=url,
                        card_type="success",
                    )

                elif item["type"] == "tool":
                    await self._send_reply(
                        event,
                        f"【{name}】是工具类道具，用于抢劫!\n"
                        f"去 /猫猫打工 → 打劫 → 抢劫地点 使用。",
                        card_type="info",
                    )
                return

        await self._send_reply(event, "无效编号", card_type="danger")

    async def _handle_titles(self, event, user_id):
        titles = self._get_titles(user_id)
        active = self._get_active_title(user_id)

        if not titles:
            await self._send_reply(event, "你还没有获得任何头衔~")
            return

        lines = ["我的头衔\n"]
        for i, title in enumerate(titles, 1):
            marker = " <<" if title == active else ""
            lines.append(f"{i}. {title}{marker}")
        lines.append(f"\n当前佩戴: {active or '无'}")
        lines.append("\n输入编号佩戴 | 0. 取消佩戴 | 其他返回")
        await self._send_reply(event, "\n".join(lines))

        choice = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(titles)
        )
        if choice is None:
            return

        if choice == 0:
            self._set_active_title(user_id, "")
            await self._send_reply(event, "已取消佩戴头衔")
            return

        if 1 <= choice <= len(titles):
            self._set_active_title(user_id, titles[choice - 1])
            await self._send_reply(event, f"已佩戴头衔【{titles[choice - 1]}】!")
        else:
            await self._send_reply(event, "无效编号", card_type="danger")

    # =============================================================
    #  动作处理
    # =============================================================

    async def _handle_adopt(self, event):
        await self._send_reply(event, "请给小猫猫取个名字（限20字内）：")
        name = await self._wait_choice(event, timeout=120)
        if not name:
            return

        if len(name) > 20:
            await self._send_reply(event, "名字太长了，最多20个字符~")
            return

        if not name:
            name = f"猫猫_{event.get_user_id()[-4:]}"

        user_id = event.get_user_id()

        had_cat_before = self._get_cat(user_id) is not None
        if had_cat_before:
            self._penalize_readopt(user_id)

        now = time.time()
        cat_data = {
            "name": name,
            "adopt_time": now,
            "fullness": 100,
            "intimacy": 0,
            "last_feed": 0,
            "feed_count": 0,
            "last_interact": 0,
            "status": "alive",
            "last_decay": now,
            "critical_since": 0,
        }
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self._inc_stat(user_id, "adopt_count")

        url = await self._fetch_image("neko")
        if had_cat_before:
            await self._send_reply(
                event,
                f"你领养了新的小猫猫 [{name}]~\n好好对待它，不要再离开了!",
                image_url=url,
                card_type="success",
            )
        else:
            await self._send_reply(
                event,
                f"领养成功! 小猫猫 [{name}] 来到了你身边~\n以小猫视角细心养护它，记得每天喂食哦!",
                image_url=url,
                card_type="success",
            )

    async def _handle_rescue(self, event, user_id):
        cat_data = self._get_cat(user_id)
        if not cat_data or cat_data.get("status") != "critical":
            await self._send_reply(event, "当前不需要急救")
            return

        buffs = self._get_buffs(user_id)
        free = buffs.get("free_rescue", False)

        if not free:
            coins = self._get_coins(user_id)
            if coins < RESCUE_COST:
                await self._send_reply(
                    event,
                    f"急救需要 {RESCUE_COST} 金币，你只有 {coins} 枚\n"
                    f"去商城购买急救包或打工赚钱吧!",
                    card_type="danger",
                )
                return

        if free:
            buffs["free_rescue"] = False
            self._set_buffs(user_id, buffs)
            cost_text = "使用急救包"
        else:
            self._add_coins(user_id, -RESCUE_COST)
            cost_text = f"花费 {RESCUE_COST} 金币"

        now = time.time()
        if random.random() < 0.5:
            cat_data["status"] = "alive"
            cat_data["fullness"] = 30
            cat_data["critical_since"] = 0
            cat_data["last_decay"] = now
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._inc_stat(user_id, "rescue_count")
            self._check_achievement_titles(user_id)

            url = await self._fetch_image("happy")
            msg = (
                f"{cost_text}...经过紧张抢救!\n"
                f"[{cat_data['name']}] 终于脱离了危险!\n"
                f"饱食度恢复到 30，好好照顾它吧~"
            )
            await self._send_reply(event, msg, image_url=url, card_type="success")
        else:
            cat_data["status"] = "dead"
            cat_data["death_cause"] = "starve"
            cat_data["death_time"] = now
            self._add_title(user_id, DEATH_TITLES["starve"])
            self._inc_stat(user_id, "death_count")
            self._penalize_death(user_id)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._check_achievement_titles(user_id)

            url = await self._fetch_image("cry")
            msg = (
                f"{cost_text}...抢救室的灯熄灭了。\n"
                f"医生摇了摇头：「抱歉，我们尽力了。」\n"
                f"[{cat_data['name']}] 永远地闭上了眼睛...\n"
                f"获得头衔【{DEATH_TITLES['starve']}】\n"
                f"使用 /猫猫 重新开始"
            )
            await self._send_reply(event, msg, image_url=url, card_type="death")

    async def _handle_work(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status == "dead":
            await self._send_dead_message(event, cat_data)
            return
        if status == "critical":
            await self._send_critical_message(event, cat_data)
            return

        now = time.time()
        last_work = self._get_work_cooldown(user_id)
        remaining = 1800 - (now - last_work)
        if remaining > 0:
            mins = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫还在打工中，{mins}分钟后再来~")
            return

        if cat_data["fullness"] < 5:
            await self._send_reply(event, "猫猫太饿了，先喂食吧!", card_type="danger")
            return

        attrs = self._get_attrs(user_id)
        edu_level = self._get_edu(user_id)
        edu_name = EDU_LEVELS[edu_level]["name"]
        available_jobs = list(JOBS.get(edu_level, JOBS[0]))

        for hj in HIDDEN_JOBS:
            show = True
            if "req_int" in hj and attrs["int"] < hj["req_int"]:
                show = False
            if "req_cha" in hj and attrs["cha"] < hj["req_cha"]:
                show = False
            if "req_rep" in hj and hj["req_rep"] is not None:
                if hj["req_rep"] >= 0 and attrs["rep"] < hj["req_rep"]:
                    show = False
                if hj["req_rep"] < 0 and attrs["rep"] > hj["req_rep"]:
                    show = False
            if show:
                available_jobs.append(hj)

        lines = [f"打工 学历:{edu_name}\n"]
        for i, job in enumerate(available_jobs, 1):
            tag = ""
            if job in HIDDEN_JOBS:
                tag = " [隐藏]"
            lines.append(
                f"{i}. {job['name']}{tag} ({job['earn_min']}-{job['earn_max']}金币)"
            )
        lines.append("\n输入编号打工 | 0 返回")
        await self._send_reply(event, "\n".join(lines))

        choice = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(available_jobs)
        )
        if choice is None or choice == 0:
            return

        job_idx = choice - 1

        job = available_jobs[job_idx]
        earnings = random.randint(job["earn_min"], job["earn_max"])
        fullness_loss = random.randint(job["nrg_min"], job["nrg_max"])

        stat_key = job.get("stat", "hp")
        stat_val = attrs.get(stat_key, 0)
        if stat_val >= 60:
            bonus = int(earnings * 0.15)
            earnings += bonus
        elif stat_val >= 30:
            bonus = int(earnings * 0.05)
            earnings += bonus

        buffs = self._get_buffs(user_id)
        if buffs.get("work_double"):
            earnings *= 2
            buffs["work_double"] = False
            self._set_buffs(user_id, buffs)

        cat_data["fullness"] = max(0, cat_data["fullness"] - fullness_loss)
        self._mod_attr(user_id, "hp", -random.randint(2, 6))
        self._mod_attr(user_id, "rep", 1)

        death_chance = min(0.3, 0.15 + edu_level * 0.02)
        if cat_data["fullness"] == 0 and random.random() < death_chance:
            cat_data["status"] = "dead"
            cat_data["death_cause"] = "overwork"
            cat_data["death_time"] = now
            self._add_title(user_id, DEATH_TITLES["overwork"])
            self._inc_stat(user_id, "death_count")
            self._penalize_death(user_id)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._add_coins(user_id, earnings)
            self._inc_stat(user_id, "work_count")
            self._set_work_cooldown(user_id)
            self._check_achievement_titles(user_id)

            url = await self._fetch_image("cry")
            msg = (
                f"[{cat_data['name']}] 在{job['name']}途中因过度劳累倒下了...\n"
                f"它带着赚到的 {earnings} 金币，永远地去了喵星。\n"
                f"获得头衔【{DEATH_TITLES['overwork']}】"
            )
            await self._send_reply(event, msg, image_url=url, card_type="death")
            return

        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self._add_coins(user_id, earnings)
        self._inc_stat(user_id, "work_count")
        self._set_work_cooldown(user_id)
        self._check_achievement_titles(user_id)

        url = await self._fetch_image("happy")
        msgs = [
            f"[{cat_data['name']}] {job['name']}回来啦! 赚了 {earnings} 金币~",
            f"{job['name']}完成! +{earnings} 金币!",
            f"辛苦{job['name']}! {earnings} 金币入袋!",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _handle_catch(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status == "dead":
            await self._send_dead_message(event, cat_data)
            return
        if status == "critical":
            await self._send_critical_message(event, cat_data)
            return

        await self._send_reply(event, "请 @你想抓的猫猫的主人:")
        args = await self._wait_choice(event)
        if not args:
            return

        if not args:
            await self._send_reply(event, "已取消")
            return

        target_id = args.strip()
        if target_id == user_id:
            await self._send_reply(event, "不能抓自己的猫猫!")
            return

        target_cat = self._get_cat(target_id)
        if not target_cat or target_cat.get("status") != "alive":
            await self._send_reply(event, "对方没有可抓的猫猫~")
            return

        now = time.time()
        last_catch = self._get_catch_cooldown(user_id)
        remaining = 3600 - (now - last_catch)
        if remaining > 0:
            mins = int(remaining // 60) + 1
            await self._send_reply(event, f"你的猫猫还在休息，{mins}分钟后再来~")
            return

        if cat_data["fullness"] < 5:
            await self._send_reply(event, "你的猫猫太饿了，先喂食!", card_type="danger")
            return

        catch_rate = max(20, 60 - target_cat["intimacy"] * 0.4)

        buffs = self._get_buffs(user_id)
        if buffs.get("catch_boost"):
            catch_rate = min(100, catch_rate + 25)
            buffs["catch_boost"] = False
            self._set_buffs(user_id, buffs)

        died = False
        if random.random() * 100 < catch_rate:
            earnings = random.randint(30, 80)
            target_loss = random.randint(15, 25)
            my_loss = random.randint(5, 10)

            if buffs.get("work_double"):
                earnings *= 2
                buffs["work_double"] = False
                self._set_buffs(user_id, buffs)

            target_cat["fullness"] = max(0, target_cat["fullness"] - target_loss)
            cat_data["fullness"] = max(0, cat_data["fullness"] - my_loss)

            if cat_data["fullness"] == 0 and random.random() < 0.15:
                cat_data["status"] = "dead"
                cat_data["death_cause"] = "overwork"
                cat_data["death_time"] = now
                self._add_title(user_id, DEATH_TITLES["overwork"])
                self._inc_stat(user_id, "death_count")
                died = True

            self.sdk.storage.set(f"nekocare:{target_id}", target_cat)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._add_coins(user_id, earnings)
            self._inc_stat(user_id, "catch_count")
            self._inc_stat(target_id, "catched_count")
            self._set_catch_cooldown(user_id)
            self._check_achievement_titles(user_id)

            if died:
                url = await self._fetch_image("cry")
                msg = (
                    f"成功抓到 [{target_cat['name']}]! 赚了 {earnings} 金币!\n"
                    f"但 [{cat_data['name']}] 因体力不支倒下了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url, card_type="death")
                return

            url = await self._fetch_image("neko")
            msgs = [
                f"成功抓到 [{target_cat['name']}] 打工! +{earnings} 金币!",
                f"[{target_cat['name']}] 被抓去打工啦! 收获 {earnings} 金币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="success"
            )
        else:
            my_loss = random.randint(5, 10)
            cat_data["fullness"] = max(0, cat_data["fullness"] - my_loss)

            if cat_data["fullness"] == 0 and random.random() < 0.1:
                cat_data["status"] = "dead"
                cat_data["death_cause"] = "overwork"
                cat_data["death_time"] = now
                self._add_title(user_id, DEATH_TITLES["overwork"])
                self._inc_stat(user_id, "death_count")
                self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
                self._inc_stat(user_id, "catch_count")
                self._set_catch_cooldown(user_id)
                self._check_achievement_titles(user_id)

                url = await self._fetch_image("cry")
                msg = (
                    f"[{target_cat['name']}] 跑掉了!\n"
                    f"[{cat_data['name']}] 追逐时累倒了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url, card_type="death")
                return

            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._set_catch_cooldown(user_id)

            url = await self._fetch_image("cry")
            msgs = [
                f"[{target_cat['name']}] 挣脱跑掉了! 还累了 {my_loss} 饱食度~",
                f"抓捕失败! [{target_cat['name']}] 太机灵了!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="danger"
            )

    async def _handle_rob(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status != "alive":
            await self._send_reply(event, "猫猫状态不对，无法打劫~")
            return

        attrs = self._get_attrs(user_id)
        if attrs["hp"] < 10:
            await self._send_reply(event, "你的猫猫太虚弱了，先休息恢复体力吧!")
            return

        now = time.time()
        last_rob = self._get_rob_cooldown(user_id)
        remaining = ROB_COOLDOWN - (now - last_rob)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫还在躲风头，{m}分钟后再来~")
            return

        menu = (
            "打劫\n\n"
            "1. 打劫野外猫猫 (低风险低回报)\n"
            "2. 打劫其他玩家 (高风险高回报)\n"
            "3. 抢劫地点 (便利店/加油站/ATM/珠宝店/银行)\n"
            "4. 黑市 (购买作案工具)\n"
            "0. 返回"
        )
        await self._send_reply(event, menu)

        mode = await self._wait_choice(event, choices=["0", "1", "2", "3", "4"])
        if mode is None or mode == "0":
            return

        if mode == "1":
            await self._do_rob_npc(event, user_id, cat_data, attrs)
        elif mode == "2":
            await self._do_rob_player(event, user_id, cat_data, attrs)
        elif mode == "3":
            await self._handle_rob_target(event, user_id, cat_data, attrs)
        elif mode == "4":
            await self._handle_blackmarket(event, user_id)

    async def _do_rob_npc(self, event, user_id, cat_data, attrs):
        now = time.time()
        last_rob = self._get_rob_cooldown(user_id)
        remaining = 900 - (now - last_rob)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫还在躲风头，{m}分钟后再来~")
            return

        target = random.choice(NPC_CATS)
        loot = random.randint(ROB_NPC_LOOT["min"], ROB_NPC_LOOT["max"])
        success_rate = min(85, max(20, 40 + attrs["cha"] * 0.4 + attrs["hp"] * 0.2))

        cat_data["fullness"] = max(0, cat_data["fullness"] - random.randint(3, 8))
        self._mod_attr(user_id, "hp", -random.randint(3, 10))
        self._set_rob_cooldown(user_id)

        police_chance = 5
        if attrs["rep"] < -20:
            police_chance += abs(attrs["rep"]) * 0.3

        if random.random() * 100 < police_chance:
            edu_level = self._get_edu(user_id)
            fine = random.randint(30, 80) + edu_level * 10
            actual_fine = min(fine, self._get_coins(user_id))
            self._add_coins(user_id, -actual_fine)
            self._mod_attr(user_id, "rep", -5)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            url = await self._fetch_image("cry")
            await self._send_reply(
                event,
                f"打劫[{target}]时被猫警抓住了!\n"
                f"罚款 {actual_fine} 金币，声望-5\n"
                f"(学历越高罚款越重哦~)",
                image_url=url,
                card_type="danger",
            )
            return

        if random.random() * 100 < success_rate:
            self._add_coins(user_id, loot)
            self._mod_attr(user_id, "rep", random.randint(-8, -3))
            self._mod_attr(user_id, "cha", random.randint(0, 1))
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            url = await self._fetch_image("neko")
            msgs = [
                f"成功打劫了[{target}]! 抢到 {loot} 金币!",
                f"从[{target}]身上摸到了 {loot} 金币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="success"
            )
        else:
            penalty = random.randint(5, 15)
            actual_penalty = min(penalty, self._get_coins(user_id))
            self._add_coins(user_id, -actual_penalty)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            url = await self._fetch_image("cry")
            msgs = [
                f"[{target}] 太机灵了! 打劫失败，倒赔 {actual_penalty} 金币~",
                f"被[{target}]揍了一顿! 损失 {actual_penalty} 金币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="danger"
            )

    async def _do_rob_player(self, event, user_id, cat_data, attrs):
        now = time.time()
        last_rob = self._get_rob_cooldown(user_id)
        remaining = ROB_COOLDOWN - (now - last_rob)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"猫猫还在躲风头，{m}分钟后再来~")
            return

        await self._send_reply(event, "请 @你想打劫的目标:")
        args = await self._wait_choice(event)
        if not args:
            return

        target_id = args.strip()
        if target_id == user_id:
            await self._send_reply(event, "不能打劫自己!")
            return

        target_coins = self._get_coins(target_id)
        if target_coins <= 0:
            await self._send_reply(event, "对方身无分文，打劫个寂寞~")
            return

        target_cat = self._get_cat(target_id)
        success_rate = min(80, max(15, 30 + attrs["cha"] * 0.5))

        cat_data["fullness"] = max(0, cat_data["fullness"] - random.randint(5, 15))
        self._mod_attr(user_id, "hp", -random.randint(5, 15))
        self._set_rob_cooldown(user_id)

        police_chance = 8
        if attrs["rep"] < -20:
            police_chance += abs(attrs["rep"]) * 0.4
        edu_level = self._get_edu(user_id)

        if random.random() * 100 < police_chance:
            fine = random.randint(50, 150) + edu_level * 15
            actual_fine = min(fine, self._get_coins(user_id))
            self._add_coins(user_id, -actual_fine)
            self._mod_attr(user_id, "rep", -10)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            target_name = target_cat["name"] if target_cat else "对方"
            url = await self._fetch_image("cry")
            await self._send_reply(
                event,
                f"打劫[{target_name}]时被猫警巡逻队抓住了!\n"
                f"罚款 {actual_fine} 金币，声望-10",
                image_url=url,
                card_type="danger",
            )
            return

        if random.random() * 100 < success_rate:
            steal_pct = random.uniform(0.2, 0.5)
            stolen = max(1, int(target_coins * steal_pct))

            self._add_coins(user_id, stolen)
            self._add_coins(target_id, -stolen)
            self._mod_attr(user_id, "rep", random.randint(-12, -5))
            self._mod_attr(user_id, "cha", random.randint(0, 2))

            if cat_data["fullness"] == 0 and random.random() < 0.1:
                cat_data["status"] = "dead"
                cat_data["death_cause"] = "overwork"
                cat_data["death_time"] = time.time()
                self._add_title(user_id, DEATH_TITLES["overwork"])
                self._inc_stat(user_id, "death_count")
                self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

                url = await self._fetch_image("cry")
                msg = (
                    f"打劫成功! 抢了 {stolen} 金币!\n"
                    f"但 [{cat_data['name']}] 在逃跑途中累倒了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url, card_type="death")
                return

            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            url = await self._fetch_image("neko")
            msgs = [
                f"打劫成功! 抢了 {stolen} 金币! (声望下降...)",
                f"[{cat_data['name']}] 成功打劫! +{stolen} 金币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="success"
            )
        else:
            penalty = random.randint(10, 30)
            actual_penalty = min(penalty, self._get_coins(user_id))
            self._add_coins(user_id, -actual_penalty)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            url = await self._fetch_image("cry")
            target_name = target_cat["name"] if target_cat else "对方猫猫"
            msgs = [
                f"打劫失败! 被[{target_name}] 发现了，赔偿 {actual_penalty} 金币!",
                f"[{cat_data['name']}] 打劫扑空了，倒赔 {actual_penalty} 金币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="danger"
            )

    async def _handle_blackmarket(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return
            coins = self._get_coins(user_id)
            inv = self._get_inventory(user_id)

            lines = [f"黑市  金币:{coins}\n"]
            lines.append("--- 购买 ---")
            for i, name in enumerate(BLACKMARKET_ITEM_LIST, 1):
                item = BLACKMARKET_ITEMS[name]
                count = inv.get(name, 0)
                lines.append(
                    f"{i}. {name} {item['price']}金币 (持有:{count}) {item['desc']}"
                )
            lines.append("\n输入编号购买 | 0 返回")
            await self._send_reply(event, "\n".join(lines))

            choice = await self._wait_choice(
                event, expect="int", min_val=0, max_val=len(BLACKMARKET_ITEM_LIST)
            )
            if choice is None or choice == 0:
                return

            idx = choice - 1
            item_name = BLACKMARKET_ITEM_LIST[idx]
            item = BLACKMARKET_ITEMS[item_name]
            coins = self._get_coins(user_id)

            if coins < item["price"]:
                await self._send_reply(
                    event,
                    f"金币不足! 需要 {item['price']}，你只有 {coins}",
                    card_type="danger",
                )
                continue

            self._add_coins(user_id, -item["price"])
            self._add_inventory(user_id, item_name, 1)

            if item["tool_tag"] == "bank_code":
                self._remove_inventory(user_id, item_name, 1)
                self._set_buffs(
                    user_id, {**self._get_buffs(user_id), "bank_code": True}
                )
                await self._send_reply(
                    event,
                    f"购买了【{item_name}】! 已记住银行密码。(一次性)",
                    card_type="success",
                )
            elif item["tool_tag"] == "disguise":
                self._remove_inventory(user_id, item_name, 1)
                self._set_buffs(
                    user_id, {**self._get_buffs(user_id), "has_disguise": True}
                )
                await self._send_reply(
                    event,
                    f"购买了【{item_name}】! 面部遮挡已装备。(一次性)",
                    card_type="success",
                )
            else:
                await self._send_reply(
                    event, f"购买了【{item_name}】! 已放入背包。", card_type="success"
                )

    async def _handle_rob_target(self, event, user_id, cat_data, attrs):
        while True:
            if user_id in self._timed_out_users:
                return

            inv = self._get_inventory(user_id)
            buffs = self._get_buffs(user_id)
            tool_tags = set()
            for bname, bval in buffs.items():
                if bval and bval is True:
                    tag = (
                        bname.replace("has_", "") if bname.startswith("has_") else bname
                    )
                    tool_tags.add(tag)
            for item_name, count in inv.items():
                if item_name in BLACKMARKET_ITEMS and count > 0:
                    tool_tags.add(BLACKMARKET_ITEMS[item_name]["tool_tag"])

            lines = ["抢劫目标\n"]
            lines.append("--- 持有工具 ---")
            if tool_tags:
                tag_labels = {
                    "melee": "近战武器",
                    "disguise": "面部遮挡",
                    "explosive": "炸药",
                    "bank_code": "银行密码",
                    "drill": "钻机",
                    "pry_bar": "撬棍",
                    "getaway": "逃跑载具",
                }
                lines.append(
                    "  " + ", ".join(tag_labels.get(t, str(t)) for t in tool_tags)
                )
            else:
                lines.append("  无 (去黑市购买作案工具)")
            lines.append("")

            now = time.time()
            for i, tname in enumerate(ROB_TARGET_LIST, 1):
                target = ROB_TARGETS[tname]
                req_met = all(r in tool_tags for r in target["require"])
                cd_key = f"nekocare_rob_{tname}_cd:{user_id}"
                last_cd = self.sdk.storage.get(cd_key)
                cd_left = 0
                if last_cd:
                    cd_left = max(0, target["cooldown"] - (now - last_cd))
                cd_text = ""
                if cd_left > 0:
                    if cd_left >= 3600:
                        cd_text = f" (冷却{int(cd_left // 3600)}时{int((cd_left % 3600) // 60)}分)"
                    else:
                        cd_text = f" (冷却{int(cd_left // 60) + 1}分)"
                status = "✓" if req_met else "✗缺工具"
                lines.append(
                    f"{i}. {tname} [{status}]{cd_text}"
                    f" 收益:{target['loot_min']}-{target['loot_max']}"
                )
            lines.append("\n输入编号 | 0 返回")
            await self._send_reply(event, "\n".join(lines))

            choice = await self._wait_choice(
                event, expect="int", min_val=0, max_val=len(ROB_TARGET_LIST)
            )
            if choice is None or choice == 0:
                return

            tname = ROB_TARGET_LIST[choice - 1]
            target = ROB_TARGETS[tname]

            req_met = all(r in tool_tags for r in target["require"])
            if not req_met:
                req_names = []
                for r in target["require"]:
                    tag_labels = {
                        "melee": "近战武器(棒球棍)",
                        "disguise": "面部遮挡(黑丝头套)",
                        "explosive": "炸药",
                        "bank_code": "银行密码",
                        "drill": "钻机",
                        "pry_bar": "撬棍",
                        "getaway": "逃跑载具",
                    }
                    req_names.append(tag_labels.get(r, r))
                await self._send_reply(
                    event,
                    f"缺少必备工具: {', '.join(req_names)}\n去黑市购买后再来!",
                    card_type="danger",
                )
                continue

            cd_key = f"nekocare_rob_{tname}_cd:{user_id}"
            last_cd = self.sdk.storage.get(cd_key)
            now = time.time()
            if last_cd and (now - last_cd) < target["cooldown"]:
                cd_left = target["cooldown"] - (now - last_cd)
                if cd_left >= 3600:
                    cd_text = f"{int(cd_left // 3600)}时{int((cd_left % 3600) // 60)}分"
                else:
                    cd_text = f"{int(cd_left // 60) + 1}分"
                await self._send_reply(
                    event, f"太近了，{cd_text}后再来!", card_type="warning"
                )
                continue

            if cat_data["fullness"] < 10:
                await self._send_reply(event, "猫猫太饿了，先喂食!", card_type="danger")
                return

            consumed_tools = []
            for r in target["require"]:
                if r == "bank_code":
                    buffs = self._get_buffs(user_id)
                    buffs.pop("bank_code", None)
                    self._set_buffs(user_id, buffs)
                    consumed_tools.append("银行密码")
                elif r == "disguise":
                    buffs = self._get_buffs(user_id)
                    buffs.pop("has_disguise", None)
                    self._set_buffs(user_id, buffs)
                    consumed_tools.append("黑丝头套")
                else:
                    for bname in BLACKMARKET_ITEM_LIST:
                        bitem = BLACKMARKET_ITEMS[bname]
                        if bitem["tool_tag"] == r:
                            if inv.get(bname, 0) > 0:
                                self._remove_inventory(user_id, bname, 1)
                                consumed_tools.append(bname)
                                break

            for opt in target.get("optional", []):
                if opt == "disguise":
                    buffs = self._get_buffs(user_id)
                    if buffs.pop("has_disguise", None):
                        self._set_buffs(user_id, buffs)
                        consumed_tools.append("黑丝头套")
                elif opt == "getaway":
                    for bname in BLACKMARKET_ITEM_LIST:
                        bitem = BLACKMARKET_ITEMS[bname]
                        if bitem["tool_tag"] == opt:
                            if inv.get(bname, 0) > 0:
                                self._remove_inventory(user_id, bname, 1)
                                consumed_tools.append(bname)
                                break

            self.sdk.storage.set(cd_key, now)
            cat_data["fullness"] = max(0, cat_data["fullness"] - random.randint(5, 15))
            self._mod_attr(user_id, "hp", -random.randint(5, 15))
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

            success_rate = (
                target["base_success"] + attrs["cha"] * 0.3 + attrs["hp"] * 0.1
            )
            police_chance = target["police_base"]
            if attrs["rep"] < -20:
                police_chance += abs(attrs["rep"]) * 0.3
            if (
                "disguise" in target.get("optional", [])
                and "黑丝头套" in consumed_tools
            ):
                police_chance *= 0.5
            if "getaway" in target.get("optional", []) and any(
                "车" in t for t in consumed_tools
            ):
                police_chance *= 0.6
            police_chance = min(50, police_chance)

            if random.random() * 100 < police_chance:
                edu_level = self._get_edu(user_id)
                fine = (
                    random.randint(target["loot_min"], target["loot_max"])
                    + edu_level * 10
                )
                actual_fine = min(fine, self._get_coins(user_id))
                self._add_coins(user_id, -actual_fine)
                self._mod_attr(user_id, "rep", -random.randint(10, 20))

                url = await self._fetch_image("cry")
                await self._send_reply(
                    event,
                    f"抢劫{tname}时被猫警抓住了!\n"
                    f"罚款 {actual_fine} 金币，声望大幅下降\n"
                    f"消耗工具: {', '.join(consumed_tools)}",
                    image_url=url,
                    card_type="danger",
                )
                self._check_achievement_titles(user_id)
                continue

            if random.random() * 100 < success_rate:
                loot = random.randint(target["loot_min"], target["loot_max"])
                if attrs["cha"] >= 60:
                    loot = int(loot * 1.15)
                self._add_coins(user_id, loot)
                self._mod_attr(user_id, "rep", -target["rep_loss"])
                self._inc_stat(user_id, "rob_target_count")

                url = await self._fetch_image("neko")
                msgs = [
                    f"成功抢劫{tname}! 抢到 {loot} 金币!",
                    f"[{cat_data['name']}] 从 {tname} 弄到了 {loot} 金币!",
                ]
                await self._send_reply(
                    event,
                    random.choice(msgs) + f"\n消耗工具: {', '.join(consumed_tools)}",
                    image_url=url,
                    card_type="success",
                )
                self._check_achievement_titles(user_id)
            else:
                penalty = random.randint(
                    target["loot_min"] // 2, target["loot_max"] // 2
                )
                actual_penalty = min(penalty, self._get_coins(user_id))
                self._add_coins(user_id, -actual_penalty)
                self._mod_attr(user_id, "rep", -target["rep_loss"] // 2)

                url = await self._fetch_image("cry")
                msgs = [
                    f"抢劫{tname}失败! 被保安发现了，赔偿 {actual_penalty} 金币!",
                    f"[{cat_data['name']}] 在 {tname} 扑了个空，倒赔 {actual_penalty} 金币!",
                ]
                await self._send_reply(
                    event,
                    random.choice(msgs) + f"\n消耗工具: {', '.join(consumed_tools)}",
                    image_url=url,
                    card_type="danger",
                )
                self._check_achievement_titles(user_id)

    async def _handle_study(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~", card_type="danger")
            return
        if status != "alive":
            await self._send_reply(event, "猫猫状态不对，无法学习~")
            return

        edu_level = self._get_edu(user_id)
        edu_name = EDU_LEVELS[edu_level]["name"]

        if edu_level >= max(EDU_LEVELS.keys()):
            await self._send_reply(event, f"你已经是{edu_name}了，学无可学!")
            return

        next_level = edu_level + 1
        next_info = EDU_LEVELS[next_level]
        progress = self._get_study_progress(user_id)
        attrs = self._get_attrs(user_id)

        bar_len = 10
        filled = int(progress / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        menu = (
            f"学习深造\n\n"
            f"当前学历: {edu_name}\n"
            f"目标: {next_info['name']} (学费:{next_info['cost']}金币)\n"
            f"学习进度: [{bar}] {progress}%\n"
            f"智力: {attrs['int']}\n\n"
            f"1. 认真学习 (进度+25 智力+1~3)\n"
            f"2. 正常学习 (进度+15)\n"
            f"3. 摸鱼 (进度+5 魅力+1~2)\n"
            f"0. 返回"
        )
        await self._send_reply(event, menu)

        choice = await self._wait_choice(event, choices=["0", "1", "2", "3"])
        if choice is None or choice == "0":
            return

        now = time.time()
        last_study = self._get_edu_cd(user_id)
        remaining = 1800 - (now - last_study)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"学习太累了，休息{m}分钟再来~")
            return

        if choice == "1":
            int_gain = random.randint(1, 3)
            hp_loss = random.randint(3, 8)
            progress = min(100, progress + 25 + attrs["int"] // 20)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"认真学习了! 进度 [{bar}] {progress}% 智力+{int_gain}\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 金币才能毕业 !!\n"
                    f"凑够学费后再来学习，无需等待冷却~",
                    card_type="warning",
                )
                return

            self._mod_attr(user_id, "int", int_gain)
            self._mod_attr(user_id, "hp", -hp_loss)
            self._set_study_progress(user_id, progress)
            self._set_edu_cd(user_id)

            if progress >= 100:
                self._add_coins(user_id, -next_info["cost"])
                self._set_edu(user_id, next_level)
                self._set_study_progress(user_id, 0)
                url = await self._fetch_image("neko")
                await self._send_reply(
                    event,
                    f"认真学习了! 进度 [{bar}] {progress}%\n"
                    f"恭喜! [{cat_data['name']}] 获得{next_info['name']}学历!\n"
                    f"解锁了新的工作机会!",
                    image_url=url,
                    card_type="success",
                )
            else:
                url = await self._fetch_image("neko")
                await self._send_reply(
                    event,
                    f"认真学习了! 进度 [{bar}] {progress}% 智力+{int_gain}",
                    image_url=url,
                    card_type="success",
                )
        elif choice == "2":
            progress = min(100, progress + 15)
            hp_loss = random.randint(2, 5)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"正常学习完成! 进度 [{bar}] {progress}%\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 金币才能毕业 !!\n"
                    f"凑够学费后再来学习~",
                    card_type="warning",
                )
                return

            self._mod_attr(user_id, "hp", -hp_loss)
            self._set_study_progress(user_id, progress)
            self._set_edu_cd(user_id)

            if progress >= 100:
                self._add_coins(user_id, -next_info["cost"])
                self._set_edu(user_id, next_level)
                self._set_study_progress(user_id, 0)
                url = await self._fetch_image("neko")
                await self._send_reply(
                    event,
                    f"正常学习完成! 进度 [{bar}] {progress}%\n"
                    f"恭喜! [{cat_data['name']}] 获得{next_info['name']}学历!",
                    image_url=url,
                    card_type="success",
                )
            else:
                await self._send_reply(
                    event,
                    f"正常学习完成! 进度 [{bar}] {progress}%",
                    card_type="success",
                )
        elif choice == "3":
            progress = min(100, progress + 5)
            cha_gain = random.randint(1, 2)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"摸鱼了一节课... 进度 [{bar}] {progress}% 魅力+{cha_gain}\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 金币才能毕业 !!\n"
                    f"凑够学费后再来学习~",
                    card_type="warning",
                )
                return

            if random.random() < 0.3:
                self._mod_attr(user_id, "int", -1)
            self._mod_attr(user_id, "cha", cha_gain)
            self._set_study_progress(user_id, progress)
            self._set_edu_cd(user_id)

            if progress >= 100:
                self._add_coins(user_id, -next_info["cost"])
                self._set_edu(user_id, next_level)
                self._set_study_progress(user_id, 0)
                url = await self._fetch_image("sleep")
                await self._send_reply(
                    event,
                    f"摸鱼了一节课... 进度 [{bar}] {progress}%\n"
                    f"居然也毕业了! 获得{next_info['name']}学历!",
                    image_url=url,
                    card_type="success",
                )
            else:
                url = await self._fetch_image("sleep")
                msgs = [
                    f"摸鱼了一节课... 进度 [{bar}] {progress}% 魅力+{cha_gain}",
                    f"上课偷偷睡觉，被老师发现了! 进度 [{bar}] {progress}%",
                ]
                await self._send_reply(
                    event, random.choice(msgs), image_url=url, card_type="success"
                )

    async def _handle_bank(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return

            bank = self._calc_bank_interest(user_id)
            loan = self._calc_loan_interest(user_id)
            fd = self._calc_fixed_interest(user_id)
            coins = self._get_coins(user_id)
            attrs = self._get_attrs(user_id)

            loan_rate = BANK_MAX_LOAN_RATE * 100
            if attrs["rep"] >= 30:
                loan_rate *= 0.7
            elif attrs["rep"] < -20:
                loan_rate *= 1.5

            max_loan = 500 * self._get_edu(user_id)
            if attrs["rep"] < -30:
                max_loan = 0

            fd_info = ""
            if fd["amount"] > 0:
                elapsed = time.time() - fd["start_time"]
                remain = max(0, BANK_FIXED_TERM - elapsed)
                h = int(remain // 3600)
                m = int((remain % 3600) // 60)
                fd_info = f"\n定期存款: {fd['amount']} 金币 (含利息{fd['interest']}) 剩余{h}时{m}分"

            menu = (
                f"喵喵银行\n\n"
                f"活期存款: {bank['deposit']} 金币\n"
                f"钱包: {coins} 金币\n"
                f"贷款: {loan['amount']} 金币 (利率{loan_rate:.1f}%/24h)\n"
                f"活期利率: {BANK_INTEREST_REGULAR * 100}% | 定期利率: {BANK_INTEREST_FIXED * 100}%\n"
                f"最大贷款: {max_loan} 金币{fd_info}\n\n"
                f"1. 活期存款/取款\n"
                f"2. 定期存款\n"
                f"3. 贷款/还款\n"
                f"4. 转账\n"
                f"5. 股票市场\n"
                f"6. 理财投资\n"
                f"0. 返回"
            )
            await self._send_reply(event, menu)

            choice = await self._wait_choice(
                event, choices=["0", "1", "2", "3", "4", "5", "6"]
            )
            if choice is None or choice == "0":
                return
            elif choice == "1":
                await self._send_reply(
                    event,
                    "1. 存款  2. 取款  0. 返回",
                )
                sub = await self._wait_choice(event, choices=["0", "1", "2"])
                if sub == "1":
                    await self._handle_deposit(event, user_id)
                elif sub == "2":
                    await self._handle_withdraw(event, user_id)
            elif choice == "2":
                await self._handle_fixed_deposit(event, user_id)
            elif choice == "3":
                await self._send_reply(
                    event,
                    "1. 贷款  2. 还款  0. 返回",
                )
                sub = await self._wait_choice(event, choices=["0", "1", "2"])
                if sub == "1":
                    await self._handle_loan_borrow(event, user_id)
                elif sub == "2":
                    await self._handle_loan_repay(event, user_id)
            elif choice == "4":
                await self._handle_transfer(event, user_id)
            elif choice == "5":
                await self._handle_stocks(event, user_id)
            elif choice == "6":
                await self._handle_invest(event, user_id)

    async def _handle_deposit(self, event, user_id):
        coins = self._get_coins(user_id)
        bank = self._get_bank(user_id)

        await self._send_reply(
            event,
            f"当前存款: {bank['deposit']} | 钱包: {coins} 金币\n最高存款: {BANK_MAX_DEPOSIT}\n请输入存款金额:",
        )

        amount = await self._wait_choice(event, expect="int", min_val=1)
        if amount is None:
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"钱包只有 {coins} 金币!")
            return

        bank = self._get_bank(user_id)
        new_deposit = bank["deposit"] + amount
        if new_deposit > BANK_MAX_DEPOSIT:
            max_allowed = BANK_MAX_DEPOSIT - bank["deposit"]
            await self._send_reply(event, f"将超出上限，最多还能存 {max_allowed} 金币")
            return

        self._add_coins(user_id, -amount)
        bank["deposit"] = new_deposit
        if bank["deposit"] == amount:
            bank["last_interest"] = time.time()
        self._set_bank(user_id, bank)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功存入 {amount} 金币! 当前存款: {bank['deposit']}",
            image_url=url,
            card_type="success",
        )

    async def _handle_withdraw(self, event, user_id):
        bank = self._get_bank(user_id)
        coins = self._get_coins(user_id)

        await self._send_reply(
            event,
            f"当前存款: {bank['deposit']} | 钱包: {coins} 金币\n请输入取款金额:",
        )

        amount = await self._wait_choice(event, expect="int", min_val=1)
        if amount is None:
            return

        bank = self._get_bank(user_id)
        if amount > bank["deposit"]:
            await self._send_reply(event, f"存款只有 {bank['deposit']} 金币!")
            return

        bank["deposit"] -= amount
        if bank["deposit"] == 0:
            bank["last_interest"] = time.time()
        self._set_bank(user_id, bank)
        self._add_coins(user_id, amount)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功取出 {amount} 金币! 当前存款: {bank['deposit']}",
            image_url=url,
            card_type="success",
        )

    async def _handle_fixed_deposit(self, event, user_id):
        fd = self._get_fixed_deposit(user_id)
        if fd["amount"] > 0:
            elapsed = time.time() - fd["start_time"]
            matured = elapsed >= BANK_FIXED_TERM
            if matured:
                fd_calc = self._calc_fixed_interest(user_id)
                total = fd_calc["amount"] + fd_calc["interest"]
                self._add_coins(user_id, total)
                self._set_fixed_deposit(user_id, {"amount": 0, "start_time": 0.0})
                url = await self._fetch_image("happy")
                await self._send_reply(
                    event,
                    f"定期存款到期! 本金 {fd_calc['amount']} + 利息 {fd_calc['interest']} = {total} 金币已到账!",
                    image_url=url,
                    card_type="success",
                )
            else:
                h = int((BANK_FIXED_TERM - elapsed) // 3600)
                m = int(((BANK_FIXED_TERM - elapsed) % 3600) // 60)
                penalty = int(fd["amount"] * BANK_FIXED_PENALTY)
                await self._send_reply(
                    event,
                    f"定期存款: {fd['amount']} 金币 (还需{h}时{m}分到期)\n"
                    f"提前取出将损失 {penalty} 金币 ({int(BANK_FIXED_PENALTY * 100)}%违约金)\n\n"
                    f"1. 提前取出\n"
                    f"0. 返回",
                )
                choice = await self._wait_choice(event, choices=["0", "1"])
                if choice == "1":
                    fd_calc = self._calc_fixed_interest(user_id)
                    recv = fd_calc["amount"] - penalty
                    if fd_calc["interest"] > penalty:
                        recv += fd_calc["interest"] - penalty
                    self._add_coins(user_id, max(0, recv))
                    self._set_fixed_deposit(user_id, {"amount": 0, "start_time": 0.0})
                    await self._send_reply(
                        event, f"提前取出! 扣除违约金后获得 {max(0, recv)} 金币"
                    )
            return

        coins = self._get_coins(user_id)
        await self._send_reply(
            event,
            f"定期存款\n\n"
            f"钱包: {coins} 金币\n"
            f"定期利率: {BANK_INTEREST_FIXED * 100}% / 24小时\n"
            f"期限: 24小时 | 提前取出违约金 {int(BANK_FIXED_PENALTY * 100)}%\n\n"
            f"请输入存入金额 (0 返回):",
        )

        amount = await self._wait_choice(event, expect="int", min_val=0)
        if amount is None or amount <= 0:
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"金币不足! 只有 {coins}", card_type="danger")
            return

        self._add_coins(user_id, -amount)
        self._set_fixed_deposit(user_id, {"amount": amount, "start_time": time.time()})
        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"存入定期 {amount} 金币! 24小时后到期~",
            image_url=url,
            card_type="success",
        )

    async def _handle_loan_borrow(self, event, user_id):
        attrs = self._get_attrs(user_id)
        loan = self._calc_loan_interest(user_id)
        if loan["amount"] > 0:
            await self._send_reply(
                event, f"你还有 {loan['amount']} 金币贷款未还! 先还清再借~"
            )
            return

        max_loan = 500 * self._get_edu(user_id)
        if attrs["rep"] < -30:
            await self._send_reply(event, "声望太低，银行拒绝贷款! 好好表现吧~")
            return

        loan_rate = BANK_MAX_LOAN_RATE * 100
        if attrs["rep"] >= 30:
            loan_rate *= 0.7

        await self._send_reply(
            event,
            f"贷款\n\n"
            f"最大可借: {max_loan} 金币\n"
            f"利率: {loan_rate:.1f}% / 24小时 (声望越高利率越低)\n"
            f"你的声望: {attrs['rep']}\n\n"
            f"请输入借款金额 (0 返回):",
        )

        amount = await self._wait_choice(
            event, expect="int", min_val=0, max_val=max_loan
        )
        if amount is None or amount <= 0:
            return

        self._set_loan(
            user_id,
            {"amount": amount, "principal": amount, "last_interest": time.time()},
        )
        self._add_coins(user_id, amount)
        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功贷款 {amount} 金币! 记得按时还款~",
            image_url=url,
            card_type="success",
        )

    async def _handle_loan_repay(self, event, user_id):
        loan = self._calc_loan_interest(user_id)
        if loan["amount"] <= 0:
            await self._send_reply(event, "你没有贷款~")
            return

        coins = self._get_coins(user_id)
        await self._send_reply(
            event,
            f"还款\n\n"
            f"贷款余额: {loan['amount']} 金币\n"
            f"你的金币: {coins}\n\n"
            f"1. 全部还清\n"
            f"2. 部分还款\n"
            f"0. 返回",
        )

        choice = await self._wait_choice(event, choices=["0", "1", "2"])
        if choice is None or choice == "0":
            return

        if choice == "1":
            repay = min(loan["amount"], coins)
            self._add_coins(user_id, -repay)
            new_amount = loan["amount"] - repay
            principal = loan.get("principal", new_amount)
            if new_amount <= 0:
                principal = 0
            self._set_loan(
                user_id,
                {
                    "amount": new_amount,
                    "principal": principal,
                    "last_interest": time.time(),
                },
            )
            self._mod_attr(user_id, "rep", 3)
            await self._send_reply(
                event, f"成功还款 {repay} 金币! 声望+3", card_type="success"
            )
        elif choice == "2":
            await self._send_reply(event, "请输入还款金额:")
            amount = await self._wait_choice(event, expect="int", min_val=1)
            if amount is None:
                return
            amount = min(amount, loan["amount"], coins)
            self._add_coins(user_id, -amount)
            new_amount = loan["amount"] - amount
            principal = loan.get("principal", new_amount)
            if new_amount <= 0:
                principal = 0
            self._set_loan(
                user_id,
                {
                    "amount": new_amount,
                    "principal": principal,
                    "last_interest": time.time(),
                },
            )
            await self._send_reply(
                event,
                f"成功还款 {amount} 金币! 剩余 {new_amount}",
                card_type="success",
            )

    async def _handle_transfer(self, event, user_id):
        coins = self._get_coins(user_id)
        await self._send_reply(
            event,
            f"转账\n\n你的金币: {coins}\n请输入转账目标 (@对方):",
        )

        target_str = await self._wait_choice(event)
        if not target_str:
            return
        target_id = target_str.strip()
        if target_id == user_id:
            await self._send_reply(event, "不能转给自己!")
            return

        await self._send_reply(event, "请输入转账金额:")
        amount = await self._wait_choice(event, expect="int", min_val=1)
        if amount is None:
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"金币不足! 只有 {coins}", card_type="danger")
            return

        self._add_coins(user_id, -amount)
        self._add_coins(target_id, amount)
        self._mod_attr(user_id, "rep", 2)
        await self._send_reply(
            event, f"成功转账 {amount} 金币! 声望+2", card_type="success"
        )

    async def _handle_stocks(self, event, user_id):
        while True:
            if user_id in self._timed_out_users:
                return

            prices = self._update_stock_prices()
            user_stocks = self._get_user_stocks(user_id)
            coins = self._get_coins(user_id)

            lines = [f"股票市场  钱包:{coins}金币\n"]
            for i, name in enumerate(STOCK_LIST, 1):
                held = user_stocks.get(name, 0)
                price = prices[name]
                change = price - STOCK_BASE_PRICES[name]
                sign = "+" if change >= 0 else ""
                lines.append(f"{i}. {name}  ¥{price} ({sign}{change})  持有:{held}股")
            lines.append("\n1.买入  2.卖出  0.返回")
            await self._send_reply(event, "\n".join(lines))

            choice = await self._wait_choice(event, choices=["0", "1", "2"])
            if choice is None or choice == "0":
                return
            if choice == "1":
                await self._handle_buy_stock(event, user_id, prices)
            elif choice == "2":
                await self._handle_sell_stock(event, user_id, prices)

    async def _handle_buy_stock(self, event, user_id, prices):
        coins = self._get_coins(user_id)
        lines = ["输入要购买的股票编号:\n"]
        for i, name in enumerate(STOCK_LIST, 1):
            lines.append(f"{i}. {name} ¥{prices[name]}")
        lines.append("0. 返回")
        await self._send_reply(event, "\n".join(lines))

        idx = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(STOCK_LIST)
        )
        if idx is None or idx == 0:
            return
        idx -= 1

        stock_name = STOCK_LIST[idx]
        price = prices[stock_name]
        await self._send_reply(event, f"{stock_name} 当前价: ¥{price}\n请输入购买数量:")

        qty = await self._wait_choice(event, expect="int", min_val=1)
        if qty is None:
            return

        total_cost = price * qty
        coins = self._get_coins(user_id)
        if total_cost > coins:
            await self._send_reply(
                event,
                f"金币不足! 需要 {total_cost}，你只有 {coins}",
                card_type="danger",
            )
            return

        self._add_coins(user_id, -total_cost)
        user_stocks = self._get_user_stocks(user_id)
        user_stocks[stock_name] = user_stocks.get(stock_name, 0) + qty
        self._set_user_stocks(user_id, user_stocks)

        await self._send_reply(
            event, f"买入 {stock_name} x{qty}! 花费 {total_cost} 金币"
        )

    async def _handle_sell_stock(self, event, user_id, prices):
        user_stocks = self._get_user_stocks(user_id)
        lines = ["输入要卖出的股票编号:\n"]
        has_stock = False
        for i, name in enumerate(STOCK_LIST, 1):
            held = user_stocks.get(name, 0)
            line = f"{i}. {name} ¥{prices[name]}"
            if held > 0:
                line += f"  持有:{held}股"
                has_stock = True
            lines.append(line)
        if not has_stock:
            await self._send_reply(event, "你没有任何股票~")
            return
        lines.append("0. 返回")
        await self._send_reply(event, "\n".join(lines))

        idx = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(STOCK_LIST)
        )
        if idx is None or idx == 0:
            return
        idx -= 1

        stock_name = STOCK_LIST[idx]
        user_stocks = self._get_user_stocks(user_id)
        held = user_stocks.get(stock_name, 0)
        if held <= 0:
            await self._send_reply(event, f"你没有持有 {stock_name}")
            return

        price = prices[stock_name]
        await self._send_reply(
            event, f"{stock_name} 当前价: ¥{price}  持有: {held}股\n请输入卖出数量:"
        )

        qty = await self._wait_choice(event, expect="int", min_val=1, max_val=held)
        if qty is None:
            return

        revenue = price * qty
        user_stocks[stock_name] = held - qty
        if user_stocks[stock_name] == 0:
            del user_stocks[stock_name]
        self._set_user_stocks(user_id, user_stocks)
        self._add_coins(user_id, revenue)

        profit = revenue - qty * STOCK_BASE_PRICES[stock_name]
        if profit != 0:
            sign = "+" if profit >= 0 else ""
            profit_text = f" (盈亏:{sign}{profit})"
        else:
            profit_text = ""
        await self._send_reply(
            event, f"卖出 {stock_name} x{qty}! 获得 {revenue} 金币{profit_text}"
        )

    async def _handle_invest(self, event, user_id):
        coins = self._get_coins(user_id)

        lines = ["理财投资\n"]
        for i, inv in enumerate(INVESTMENTS, 1):
            lines.append(
                f"{i}. {inv['name']}  投入:{inv['cost']}金币  "
                f"收益:{inv['profit_min']}-{inv['profit_max']}  "
                f"失败率:{int(inv['fail_rate'] * 100)}%"
            )
        lines.append(f"\n你的金币: {coins}")
        lines.append("\n输入编号投资 | 0 返回")
        await self._send_reply(event, "\n".join(lines))

        choice = await self._wait_choice(
            event, expect="int", min_val=0, max_val=len(INVESTMENTS)
        )
        if choice is None or choice == 0:
            return

        idx = choice - 1

        inv = INVESTMENTS[idx]
        coins = self._get_coins(user_id)

        if coins < inv["cost"]:
            await self._send_reply(
                event,
                f"金币不足! 需要 {inv['cost']}，你只有 {coins}",
                card_type="danger",
            )
            return

        self._add_coins(user_id, -inv["cost"])

        if random.random() < inv["fail_rate"]:
            self._inc_stat(user_id, "invest_count")
            self._inc_stat(user_id, "invest_lost", inv["cost"])
            url = await self._fetch_image("cry")
            await self._send_reply(
                event,
                f"{inv['name']}失败... 投入的 {inv['cost']} 金币打了水漂!",
                image_url=url,
                card_type="danger",
            )
        else:
            profit = random.randint(inv["profit_min"], inv["profit_max"])
            self._add_coins(user_id, inv["cost"] + profit)
            self._inc_stat(user_id, "invest_count")
            self._inc_stat(user_id, "invest_profit", profit)
            url = await self._fetch_image("happy")
            await self._send_reply(
                event,
                f"{inv['name']}成功! 投入 {inv['cost']}，回报 {inv['cost'] + profit} 金币! (净赚 {profit})",
                image_url=url,
                card_type="success",
            )
        self._check_achievement_titles(user_id)

    async def _handle_foster(self, event, user_id, cat_data):
        menu = (
            f"寄养 [{cat_data['name']}]\n\n"
            f"寄养期间猫猫不会饿肚子\n"
            f"费用: {FOSTER_COST_PER_DAY}金币/天 (接回时结算)\n"
            f"最多寄养 {FOSTER_MAX_DAYS} 天\n\n"
            f"1. 确认寄养\n"
            f"0. 取消"
        )
        await self._send_reply(event, menu)

        choice = await self._wait_choice(event, choices=["0", "1"])
        if choice is None or choice != "1":
            await self._send_reply(event, "已取消寄养")
            return

        now = time.time()
        cat_data["status"] = "fostered"
        cat_data["foster_time"] = now
        cat_data["foster_fullness"] = cat_data["fullness"]
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        url = await self._fetch_image("sleep")
        await self._send_reply(
            event,
            f"[{cat_data['name']}] 被送到了寄养家庭~\n"
            f"它会好好吃饭的，放心吧!\n"
            f"随时可以用菜单接它回家。",
            image_url=url,
            card_type="success",
        )

    async def _handle_unfoster(self, event, user_id, cat_data):
        cost = self._calc_foster_cost(cat_data)
        coins = self._get_coins(user_id)
        foster_days = self._get_foster_days(cat_data)

        menu = (
            f"接 [{cat_data['name']}] 回家\n\n"
            f"寄养天数: {foster_days} 天\n"
            f"寄养费用: {cost} 金币\n"
            f"你的金币: {coins} 枚\n\n"
            f"1. 确认接回\n"
            f"0. 取消"
        )
        await self._send_reply(event, menu)

        choice = await self._wait_choice(event, choices=["0", "1"])
        if choice is None or choice != "1":
            await self._send_reply(event, "已取消")
            return

        if coins < cost:
            await self._send_reply(
                event,
                f"金币不足! 需要 {cost} 枚，你只有 {coins} 枚",
                card_type="danger",
            )
            return

        self._add_coins(user_id, -cost)
        now = time.time()
        cat_data["status"] = "alive"
        cat_data["fullness"] = cat_data.get("foster_fullness", cat_data["fullness"])
        cat_data["last_decay"] = now
        cat_data.pop("foster_time", None)
        cat_data.pop("foster_fullness", None)
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"[{cat_data['name']}] 回家啦! 花了 {cost} 金币寄养费~",
            image_url=url,
            card_type="success",
        )

    async def _handle_status(self, event, cat_data, user_id):
        coins = self._get_coins(user_id)
        from datetime import datetime, timezone

        adopt_dt = datetime.fromtimestamp(cat_data["adopt_time"], tz=timezone.utc)
        now_dt = datetime.now(tz=timezone.utc)
        adopt_days = max(1, (now_dt.date() - adopt_dt.date()).days + 1)
        fullness = cat_data["fullness"]
        intimacy = cat_data["intimacy"]
        status = cat_data.get("status", "alive")
        active_title = self._get_active_title(user_id)

        status_map = {
            "alive": "存活",
            "critical": "危急",
            "dead": "已去喵星",
            "fostered": "寄养中",
        }
        fl, fc = self._get_stat_style("fullness", fullness)
        il, ic = self._get_stat_style("intimacy", intimacy)

        title_str = f" [{active_title}]" if active_title else ""

        lines = [
            f"[{cat_data['name']}{title_str}] 的状态\n",
            f"生命状态: {status_map.get(status, '???')}",
            f"领养天数: {adopt_days} 天",
            f"饱食度: {fl}  亲密度: {il}",
            f"学历: {EDU_LEVELS[self._get_edu(user_id)]['name']}",
            f"金币: {coins} 枚",
            f"存款: {self._get_bank(user_id)['deposit']} 枚",
        ]

        attrs = self._get_attrs(user_id)
        lines.append(
            f"智力:{attrs['int']} 体力:{attrs['hp']}  魅力:{attrs['cha']}  声望:{attrs['rep']}"
        )

        loan = self._get_loan(user_id)
        if loan["amount"] > 0:
            lines.append(f"贷款: {loan['amount']} 枚")

        fd = self._get_fixed_deposit(user_id)
        if fd["amount"] > 0:
            lines.append(f"定期存款: {fd['amount']} 枚")

        lines.append(f"今日喂食: {cat_data['feed_count']}/5 次")

        if status == "fostered":
            fd = self._get_foster_days(cat_data)
            lines.append(f"寄养天数: {fd} 天")

        buffs = self._get_buffs(user_id)
        active_buffs: list[str] = []
        for k, v in buffs.items():
            if v:
                label = self._get_buff_label(k)
                if label:
                    active_buffs.append(label)
        if active_buffs:
            lines.append(f"增益: {', '.join(active_buffs)}")

        await self._send_reply(event, "\n".join(lines), card_type="status")

    async def _handle_abandon(self, event, user_id, cat_data) -> bool:
        menu = (
            f"!! 确定要弃养 [{cat_data['name']}] 吗? !!\n\n"
            f"这将是不可逆的操作...\n\n"
            f"1. 确认弃养\n"
            f"0. 我再想想"
        )
        await self._send_reply(event, menu, card_type="danger")

        choice = await self._wait_choice(event, choices=["0", "1"])
        if choice is None:
            return False
        if choice != "1":
            await self._send_reply(event, "好好珍惜你的猫猫吧~")
            return False

        self._add_title(user_id, ABANDON_TITLE)
        self._penalize_abandon(user_id)
        self.sdk.storage.delete(f"nekocare:{user_id}")

        url = await self._fetch_image("cry")
        msg = (
            f"你把 [{cat_data['name']}] 送走了...\n"
            f"猫猫回头看了你一眼，眼中满是不解。\n"
            f"获得头衔【{ABANDON_TITLE}】\n"
            f"弃养惩罚: 扣除大量金币、学历清零、属性重置"
        )
        await self._send_reply(event, msg, image_url=url)
        return True

    async def _handle_rename(self, event, user_id, cat_data):
        await self._send_reply(event, "请输入新名字（限20字内）：")
        new_name = await self._wait_choice(event, timeout=120)
        if not new_name:
            return

        if not new_name:
            await self._send_reply(event, "名字不能为空")
            return
        if len(new_name) > 20:
            await self._send_reply(event, "名字太长啦")
            return

        old_name = cat_data["name"]
        cat_data["name"] = new_name
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        await self._send_reply(event, f"[{old_name}] 改名为【{new_name}】啦!")

    async def _do_feed(self, event, user_id, cat_data):
        now = time.time()
        today_start = int(time.strftime("%Y%m%d", time.localtime(now)))
        last_feed_day = int(
            time.strftime("%Y%m%d", time.localtime(cat_data.get("last_feed", 0)))
        )
        if today_start != last_feed_day:
            cat_data["feed_count"] = 0

        if cat_data["feed_count"] >= 5:
            await self._send_reply(event, "今天已经喂了5次啦! 明天再喂~")
            return

        cat_data["fullness"] = min(100, cat_data["fullness"] + 15)
        cat_data["feed_count"] += 1
        cat_data["last_feed"] = now

        ig = random.randint(1, 3)
        cat_data["intimacy"] = min(100, cat_data["intimacy"] + ig)
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        url = await self._fetch_image("hug")
        msgs = [
            f"喂食成功! 饱食度+15 亲密度+{ig}",
            f"猫猫吃得超开心! 饱食度 {cat_data['fullness']}",
            f"第 {cat_data['feed_count']} 次喂食~猫猫蹭了蹭你的手",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _do_cuddle(self, event, user_id, cat_data):
        now = time.time()
        if now - cat_data.get("last_interact", 0) < 30:
            await self._send_reply(event, "贴贴太频繁啦，让猫猫休息一下~")
            return

        ig = random.randint(2, 5)
        cat_data["intimacy"] = min(100, cat_data["intimacy"] + ig)
        cat_data["last_interact"] = now
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        url = await self._fetch_image("cuddle")
        msgs = [
            f"和猫猫贴贴~亲密度+{ig}",
            "猫猫蹭了蹭你，好温暖~",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _do_pat(self, event, user_id, cat_data):
        now = time.time()
        if now - cat_data.get("last_interact", 0) < 20:
            await self._send_reply(event, "摸摸太多啦，让猫猫缓一缓~")
            return

        ig = random.randint(1, 3)
        cat_data["intimacy"] = min(100, cat_data["intimacy"] + ig)
        cat_data["last_interact"] = now
        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        url = await self._fetch_image("pat")
        await self._send_reply(
            event, f"猫猫舒服地咕噜咕噜~亲密度+{ig}", image_url=url, card_type="success"
        )

    async def _do_buy(self, event, user_id, item_name):
        item = SHOP_ITEMS[item_name]
        coins = self._get_coins(user_id)

        if coins < item["price"]:
            await self._send_reply(
                event,
                f"金币不足! 【{item_name}】{item['price']}金币，你只有 {coins} 枚",
                card_type="danger",
            )
            return

        self._add_coins(user_id, -item["price"])
        self._add_inventory(user_id, item_name, 1)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"购买了【{item_name}】! 已放入背包。\n用「使用道具」来使用它。",
            image_url=url,
            card_type="success",
        )

    async def _show_buffs(self, event, user_id):
        buffs = self._get_buffs(user_id)
        active = {k: v for k, v in buffs.items() if v}

        if not active:
            await self._send_reply(event, "当前没有活跃的增益效果")
            return

        lines = ["活跃增益\n"]
        for buff_name in active:
            label = self._get_buff_label(buff_name)
            if label:
                lines.append(f"- {label}")
        await self._send_reply(event, "\n".join(lines))

    # =============================================================
    #  饥饿衰减 / 生命系统
    # =============================================================

    def _apply_hunger_decay(self, user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        cat_data = self._get_cat(user_id)
        if not cat_data:
            return None, None

        status = cat_data.get("status", "alive")

        if status == "dead":
            return cat_data, "dead"

        now = time.time()
        last_decay = cat_data.get("last_decay", cat_data.get("adopt_time", now))
        hours_passed = (now - last_decay) / 3600

        if hours_passed >= 0.1:
            loss = int(hours_passed * DECAY_RATE)
            if loss > 0:
                cat_data["fullness"] = max(0, cat_data["fullness"] - loss)
                cat_data["last_decay"] = now

                if cat_data["fullness"] <= 0:
                    coins = self._get_coins(user_id)
                    if coins >= 20:
                        cat_data["fullness"] = 20
                        self._add_coins(user_id, -20)
                    if status != "critical":
                        cat_data["status"] = "critical"
                        cat_data["critical_since"] = now
                    else:
                        critical_duration = now - cat_data.get("critical_since", now)
                        if critical_duration >= CRITICAL_TIMEOUT:
                            cat_data["status"] = "dead"
                            cat_data["death_cause"] = "starve"
                            cat_data["death_time"] = now
                            self._add_title(user_id, DEATH_TITLES["starve"])
                            self._inc_stat(user_id, "death_count")
                            self._check_achievement_titles(user_id)

                self.sdk.storage.set(f"nekocare:{user_id}", cat_data)

        return cat_data, cat_data.get("status", "alive")

    def _get_critical_remaining(self, cat_data: dict) -> int:
        now = time.time()
        since = cat_data.get("critical_since", now)
        remaining = max(0, CRITICAL_TIMEOUT - (now - since))
        return int(remaining / 3600) + 1

    def _get_foster_days(self, cat_data: dict) -> int:
        now = time.time()
        foster_time = cat_data.get("foster_time", now)
        return max(1, int((now - foster_time) / 86400) + 1)

    def _calc_foster_cost(self, cat_data: dict) -> int:
        return self._get_foster_days(cat_data) * FOSTER_COST_PER_DAY

    async def _send_dead_message(self, event, cat_data: dict):
        cause = cat_data.get("death_cause", "starve")
        title = DEATH_TITLES.get(cause, "???")
        stories = {
            "starve": (
                f"[{cat_data['name']}] 已经永远地去了喵星...\n"
                f"它走得很安静，肚子瘪瘪的。\n"
                f"获得头衔【{title}】"
            ),
            "overwork": (
                f"[{cat_data['name']}] 因劳累过度去了喵星...\n"
                f"它是为了给你赚钱才倒下的。\n"
                f"获得头衔【{title}】"
            ),
        }
        url = await self._fetch_image("cry")
        await self._send_reply(
            event,
            stories.get(cause, stories["starve"]),
            image_url=url,
            card_type="death",
        )

    async def _send_critical_message(self, event, cat_data: dict):
        hours = self._get_critical_remaining(cat_data)
        url = await self._fetch_image("cry")
        msg = (
            f"!! [{cat_data['name']}] 饿晕了，被送往宠物医院 !!\n\n"
            f"请 {hours} 小时内使用急救!\n"
            f"急救费用: {RESCUE_COST} 金币 (50%成功率)"
        )
        await self._send_reply(event, msg, image_url=url, card_type="danger")

    # =============================================================

    def _get_cat(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.sdk.storage.get(f"nekocare:{user_id}")

    def _get_coins(self, user_id: str) -> int:
        coins = self.sdk.storage.get(f"nekocare_coins:{user_id}")
        return coins if coins is not None else 0

    def _add_coins(self, user_id: str, amount: int):
        current = self._get_coins(user_id)
        self.sdk.storage.set(f"nekocare_coins:{user_id}", current + amount)

    def _get_work_cooldown(self, user_id: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_work_cd:{user_id}")
        return cd if cd is not None else 0

    def _set_work_cooldown(self, user_id: str):
        self.sdk.storage.set(f"nekocare_work_cd:{user_id}", time.time())

    def _get_catch_cooldown(self, user_id: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_catch_cd:{user_id}")
        return cd if cd is not None else 0

    def _set_catch_cooldown(self, user_id: str):
        self.sdk.storage.set(f"nekocare_catch_cd:{user_id}", time.time())

    def _get_rob_cooldown(self, user_id: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_rob_cd:{user_id}")
        return cd if cd is not None else 0

    def _set_rob_cooldown(self, user_id: str):
        self.sdk.storage.set(f"nekocare_rob_cd:{user_id}", time.time())

    def _get_scavenge_cooldown(self, user_id: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_scavenge_cd:{user_id}")
        return cd if cd is not None else 0

    def _set_scavenge_cooldown(self, user_id: str):
        self.sdk.storage.set(f"nekocare_scavenge_cd:{user_id}", time.time())

    def _get_signin_data(self, user_id: str) -> dict:
        data = self.sdk.storage.get(f"nekocare_signin:{user_id}")
        return data if data is not None else {}

    def _set_signin_data(self, user_id: str, data: dict):
        self.sdk.storage.set(f"nekocare_signin:{user_id}", data)

    def _get_edu(self, user_id: str) -> int:
        edu = self.sdk.storage.get(f"nekocare_edu:{user_id}")
        return edu if edu is not None else 0

    def _set_edu(self, user_id: str, level: int):
        self.sdk.storage.set(f"nekocare_edu:{user_id}", level)

    def _get_edu_cd(self, user_id: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_edu_cd:{user_id}")
        return cd if cd is not None else 0

    def _set_edu_cd(self, user_id: str):
        self.sdk.storage.set(f"nekocare_edu_cd:{user_id}", time.time())

    def _get_bank(self, user_id: str) -> dict:
        bank = self.sdk.storage.get(f"nekocare_bank:{user_id}")
        if bank is None:
            bank = {"deposit": 0, "last_interest": time.time()}
        return bank

    def _set_bank(self, user_id: str, data: dict):
        self.sdk.storage.set(f"nekocare_bank:{user_id}", data)

    def _calc_bank_interest(self, user_id: str) -> dict:
        bank = self._get_bank(user_id)
        if bank["deposit"] <= 0:
            return bank
        now = time.time()
        hours = (now - bank["last_interest"]) / 3600
        if hours >= 1:
            interest = int(bank["deposit"] * BANK_INTEREST_REGULAR * (hours / 24))
            if interest > 0:
                bank["deposit"] = min(BANK_MAX_DEPOSIT, bank["deposit"] + interest)
                bank["last_interest"] = now
                self._set_bank(user_id, bank)
        return bank

    def _get_user_stocks(self, user_id: str) -> Dict[str, int]:
        stocks = self.sdk.storage.get(f"nekocare_stocks:{user_id}")
        return stocks if stocks is not None else {}

    def _set_user_stocks(self, user_id: str, stocks: Dict[str, int]):
        self.sdk.storage.set(f"nekocare_stocks:{user_id}", stocks)

    def _get_stock_prices(self) -> dict:
        prices = self.sdk.storage.get("nekocare_stock_prices")
        if prices is None:
            prices = dict(STOCK_BASE_PRICES)
        self.sdk.storage.set("nekocare_stock_prices", prices)
        return prices

    def _get_attrs(self, user_id: str) -> dict:
        attrs = self.sdk.storage.get(f"nekocare_attrs:{user_id}")
        if attrs is None:
            attrs = {"int": 10, "hp": 100, "cha": 10, "rep": 0}
        return attrs

    def _set_attrs(self, user_id: str, attrs: dict):
        for k in ("int", "hp", "cha"):
            attrs[k] = max(0, min(100, attrs.get(k, 0)))
        attrs["rep"] = max(-100, min(100, attrs.get("rep", 0)))
        self.sdk.storage.set(f"nekocare_attrs:{user_id}", attrs)

    def _mod_attr(self, user_id: str, key: str, delta: int):
        attrs = self._get_attrs(user_id)
        attrs[key] = attrs.get(key, 0) + delta
        self._set_attrs(user_id, attrs)

    def _penalize_abandon(self, user_id: str):
        coins = self._get_coins(user_id)
        penalty = max(200, coins // 2)
        self._add_coins(user_id, -penalty)
        self._set_edu(user_id, 0)
        self._set_study_progress(user_id, 0)
        self._set_attrs(user_id, {"int": 0, "hp": 50, "cha": 0, "rep": -30})
        self._set_bank(user_id, {"deposit": 0, "last_interest": time.time()})
        self._set_fixed_deposit(user_id, {"amount": 0, "start_time": 0.0})
        self._set_loan(user_id, {"amount": 0, "principal": 0, "last_interest": 0.0})
        self._set_user_stocks(user_id, {})

    def _penalize_death(self, user_id: str):
        coins = self._get_coins(user_id)
        penalty = max(100, coins * 3 // 10)
        self._add_coins(user_id, -penalty)
        self._mod_attr(user_id, "hp", -40)
        self._mod_attr(user_id, "rep", -15)

    def _penalize_readopt(self, user_id: str):
        coins = self._get_coins(user_id)
        penalty = max(100, coins // 3)
        self._add_coins(user_id, -penalty)
        self._set_edu(user_id, 0)
        self._set_study_progress(user_id, 0)
        self._set_attrs(user_id, {"int": 0, "hp": 50, "cha": 0, "rep": -10})
        self._set_bank(user_id, {"deposit": 0, "last_interest": time.time()})
        self._set_fixed_deposit(user_id, {"amount": 0, "start_time": 0.0})
        self._set_loan(user_id, {"amount": 0, "principal": 0, "last_interest": 0.0})
        self._set_user_stocks(user_id, {})

    def _get_study_progress(self, user_id: str) -> int:
        p = self.sdk.storage.get(f"nekocare_study_progress:{user_id}")
        return p if p is not None else 0

    def _set_study_progress(self, user_id: str, val: int):
        self.sdk.storage.set(
            f"nekocare_study_progress:{user_id}", min(100, max(0, val))
        )

    def _get_loan(self, user_id: str) -> dict:
        loan = self.sdk.storage.get(f"nekocare_loan:{user_id}")
        return (
            loan
            if loan is not None
            else {"amount": 0, "principal": 0, "last_interest": 0.0}
        )

    def _set_loan(self, user_id: str, data: dict):
        self.sdk.storage.set(f"nekocare_loan:{user_id}", data)

    def _calc_loan_interest(self, user_id: str) -> dict:
        loan = self._get_loan(user_id)
        if loan["amount"] <= 0:
            return loan
        now = time.time()
        hours = (now - loan["last_interest"]) / 3600
        if hours >= 1:
            interest = int(loan["amount"] * BANK_MAX_LOAN_RATE * (hours / 24))
            if interest > 0:
                loan["amount"] += interest
                principal = loan.get("principal", loan["amount"] - interest)
                cap = max(
                    int(principal * BANK_LOAN_CAP_RATIO),
                    BANK_LOAN_CAP_ABSOLUTE,
                )
                if loan["amount"] > cap:
                    loan["amount"] = cap
                loan["last_interest"] = now
                self._set_loan(user_id, loan)
        return loan

    def _get_fixed_deposit(self, user_id: str) -> dict:
        fd = self.sdk.storage.get(f"nekocare_fixed:{user_id}")
        return fd if fd is not None else {"amount": 0, "start_time": 0.0}

    def _set_fixed_deposit(self, user_id: str, data: dict):
        self.sdk.storage.set(f"nekocare_fixed:{user_id}", data)

    def _calc_fixed_interest(self, user_id: str) -> dict:
        fd = self._get_fixed_deposit(user_id)
        if fd["amount"] <= 0 or fd["start_time"] <= 0:
            return fd
        now = time.time()
        elapsed = now - fd["start_time"]
        interest = int(fd["amount"] * BANK_INTEREST_FIXED * (elapsed / 86400))
        return {
            "amount": fd["amount"],
            "start_time": fd["start_time"],
            "interest": interest,
        }

    def _update_stock_prices(self) -> dict:
        prices = self._get_stock_prices()
        now = time.time()
        last_update = self.sdk.storage.get("nekocare_stock_last_update")
        interval = 300
        if last_update is None or (now - last_update) < interval:
            return prices
        self.sdk.storage.set("nekocare_stock_last_update", now)
        for name in STOCK_LIST:
            base = STOCK_BASE_PRICES[name]
            change = random.uniform(-0.15, 0.15)
            noise = random.uniform(-base * 0.1, base * 0.1)
            target = base * (1 + change) + noise
            current = prices[name]
            new_price = current + (target - current) * 0.3
            new_price = max(int(base * 0.3), min(int(base * 2.5), int(new_price)))
            prices[name] = max(1, new_price)
        self.sdk.storage.set("nekocare_stock_prices", prices)
        return prices

    def _get_inventory(self, user_id: str) -> Dict[str, int]:
        inv = self.sdk.storage.get(f"nekocare_inv:{user_id}")
        return inv if inv is not None else {}

    def _add_inventory(self, user_id: str, item: str, count: int):
        inv = self._get_inventory(user_id)
        inv[item] = inv.get(item, 0) + count
        self.sdk.storage.set(f"nekocare_inv:{user_id}", inv)

    def _remove_inventory(self, user_id: str, item: str, count: int):
        inv = self._get_inventory(user_id)
        current = inv.get(item, 0)
        if current <= count:
            inv.pop(item, None)
        else:
            inv[item] = current - count
        self.sdk.storage.set(f"nekocare_inv:{user_id}", inv)

    def _get_buffs(self, user_id: str) -> Dict[str, bool]:
        buffs = self.sdk.storage.get(f"nekocare_buffs:{user_id}")
        return buffs if buffs is not None else {}

    def _set_buffs(self, user_id: str, buffs: Dict[str, bool]):
        self.sdk.storage.set(f"nekocare_buffs:{user_id}", buffs)

    def _get_buff_label(self, buff_name: str) -> Optional[str]:
        labels = {
            "work_double": "金币加成卡",
            "catch_boost": "幸运铃铛",
            "free_rescue": "急救包",
        }
        return labels.get(buff_name)

    def _get_titles(self, user_id: str) -> list:
        titles = self.sdk.storage.get(f"nekocare_titles:{user_id}")
        return titles if titles is not None else []

    def _add_title(self, user_id: str, title: str):
        titles = self._get_titles(user_id)
        if title not in titles:
            titles.append(title)
            self.sdk.storage.set(f"nekocare_titles:{user_id}", titles)

    def _get_active_title(self, user_id: str) -> Optional[str]:
        return self.sdk.storage.get(f"nekocare_active_title:{user_id}")

    def _set_active_title(self, user_id: str, title: str):
        self.sdk.storage.set(f"nekocare_active_title:{user_id}", title)

    def _get_stats(self, user_id: str) -> Dict[str, int]:
        stats = self.sdk.storage.get(f"nekocare_stats:{user_id}")
        return stats if stats is not None else {}

    def _inc_stat(self, user_id: str, name: str, amount: int = 1):
        stats = self._get_stats(user_id)
        stats[name] = stats.get(name, 0) + amount
        self.sdk.storage.set(f"nekocare_stats:{user_id}", stats)

    def _register_user(self, user_id: str, nickname: str = ""):
        users = self.sdk.storage.get("nekocare_user_registry")
        if users is None:
            users = []
        if user_id not in users:
            users.append(user_id)
            self.sdk.storage.set("nekocare_user_registry", users)
        if nickname:
            self.sdk.storage.set(f"nekocare_nickname:{user_id}", nickname)

    def _get_all_users(self) -> list:
        users = self.sdk.storage.get("nekocare_user_registry")
        return users if users else []

    def _check_achievement_titles(self, user_id: str):
        stats = self._get_stats(user_id)
        coins = self._get_coins(user_id)
        cat_data = self._get_cat(user_id)

        if stats.get("work_count", 0) >= 50:
            self._add_title(user_id, "打工狂魔")
        if stats.get("work_count", 0) >= 100:
            self._add_title(user_id, "佛系玩家")
        if stats.get("catch_count", 0) >= 20:
            self._add_title(user_id, "捕猫达人")
        if stats.get("catch_count", 0) >= 50:
            self._add_title(user_id, "驭猫达人")
        if stats.get("rescue_count", 0) >= 5:
            self._add_title(user_id, "神医再世")
        if stats.get("rescue_count", 0) >= 15:
            self._add_title(user_id, "欧皇附体")
        if stats.get("death_count", 0) >= 3:
            self._add_title(user_id, "非酋酋长")
        if coins >= 1000:
            self._add_title(user_id, "富可敌国")
        if coins >= 5000:
            self._add_title(user_id, "清丽多金")
        if coins <= 0:
            loan = self._get_loan(user_id)
            if loan["amount"] > 0:
                self._add_title(user_id, "负债累累")
            else:
                self._add_title(user_id, "千金散尽")
        total_lost = stats.get("invest_lost", 0)
        if total_lost >= 500:
            self._add_title(user_id, "散尽家财")
        invest_profit = stats.get("invest_profit", 0)
        if invest_profit >= 500:
            self._add_title(user_id, "理财圣手")
        if invest_profit >= 2000:
            self._add_title(user_id, "止盈大师")
        if invest_profit >= 5000:
            self._add_title(user_id, "富贵险求")
        invest_total = stats.get("invest_count", 0)
        if invest_total >= 10:
            self._add_title(user_id, "果断梭哈")
        if invest_total >= 30:
            self._add_title(user_id, "佛系玩家")

        if cat_data and cat_data.get("status") == "alive":
            from datetime import datetime, timezone

            adopt_dt = datetime.fromtimestamp(cat_data["adopt_time"], tz=timezone.utc)
            now_dt = datetime.now(tz=timezone.utc)
            days = max(1, (now_dt.date() - adopt_dt.date()).days + 1)
            if days >= 30:
                self._add_title(user_id, "好主人")
            if cat_data.get("intimacy", 0) >= 90:
                self._add_title(user_id, "萌系可爱")
            if cat_data.get("intimacy", 0) >= 100 and days >= 7:
                self._add_title(user_id, "软萌可爱")
            if cat_data.get("intimacy", 0) >= 100 and days >= 14:
                self._add_title(user_id, "软萌喵系")
            if cat_data.get("intimacy", 0) >= 100 and days >= 30:
                self._add_title(user_id, "萌态万千")
            if cat_data.get("intimacy", 0) >= 100 and days >= 60:
                self._add_title(user_id, "人间可爱")
            if cat_data.get("intimacy", 0) >= 100 and coins >= 10000:
                self._add_title(user_id, "盛世美颜")
            attrs = self._get_attrs(user_id)
            if attrs["cha"] >= 80 and attrs["int"] >= 60 and coins >= 5000:
                self._add_title(user_id, "俊朗多金")
                self._add_title(user_id, "好主人")

    # =============================================================
    #  显示工具
    # =============================================================

    def _str_width(self, s: str) -> int:
        w = 0
        for c in s:
            if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u303f":
                w += 2
            else:
                w += 1
        return w

    def _pad(self, s: str, width: int) -> str:
        return s + " " * max(0, width - self._str_width(s))

    def _get_stat_style(self, stat_type: str, value: int) -> Tuple[str, str]:
        if stat_type == "fullness":
            if value >= 80:
                label, color = "很饱", "#4caf50"
            elif value >= 50:
                label, color = "还行", "#ff9800"
            elif value >= 20:
                label, color = "有点饿", "#ff5722"
            else:
                label, color = "非常饿", "#f44336"
        else:
            if value >= 80:
                label, color = "非常亲密", "#e91e63"
            elif value >= 50:
                label, color = "友好", "#9c27b0"
            elif value >= 20:
                label, color = "普通", "#607d8b"
            else:
                label, color = "陌生", "#9e9e9e"
        return f"{value}/100 [{label}]", color

    def _build_bag_display(self, user_id: str, coins: int) -> str:
        inv = self._get_inventory(user_id)
        all_items = list(SHOP_ITEM_LIST) + list(BLACKMARKET_ITEM_LIST)
        name_w = max(self._str_width(n) for n in all_items) + 2

        header = self._pad("背包", 22) + f"金币:{coins}"
        lines = [header, ""]

        lines.append("=== 商城道具 ===")
        half = (len(SHOP_ITEM_LIST) + 1) // 2
        for row in range(half):
            left_idx = row
            right_idx = row + half

            left_name = SHOP_ITEM_LIST[left_idx]
            left_count = inv.get(left_name, 0)
            left_str = self._pad(
                f"{left_idx + 1}.{left_name}  x{left_count}", name_w + 8
            )

            if right_idx < len(SHOP_ITEM_LIST):
                right_name = SHOP_ITEM_LIST[right_idx]
                right_count = inv.get(right_name, 0)
                right_str = f"{right_idx + 1}.{right_name}  x{right_count}"
                lines.append(f"{left_str}| {right_str}")
            else:
                lines.append(left_str)

        has_tool = any(inv.get(n, 0) > 0 for n in BLACKMARKET_ITEM_LIST)
        if has_tool:
            lines.append("")
            lines.append("=== 作案工具 ===")
            for i, name in enumerate(BLACKMARKET_ITEM_LIST):
                count = inv.get(name, 0)
                if count > 0:
                    item = BLACKMARKET_ITEMS[name]
                    lines.append(f"{name}  x{count}  {item['desc']}")

        return "\n".join(lines)

    def _build_shop_display(self, coins: int) -> str:
        name_w = max(self._str_width(n) for n in SHOP_ITEM_LIST) + 2

        header = self._pad("商城", 22) + f"金币:{coins}"
        lines = [header, ""]

        for i, name in enumerate(SHOP_ITEM_LIST):
            item = SHOP_ITEMS[name]
            item_str = self._pad(f"{i + 1}.{name}  {item['price']}金币", name_w + 10)
            lines.append(f"{item_str} {item['desc']}")

        return "\n".join(lines)

    # =============================================================
    #  富文本渲染
    # =============================================================

    def _render_line_html(self, line: str, is_first: bool, styles: dict) -> str:
        stripped = line.strip()
        if not stripped:
            return ""

        if stripped.startswith("===") and stripped.endswith("==="):
            title = stripped.strip("= ").strip()
            return f'<div style="{styles["subheader"]}">{title}</div>'

        if stripped.startswith("!!") and stripped.endswith("!!"):
            text = stripped.strip("! ").strip()
            return f'<div style="{styles["danger"]}">{text}</div>'

        if is_first:
            return (
                f'<div style="{styles["header"]}">{stripped}</div>'
                f'<div style="{styles["divider"]}"></div>'
            )

        if stripped.startswith("|"):
            cols = stripped.strip("|").split("|")
            inner = ""
            for col in cols:
                c = col.strip()
                if not c:
                    continue
                inner += f'<div style="{styles["col_item"]}">{c}</div>'
            return f'<div style="{styles["col"]}">{inner}</div>' if inner else ""

        if len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in ". ":
            return f'<div style="{styles["item"]}">{stripped}</div>'

        if "|" in stripped and not stripped[0].isdigit():
            cols = stripped.split("|")
            inner = ""
            for col in cols:
                c = col.strip()
                if not c:
                    continue
                inner += f'<div style="{styles["col_item"]}">{c}</div>'
            return f'<div style="{styles["col"]}">{inner}</div>' if inner else ""

        if ":" in stripped:
            idx = stripped.index(":")
            key = stripped[:idx].strip()
            val = stripped[idx + 1 :].strip()
            if key and val:
                return (
                    f'<div style="{styles["kv"]}">'
                    f'<span style="{styles["kv_key"]}">{key}:</span> {val}'
                    f"</div>"
                )

        return f'<div style="{styles["body"]}">{stripped}</div>'

    def _get_styles(self, card_type: str = "menu") -> dict:
        theme = CARD_THEMES.get(card_type, CARD_THEMES["menu"])
        accent = theme["accent"]
        bg = theme["bg"]
        header_color = theme["header_color"]
        tag_bg = theme["tag_bg"]
        border = theme["border"]
        text_color = theme["text"]
        text_sub = theme.get("text_sub", "#666666")

        return {
            "wrapper": (
                f"padding:20px 24px;border-radius:16px;font-size:14px;"
                f"line-height:1.7;{_FONT}"
                f"background:{bg};"
                f"color:{text_color};"
                f"box-shadow:0 4px 12px rgba(0,0,0,0.08);"
                f"border:1px solid {border};"
            ),
            "header": (
                f"font-size:18px;font-weight:600;"
                f"color:{header_color};letter-spacing:-0.01em;"
            ),
            "divider": (
                f"height:1px;background:{border};margin:8px 0 12px 0;opacity:0.6;"
            ),
            "subheader": (
                f"font-weight:500;padding:6px 16px;border-radius:12px;"
                f"color:{header_color};background:{tag_bg};"
                f"display:inline-block;margin:8px 0 4px 0;font-size:13px;"
                f"border:1px solid {border};"
            ),
            "item": (
                f"padding:4px 10px;color:{text_color};border-radius:8px;"
                f"margin:1px 0;font-size:14px;"
            ),
            "kv": (
                f"margin-bottom:2px;font-size:14px;color:{text_color};padding:2px 0;"
            ),
            "kv_key": f"color:{text_sub};font-weight:500;",
            "warn": (
                f"padding:10px 14px;background:{tag_bg};border-radius:8px;"
                f"font-size:13px;color:{accent};margin:6px 0;"
                f"border:1px solid {border};"
            ),
            "danger": (
                f"padding:10px 14px;background:{tag_bg};border-radius:8px;"
                f"font-size:13px;color:{accent};margin:6px 0;"
                f"border:1px solid {border};"
            ),
            "success": (
                f"padding:10px 14px;background:{tag_bg};border-radius:8px;"
                f"font-size:13px;color:{accent};margin:6px 0;"
                f"border:1px solid {border};"
            ),
            "muted": f"color:{text_sub};font-size:12px;",
            "body": f"margin-bottom:3px;font-size:14px;color:{text_color};",
            "col": (
                f"display:flex;gap:8px;font-size:13px;"
                f"font-family:monospace;color:{text_color};"
            ),
            "col_item": "flex:1;white-space:pre;",
        }

    def _build_html(
        self, text: str, image_url: Optional[str] = None, card_type: str = "menu"
    ) -> str:
        styles = self._get_styles(card_type)
        html = f'<div style="{styles["wrapper"]}">'

        if image_url:
            html += (
                f'<div style="text-align:center;margin-bottom:12px;">'
                f'<img src="{image_url}" style="'
                f"max-width:100%;max-height:300px;"
                f'border-radius:12px;" /></div>'
            )

        for i, raw_line in enumerate(text.strip().split("\n")):
            rendered = self._render_line_html(raw_line, i == 0, styles)
            if rendered:
                html += rendered

        html += "</div>"
        return html

    def _build_markdown(self, text: str, image_url: Optional[str] = None) -> str:
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        md = ""

        for i, line in enumerate(lines):
            s = line.strip()

            if s.startswith("===") and s.endswith("==="):
                title = s.strip("= ").strip()
                md += f"> **{title}**\n\n"
            elif s.startswith("!!") and s.endswith("!!"):
                text = s.strip("! ").strip()
                md += f"> **{text}**\n\n"
            elif i == 0:
                md += f"**{s}**\n\n"
            elif len(s) > 1 and s[0].isdigit() and s[1] in ". ":
                md += f"{s}\n"
            elif s.startswith("- "):
                md += f"{s}\n"
            else:
                md += f"{s}\n"

        if image_url:
            md += f'\n<center><img src="{image_url}" width="300" /></center>'

        return md

    # =============================================================
    #  排行榜
    # =============================================================

    def _build_ranking(self, data: list, value_label: str, reverse: bool = True) -> str:
        sorted_data = sorted(data, key=lambda x: x[1], reverse=reverse)
        if not sorted_data:
            return "暂无数据"
        lines = []
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        for i, (uid, val) in enumerate(sorted_data[:10]):
            medal = medals.get(i, f"{i + 1}.")
            nickname = self.sdk.storage.get(f"nekocare_nickname:{uid}") or uid
            cat = self._get_cat(uid)
            cat_name = cat["name"] if cat else "无猫"
            lines.append(f"{medal} {nickname} | {cat_name} | {value_label}: {val}")
        return "\n".join(lines)

    async def _handle_leaderboard(self, event):
        user_id = event.get_user_id()
        self._register_user(user_id, event.get_user_nickname() or "")
        while True:
            if user_id in self._timed_out_users:
                return
            menu = (
                "喵喵榜\n\n"
                "1. 喵币榜\n"
                "2. 存活榜\n"
                "3. 亲密榜\n"
                "4. 喵亡榜\n"
                "5. 黑喵榜\n"
                "0. 返回"
            )
            await self._send_reply(event, menu)

            choice = await self._wait_choice(
                event, choices=["0", "1", "2", "3", "4", "5"]
            )
            if choice is None or choice == "0":
                return

            all_users = self._get_all_users()
            if not all_users:
                await self._send_reply(
                    event, "暂无数据，还没有玩家注册~", card_type="info"
                )
                return

            if choice == "1":
                coin_data = []
                for uid in all_users:
                    c = self._get_coins(uid)
                    if c > 0:
                        coin_data.append((uid, c))
                header = "喵币排行榜\n"
                body = self._build_ranking(coin_data, "喵币")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            if choice == "2":
                alive_data = []
                for uid in all_users:
                    cat = self._get_cat(uid)
                    if cat and cat.get("status") == "alive":
                        from datetime import datetime, timezone

                        adopt_dt = datetime.fromtimestamp(
                            cat["adopt_time"], tz=timezone.utc
                        )
                        now_dt = datetime.now(tz=timezone.utc)
                        days = max(1, (now_dt.date() - adopt_dt.date()).days + 1)
                        alive_data.append((uid, days))
                header = "存活时长排行\n"
                body = self._build_ranking(alive_data, "存活天数")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            elif choice == "3":
                intimacy_data = []
                for uid in all_users:
                    cat = self._get_cat(uid)
                    if cat and cat.get("status") == "alive":
                        intimacy_data.append((uid, cat["intimacy"]))
                header = "亲密度排行\n"
                body = self._build_ranking(intimacy_data, "亲密度")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            elif choice == "4":
                death_data = []
                for uid in all_users:
                    stats = self._get_stats(uid)
                    dc = stats.get("death_count", 0)
                    if dc > 0:
                        death_data.append((uid, dc))
                header = "喵亡榜\n"
                body = self._build_ranking(death_data, "死猫次数")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            elif choice == "5":
                catched_data = []
                for uid in all_users:
                    stats = self._get_stats(uid)
                    cc = stats.get("catched_count", 0)
                    if cc > 0:
                        catched_data.append((uid, cc))
                header = "黑喵榜\n"
                body = self._build_ranking(catched_data, "被抓次数")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            else:
                await self._send_reply(event, "无效选项", card_type="danger")

    # =============================================================
    #  基础工具
    # =============================================================

    def _load_config(self) -> dict:
        default_config = {"timeout": 10}
        cfg = self.sdk.config.getConfig("NekoCare")
        if not cfg:
            self.sdk.config.setConfig("NekoCare", default_config)
            return default_config
        return cfg

    async def _fetch_image(self, category: str) -> Optional[str]:
        api_url = self.image_categories.get(category)
        if not api_url:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=self.config["timeout"]) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("results") and len(data["results"]) > 0:
                            return data["results"][0].get("url")
        except Exception as e:
            self.logger.error(f"获取图片失败 ({category}): {e}")
        return None

    async def _send_reply(
        self,
        event,
        content: str,
        image_url: Optional[str] = None,
        card_type: str = "menu",
        force_new: bool = False,
    ):
        platform = event.get_platform()
        supported = self._get_supported_methods(platform)

        if image_url:
            if "Html" in supported:
                try:
                    result = await event.reply(
                        self._build_html(
                            content, image_url=image_url, card_type=card_type
                        ),
                        method="HTML",
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"HTML 发送失败: {e}")

            if "Markdown" in supported:
                try:
                    result = await event.reply(
                        self._build_markdown(content, image_url=image_url),
                        method="Markdown",
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"Markdown 发送失败: {e}")

            if "Image" in supported:
                try:
                    result = await event.reply(image_url, method="Image")
                    await event.reply(content)
                    return
                except Exception as e:
                    self.logger.warning(f"Image 发送失败: {e}")

            await event.reply(content)
        else:
            if "Html" in supported:
                try:
                    result = await event.reply(
                        self._build_html(content, card_type=card_type), method="HTML"
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"HTML 发送失败: {e}")

            if "Markdown" in supported:
                try:
                    result = await event.reply(
                        self._build_markdown(content), method="Markdown"
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"Markdown 发送失败: {e}")

            await event.reply(content)

    def _get_supported_methods(self, platform: str) -> list:
        if hasattr(self.sdk.adapter, "list_sends"):
            methods = self.sdk.adapter.list_sends(platform)
            return methods

        supported = []
        if hasattr(self.sdk.adapter.get(platform).Send, "Markdown"):
            supported.append("Markdown")
        if hasattr(self.sdk.adapter.get(platform).Send, "Html"):
            supported.append("Html")
        if hasattr(self.sdk.adapter.get(platform).Send, "Image"):
            supported.append("Image")
        if hasattr(self.sdk.adapter.get(platform).Send, "Text"):
            supported.append("Text")
        return supported