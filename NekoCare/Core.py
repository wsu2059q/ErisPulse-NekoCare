import asyncio
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
    "亲密糖果": {
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
    "能量棒": {
        "price": 30,
        "desc": "体力+15",
        "type": "consumable",
        "effect": {"hp_boost": 15},
    },
    "聚宝喵符": {
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
}

SHOP_ITEM_LIST = list(SHOP_ITEMS.keys())

DEATH_TITLES = {"starve": "😵 - 饿死大王", "overwork": "💪 - 劳累过度"}
ABANDON_TITLE = "🚫 - 弃养者"

ALL_TITLES = {
    "death": ["😵 - 饿死大王", "💪 - 劳累过度"],
    "punish": ["🚫 - 弃养者"],
    "achievement": [
        "🐱 - 喵喵医生",
        "⚒️ - 打工狂魔",
        "🐱 - 捕猫达人",
        "🩺 - 神医再世",
        "💰 - 富可敌国",
        "❤️ - 好主人",
        "📈 - 理财圣手",
        "🛑 - 止盈大师",
        "🎲 - 富贵险求",
        "🚀 - 果断梭哈",
        "💸 - 千金散尽",
        "📉 - 散尽家财",
        "⛔ - 负债累累",
        "🧘 - 佛系玩家",
        "🌟 - 欧皇附体",
        "🎭 - 非酋酋长",
        "🐾 - 驭猫达人",
    ],
    "cute": [
        "🌸 - 萌系可爱",
        "🍡 - 软萌可爱",
        "🐱 - 软萌喵系",
        "🌟 - 萌态万千",
        "🌙 - 人间可爱",
        "✨ - 盛世美颜",
    ],
    "rich": ["💎 - 清丽多金", "💼 - 俊朗多金"],
}

EDU_LEVELS = {
    0: {"name": "未入学", "cost": 0},
    1: {"name": "萌喵小学", "cost": 0},
    2: {"name": "萌喵初中", "cost": 80},
    3: {"name": "萌喵高中", "cost": 200},
    4: {"name": "萌喵专科", "cost": 500},
    5: {"name": "萌喵大学", "cost": 1200},
    6: {"name": "喵星研究院", "cost": 3000},
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
            "name": "摆摊卖小鱼干",
            "earn_min": 6,
            "earn_max": 22,
            "nrg_min": 5,
            "nrg_max": 10,
            "stat": "cha",
        },
    ],
    1: [
        {
            "name": "生鲜配送员",
            "earn_min": 10,
            "earn_max": 28,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "hp",
        },
        {
            "name": "猫砂厂操作工",
            "earn_min": 12,
            "earn_max": 25,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
        {
            "name": "猫粮搬运工",
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
            "name": "小区安保",
            "earn_min": 18,
            "earn_max": 42,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "hp",
        },
        {
            "name": "宠物店助理",
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
            "name": "猫咖服务生",
            "earn_min": 22,
            "earn_max": 48,
            "nrg_min": 8,
            "nrg_max": 15,
            "stat": "cha",
        },
        {
            "name": "汽修喵",
            "earn_min": 25,
            "earn_max": 58,
            "nrg_min": 12,
            "nrg_max": 20,
            "stat": "int",
        },
    ],
    4: [
        {
            "name": "宠物医师助理",
            "earn_min": 28,
            "earn_max": 62,
            "nrg_min": 10,
            "nrg_max": 18,
            "stat": "int",
        },
        {
            "name": "喵星银行柜员",
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
            "name": "喵园教师",
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
            "name": "创意设计师",
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
            "name": "喵教授",
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
            "name": "城市规划喵",
            "earn_min": 65,
            "earn_max": 138,
            "nrg_min": 15,
            "nrg_max": 25,
            "stat": "int",
        },
        {
            "name": "集团企业高管",
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
        "name": "赏金猎喵",
        "earn_min": 50,
        "earn_max": 120,
        "nrg_min": 15,
        "nrg_max": 25,
        "req_cha": 60,
        "req_rep": 20,
        "stat": "cha",
    },
    {
        "name": "黑市中间人",
        "earn_min": 40,
        "earn_max": 100,
        "nrg_min": 12,
        "nrg_max": 20,
        "req_rep": -30,
        "stat": "cha",
    },
    {
        "name": "猫居设计师",
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

STOCK_UPDATE_INTERVAL = 300
STOCK_BASE_VOLATILITY = 0.05
STOCK_PRICE_MIN_RATIO = 0.3
STOCK_PRICE_MAX_RATIO = 2.5
STOCK_SMOOTH_FACTOR = 0.3
STOCK_MARKET_TREND_CYCLE = 604800
STOCK_EVENT_DURATION = 432000
STOCK_DAILY_RESET_INTERVAL = 86400

COMPANY_TYPES = {
    "tech": {"name": "科技", "fee": 3000, "growth": 0.15, "risk": 0.12},
    "manufacture": {"name": "制造", "fee": 2000, "growth": 0.08, "risk": 0.05},
    "retail": {"name": "零售", "fee": 1500, "growth": 0.10, "risk": 0.07},
    "service": {"name": "服务", "fee": 1000, "growth": 0.12, "risk": 0.04},
    "finance": {"name": "金融", "fee": 2500, "growth": 0.18, "risk": 0.10},
}

COMPANY_INITIAL_CAPITAL = 5000
COMPANY_MAX_LEVEL = 10
COMPANY_LEVEL_UP_REVENUE = 10000
COMPANY_IPO_DAYS = 30
COMPANY_IPO_MIN_PROFIT = 10000
COMPANY_IPO_MIN_CASH = 5000
COMPANY_IPO_MIN_LEVEL = 3
COMPANY_IPO_FEE = 10000
COMPANY_DIVIDEND_CYCLE = 2592000
COMPANY_MAX_COMPANIES_PER_USER = 2

JOB_POSITIONS = {
    1: {"name": "实习生", "salary": 50, "req_edu": 0, "max_employees": 5},
    2: {"name": "员工", "salary": 80, "req_edu": 1, "max_employees": 4},
    3: {"name": "专员", "salary": 120, "req_edu": 2, "max_employees": 3},
    4: {"name": "主管", "salary": 160, "req_edu": 3, "max_employees": 2},
    5: {"name": "经理", "salary": 200, "req_edu": 4, "max_employees": 1},
}

COMPANY_SALARY_INTERVAL = 86400
COMPANY_MAX_POSITIONS_PER_COMPANY = 3

NPC_EMPLOYEE_LEVELS = {
    1: {"name": "新手", "salary": 30, "efficiency": 0.5, "rarity": 0.4},
    2: {"name": "普通", "salary": 50, "efficiency": 0.7, "rarity": 0.3},
    3: {"name": "熟练", "salary": 80, "efficiency": 1.0, "rarity": 0.15},
    4: {"name": "精英", "salary": 120, "efficiency": 1.5, "rarity": 0.1},
    5: {"name": "传奇", "salary": 200, "efficiency": 2.5, "rarity": 0.05},
}

NPC_EMPLOYEE_NAMES = [
    "小棉花", "小雪球", "小团子", "小汤圆", "小糍粑",
    "胖橘喵", "黑豆豆", "小花咪", "小奶牛", "小狸子",
    "英短仔", "美短仔", "布偶咪", "波斯妮", "缅因哥",
    "加菲宝", "无毛仔", "折耳妹", "暹罗弟", "豹小子",
    "金金", "银银", "蓝蓝", "白白", "斑斑",
]

COMPANY_SETTLEMENT_HOUR = 0
COMPANY_SLACK_CHANCE = 0.15
COMPANY_LAZY_CHANCE = 0.1
COMPANY_SLACK_PENALTY = 0.3
COMPANY_LAZY_PENALTY = 0.5
COMPANY_MAX_NPC_PER_COMPANY = 10

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
    "signin": {"label": "📅 - 签到", "coins": 20, "intimacy": 0},
    "morning": {"label": "☀️ - 早安", "coins": 8, "intimacy": 2},
    "noon": {"label": "☀️ - 午安", "coins": 8, "intimacy": 2},
    "night": {"label": "🌙 - 晚安", "coins": 8, "intimacy": 2},
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
    "🐱 - 橘座",
    "🎀 - 布偶妹妹",
    "🐅 - 三花大姐",
    "⚫ - 黑猫警长",
    "🐶 - 暹罗少爷",
    "🐯 - 狸花老哥",
    "🐄 - 奶牛仔",
    "🐻 - 英短胖虎",
    "🌸 - 美短小花",
    "👑 - 无毛猫王",
    "👸 - 波斯公主",
    "🦁 - 缅因大佬",
    "🧸 - 折耳弟弟",
    "🍚 - 加菲吃货",
    "🦸 - 狮子猫侠",
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
    "手携式钻机": {
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
    "萌喵银行": {
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

MULTIPLAYER_GAMES = {
    "赛跑": {
        "min_players": 2,
        "max_players": 4,
        "duration": 300,
        "entry_fee": 10,
        "reward_multiplier": 2.5,
    },
    "捉迷藏": {
        "min_players": 2,
        "max_players": 6,
        "duration": 600,
        "entry_fee": 5,
        "reward_multiplier": 2.0,
    },
    "打工竞赛": {
        "min_players": 2,
        "max_players": 4,
        "duration": 1800,
        "entry_fee": 20,
        "reward_multiplier": 3.0,
    },
    "钓鱼比赛": {
        "min_players": 2,
        "max_players": 5,
        "duration": 900,
        "entry_fee": 15,
        "reward_multiplier": 2.5,
    },
}

MULTIPLAYER_GAME_LIST = list(MULTIPLAYER_GAMES.keys())
PARTY_MAX_SIZE = 4
PARTY_EXPIRE = 1800
FRIEND_REQUEST_EXPIRE = 3600
GAME_INVITE_EXPIRE = 600

INVEST_TITLE_ACHIEVEMENTS = {
    "invest_profit_500": ("理财圣手", "累计理财净赚500喵币"),
    "invest_profit_2000": ("止盈大师", "累计理财净赚2000喵币"),
    "invest_profit_5000": ("富贵险求", "累计理财净赚5000喵币"),
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
    "签到: 每天领一次喵币 (连续签到奖励更多!)\n"
    "早安/午安/晚安: 各领一次，得少量喵币+亲密度\n"
    "全部完成额外奖励!\n\n"
    "--- 教育系统 ---\n"
    "学历: 喵喵小学→初中→高中→大专→大学→研究院\n"
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
    "1. 每天签到+问候白拿喵币!\n"
    "2. 捡瓶子/捉虫子零门槛赚零花钱\n"
    "3. 先上学提升学历 → 解锁高薪工作\n"
    "4. 打工赚到的钱存银行吃利息\n"
    "5. 适当炒股/理财加速致富\n"
    "6. 贷款利息有上限，不会失控\n"
    "7. 别忘了每天喂猫猫!\n\n"
    "!!! 注意 !!!\n"
    "弃养猫猫: 扣50%喵币(最低200)、学历清零、属性重置、银行清空\n"
    "猫猫死亡: 扣30%喵币(最低100)、体力-40、声望-15\n"
    "重新领养: 扣33%喵币、学历清零、属性重置、银行清空"
)

CARD_THEMES = {
    "menu": {
        "accent": "#D4D4AA",
        "bg": "",  # #FFFFFF
        "header_color": "#2C2C2C",
        "tag_bg": "#E8E8D0",
        "border": "#E0E0E0",
        "text": "",  # #5A8CCC
        "text_sub": "#666666",
    },
    "status": {
        "accent": "#9775FA",
        "bg": "",  # #FFFFFF
        "header_color": "#6741D9",
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
        "accent": "#ADB5BD",
        "bg": "#2D2D3A",
        "header_color": "#DEE2E6",
        "tag_bg": "rgba(134,142,150,0.25)",
        "border": "#404040",
        "text": "#DEE2E6",
        "text_sub": "#ADB5BD",
    },
    "info": {
        "accent": "#1971C2",
        "bg": "",  # #FFFFFF
        "header_color": "#1971C2",
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
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            cat_data, status = self._apply_hunger_decay(user_id)
            if not cat_data:
                await self._send_reply(cmd_event, "你还没有猫猫呢~去 /猫猫 领养一只吧!")
                return
            if status != "alive":
                await self._send_reply(cmd_event, "猫猫状态不对，无法学习~")
                return
            await self._handle_study(cmd_event, cmd_event.get_user_id())

        @command("猫猫背包", help="背包/商城")
        async def bag_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            await self._handle_bag_menu(cmd_event, user_id)

        @command("猫图", help="随机猫图")
        async def cat_image_cmd(cmd_event):
            url = await self._fetch_image("neko")
            if url:
                await self._send_reply(cmd_event, "随机猫图", image_url=url)
            else:
                await self._send_reply(cmd_event, "获取图片失败~", card_type="danger")

        @command("喵喵榜", help="查看排行榜")
        async def leaderboard_cmd(cmd_event):
            await self._handle_leaderboard(cmd_event)

        @command("喵喵帮助", help="喵喵世界游戏指南")
        async def help_cmd(cmd_event):
            await self._send_reply(cmd_event, HELP_TEXT, card_type="info")

        @command("喵喵友", help="喵友系统")
        async def friends_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            await self._handle_friends_menu(cmd_event, user_id)

        @command("喵喵竞赛", help="多人竞赛")
        async def competition_cmd(cmd_event):
            user_id = cmd_event.get_user_id()
            self._register_user(user_id, cmd_event.get_user_nickname() or "")
            cat_data, status = self._apply_hunger_decay(user_id)
            if not cat_data:
                await self._send_reply(cmd_event, "你还没有猫猫呢~去 /猫猫 领养一只吧!")
                return
            if status != "alive":
                await self._send_reply(cmd_event, "猫猫状态不对，无法参加竞赛~")
                return
            await self._handle_competition_menu(cmd_event, user_id)

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

    async def _handle_main_menu(self, event):
        user_id = event.get_user_id()
        self._register_user(user_id, event.get_user_nickname() or "")

        while True:
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

                choice = await event.choose(header, ["退出", "领养一只小猫猫"])
                if choice is None or choice == 0:
                    nickname = event.get_user_nickname() or user_id
                    cat_data_exit = self._get_cat(user_id)
                    if cat_data_exit:
                        exit_msg = f"[{cat_data_exit['name']}] 在等你回来哦~\n{nickname}，下次再来玩~"
                    else:
                        exit_msg = f"{nickname}，快去领养一只小猫猫吧~"
                    await self._send_reply(
                        event, exit_msg, card_type="info", force_new=True
                    )
                    return
                await self._handle_adopt(event)
                continue

            elif status == "fostered":
                foster_days = self._get_foster_days(cat_data)
                foster_cost = self._calc_foster_cost(cat_data)
                header = (
                    f"[{cat_data['name']}] 正在寄养中  喵币:{coins}\n\n"
                    f"寄养天数: {foster_days}天 | 费用: {foster_cost}喵币\n"
                    f"(接回时结算，最多寄养{FOSTER_MAX_DAYS}天)"
                )

                choice = await event.choose(
                    header,
                    ["退出", f"接回家 ({foster_cost}喵币)", "查看状态", "背包/商城"],
                )
                if choice is None or choice == 0:
                    nickname = event.get_user_nickname() or user_id
                    cat_data_exit = self._get_cat(user_id)
                    if cat_data_exit:
                        exit_msg = f"[{cat_data_exit['name']}] 在等你回来哦~\n{nickname}，下次再来玩~"
                    else:
                        exit_msg = f"{nickname}，快去领养一只小猫猫吧~"
                    await self._send_reply(
                        event, exit_msg, card_type="info", force_new=True
                    )
                    return
                if choice == 1:
                    await self._handle_unfoster(event, user_id, cat_data)
                elif choice == 2:
                    await self._handle_status(event, cat_data, user_id)
                elif choice == 3:
                    await self._handle_bag_menu(event, user_id)

            else:
                fullness = cat_data["fullness"]
                fl, fc = self._get_stat_style("fullness", fullness)
                edu_name = EDU_LEVELS[self._get_edu(user_id)]["name"]
                attrs = self._get_attrs(user_id)
                attr_line = f"智:{attrs['int']} 体:{attrs['hp']} 魅:{attrs['cha']} 声:{attrs['rep']}"

                critical_cats = self._get_critical_cats()
                critical_notice = ""
                if len(critical_cats) > 0:
                    critical_notice = f"\n⚠️  现在有 {len(critical_cats)} 只猫猫正处于危险中，需要帮助!"

                header = (
                    f"[{cat_data['name']}] 作为铲屎官，今天做什么呢?\n\n"
                    f"饱食度: {fl}  喵币:{coins}  学历:{edu_name}\n"
                    f"{attr_line}{critical_notice}\n"
                    f"快捷命令: /猫猫状态 /猫猫喂食 /猫猫打工\n"
                    f"  /猫猫银行 /猫猫学习 /猫猫背包"
                )

                choice = await event.choose(
                    header,
                    [
                        "退出",
                        "查看状态",
                        "喂食/互动",
                        "赚钱",
                        "喵喵银行",
                        "学习深造",
                        "背包/商城",
                        "公司中心",
                        "其他列表",
                        "救助危急猫猫",
                        "多人活动",
                    ],
                )
                if choice is None or choice == 0:
                    nickname = event.get_user_nickname() or user_id
                    cat_data_exit = self._get_cat(user_id)
                    if cat_data_exit:
                        exit_msg = f"[{cat_data_exit['name']}] 在等你回来哦~\n{nickname}，下次再来玩~"
                    else:
                        exit_msg = f"{nickname}，快去领养一只小猫猫吧~"
                    await self._send_reply(
                        event, exit_msg, card_type="info", force_new=True
                    )
                    return
                if choice == 1:
                    await self._handle_status(event, cat_data, user_id)
                elif choice == 2:
                    await self._handle_feed_menu(event, user_id)
                elif choice == 3:
                    await self._handle_earn_menu(event, user_id, cat_data)
                elif choice == 4:
                    await self._handle_bank(event, user_id)
                elif choice == 5:
                    await self._handle_study(event, user_id)
                elif choice == 6:
                    await self._handle_bag_menu(event, user_id)
                elif choice == 7:
                    await self._handle_company_menu(event, user_id)
                elif choice == 8:
                    await self._handle_other_menu(event, user_id, cat_data)
                elif choice == 9:
                    await self._handle_rescue_menu(event, user_id)
                elif choice == 10:
                    await self._handle_multiplayer_menu(event, user_id, cat_data)

    async def _handle_multiplayer_menu(self, event, user_id, cat_data):
        while True:
            friend_count = len(self._get_friends(user_id))
            header = f"多人活动  喵友:{friend_count}人"

            choice = await event.choose(
                header,
                ["返回", "喵友系统", "多人竞赛", "一起喂食", "一起打工"]
            )
            if choice is None or choice == 0:
                return
            elif choice == 1:
                await self._handle_friends_menu(event, user_id)
            elif choice == 2:
                await self._handle_competition_menu(event, user_id)
            elif choice == 3:
                await self._handle_invite_feed(event, user_id, cat_data)
            elif choice == 4:
                await self._handle_invite_work(event, user_id, cat_data)

    async def _handle_invite_feed(self, event, user_id, cat_data):
        friends = self._get_friends(user_id)
        if not friends:
            await self._send_reply(
                event,
                "你还没有喵友~\n先添加喵友再一起喂食吧!",
                card_type="warning"
            )
            return

        options = ["返回"]
        for friend_id in friends:
            friend_nick = self.sdk.storage.get(f"nekocare_nickname:{friend_id}") or friend_id
            options.append(friend_nick)

        choice = await event.choose("选择喵友一起喂食", options)
        if choice is None or choice == 0:
            return

        target_id = friends[choice - 1]
        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id

        target_cat = self._get_cat(target_id)
        if not target_cat or target_cat.get("status") != "alive":
            await self._send_reply(
                event,
                f"{target_nick} 没有可以喂食的猫猫~",
                card_type="danger"
            )
            return

        feed_fullness = random.randint(3, 8)
        feed_intimacy = random.randint(1, 3)

        cat_data["fullness"] = min(100, cat_data["fullness"] + feed_fullness)
        cat_data["intimacy"] = min(100, cat_data["intimacy"] + feed_intimacy)
        target_cat["fullness"] = min(100, target_cat["fullness"] + feed_fullness)
        target_cat["intimacy"] = min(100, target_cat["intimacy"] + feed_intimacy)

        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self.sdk.storage.set(f"nekocare:{target_id}", target_cat)

        url = await self._fetch_image("hug")
        await self._send_reply(
            event,
            f"你和 [{cat_data['name']}] 一起喂 [{target_cat['name']}] ~\n"
            f"饱食度+{feed_fullness} 亲密度+{feed_intimacy}\n\n"
            f"[{target_nick}] 的 [{target_cat['name']}] 也吃饱啦!",
            image_url=url,
            card_type="success"
        )
        await event.reply(f"🎉 {target_nick}，你的猫猫也被喂饱了!")

    async def _handle_invite_work(self, event, user_id, cat_data):
        friends = self._get_friends(user_id)
        if not friends:
            await self._send_reply(
                event,
                "你还没有喵友~\n先添加喵友再一起打工吧!",
                card_type="warning"
            )
            return

        options = ["返回"]
        for friend_id in friends:
            friend_nick = self.sdk.storage.get(f"nekocare_nickname:{friend_id}") or friend_id
            options.append(friend_nick)

        choice = await event.choose("选择喵友一起打工", options)
        if choice is None or choice == 0:
            return

        target_id = friends[choice - 1]
        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id

        target_cat = self._get_cat(target_id)
        if not target_cat or target_cat.get("status") != "alive":
            await self._send_reply(
                event,
                f"{target_nick} 没有可以打工的猫猫~",
                card_type="danger"
            )
            return

        now = time.time()
        last_work = self._get_work_cooldown(user_id)
        remaining = 1800 - (now - last_work)
        if remaining > 0:
            mins = int(remaining // 60) + 1
            await self._send_reply(event, f"你的猫猫还在休息，{mins}分钟后再来~")
            return

        if cat_data["fullness"] < 10 or target_cat["fullness"] < 10:
            await self._send_reply(event, "猫猫太饿了，先喂饱再来~", card_type="danger")
            return

        job = random.choice(JOBS[0])
        earnings = random.randint(job["earn_min"], job["earn_max"])
        target_earnings = random.randint(job["earn_min"], job["earn_max"])

        bonus = 0
        attrs = self._get_attrs(user_id)
        target_attrs = self._get_attrs(target_id)
        stat_val = attrs.get(job.get("stat", "hp"), 0)
        target_stat_val = target_attrs.get(job.get("stat", "hp"), 0)

        if stat_val >= 60:
            bonus = int(earnings * 0.15)
            earnings += bonus

        self._add_coins(user_id, earnings)
        self._add_coins(target_id, target_earnings)
        self._set_work_cooldown(user_id)

        my_fullness_loss = random.randint(job["nrg_min"], job["nrg_max"])
        target_fullness_loss = random.randint(job["nrg_min"], job["nrg_max"])

        cat_data["fullness"] = max(0, cat_data["fullness"] - my_fullness_loss)
        target_cat["fullness"] = max(0, target_cat["fullness"] - target_fullness_loss)

        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self.sdk.storage.set(f"nekocare:{target_id}", target_cat)

        self._inc_stat(user_id, "work_count")
        self._inc_stat(target_id, "work_count")

        url = await self._fetch_image("happy")
        results = (
            f"你们一起打工回来啦!\n\n"
            f"[{cat_data['name']}]: +{earnings}喵币\n"
            f"[{target_cat['name']}]: +{target_earnings}喵币\n\n"
            f"团队加成: 合作愉快!"
        )
        await self._send_reply(event, results, image_url=url, card_type="success")
        await event.reply(f"🎉 {target_nick}，你获得了 {target_earnings} 喵币!")

    async def _handle_feed_menu(self, event, user_id):
        while True:
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
            header = f"饱食度: {fl}\n今日剩余{feed_left}次喂食"

            choice = await event.choose(header, ["返回", "喂食", "贴贴", "摸摸"])
            if choice is None or choice == 0:
                return
            if choice == 1:
                await self._do_feed(event, user_id, cat_data)
            elif choice == 2:
                await self._do_cuddle(event, user_id, cat_data)
            elif choice == 3:
                await self._do_pat(event, user_id, cat_data)

    async def _handle_earn_menu(self, event, user_id, cat_data=None):
        while True:
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

            header = f"打工({wr})  抓猫({cr})  打劫({rr})\n捡瓶子({sr})  摸鱼捉虫({sr})  招聘市场"

            choice = await event.choose(
                header, ["返回", "打工", "抓猫打工", "打劫", "捡瓶子", "摸鱼捉虫", "招聘市场"]
            )
            if choice is None or choice == 0:
                return
            elif choice == 1:
                await self._handle_work(event, user_id)
            elif choice == 2:
                await self._handle_catch(event, user_id)
            elif choice == 3:
                await self._handle_rob(event, user_id)
            elif choice == 4:
                await self._handle_scavenge(event, user_id)
            elif choice == 5:
                await self._handle_bugcatch(event, user_id)
            elif choice == 6:
                await self._handle_job_market(event, user_id)

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
        reward_text = f"+{info['coins']}喵币"
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

        text = f"签到成功! 第{streak}天连续签到\n+{bonus}喵币"
        if extra > 0:
            text += f"\n今日全部完成! 额外+{extra}喵币"
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
            active_title = self._get_active_title(user_id)
            title_text = f" [{active_title}]" if active_title else ""
            friend_count = len(self._get_friends(user_id))
            header = f"当前猫猫: [{cat_data['name']}]{title_text}\n喵友: {friend_count}人"

            choice = await event.choose(
                header, ["返回", "寄养猫猫", "改名", "查看/设置头衔", "喵友系统", "弃养猫猫"]
            )
            if choice is None or choice == 0:
                return
            elif choice == 1:
                await self._handle_foster(event, user_id, cat_data)
            elif choice == 2:
                await self._handle_rename(event, user_id, cat_data)
            elif choice == 3:
                await self._handle_titles(event, user_id)
            elif choice == 4:
                await self._handle_friends_menu(event, user_id)
            elif choice == 5:
                if await self._handle_abandon(event, user_id, cat_data):
                    return

    async def _handle_friends_menu(self, event, user_id):
        while True:
            friends = self._get_friends(user_id)
            requests = self._get_friend_requests(user_id)
            request_count = len(requests)
            header = f"喵友系统  喵友:{len(friends)}人"
            if request_count > 0:
                header += f"  请求:{request_count}人"

            choice = await event.choose(
                header,
                ["返回", "查看喵友", "添加喵友", "删除喵友", f"好友请求({request_count})", "竞赛大厅"]
            )
            if choice is None or choice == 0:
                return
            elif choice == 1:
                await self._handle_list_friends(event, user_id)
            elif choice == 2:
                await self._handle_add_friend(event, user_id)
            elif choice == 3:
                await self._handle_remove_friend(event, user_id)
            elif choice == 4:
                await self._handle_friend_requests(event, user_id)
            elif choice == 5:
                await self._handle_competition_menu(event, user_id)

    async def _handle_list_friends(self, event, user_id):
        friends = self._get_friends(user_id)
        if not friends:
            await self._send_reply(event, "你还没有喵友呢~\n输入 2 添加喵友吧!", card_type="info")
            return

        lines = ["你的喵友\n"]
        for i, friend_id in enumerate(friends, 1):
            friend_nick = self.sdk.storage.get(f"nekocare_nickname:{friend_id}") or friend_id
            friend_cat = self._get_cat(friend_id)
            cat_status = friend_cat["status"] if friend_cat else "无猫"
            cat_name = friend_cat["name"] if friend_cat else "-"
            lines.append(f"{i}. {friend_nick} | {cat_name} [{cat_status}]")

        await self._send_reply(event, "\n".join(lines), card_type="info")

    async def _handle_add_friend(self, event, user_id):
        reply = await event.wait_reply("请 @你想加为喵友的用户 (或输入用户ID):", timeout=60)
        if not reply:
            return

        mentions = reply.get_mentions()
        target_id = mentions[0] if mentions else reply.get_text().strip()
        if not target_id:
            await self._send_reply(event, "已取消")
            return

        if target_id == user_id:
            await self._send_reply(event, "不能加自己为喵友!")
            return

        if self._is_friend(user_id, target_id):
            await self._send_reply(event, "这个人已经是你的喵友了!")
            return

        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id
        if self._add_friend_request(user_id, target_id):
            await self._send_reply(
                event,
                f"已向 {target_nick} 发送好友请求~\n等待对方同意，就能一起玩了!",
                card_type="success"
            )
        else:
            await self._send_reply(event, "你已经给TA发过请求了，等待同意~", card_type="warning")

    async def _handle_remove_friend(self, event, user_id):
        friends = self._get_friends(user_id)
        if not friends:
            await self._send_reply(event, "你还没有喵友呢!", card_type="info")
            return

        options = ["返回"]
        for friend_id in friends:
            friend_nick = self.sdk.storage.get(f"nekocare_nickname:{friend_id}") or friend_id
            options.append(friend_nick)

        choice = await event.choose("删除喵友", options)
        if choice is None or choice == 0:
            return

        target_id = friends[choice - 1]
        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id

        if self._remove_friend(user_id, target_id):
            self._remove_friend(target_id, user_id)
            await self._send_reply(event, f"已删除喵友 {target_nick}", card_type="success")

    async def _handle_friend_requests(self, event, user_id):
        requests = self._get_friend_requests(user_id)
        if not requests:
            await self._send_reply(event, "没有新的好友请求~", card_type="info")
            return

        now = time.time()
        valid_requests = []
        for req in requests:
            if now - req["time"] < FRIEND_REQUEST_EXPIRE:
                valid_requests.append(req)

        if not valid_requests:
            await self._send_reply(event, "没有新的好友请求~", card_type="info")
            return

        self.sdk.storage.set(f"nekocare_friend_requests:{user_id}", valid_requests)

        options = ["返回"]
        for req in valid_requests:
            from_id = req["from"]
            from_nick = self.sdk.storage.get(f"nekocare_nickname:{from_id}") or from_id
            options.append(from_nick)

        choice = await event.choose(f"好友请求 ({len(valid_requests)}人)", options)
        if choice is None or choice == 0:
            return

        target_id = valid_requests[choice - 1]["from"]
        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id

        await event.reply(f"1. 同意  2. 拒绝  0. 返回")
        reply = await event.wait_reply(f"是否同意 {target_nick} 的好友请求?", timeout=30)
        if not reply:
            return

        text = reply.get_text().strip()
        if text == "1":
            if self._is_friend(user_id, target_id):
                await self._send_reply(event, "你们已经是好友了~", card_type="info")
            else:
                self._add_friend(user_id, target_id)
                self._add_friend(target_id, user_id)
                await self._send_reply(
                    event,
                    f"已同意 {target_nick} 的请求!\n现在你们是喵友了~",
                    card_type="success"
                )
                await event.reply(f"🎉 你和 {target_nick} 成为喵友了!")
        elif text == "2":
            await self._send_reply(event, "已拒绝请求", card_type="info")
        else:
            return

    async def _handle_competition_menu(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data or status != "alive":
            await self._send_reply(event, "你需要有一只活着的猫猫才能参加竞赛!", card_type="danger")
            return

        coins = self._get_coins(user_id)
        friends = self._get_friends(user_id)
        party = self._get_party(user_id)
        party_info = ""
        if party:
            member_count = len(party["members"])
            party_info = f"\n当前队伍: {member_count}/{PARTY_MAX_SIZE}人"

        header = f"多人竞赛  喵币:{coins}\n 喵友: {len(friends)}人{party_info}"

        choice = await event.choose(
            header,
            ["返回", "队伍(组队)", "快速开始", "我的竞赛"]
        )
        if choice is None or choice == 0:
            return
        elif choice == 1:
            await self._handle_party_menu(event, user_id, cat_data)
        elif choice == 2:
            await self._handle_quick_start(event, user_id, cat_data)
        elif choice == 3:
            await self._handle_my_competitions(event, user_id, cat_data)

    async def _handle_create_competition(self, event, user_id, cat_data):
        options = ["返回"]
        for game in MULTIPLAYER_GAME_LIST:
            config = MULTIPLAYER_GAMES[game]
            options.append(f"{game} (押金{config['entry_fee']}喵币)")

        choice = await event.choose("选择竞赛类型", options)
        if choice is None or choice == 0:
            return

        game_type = MULTIPLAYER_GAME_LIST[choice - 1]
        config = MULTIPLAYER_GAMES[game_type]
        entry_fee = config["entry_fee"]

        coins = self._get_coins(user_id)
        if coins < entry_fee:
            await self._send_reply(
                event,
                f"押金不足! 需要 {entry_fee} 喵币，你只有 {coins} 喵币",
                card_type="danger"
            )
            return

        invites = self._get_game_invites(game_type)
        for inv in invites:
            if inv["host_id"] == user_id:
                await self._send_reply(event, "你已经在竞赛中了!", card_type="warning")
                return

        self._add_coins(user_id, -entry_fee)
        self._create_game_invite(user_id, game_type, {
            "game_type": game_type,
            "entry_fee": entry_fee,
            "cat_data": cat_data
        })

        friends = self._get_friends(user_id)
        invite_text = f"你创建了【{game_type}】竞赛!\n押金: {entry_fee} 喵币\n\n"
        if friends:
            invite_text += "请你的喵友使用 /喵喵竞赛 → 加入竞赛 来参加!"
        else:
            invite_text += "建议先添加喵友后再创建竞赛~"

        await self._send_reply(event, invite_text, card_type="success")

    async def _handle_join_competition(self, event, user_id, cat_data):
        has_open = False
        all_games = []

        for game_type in MULTIPLAYER_GAME_LIST:
            invites = self._get_game_invites(game_type)
            for inv in invites:
                if user_id not in inv["players"] and inv["expire"] > time.time():
                    has_open = True
                    all_games.append((game_type, inv))

        if not has_open:
            await self._send_reply(event, "当前没有可加入的竞赛~", card_type="info")
            return

        options = ["返回"]
        for game_type, inv in all_games:
            host_id = inv["host_id"]
            host_nick = self.sdk.storage.get(f"nekocare_nickname:{host_id}") or host_id
            player_count = len(inv["players"])
            config = MULTIPLAYER_GAMES[game_type]
            options.append(f"{game_type} | {host_nick} | {player_count}/{config['max_players']}人")

        choice = await event.choose("可加入的竞赛", options)
        if choice is None or choice == 0:
            return

        game_type, invite = all_games[choice - 1]
        config = MULTIPLAYER_GAMES[game_type]
        entry_fee = config["entry_fee"]

        coins = self._get_coins(user_id)
        if coins < entry_fee:
            await self._send_reply(
                event,
                f"押金不足! 需要 {entry_fee} 喵币，你只有 {coins} 喵币",
                card_type="danger"
            )
            return

        result = self._join_game(game_type, user_id)
        if result:
            self._add_coins(user_id, -entry_fee)
            await self._send_reply(
                event,
                f"已加入【{game_type}】竞赛!\n当前玩家: {len(result['players'])}人",
                card_type="success"
            )
            host_nick = self.sdk.storage.get(f"nekocare_nickname:{invite['host_id']}") or invite['host_id']
            await event.reply(f"🎉 {host_nick} 发起了一场 {game_type}，你已加入!")
        else:
            await self._send_reply(event, "加入失败，可能人满或已过期~", card_type="danger")

    async def _handle_my_competitions(self, event, user_id, cat_data):
        all_my_games = []

        for game_type in MULTIPLAYER_GAME_LIST:
            invites = self._get_game_invites(game_type)
            for inv in invites:
                if user_id in inv["players"]:
                    all_my_games.append((game_type, inv))

        if not all_my_games:
            await self._send_reply(event, "你还没有参加任何竞赛~", card_type="info")
            return

        options = ["返回"]
        for game_type, inv in all_my_games:
            host_nick = self.sdk.storage.get(f"nekocare_nickname:{inv['host_id']}") or inv['host_id']
            is_host = inv["host_id"] == user_id
            status = "房主" if is_host else "玩家"
            player_count = len(inv["players"])
            config = MULTIPLAYER_GAMES[game_type]
            options.append(f"{game_type} | {host_nick}({status}) | {player_count}/{config['max_players']}人")

        choice = await event.choose("我的竞赛", options)
        if choice is None or choice == 0:
            return

        game_type, invite = all_my_games[choice - 1]
        is_host = invite["host_id"] == user_id
        config = MULTIPLAYER_GAMES[game_type]
        player_count = len(invite["players"])

        if is_host:
            if player_count >= config["min_players"]:
                await self._run_competition(event, user_id, game_type, invite)
                return

            await event.reply(
                f"当前 {player_count} 人，需要至少 {config['min_players']} 人\n"
                f"1. 立即开始  2. 等待更多玩家  0. 返回"
            )
            reply = await event.wait_reply(
                f"人数不足，是否立即开始?(押金不退)", timeout=30
            )
            if reply:
                text = reply.get_text().strip()
                if text == "1":
                    await self._run_competition(event, user_id, game_type, invite)
                elif text == "2":
                    return
        else:
            host_nick = self.sdk.storage.get(f"nekocare_nickname:{invite['host_id']}") or invite['host_id']
            await self._send_reply(
                event,
                f"你是玩家，等待房主 {host_nick} 开始游戏~\n当前 {player_count}/{config['max_players']} 人",
                card_type="info"
            )

    async def _run_competition(self, event, host_id, game_type, invite):
        game_config = MULTIPLAYER_GAMES[game_type]
        players = invite["players"]
        entry_fee = game_config["entry_fee"]
        reward = int(entry_fee * game_config["reward_multiplier"])

        results = [f"=== {game_type} 结果 ===\n"]
        player_results = {}

        for player_id in players:
            cat = self._get_cat(player_id)
            if cat and cat.get("status") == "alive":
                if game_type == "赛跑":
                    score = random.randint(1, 100) + random.randint(0, 30)
                elif game_type == "捉迷藏":
                    score = random.randint(1, 100) + random.randint(0, 20)
                elif game_type == "打工竞赛":
                    job = random.choice(JOBS[0])
                    score = random.randint(job["earn_min"], job["earn_max"]) * 3
                elif game_type == "钓鱼比赛":
                    score = random.randint(5, 50)
                else:
                    score = random.randint(1, 100)

                player_results[player_id] = score

        if not player_results:
            for player_id in players:
                self._add_coins(player_id, entry_fee)

            await self._send_reply(event, "没有玩家完成任务，退还押金~", card_type="warning")
            return

        sorted_results = sorted(player_results.items(), key=lambda x: x[1], reverse=True)

        rewards = {0: reward, 1: int(reward * 0.6), 2: int(reward * 0.3)}
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}

        for i, (player_id, score) in enumerate(sorted_results):
            nick = self.sdk.storage.get(f"nekocare_nickname:{player_id}") or player_id
            cat = self._get_cat(player_id)
            cat_name = cat["name"] if cat else "?"
            medal = medals.get(i, f"{i + 1}.")
            prize = rewards.get(i, 0)

            self._add_coins(player_id, prize)
            self._inc_stat(player_id, "contest_count")

            results.append(f"{medal} {nick} | {cat_name} | {score}分 | +{prize}喵币")

        await self._send_reply(event, "\n".join(results), card_type="success")

        game_invites = self._get_game_invites(game_type)
        game_invites = [inv for inv in game_invites if inv["host_id"] != host_id or set(inv["players"]) != set(players)]
        self.sdk.storage.set(f"nekocare_game_invites:{game_type}", game_invites)

    async def _handle_party_menu(self, event, user_id, cat_data):
        while True:
            party = self._get_party(user_id)
            friends = self._get_friends(user_id)

            if party:
                member_list = []
                for mid in party["members"]:
                    nick = self.sdk.storage.get(f"nekocare_nickname:{mid}") or mid
                    cat_name = party["cat_names"].get(mid, "?")
                    is_host = "⭐" if mid == party["host_id"] else ""
                    member_list.append(f"{nick}({cat_name}){is_host}")
                member_text = "\n".join(member_list)
                header = f"队伍(组队)\n{member_text}"
                options = ["返回", "快速开始", "离开队伍"]
            else:
                header = "队伍(组队)\n你还没有队伍"
                options = ["返回", "创建队伍", "加入队伍"]

            choice = await event.choose(header, options)
            if choice is None or choice == 0:
                return

            if party:
                if choice == 1:
                    await self._handle_quick_race(event, user_id, cat_data)
                elif choice == 2:
                    await self._handle_leave_party(event, user_id)
            else:
                if choice == 1:
                    await self._handle_create_party(event, user_id, cat_data)
                elif choice == 2:
                    await self._handle_join_party_menu(event, user_id, cat_data)

    async def _handle_create_party(self, event, user_id, cat_data):
        self._create_party(user_id, cat_data)
        host_nick = self.sdk.storage.get(f"nekocare_nickname:{user_id}") or user_id
        await self._send_reply(event, f"队伍创建成功!\n队长: {host_nick}\n\n让喵友使用 /喵喵竞赛 → 队伍(组队) → 加入队伍 来加入!", card_type="success")

    async def _handle_join_party_menu(self, event, user_id, cat_data):
        all_parties = self._get_all_parties()
        available = []
        for p in all_parties:
            if len(p["members"]) < PARTY_MAX_SIZE and user_id not in p["members"]:
                if time.time() - p.get("created", 0) <= PARTY_EXPIRE:
                    available.append(p)

        if not available:
            await self._send_reply(event, "当前没有可加入的队伍~\n让喵友先创建队伍吧!", card_type="info")
            return

        options = ["返回"]
        for p in available:
            host_nick = self.sdk.storage.get(f"nekocare_nickname:{p['host_id']}") or p["host_id"]
            options.append(f"{host_nick} ({len(p['members'])}/{PARTY_MAX_SIZE})")

        choice = await event.choose("可加入的队伍", options)
        if choice is None or choice == 0:
            return

        party = available[choice - 1]
        host_id = party["host_id"]
        self._join_party(host_id, user_id, cat_data)

        host_nick = self.sdk.storage.get(f"nekocare_nickname:{host_id}") or host_id
        await self._send_reply(event, f"已加入 {host_nick} 的队伍!", card_type="success")

    async def _handle_invite_party(self, event, user_id, cat_data):
        party = self._get_party(user_id)
        if not party:
            await self._send_reply(event, "你还没有队伍，先创建一个吧!", card_type="warning")
            return

        friends = self._get_friends(user_id)
        if not friends:
            await self._send_reply(event, "你还没有喵友，先添加喵友吧!", card_type="warning")
            return

        members = set(party["members"])
        available = [f for f in friends if f not in members]
        if not available:
            await self._send_reply(event, "所有喵友都已在队伍中!", card_type="info")
            return

        options = ["返回"]
        for friend_id in available:
            nick = self.sdk.storage.get(f"nekocare_nickname:{friend_id}") or friend_id
            options.append(nick)

        choice = await event.choose("邀请喵友加入队伍", options)
        if choice is None or choice == 0:
            return

        target_id = available[choice - 1]
        target_nick = self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id

        host_nick = self.sdk.storage.get(f"nekocare_nickname:{user_id}") or user_id
        await event.reply(f"邀请已发送给 {target_nick}!")
        await self._send_reply(event, f"⭐ {host_nick} 邀请你加入队伍!\n1. 加入  0. 拒绝", card_type="info")

    async def _handle_leave_party(self, event, user_id):
        party = self._get_party(user_id)
        if not party:
            await self._send_reply(event, "你不在队伍中!", card_type="warning")
            return

        self._leave_party(user_id)
        await self._send_reply(event, "已离开队伍!", card_type="info")

    async def _handle_quick_start(self, event, user_id, cat_data):
        party = self._get_party(user_id)
        if not party:
            await self._send_reply(event, "你还没有队伍!\n先创建一个队伍，然后邀请喵友加入吧~", card_type="warning")
            return

        config = MULTIPLAYER_GAMES["打工竞赛"]
        entry_fee = config["entry_fee"]
        total_fee = entry_fee * len(party["members"])

        coins = self._get_coins(user_id)
        if coins < total_fee:
            await self._send_reply(event, f"押金不足! 需要 {total_fee} 喵币，你只有 {coins} 喵币", card_type="danger")
            return

        await self._run_party_competition(event, user_id, cat_data, party, "打工竞赛")

    async def _handle_quick_race(self, event, user_id, cat_data):
        party = self._get_party(user_id)
        if not party:
            await self._send_reply(event, "你还没有队伍!\n先创建一个队伍吧~", card_type="warning")
            return

        options = ["返回", "赛跑", "捉迷藏", "打工竞赛", "钓鱼比赛"]
        choice = await event.choose("选择游戏", options)
        if choice is None or choice == 0:
            return

        game_type = MULTIPLAYER_GAME_LIST[choice - 1]
        config = MULTIPLAYER_GAMES[game_type]
        entry_fee = config["entry_fee"]
        total_fee = entry_fee * len(party["members"])

        coins = self._get_coins(user_id)
        if coins < total_fee:
            await self._send_reply(event, f"押金不足! 需要 {total_fee} 喵币，你只有 {coins} 喵币", card_type="danger")
            return

        await self._run_party_competition(event, user_id, cat_data, party, game_type)

    async def _run_party_competition(self, event, user_id, cat_data, party, game_type):
        game_config = MULTIPLAYER_GAMES[game_type]
        players = party["members"]
        entry_fee = game_config["entry_fee"]
        total_fee = entry_fee * len(players)
        reward = int(entry_fee * game_config["reward_multiplier"])

        for p in players:
            self._add_coins(p, -entry_fee)

        results = [f"=== {game_type} 组队赛 ===\n"]
        player_results = {}

        for player_id in players:
            cat = self._get_cat(player_id)
            if cat and cat.get("status") == "alive":
                if game_type == "赛跑":
                    score = random.randint(1, 100) + random.randint(0, 30)
                elif game_type == "捉迷藏":
                    score = random.randint(1, 100) + random.randint(0, 20)
                elif game_type == "打工竞赛":
                    job = random.choice(JOBS[0])
                    score = random.randint(job["earn_min"], job["earn_max"]) * 3
                elif game_type == "钓鱼比赛":
                    score = random.randint(5, 50)
                else:
                    score = random.randint(1, 100)

                player_results[player_id] = score

        if not player_results:
            for player_id in players:
                self._add_coins(player_id, entry_fee)
            await self._send_reply(event, "没有玩家完成游戏，退还押金~", card_type="warning")
            return

        sorted_results = sorted(player_results.items(), key=lambda x: x[1], reverse=True)
        rewards = {0: reward, 1: int(reward * 0.6), 2: int(reward * 0.3)}
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}

        for i, (player_id, score) in enumerate(sorted_results):
            nick = self.sdk.storage.get(f"nekocare_nickname:{player_id}") or player_id
            cat = self._get_cat(player_id)
            cat_name = cat["name"] if cat else "?"
            medal = medals.get(i, f"{i + 1}.")
            prize = rewards.get(i, 0)

            self._add_coins(player_id, prize)
            self._inc_stat(player_id, "contest_count")

            results.append(f"{medal} {nick} | {cat_name} | {score}分 | +{prize}喵币")

        await self._send_reply(event, "\n".join(results), card_type="success")

    async def _handle_scavenge(self, event, user_id):
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
            f"[{cat_data['name']}] 在路边捡到了【{item_name}】!\n卖了 {coins} 喵币~",
            f"[{cat_data['name']}] 叼回了【{item_name}】!\n换了 {coins} 喵币!",
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
            f"[{cat_data['name']}] 捉到了【{bug_name}】!\n卖了 {coins} 喵币~",
            f"[{cat_data['name']}] 扑腾半天抓到【{bug_name}】!\n赚了 {coins} 喵币!",
        ]
        await self._send_reply(
            event, random.choice(msgs), image_url=url, card_type="success"
        )

    async def _handle_bag_menu(self, event, user_id):
        while True:
            coins = self._get_coins(user_id)
            bag_text = self._build_bag_display(user_id, coins)
            bag_text += "\n1.使用道具  2.前往商城  3.查看增益  4.查看头衔  0. 返回"

            reply = await event.wait_reply(bag_text, timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            if text == "0":
                return
            if text == "1":
                await self._handle_use_item(event, user_id)
            elif text == "2":
                await self._handle_shop_menu(event, user_id)
            elif text == "3":
                await self._show_buffs(event, user_id)
            elif text == "4":
                await self._handle_titles(event, user_id)

    async def _handle_shop_menu(self, event, user_id):
        while True:
            coins = self._get_coins(user_id)
            shop_text = self._build_shop_display(coins)
            shop_text += "\n输入编号购买 | 0. 返回"

            reply = await event.wait_reply(shop_text, timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            try:
                idx = int(text)
            except ValueError:
                await event.reply("请输入有效编号")
                continue
            if idx == 0:
                return
            if idx < 1 or idx > len(SHOP_ITEM_LIST):
                await event.reply("无效编号")
                continue
            await self._do_buy(event, user_id, SHOP_ITEM_LIST[idx - 1])

    async def _handle_use_item(self, event, user_id):
        inventory = self._get_inventory(user_id)
        coins = self._get_coins(user_id)

        available = []
        display_indices = []
        for i, name in enumerate(SHOP_ITEM_LIST):
            count = inventory.get(name, 0)
            if count > 0:
                item = SHOP_ITEMS[name]
                display_idx = i + 1
                available.append((display_idx, name, count, item))
                display_indices.append(display_idx)

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

        lines = [f"使用道具  喵币:{coins}\n"]
        for idx, name, count, item in available:
            lines.append(f"{idx}. {name}  x{count}  {item['desc']}")
        if has_tools:
            lines.append("\n--- 作案工具 (用于抢劫) ---")
            lines.extend(tool_lines)
        lines.append("\n输入编号使用 | 0. 返回")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            selected_idx = int(text)
        except ValueError:
            await self._send_reply(event, "请输入有效编号", card_type="danger")
            return

        if selected_idx == 0:
            return

        selected_item = None
        for idx, name, count, item in available:
            if idx == selected_idx:
                selected_item = (idx, name, count, item)
                break

        if selected_item is None:
            await self._send_reply(event, "无效编号", card_type="danger")
            return

        idx, name, count, item = selected_item
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

            reply = await event.wait_reply(
                f"使用几个【{name}】? (1-{count})", timeout=60
            )
            if reply is None:
                return
            try:
                qty = int(reply.get_text().strip())
            except ValueError:
                await event.reply("请输入数字")
                return
            if qty < 1 or qty > count:
                await event.reply(f"请输入 1-{count}")
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

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            choice = int(text)
        except ValueError:
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
        reply = await event.wait_reply("请给小猫猫取个名字（限20字内）：", timeout=120)
        if not reply:
            return

        name = reply.get_text().strip()

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

    async def _handle_rescue_menu(self, event, rescuer_id):
        critical_cats = self._get_critical_cats()

        if not critical_cats:
            await self._send_reply(
                event,
                "🎉 太棒了！现在没有需要救助的猫猫~\n所有猫猫都安全健康着呢~",
                card_type="success",
            )
            return

        menu = "🐾  待救助的危急猫猫\n\n"
        rescue_options = ["返回上一级"]

        for idx, cat in enumerate(critical_cats, 1):
            menu += f"{idx}. [{cat['name']}] - 剩余 {cat['remaining']} 小时\n"
            rescue_options.append(f"[{cat['name']}] - 剩余 {cat['remaining']} 小时")

        menu += "\n选择要救助的猫猫:"
        await self._send_reply(event, menu, card_type="warning")
        choice = await event.choose("选择要救助的猫猫编号:", rescue_options)

        if choice is None or choice == 0:
            return

        selected_idx = choice - 1
        target_cat = critical_cats[selected_idx]
        target_user_id = target_cat["user_id"]

        await self._perform_rescue(event, rescuer_id, target_user_id, target_cat)

    async def _perform_rescue(self, event, rescuer_id, target_user_id, target_cat):
        cat_data = self._get_cat(target_user_id)

        if not cat_data or cat_data.get("status") != "critical":
            await self._send_reply(
                event, "这只猫猫已经被其他人救走啦~", card_type="info"
            )
            return

        rescuer_coins = self._get_coins(rescuer_id)

        if rescuer_coins < 30:
            await self._send_reply(
                event,
                f"救助需要 30 喵币购买营养针和食物，你只有 {rescuer_coins} 枚\n"
                f"先去打打工再来帮助它吧！",
                card_type="danger",
            )
            return

        # 扣除救助费用
        self._add_coins(rescuer_id, -30)

        # 100% 救助成功
        now = time.time()
        cat_data["status"] = "alive"
        cat_data["fullness"] = 35
        cat_data["critical_since"] = 0
        cat_data["last_decay"] = now
        self.sdk.storage.set(f"nekocare:{target_user_id}", cat_data)

        # 增加救助者统计
        self._inc_stat(rescuer_id, "rescue_count")
        self._check_achievement_titles(rescuer_id)

        # 给被救助者发送通知
        rescuer_nick = event.get_user_nickname() or "好心的铲屎官"
        notify_msg = (
            f"🎉 好消息！你的猫猫 [{cat_data['name']}] 被救了！\n"
            f"感谢 {rescuer_nick} 伸出援手，它现在已经脱离危险~\n"
            f"饱食度恢复到 35，以后要好好照顾它哦！"
        )
        await event.reply(notify_msg)

        url = await self._fetch_image("happy")
        msg = (
            f"💖 救助成功！\n\n"
            f"你花费 30 喵币救助了 [{target_cat['name']}]\n"
            f"它现在脱离了危险，正在咕噜咕噜感谢你~\n"
            f"救助计数 +1，继续加油哦！"
        )
        await self._send_reply(event, msg, image_url=url, card_type="success")

    async def _handle_rescue(self, event, user_id):
        await self._handle_rescue_menu(event, user_id)

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

        header = f"学历:{edu_name}\n输入编号打工"
        job_options = ["返回"]
        for i, job in enumerate(available_jobs, 1):
            tag = " [隐藏]" if job in HIDDEN_JOBS else ""
            job_options.append(
                f"{job['name']}{tag} ({job['earn_min']}-{job['earn_max']}喵币)"
            )

        choice = await event.choose(header, job_options)
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
                f"它带着赚到的 {earnings} 喵币，永远地去了喵星。\n"
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
            f"[{cat_data['name']}] {job['name']}回来啦! 赚了 {earnings} 喵币~",
            f"{job['name']}完成! +{earnings} 喵币!",
            f"辛苦{job['name']}! {earnings} 喵币入袋!",
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

        reply = await event.wait_reply(
            "请 @你想抓的猫猫的主人 (或输入用户ID):", timeout=60
        )
        if not reply:
            return

        mentions = reply.get_mentions()
        target_id = mentions[0] if mentions else reply.get_text().strip()
        if not target_id:
            await self._send_reply(event, "已取消")
            return
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
                    f"成功抓到 [{target_cat['name']}]! 赚了 {earnings} 喵币!\n"
                    f"但 [{cat_data['name']}] 因体力不支倒下了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url, card_type="death")
                return

            url = await self._fetch_image("neko")
            msgs = [
                f"成功抓到 [{target_cat['name']}] 打工! +{earnings} 喵币!",
                f"[{target_cat['name']}] 被抓去打工啦! 收获 {earnings} 喵币!",
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

        choice = await event.choose(
            "打劫",
            [
                "返回",
                "打劫野外猫猫 (低风险低回报)",
                "打劫其他玩家 (高风险高回报)",
                "抢劫地点 (便利店/加油站/ATM/珠宝店/银行)",
                "黑市 (购买作案工具)",
            ],
        )
        if choice is None or choice == 0:
            return

        if choice == 1:
            await self._do_rob_npc(event, user_id, cat_data, attrs)
        elif choice == 2:
            await self._do_rob_player(event, user_id, cat_data, attrs)
        elif choice == 3:
            await self._handle_rob_target(event, user_id, cat_data, attrs)
        elif choice == 4:
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
                f"罚款 {actual_fine} 喵币，声望-5\n"
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
                f"成功打劫了[{target}]! 抢到 {loot} 喵币!",
                f"从[{target}]身上摸到了 {loot} 喵币!",
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
                f"[{target}] 太机灵了! 打劫失败，倒赔 {actual_penalty} 喵币~",
                f"被[{target}]揍了一顿! 损失 {actual_penalty} 喵币!",
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

        reply = await event.wait_reply("请 @你想打劫的目标 (或输入用户ID):", timeout=60)
        if not reply:
            return

        mentions = reply.get_mentions()
        target_id = mentions[0] if mentions else reply.get_text().strip()
        if not target_id:
            await self._send_reply(event, "已取消")
            return
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
                f"罚款 {actual_fine} 喵币，声望-10",
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
                    f"打劫成功! 抢了 {stolen} 喵币!\n"
                    f"但 [{cat_data['name']}] 在逃跑途中累倒了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url, card_type="death")
                return

            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            url = await self._fetch_image("neko")
            msgs = [
                f"打劫成功! 抢了 {stolen} 喵币! (声望下降...)",
                f"[{cat_data['name']}] 成功打劫! +{stolen} 喵币!",
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
                f"打劫失败! 被[{target_name}] 发现了，赔偿 {actual_penalty} 喵币!",
                f"[{cat_data['name']}] 打劫扑空了，倒赔 {actual_penalty} 喵币!",
            ]
            await self._send_reply(
                event, random.choice(msgs), image_url=url, card_type="danger"
            )

    async def _handle_blackmarket(self, event, user_id):
        while True:
            coins = self._get_coins(user_id)
            inv = self._get_inventory(user_id)

            lines = [f"黑市  喵币:{coins}\n"]
            lines.append("--- 购买 ---")
            for i, name in enumerate(BLACKMARKET_ITEM_LIST, 1):
                item = BLACKMARKET_ITEMS[name]
                count = inv.get(name, 0)
                lines.append(
                    f"{i}. {name} {item['price']}喵币 (持有:{count}) {item['desc']}"
                )
            lines.append("\n输入编号购买 | 0 返回")

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return

            text = reply.get_text().strip()
            try:
                choice = int(text)
            except ValueError:
                await event.reply("请输入有效编号")
                continue

            if choice == 0:
                return

            if choice < 1 or choice > len(BLACKMARKET_ITEM_LIST):
                await event.reply("无效编号")
                continue

            idx = choice - 1
            item_name = BLACKMARKET_ITEM_LIST[idx]
            item = BLACKMARKET_ITEMS[item_name]
            coins = self._get_coins(user_id)

            if coins < item["price"]:
                await self._send_reply(
                    event,
                    f"喵币不足! 需要 {item['price']}，你只有 {coins}",
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

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return

            text = reply.get_text().strip()
            try:
                choice = int(text)
            except ValueError:
                await event.reply("请输入有效编号")
                continue

            if choice == 0:
                return

            if choice < 1 or choice > len(ROB_TARGET_LIST):
                await event.reply("无效编号")
                continue

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
                    f"罚款 {actual_fine} 喵币，声望大幅下降\n"
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
                    f"成功抢劫{tname}! 抢到 {loot} 喵币!",
                    f"[{cat_data['name']}] 从 {tname} 弄到了 {loot} 喵币!",
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
                    f"抢劫{tname}失败! 被保安发现了，赔偿 {actual_penalty} 喵币!",
                    f"[{cat_data['name']}] 在 {tname} 扑了个空，倒赔 {actual_penalty} 喵币!",
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

        header = (
            f"当前学历: {edu_name}\n"
            f"目标: {next_info['name']} (学费:{next_info['cost']}喵币)\n"
            f"学习进度: [{bar}] {progress}%\n"
            f"智力: {attrs['int']}"
        )

        choice = await event.choose(
            header,
            [
                "返回",
                "认真学习 (进度+25 智力+1~3)",
                "正常学习 (进度+15)",
                "摸鱼 (进度+5 魅力+1~2)",
            ],
        )
        if choice is None or choice == 0:
            return

        now = time.time()
        last_study = self._get_edu_cd(user_id)
        remaining = 1800 - (now - last_study)
        if remaining > 0:
            m = int(remaining // 60) + 1
            await self._send_reply(event, f"学习太累了，休息{m}分钟再来~")
            return

        if choice == 1:
            int_gain = random.randint(1, 3)
            hp_loss = random.randint(3, 8)
            progress = min(100, progress + 25 + attrs["int"] // 20)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"认真学习了! 进度 [{bar}] {progress}% 智力+{int_gain}\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 喵币才能毕业 !!\n"
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
        elif choice == 2:
            progress = min(100, progress + 15)
            hp_loss = random.randint(2, 5)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"正常学习完成! 进度 [{bar}] {progress}%\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 喵币才能毕业 !!\n"
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
        elif choice == 3:
            progress = min(100, progress + 5)
            cha_gain = random.randint(1, 2)

            if progress >= 100 and self._get_coins(user_id) < next_info["cost"]:
                self._set_study_progress(user_id, 100)
                await self._send_reply(
                    event,
                    f"摸鱼了一节课... 进度 [{bar}] {progress}% 魅力+{cha_gain}\n"
                    f"!! 学费不足，还需要 {next_info['cost']} 喵币才能毕业 !!\n"
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
                fd_info = f"\n定期存款: {fd['amount']} 喵币 (含利息{fd['interest']}) 剩余{h}时{m}分"

            header = (
                f"活期存款: {bank['deposit']} 喵币\n"
                f"钱包: {coins} 喵币\n"
                f"贷款: {loan['amount']} 喵币 (利率{loan_rate:.1f}%/24h)\n"
                f"活期利率: {BANK_INTEREST_REGULAR * 100}% | 定期利率: {BANK_INTEREST_FIXED * 100}%\n"
                f"最大贷款: {max_loan} 喵币{fd_info}"
            )

            choice = await event.choose(
                header,
                [
                    "返回",
                    "存款",
                    "取款",
                    "定期存款",
                    "贷款",
                    "还款",
                    "转账",
                    "股票市场",
                    "理财投资",
                ],
            )
            if choice is None or choice == 0:
                return
            elif choice == 1:
                await self._handle_deposit(event, user_id)
            elif choice == 2:
                await self._handle_withdraw(event, user_id)
            elif choice == 3:
                await self._handle_fixed_deposit(event, user_id)
            elif choice == 4:
                await self._handle_loan_borrow(event, user_id)
            elif choice == 5:
                await self._handle_loan_repay(event, user_id)
            elif choice == 6:
                await self._handle_transfer(event, user_id)
            elif choice == 7:
                await self._handle_stocks(event, user_id)
            elif choice == 8:
                await self._handle_invest(event, user_id)

    async def _handle_deposit(self, event, user_id):
        coins = self._get_coins(user_id)
        bank = self._get_bank(user_id)

        reply = await event.wait_reply(
            f"当前存款: {bank['deposit']} | 钱包: {coins} 喵币\n最高存款: {BANK_MAX_DEPOSIT}\n请输入存款金额:",
            timeout=60,
        )
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            amount = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if amount < 1:
            await event.reply("请输入正整数")
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"钱包只有 {coins} 喵币!")
            return

        bank = self._get_bank(user_id)
        new_deposit = bank["deposit"] + amount
        if new_deposit > BANK_MAX_DEPOSIT:
            max_allowed = BANK_MAX_DEPOSIT - bank["deposit"]
            await self._send_reply(event, f"将超出上限，最多还能存 {max_allowed} 喵币")
            return

        self._add_coins(user_id, -amount)
        bank["deposit"] = new_deposit
        if bank["deposit"] == amount:
            bank["last_interest"] = time.time()
        self._set_bank(user_id, bank)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功存入 {amount} 喵币! 当前存款: {bank['deposit']}",
            image_url=url,
            card_type="success",
        )

    async def _handle_withdraw(self, event, user_id):
        bank = self._get_bank(user_id)
        coins = self._get_coins(user_id)

        reply = await event.wait_reply(
            f"当前存款: {bank['deposit']} | 钱包: {coins} 喵币\n请输入取款金额:",
            timeout=60,
        )
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            amount = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if amount < 1:
            await event.reply("请输入正整数")
            return

        bank = self._get_bank(user_id)
        if amount > bank["deposit"]:
            await self._send_reply(event, f"存款只有 {bank['deposit']} 喵币!")
            return

        bank["deposit"] -= amount
        if bank["deposit"] == 0:
            bank["last_interest"] = time.time()
        self._set_bank(user_id, bank)
        self._add_coins(user_id, amount)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功取出 {amount} 喵币! 当前存款: {bank['deposit']}",
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
                    f"定期存款到期! 本金 {fd_calc['amount']} + 利息 {fd_calc['interest']} = {total} 喵币已到账!",
                    image_url=url,
                    card_type="success",
                )
            else:
                h = int((BANK_FIXED_TERM - elapsed) // 3600)
                m = int(((BANK_FIXED_TERM - elapsed) % 3600) // 60)
                penalty = int(fd["amount"] * BANK_FIXED_PENALTY)
                choice = await event.choose(
                    f"定期存款: {fd['amount']} 喵币 (还需{h}时{m}分到期)\n"
                    f"提前取出将损失 {penalty} 喵币 ({int(BANK_FIXED_PENALTY * 100)}%违约金)",
                    ["返回", "提前取出"],
                )
                if choice == 1:
                    fd_calc = self._calc_fixed_interest(user_id)
                    recv = fd_calc["amount"] - penalty
                    if fd_calc["interest"] > penalty:
                        recv += fd_calc["interest"] - penalty
                    self._add_coins(user_id, max(0, recv))
                    self._set_fixed_deposit(user_id, {"amount": 0, "start_time": 0.0})
                    await self._send_reply(
                        event, f"提前取出! 扣除违约金后获得 {max(0, recv)} 喵币"
                    )
            return

        coins = self._get_coins(user_id)
        reply = await event.wait_reply(
            f"定期存款\n\n"
            f"钱包: {coins} 喵币\n"
            f"定期利率: {BANK_INTEREST_FIXED * 100}% / 24小时\n"
            f"期限: 24小时 | 提前取出违约金 {int(BANK_FIXED_PENALTY * 100)}%\n\n"
            f"请输入存入金额 (0 返回):",
            timeout=60,
        )
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            amount = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if amount <= 0:
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"喵币不足! 只有 {coins}", card_type="danger")
            return

        self._add_coins(user_id, -amount)
        self._set_fixed_deposit(user_id, {"amount": amount, "start_time": time.time()})
        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"存入定期 {amount} 喵币! 24小时后到期~",
            image_url=url,
            card_type="success",
        )

    async def _handle_loan_borrow(self, event, user_id):
        attrs = self._get_attrs(user_id)
        loan = self._calc_loan_interest(user_id)
        if loan["amount"] > 0:
            await self._send_reply(
                event, f"你还有 {loan['amount']} 喵币贷款未还! 先还清再借~"
            )
            return

        max_loan = 500 * self._get_edu(user_id)
        if attrs["rep"] < -30:
            await self._send_reply(event, "声望太低，银行拒绝贷款! 好好表现吧~")
            return

        loan_rate = BANK_MAX_LOAN_RATE * 100
        if attrs["rep"] >= 30:
            loan_rate *= 0.7

        reply = await event.wait_reply(
            f"贷款\n\n"
            f"最大可借: {max_loan} 喵币\n"
            f"利率: {loan_rate:.1f}% / 24小时 (声望越高利率越低)\n"
            f"你的声望: {attrs['rep']}\n\n"
            f"请输入借款金额 (0. 返回):",
            timeout=60,
        )
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            amount = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if amount <= 0:
            return
        if amount > max_loan:
            await event.reply(f"最大可借 {max_loan} 喵币")
            return

        self._set_loan(
            user_id,
            {"amount": amount, "principal": amount, "last_interest": time.time()},
        )
        self._add_coins(user_id, amount)
        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"成功贷款 {amount} 喵币! 记得按时还款~",
            image_url=url,
            card_type="success",
        )

    async def _handle_loan_repay(self, event, user_id):
        loan = self._calc_loan_interest(user_id)
        if loan["amount"] <= 0:
            await self._send_reply(event, "你没有贷款~")
            return

        coins = self._get_coins(user_id)
        choice = await event.choose(
            f"贷款余额: {loan['amount']} 喵币\n你的喵币: {coins}",
            ["返回", "全部还清", "部分还款"],
        )
        if choice is None or choice == 0:
            return

        if choice == 1:
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
                event, f"成功还款 {repay} 喵币! 声望+3", card_type="success"
            )
        elif choice == 2:
            reply = await event.wait_reply("请输入还款金额:", timeout=60)
            if reply is None:
                return
            try:
                amount = int(reply.get_text().strip())
            except ValueError:
                await event.reply("请输入有效数字")
                return
            if amount < 1:
                await event.reply("请输入正整数")
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
                f"成功还款 {amount} 喵币! 剩余 {new_amount}",
                card_type="success",
            )

    async def _handle_transfer(self, event, user_id):
        coins = self._get_coins(user_id)
        reply = await event.wait_reply(
            f"转账\n\n你的喵币: {coins}\n请输入转账目标 (@对方 或 输入用户ID):",
            timeout=60,
        )
        if reply is None:
            return

        mentions = reply.get_mentions()
        target_id = mentions[0] if mentions else reply.get_text().strip()
        if not target_id:
            await self._send_reply(event, "请指定转账目标")
            return

        if target_id == user_id:
            await self._send_reply(event, "不能转给自己!")
            return

        all_users = self._get_all_users()
        if target_id not in all_users:
            await self._send_reply(event, "该用户未注册，无法转账!", card_type="danger")
            return

        target_nickname = (
            self.sdk.storage.get(f"nekocare_nickname:{target_id}") or target_id
        )
        target_cat = self._get_cat(target_id)
        cat_info = f"猫猫: {target_cat['name']}" if target_cat else "猫猫: 无"

        reply = await event.wait_reply("请输入转账金额:", timeout=60)
        if reply is None:
            return

        try:
            amount = int(reply.get_text().strip())
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if amount < 1:
            await event.reply("请输入正整数")
            return

        coins = self._get_coins(user_id)
        if amount > coins:
            await self._send_reply(event, f"喵币不足! 只有 {coins}", card_type="danger")
            return

        confirm = await event.choose(
            f"确认转账给 {target_nickname}\n{cat_info}\n金额: {amount} 喵币",
            ["取消", "确认转账"],
        )
        if confirm != 1:
            await self._send_reply(event, "已取消转账")
            return

        self._add_coins(user_id, -amount)
        self._add_coins(target_id, amount)
        self._mod_attr(user_id, "rep", 2)
        await self._send_reply(
            event,
            f"成功转账 {amount} 喵币给 {target_nickname}! 声望+2",
            card_type="success",
        )

    async def _handle_stocks(self, event, user_id):
        while True:
            prices = self._update_stock_prices()
            user_stocks = self._get_user_stocks(user_id)
            coins = self._get_coins(user_id)

            lines = [f"股票市场  钱包:{coins}喵币\n"]
            stock_list = STOCK_LIST.copy()
            
            companies = self._get_companies()
            for company_id, company in companies.items():
                if company.get("listed"):
                    stock_name = f"[{company['name']}]股"
                    if stock_name not in stock_list:
                        stock_list.append(stock_name)
                        STOCK_BASE_PRICES[stock_name] = company["base_price"]
            
            for i, name in enumerate(stock_list, 1):
                held = user_stocks.get(name, 0)
                price = prices.get(name, STOCK_BASE_PRICES.get(name, 100))
                base = STOCK_BASE_PRICES.get(name, 100)
                change = price - base
                sign = "+" if change >= 0 else ""
                lines.append(f"{i}. {name}  ¥{price} ({sign}{change})  持有:{held}股")
            lines.append("\n1.买入  2.卖出  0.返回")

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            if text == "0":
                return
            if text == "1":
                await self._handle_buy_stock(event, user_id, prices)
            elif text == "2":
                await self._handle_sell_stock(event, user_id, prices)

    async def _handle_buy_stock(self, event, user_id, prices):
        coins = self._get_coins(user_id)
        lines = ["输入要购买的股票编号:\n"]
        stock_list = STOCK_LIST.copy()
        
        companies = self._get_companies()
        for company_id, company in companies.items():
            if company.get("listed"):
                stock_name = f"[{company['name']}]股"
                if stock_name not in stock_list:
                    stock_list.append(stock_name)
                    STOCK_BASE_PRICES[stock_name] = company["base_price"]
        
        for i, name in enumerate(stock_list, 1):
            price = prices.get(name, STOCK_BASE_PRICES.get(name, 100))
            lines.append(f"{i}. {name} ¥{price}")
        lines.append("0. 返回")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        try:
            idx = int(reply.get_text().strip())
        except ValueError:
            await event.reply("请输入有效编号")
            return
        if idx == 0:
            return
        if idx < 1 or idx > len(stock_list):
            await event.reply("无效编号")
            return
        idx -= 1

        stock_name = stock_list[idx]
        price = prices.get(stock_name, STOCK_BASE_PRICES.get(stock_name, 100))
        
        if stock_name.startswith("[") and stock_name.endswith("]股"):
            company_name = stock_name[1:-2]
            companies = self._get_companies()
            company_id = None
            for cid, comp in companies.items():
                if comp["name"] == company_name:
                    company_id = cid
                    break
            
            if company_id:
                await self._handle_buy_company_stock(event, user_id, company_id)
                return
        
        reply = await event.wait_reply(
            f"{stock_name} 当前价: ¥{price}\n请输入购买数量:", timeout=60
        )
        if reply is None:
            return
        try:
            qty = int(reply.get_text().strip())
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if qty < 1:
            await event.reply("请输入正整数")
            return

        total_cost = price * qty
        coins = self._get_coins(user_id)
        if total_cost > coins:
            await self._send_reply(
                event,
                f"喵币不足! 需要 {total_cost}，你只有 {coins}",
                card_type="danger",
            )
            return

        self._add_coins(user_id, -total_cost)
        user_stocks = self._get_user_stocks(user_id)
        user_stocks[stock_name] = user_stocks.get(stock_name, 0) + qty
        self._set_user_stocks(user_id, user_stocks)
        
        stock_data = self._get_stock_data(stock_name)
        stock_data["volume_buy"] += qty
        self._set_stock_data(stock_name, stock_data)

        await self._send_reply(
            event, f"买入 {stock_name} x{qty}! 花费 {total_cost} 喵币"
        )

    async def _handle_sell_stock(self, event, user_id, prices):
        user_stocks = self._get_user_stocks(user_id)
        lines = ["输入要卖出的股票编号:\n"]
        has_stock = False
        stock_list = STOCK_LIST.copy()
        
        companies = self._get_companies()
        for company_id, company in companies.items():
            if company.get("listed"):
                stock_name = f"[{company['name']}]股"
                if stock_name not in stock_list:
                    stock_list.append(stock_name)
                    STOCK_BASE_PRICES[stock_name] = company["base_price"]
        
        for i, name in enumerate(stock_list, 1):
            held = user_stocks.get(name, 0)
            price = prices.get(name, STOCK_BASE_PRICES.get(name, 100))
            line = f"{i}. {name} ¥{price}"
            if held > 0:
                line += f"  持有:{held}股"
                has_stock = True
            lines.append(line)
        if not has_stock:
            await self._send_reply(event, "你没有任何股票~")
            return
        lines.append("0. 返回")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        try:
            idx = int(reply.get_text().strip())
        except ValueError:
            await event.reply("请输入有效编号")
            return
        if idx == 0:
            return
        if idx < 1 or idx > len(stock_list):
            await event.reply("无效编号")
            return
        idx -= 1

        stock_name = stock_list[idx]
        user_stocks = self._get_user_stocks(user_id)
        held = user_stocks.get(stock_name, 0)
        if held <= 0:
            await self._send_reply(event, f"你没有持有 {stock_name}")
            return

        price = prices.get(stock_name, STOCK_BASE_PRICES.get(stock_name, 100))
        
        if stock_name.startswith("[") and stock_name.endswith("]股"):
            company_name = stock_name[1:-2]
            companies = self._get_companies()
            company_id = None
            for cid, comp in companies.items():
                if comp["name"] == company_name:
                    company_id = cid
                    break
            
            if company_id:
                await self._handle_sell_company_stock(event, user_id, company_id)
                return
        
        reply = await event.wait_reply(
            f"{stock_name} 当前价: ¥{price}  持有: {held}股\n请输入卖出数量:",
            timeout=60,
        )
        if reply is None:
            return
        try:
            qty = int(reply.get_text().strip())
        except ValueError:
            await event.reply("请输入有效数字")
            return
        if qty < 1 or qty > held:
            await event.reply(f"请输入 1-{held}")
            return

        revenue = price * qty
        user_stocks[stock_name] = held - qty
        if user_stocks[stock_name] == 0:
            del user_stocks[stock_name]
        self._set_user_stocks(user_id, user_stocks)
        self._add_coins(user_id, revenue)
        
        stock_data = self._get_stock_data(stock_name)
        stock_data["volume_sell"] += qty
        self._set_stock_data(stock_name, stock_data)

        profit = revenue - qty * STOCK_BASE_PRICES[stock_name]
        if profit != 0:
            sign = "+" if profit >= 0 else ""
            profit_text = f" (盈亏:{sign}{profit})"
        else:
            profit_text = ""
        await self._send_reply(
            event, f"卖出 {stock_name} x{qty}! 获得 {revenue} 喵币{profit_text}"
        )

    async def _handle_invest(self, event, user_id):
        coins = self._get_coins(user_id)

        lines = ["理财投资\n"]
        for i, inv in enumerate(INVESTMENTS, 1):
            lines.append(
                f"{i}. {inv['name']}  投入:{inv['cost']}喵币  "
                f"收益:{inv['profit_min']}-{inv['profit_max']}  "
                f"失败率:{int(inv['fail_rate'] * 100)}%"
            )
        lines.append(f"\n你的喵币: {coins}")
        lines.append("\n输入编号投资 | 0. 返回")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return

        text = reply.get_text().strip()
        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效编号")
            return
        if choice == 0:
            return
        if choice < 1 or choice > len(INVESTMENTS):
            await event.reply("无效编号")
            return

        idx = choice - 1

        inv = INVESTMENTS[idx]
        coins = self._get_coins(user_id)

        if coins < inv["cost"]:
            await self._send_reply(
                event,
                f"喵币不足! 需要 {inv['cost']}，你只有 {coins}",
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
                f"{inv['name']}失败... 投入的 {inv['cost']} 喵币打了水漂!",
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
                f"{inv['name']}成功! 投入 {inv['cost']}，回报 {inv['cost'] + profit} 喵币! (净赚 {profit})",
                image_url=url,
                card_type="success",
            )
        self._check_achievement_titles(user_id)

    async def _handle_foster(self, event, user_id, cat_data):
        choice = await event.choose(
            f"寄养 [{cat_data['name']}]\n"
            f"寄养期间猫猫不会饿肚子\n"
            f"费用: {FOSTER_COST_PER_DAY}喵币/天 (接回时结算)\n"
            f"最多寄养 {FOSTER_MAX_DAYS} 天",
            ["取消", "确认寄养"],
        )
        if choice is None or choice != 1:
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

        choice = await event.choose(
            f"接 [{cat_data['name']}] 回家\n"
            f"寄养天数: {foster_days} 天\n"
            f"寄养费用: {cost} 喵币\n"
            f"你的喵币: {coins} 枚",
            ["取消", "确认接回"],
        )
        if choice is None or choice != 1:
            await self._send_reply(event, "已取消")
            return

        if coins < cost:
            await self._send_reply(
                event,
                f"喵币不足! 需要 {cost} 枚，你只有 {coins} 枚",
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
            f"[{cat_data['name']}] 回家啦! 花了 {cost} 喵币寄养费~",
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
            f"喵币: {coins} 枚",
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
        choice = await event.choose(
            f"!! 确定要弃养 [{cat_data['name']}] 吗? !!\n\n这将是不可逆的操作...",
            ["我再想想", "确认弃养"],
        )
        if choice is None or choice != 1:
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
            f"弃养惩罚: 扣除大量喵币、学历清零、属性重置"
        )
        await self._send_reply(event, msg, image_url=url)
        return True

    async def _handle_rename(self, event, user_id, cat_data):
        reply = await event.wait_reply("请输入新名字（限20字内）：", timeout=120)
        if not reply:
            return

        new_name = reply.get_text().strip()
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
                f"喵币不足! 【{item_name}】{item['price']}喵币，你只有 {coins} 枚",
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
            f"⚠️ [{cat_data['name']}] 饿晕了，现在非常危险！\n\n"
            f"剩余 {hours} 小时生命倒计时\n"
            f"其他玩家可以在主菜单看到它并进行救助~\n\n"
            f"快叫好朋友来帮帮它吧！"
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
        if last_update is None or (now - last_update) < STOCK_UPDATE_INTERVAL:
            return prices
        self.sdk.storage.set("nekocare_stock_last_update", now)
        
        self._update_stock_demand(now)
        market_trend = self._update_market_trend(now)
        self._trigger_market_event(now)
        active_events = self._get_active_events(now)
        
        for name in STOCK_LIST:
            base = STOCK_BASE_PRICES[name]
            current = prices[name]
            
            base_change = random.uniform(-STOCK_BASE_VOLATILITY, STOCK_BASE_VOLATILITY)
            noise = random.uniform(-base * 0.1, base * 0.1)
            
            stock_data = self._get_stock_data(name)
            demand_factor = self._calculate_demand_factor(stock_data)
            
            event_impact = self._calculate_event_impact(name, active_events)
            
            target = base * (1 + base_change + market_trend + demand_factor + event_impact) + noise
            new_price = current + (target - current) * STOCK_SMOOTH_FACTOR
            new_price = max(int(base * STOCK_PRICE_MIN_RATIO), min(int(base * STOCK_PRICE_MAX_RATIO), int(new_price)))
            prices[name] = max(1, new_price)
            
            stock_data["price"] = new_price
            self._set_stock_data(name, stock_data)
        
        self.sdk.storage.set("nekocare_stock_prices", prices)
        return prices
    
    def _get_stock_data(self, stock_name: str) -> dict:
        stock_data = self.sdk.storage.get(f"nekocare_stock_data:{stock_name}")
        if stock_data is None:
            stock_data = {
                "price": STOCK_BASE_PRICES[stock_name],
                "base_price": STOCK_BASE_PRICES[stock_name],
                "volume_buy": 0,
                "volume_sell": 0,
                "trend": 0.0,
                "events": []
            }
        return stock_data
    
    def _set_stock_data(self, stock_name: str, data: dict):
        self.sdk.storage.set(f"nekocare_stock_data:{stock_name}", data)
    
    def _update_stock_demand(self, now: float):
        last_reset = self.sdk.storage.get("nekocare_stock_daily_reset")
        if last_reset is None or (now - last_reset) >= STOCK_DAILY_RESET_INTERVAL:
            self.sdk.storage.set("nekocare_stock_daily_reset", now)
            for name in STOCK_LIST:
                stock_data = self._get_stock_data(name)
                stock_data["volume_buy"] = 0
                stock_data["volume_sell"] = 0
                self._set_stock_data(name, stock_data)
    
    def _calculate_demand_factor(self, stock_data: dict) -> float:
        total_volume = stock_data["volume_buy"] + stock_data["volume_sell"]
        if total_volume == 0:
            return 0.0
        buy_ratio = stock_data["volume_buy"] / total_volume
        return (buy_ratio - 0.5) * 0.1
    
    def _update_market_trend(self, now: float) -> float:
        trend_data = self.sdk.storage.get("nekocare_market_trend")
        if trend_data is None:
            trend_data = {
                "status": "neutral",
                "change_time": now,
                "coefficient": 0.0
            }
        
        if (now - trend_data["change_time"]) >= STOCK_MARKET_TREND_CYCLE:
            trend_data["change_time"] = now
            rand = random.random()
            if rand < 0.33:
                trend_data["status"] = "bull"
                trend_data["coefficient"] = random.uniform(0.1, 0.2)
            elif rand < 0.66:
                trend_data["status"] = "bear"
                trend_data["coefficient"] = random.uniform(-0.2, -0.1)
            else:
                trend_data["status"] = "neutral"
                trend_data["coefficient"] = random.uniform(-0.05, 0.05)
        
        self.sdk.storage.set("nekocare_market_trend", trend_data)
        return trend_data["coefficient"]
    
    def _get_active_events(self, now: float) -> list:
        events = self.sdk.storage.get("nekocare_market_events")
        if events is None:
            return []
        return [e for e in events if e["end_time"] > now]
    
    def _trigger_market_event(self, now: float):
        active_events = self._get_active_events(now)
        if len(active_events) >= 2:
            return
        
        if random.random() < 0.1:
            event_types = [
                {"type": "bullish", "impact": 0.1, "target": "all", "desc": "政策扶持，市场繁荣"},
                {"type": "bullish", "impact": 0.15, "target": "tech", "desc": "技术突破，科技股大涨"},
                {"type": "bearish", "impact": -0.1, "target": "all", "desc": "市场恐慌，全线下跌"},
                {"type": "bearish", "impact": -0.15, "target": "manufacture", "desc": "行业监管，制造业受挫"},
            ]
            
            selected_event = random.choice(event_types)
            event = {
                "id": str(int(now)),
                "type": selected_event["type"],
                "target": selected_event["target"],
                "impact": selected_event["impact"],
                "start_time": now,
                "end_time": now + STOCK_EVENT_DURATION,
                "description": selected_event["desc"]
            }
            
            events = self.sdk.storage.get("nekocare_market_events") or []
            events.append(event)
            self.sdk.storage.set("nekocare_market_events", events)
    
    def _calculate_event_impact(self, stock_name: str, active_events: list) -> float:
        total_impact = 0.0
        for event in active_events:
            target = event["target"]
            if target == "all":
                total_impact += event["impact"]
            elif target == "tech" and stock_name in ["罐头科技", "猫薄荷股"]:
                total_impact += event["impact"]
            elif target == "manufacture" and stock_name in ["猫砂股", "鱼干公司"]:
                total_impact += event["impact"]
        return total_impact

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
            "work_double": "聚宝喵符",
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

    def _get_friends(self, user_id: str) -> list:
        friends = self.sdk.storage.get(f"nekocare_friends:{user_id}")
        return friends if friends is not None else []

    def _add_friend(self, user_id: str, friend_id: str) -> bool:
        friends = self._get_friends(user_id)
        if friend_id not in friends:
            friends.append(friend_id)
            self.sdk.storage.set(f"nekocare_friends:{user_id}", friends)
            return True
        return False

    def _remove_friend(self, user_id: str, friend_id: str) -> bool:
        friends = self._get_friends(user_id)
        if friend_id in friends:
            friends.remove(friend_id)
            self.sdk.storage.set(f"nekocare_friends:{user_id}", friends)
            return True
        return False

    def _get_friend_requests(self, user_id: str) -> list:
        requests = self.sdk.storage.get(f"nekocare_friend_requests:{user_id}")
        return requests if requests is not None else []

    def _add_friend_request(self, from_id: str, to_id: str) -> bool:
        requests = self._get_friend_requests(to_id)
        for req in requests:
            if req["from"] == from_id:
                return False
        now = time.time()
        requests.append({"from": from_id, "time": now})
        self.sdk.storage.set(f"nekocare_friend_requests:{to_id}", requests)
        return True

    def _remove_friend_request(self, from_id: str, to_id: str) -> bool:
        requests = self._get_friend_requests(to_id)
        original_len = len(requests)
        requests = [r for r in requests if r["from"] != from_id]
        if len(requests) != original_len:
            self.sdk.storage.set(f"nekocare_friend_requests:{to_id}", requests)
            return True
        return False

    def _is_friend(self, user_id: str, other_id: str) -> bool:
        friends = self._get_friends(user_id)
        return other_id in friends

    def _get_party(self, user_id: str) -> Optional[dict]:
        parties = self._get_all_parties()
        for party in parties:
            if user_id in party["members"]:
                if time.time() - party.get("created", 0) > PARTY_EXPIRE:
                    self._remove_party(party["host_id"])
                    return None
                return party
        return None

    def _get_all_parties(self) -> list:
        parties = self.sdk.storage.get("nekocare_parties")
        return parties if parties is not None else []

    def _create_party(self, host_id: str, cat_data: dict) -> dict:
        party = {
            "host_id": host_id,
            "members": [host_id],
            "cat_names": {host_id: cat_data.get("name", "?")},
            "created": time.time()
        }
        parties = self._get_all_parties()
        parties = [p for p in parties if p["host_id"] != host_id]
        parties.append(party)
        self.sdk.storage.set("nekocare_parties", parties)
        return party

    def _join_party(self, host_id: str, user_id: str, cat_data: dict) -> bool:
        parties = self._get_all_parties()
        for party in parties:
            if party["host_id"] == host_id:
                if len(party["members"]) >= PARTY_MAX_SIZE:
                    return False
                if user_id not in party["members"]:
                    party["members"].append(user_id)
                    party["cat_names"][user_id] = cat_data.get("name", "?")
                    party["created"] = time.time()
                    self.sdk.storage.set("nekocare_parties", parties)
                return True
        return False

    def _leave_party(self, user_id: str) -> bool:
        party = self._get_party(user_id)
        if not party:
            return False
        party["members"].remove(user_id)
        party["cat_names"].pop(user_id, None)
        if not party["members"]:
            self._remove_party(party["host_id"])
        else:
            if user_id == party["host_id"] and party["members"]:
                party["host_id"] = party["members"][0]
            parties = self._get_all_parties()
            for i, p in enumerate(parties):
                if p["host_id"] == party["host_id"]:
                    parties[i] = party
                    break
            self.sdk.storage.set("nekocare_parties", parties)
        return True

    def _remove_party(self, host_id: str):
        parties = self._get_all_parties()
        parties = [p for p in parties if p["host_id"] != host_id]
        self.sdk.storage.set("nekocare_parties", parties)

    def _get_party_members(self, host_id: str) -> list:
        party = self._get_party(host_id)
        return party["members"] if party else []

    def _get_game_invites(self, game_type: str) -> list:
        invites = self.sdk.storage.get(f"nekocare_game_invites:{game_type}")
        return invites if invites is not None else []

    def _create_game_invite(self, host_id: str, game_type: str, invite_data: dict):
        invites = self._get_game_invites(game_type)
        now = time.time()
        invites.append({
            "host_id": host_id,
            "players": [host_id],
            "created": now,
            "expire": now + GAME_INVITE_EXPIRE,
            **invite_data
        })
        self.sdk.storage.set(f"nekocare_game_invites:{game_type}", invites)

    def _join_game(self, game_type: str, player_id: str) -> Optional[dict]:
        invites = self._get_game_invites(game_type)
        now = time.time()
        for invite in invites:
            if player_id in invite["players"]:
                return None
            if invite["expire"] < now:
                continue
            game_config = MULTIPLAYER_GAMES[game_type]
            if len(invite["players"]) >= game_config["max_players"]:
                continue
            invite["players"].append(player_id)
            self.sdk.storage.set(f"nekocare_game_invites:{game_type}", invites)
            return invite
        return None

    def _cleanup_expired_game_invites(self):
        now = time.time()
        for game_type in MULTIPLAYER_GAME_LIST:
            invites = self._get_game_invites(game_type)
            valid_invites = [inv for inv in invites if inv["expire"] > now]
            if len(valid_invites) != len(invites):
                self.sdk.storage.set(f"nekocare_game_invites:{game_type}", valid_invites)

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

    def _get_critical_cats(self) -> list:
        users = self._get_all_users()
        critical_cats = []
        now = time.time()

        for user_id in users:
            cat_data = self._get_cat(user_id)
            if cat_data and cat_data.get("status") == "critical":
                remaining = self._get_critical_remaining(cat_data)
                critical_cats.append(
                    {
                        "user_id": user_id,
                        "name": cat_data["name"],
                        "remaining": remaining,
                        "critical_since": cat_data.get("critical_since", now),
                    }
                )

        # 按剩余时间排序，最紧急的在前
        critical_cats.sort(key=lambda x: x["remaining"])
        return critical_cats

    def _check_achievement_titles(self, user_id: str):
        stats = self._get_stats(user_id)
        coins = self._get_coins(user_id)
        cat_data = self._get_cat(user_id)

        if stats.get("work_count", 0) >= 50:
            self._add_title(user_id, "⚒️ - 打工狂魔")
        if stats.get("work_count", 0) >= 100:
            self._add_title(user_id, "🧘 - 佛系玩家")
        if stats.get("catch_count", 0) >= 20:
            self._add_title(user_id, "🐱 - 捕猫达人")
        if stats.get("catch_count", 0) >= 50:
            self._add_title(user_id, "🐾 - 驭猫达人")
        if stats.get("rescue_count", 0) >= 3:
            self._add_title(user_id, "🐱 - 喵喵医生")
        if stats.get("rescue_count", 0) >= 10:
            self._add_title(user_id, "🩺 - 神医再世")
        if stats.get("rescue_count", 0) >= 25:
            self._add_title(user_id, "✨ - 天使守护者")
        if stats.get("death_count", 0) >= 3:
            self._add_title(user_id, "🎭 - 非酋酋长")
        if coins >= 1000:
            self._add_title(user_id, "💰 - 富可敌国")
        if coins >= 5000:
            self._add_title(user_id, "💎 - 清丽多金")
        if coins <= 0:
            loan = self._get_loan(user_id)
            if loan["amount"] > 0:
                self._add_title(user_id, "⛔ - 负债累累")
            else:
                self._add_title(user_id, "💸 - 千金散尽")
        total_lost = stats.get("invest_lost", 0)
        if total_lost >= 500:
            self._add_title(user_id, "📉 - 散尽家财")
        invest_profit = stats.get("invest_profit", 0)
        if invest_profit >= 500:
            self._add_title(user_id, "📈 - 理财圣手")
        if invest_profit >= 2000:
            self._add_title(user_id, "🛑 - 止盈大师")
        if invest_profit >= 5000:
            self._add_title(user_id, "🎲 - 富贵险求")
        invest_total = stats.get("invest_count", 0)
        if invest_total >= 10:
            self._add_title(user_id, "🚀 - 果断梭哈")
        if invest_total >= 30:
            self._add_title(user_id, "🧘 - 佛系玩家")

        if cat_data and cat_data.get("status") == "alive":
            from datetime import datetime, timezone

            adopt_dt = datetime.fromtimestamp(cat_data["adopt_time"], tz=timezone.utc)
            now_dt = datetime.now(tz=timezone.utc)
            days = max(1, (now_dt.date() - adopt_dt.date()).days + 1)
            if days >= 30:
                self._add_title(user_id, "❤️ - 好主人")
            if cat_data.get("intimacy", 0) >= 90:
                self._add_title(user_id, "🌸 - 萌系可爱")
            if cat_data.get("intimacy", 0) >= 100 and days >= 7:
                self._add_title(user_id, "🍡 - 软萌可爱")
            if cat_data.get("intimacy", 0) >= 100 and days >= 14:
                self._add_title(user_id, "🐱 - 软萌喵系")
            if cat_data.get("intimacy", 0) >= 100 and days >= 30:
                self._add_title(user_id, "🌟 - 萌态万千")
            if cat_data.get("intimacy", 0) >= 100 and days >= 60:
                self._add_title(user_id, "🌙 - 人间可爱")
            if cat_data.get("intimacy", 0) >= 100 and coins >= 10000:
                self._add_title(user_id, "✨ - 盛世美颜")
            attrs = self._get_attrs(user_id)
            if attrs["cha"] >= 80 and attrs["int"] >= 60 and coins >= 5000:
                self._add_title(user_id, "💼 - 俊朗多金")
                self._add_title(user_id, "❤️ - 好主人")

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
                label, color = "很饱", "#4CAF50"
            elif value >= 50:
                label, color = "还行", "#FF9800"
            elif value >= 20:
                label, color = "有点饿", "#FF5722"
            else:
                label, color = "非常饿", "#F44336"
        else:
            if value >= 80:
                label, color = "非常亲密", "#E91E63"
            elif value >= 50:
                label, color = "友好", "#9C27B0"
            elif value >= 20:
                label, color = "普通", "#607D8B"
            else:
                label, color = "陌生", "#9E9E9E"
        return f"{value}/100 [{label}]", color

    def _build_bag_display(self, user_id: str, coins: int) -> str:
        inv = self._get_inventory(user_id)
        all_items = list(SHOP_ITEM_LIST) + list(BLACKMARKET_ITEM_LIST)
        name_w = max(self._str_width(n) for n in all_items) + 2

        header = self._pad("背包", 22) + f"喵币:{coins}"
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

        header = self._pad("商城", 22) + f"喵币:{coins}"
        lines = [header, ""]

        for i, name in enumerate(SHOP_ITEM_LIST):
            item = SHOP_ITEMS[name]
            item_str = self._pad(f"{i + 1}.{name}  {item['price']}喵币", name_w + 10)
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
            choice = await event.choose(
                "喵喵榜",
                [
                    "返回",
                    "喵币榜",
                    "存活榜",
                    "亲密榜",
                    "喵亡榜",
                    "黑喵榜",
                ],
            )
            if choice is None or choice == 0:
                return

            all_users = self._get_all_users()
            if not all_users:
                await self._send_reply(
                    event, "暂无数据，还没有玩家注册~", card_type="info"
                )
                return

            if choice == 1:
                coin_data = []
                for uid in all_users:
                    c = self._get_coins(uid)
                    if c > 0:
                        coin_data.append((uid, c))
                header = "喵币排行榜\n"
                body = self._build_ranking(coin_data, "喵币")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            if choice == 2:
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

            elif choice == 3:
                intimacy_data = []
                for uid in all_users:
                    cat = self._get_cat(uid)
                    if cat and cat.get("status") == "alive":
                        intimacy_data.append((uid, cat["intimacy"]))
                header = "亲密度排行\n"
                body = self._build_ranking(intimacy_data, "亲密度")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            elif choice == 4:
                death_data = []
                for uid in all_users:
                    stats = self._get_stats(uid)
                    dc = stats.get("death_count", 0)
                    if dc > 0:
                        death_data.append((uid, dc))
                header = "喵亡榜\n"
                body = self._build_ranking(death_data, "死猫次数")
                await self._send_reply(event, f"{header}\n{body}", card_type="info")

            elif choice == 5:
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
            timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 10))
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("results") and len(data["results"]) > 0:
                            return data["results"][0].get("url")
        except asyncio.TimeoutError:
            self.logger.warning(f"获取图片超时 ({category})")
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
    
    def _get_companies(self) -> dict:
        companies = self.sdk.storage.get("nekocare_companies")
        return companies if companies is not None else {}
    
    def _set_companies(self, companies: dict):
        self.sdk.storage.set("nekocare_companies", companies)
    
    def _get_company(self, company_id: str) -> Optional[dict]:
        companies = self._get_companies()
        return companies.get(company_id)
    
    def _set_company(self, company_id: str, data: dict):
        companies = self._get_companies()
        companies[company_id] = data
        self._set_companies(companies)
    
    def _get_user_company_ids(self, user_id: str) -> list:
        user_companies = self.sdk.storage.get(f"nekocare_user_companies:{user_id}")
        return user_companies if user_companies is not None else []
    
    def _set_user_company_ids(self, user_id: str, company_ids: list):
        self.sdk.storage.set(f"nekocare_user_companies:{user_id}", company_ids)
    
    def _get_company_counter(self) -> int:
        counter = self.sdk.storage.get("nekocare_company_counter")
        return counter if counter is not None else 0
    
    def _increment_company_counter(self):
        counter = self._get_company_counter() + 1
        self.sdk.storage.set("nekocare_company_counter", counter)
        return counter
    
    def _get_all_companies(self) -> dict:
        return self._get_companies()
    
    def _get_npc_employees(self, company_id: str) -> dict:
        company = self._get_company(company_id)
        if company:
            return company.get("npc_employees", {})
        return {}
    
    def _set_npc_employees(self, company_id: str, npc_employees: dict):
        company = self._get_company(company_id)
        if company:
            company["npc_employees"] = npc_employees
            self._set_company(company_id, company)
    
    def _generate_npc_employee(self, company_level: int) -> dict:
        rarity_roll = random.random()
        cumulative = 0
        selected_level = 1
        for level, data in NPC_EMPLOYEE_LEVELS.items():
            cumulative += data["rarity"]
            if rarity_roll <= cumulative:
                selected_level = level
                break
        
        level_data = NPC_EMPLOYEE_LEVELS[selected_level]
        name = random.choice(NPC_EMPLOYEE_NAMES)
        while name.endswith("的NPC"):
            name = random.choice(NPC_EMPLOYEE_NAMES)
        
        efficiency_modifier = 1.0 + (company_level - 1) * 0.1
        actual_efficiency = level_data["efficiency"] * efficiency_modifier
        
        return {
            "name": f"{name}",
            "level": selected_level,
            "level_name": level_data["name"],
            "base_salary": level_data["salary"],
            "efficiency": actual_efficiency,
            "hired_time": time.time(),
            "total_earnings": 0,
            "status": "active",
        }
    
    def _get_npc_recruit_probability(self, company_level: int, npc_level: int) -> float:
        base_prob = NPC_EMPLOYEE_LEVELS[npc_level]["rarity"]
        level_bonus = company_level * 0.05
        return min(base_prob + level_bonus, 0.8)
    
    def _company_exists(self, name: str) -> bool:
        companies = self._get_companies()
        for company in companies.values():
            if company.get("name") == name:
                return True
        return False
    
    async def _handle_company_menu(self, event, user_id):
        while True:
            lines = ["公司中心\n"]
            company_ids = self._get_user_company_ids(user_id)
            
            if company_ids:
                lines.append("你的公司：")
                for i, company_id in enumerate(company_ids, 1):
                    company = self._get_company(company_id)
                    if company:
                        status = "已上市" if company.get("listed") else "未上市"
                        lines.append(f"{i}. {company['name']} ({company['type']}) {status}")
                lines.append(f"\n{len(company_ids) + 1}. 管理公司\n")
            else:
                lines.append("你还没有公司\n")
            
            lines.append(f"{len(company_ids) + 2 if company_ids else 1}. 注册新公司\n")
            lines.append("0. 返回")
            
            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            
            if text == "0":
                return
            
            try:
                choice = int(text)
            except ValueError:
                await event.reply("请输入有效编号")
                continue
            
            if company_ids:
                if choice == len(company_ids) + 1:
                    await self._handle_select_company_manage(event, user_id)
                elif choice == len(company_ids) + 2:
                    await self._handle_register_company(event, user_id)
                elif 1 <= choice <= len(company_ids):
                    company = self._get_company(company_ids[choice - 1])
                    if company:
                        await self._handle_company_info(event, company_ids[choice - 1], company)
                else:
                    await event.reply("无效编号")
            else:
                if choice == 1:
                    await self._handle_register_company(event, user_id)
                else:
                    await event.reply("无效编号")
    
    async def _handle_register_company(self, event, user_id):
        if len(self._get_user_company_ids(user_id)) >= COMPANY_MAX_COMPANIES_PER_USER:
            await self._send_reply(
                event,
                f"你最多只能拥有 {COMPANY_MAX_COMPANIES_PER_USER} 个公司",
                card_type="danger"
            )
            return
        
        lines = ["注册新公司\n"]
        lines.append("选择公司类型：\n")
        for key, data in COMPANY_TYPES.items():
            lines.append(f"{key}. {data['name']} - 注册费:{data['fee']} 喵币")
        lines.append("\n请输入类型编号 (输入0取消):")
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        company_type = text
        if company_type not in COMPANY_TYPES:
            await event.reply("无效的公司类型")
            return
        
        type_data = COMPANY_TYPES[company_type]
        coins = self._get_coins(user_id)
        
        if coins < type_data["fee"] + COMPANY_INITIAL_CAPITAL:
            await self._send_reply(
                event,
                f"喵币不足！需要 {type_data['fee'] + COMPANY_INITIAL_CAPITAL} 喵币（注册费{type_data['fee']} + 初始资本{COMPANY_INITIAL_CAPITAL}）",
                card_type="danger"
            )
            return
        
        reply = await event.wait_reply(
            f"请输入公司名称（不能重复，输入0取消）:",
            timeout=60
        )
        if reply is None:
            return
        company_name = reply.get_text().strip()
        
        if company_name == "0":
            return
        
        if len(company_name) < 2 or len(company_name) > 10:
            await self._send_reply(
                event,
                "公司名称长度为2-10个字符",
                card_type="danger"
            )
            return
        
        if self._company_exists(company_name):
            await self._send_reply(
                event,
                "公司名称已被使用",
                card_type="danger"
            )
            return
        
        total_cost = type_data["fee"] + COMPANY_INITIAL_CAPITAL
        self._add_coins(user_id, -total_cost)
        
        company_id = str(self._increment_company_counter())
        now = time.time()
        
        company = {
            "id": company_id,
            "name": company_name,
            "owner_id": user_id,
            "type": company_type,
            "level": 1,
            "registered_time": now,
            "listed": False,
            "cash": COMPANY_INITIAL_CAPITAL,
            "total_shares": 0,
            "share_price": 0,
            "base_price": 0,
            "revenue": 0,
            "profit": 0,
            "employees": {},
            "npc_employees": {},
            "dividend_ratio": 0.5,
            "last_dividend_time": 0,
            "last_npc_settlement": 0,
            "market_sentiment": 0.0,
        }
        
        self._set_company(company_id, company)
        
        user_company_ids = self._get_user_company_ids(user_id)
        user_company_ids.append(company_id)
        self._set_user_company_ids(user_id, user_company_ids)
        
        await self._send_reply(
            event,
            f"🎉 公司注册成功！\n\n"
            f"公司名称: {company_name}\n"
            f"公司类型: {type_data['name']}\n"
            f"初始资本: {COMPANY_INITIAL_CAPITAL} 喵币\n"
            f"公司等级: 1\n"
            f"\n祝你的公司生意兴隆！",
            card_type="success"
        )
    
    async def _handle_company_info(self, event, company_id: str, company: dict):
        type_data = COMPANY_TYPES[company["type"]]
        days_registered = int((time.time() - company["registered_time"]) / 86400)
        
        npc_count = len(company.get("npc_employees", {}))
        
        lines = [
            f"  {company['name']}\n",
            f"类型: {type_data['name']}",
            f"等级: {company['level']}/{COMPANY_MAX_LEVEL}",
            f"成立天数: {days_registered}天",
            f"\n 财务状况",
            f"现金: {company['cash']} 喵币",
            f"累计收入: {company['revenue']} 喵币",
            f"累计利润: {company['profit']} 喵币",
            f"\n  公司规模",
            f"玩家员工: {len(company['employees'])}人",
            f"NPC员工: {npc_count}人",
        ]
        
        if company["listed"]:
            lines.append(f"\n  上市状态: 已上市")
            lines.append(f"总股本: {company['total_shares']}股")
            lines.append(f"当前股价: ¥{company['share_price']}")
        else:
            lines.append(f"\n  上市状态: 未上市")
            days_to_ipo = max(0, COMPANY_IPO_DAYS - days_registered)
            if days_to_ipo > 0:
                lines.append(f"距离上市条件（时间）: {days_to_ipo}天")
            else:
                lines.append(f"√ 时间条件已满足")
            
            profit_ready = "√" if company["profit"] >= COMPANY_IPO_MIN_PROFIT else "×"
            lines.append(f"累计利润要求: {profit_ready} ({company['profit']}/{COMPANY_IPO_MIN_PROFIT})")
            
            cash_ready = "√" if company["cash"] >= COMPANY_IPO_MIN_CASH else "×"
            lines.append(f"现金要求: {cash_ready} ({company['cash']}/{COMPANY_IPO_MIN_CASH})")
            
            level_ready = "√" if company["level"] >= COMPANY_IPO_MIN_LEVEL else "×"
            lines.append(f"公司等级要求: {level_ready} ({company['level']}/{COMPANY_IPO_MIN_LEVEL})")
            
            if (days_to_ipo == 0 and 
                company["profit"] >= COMPANY_IPO_MIN_PROFIT and 
                company["cash"] >= COMPANY_IPO_MIN_CASH and 
                company["level"] >= COMPANY_IPO_MIN_LEVEL):
                lines.append(f"\n  满足上市条件！可以申请上市")
        
        await event.reply("\n".join(lines))
    
    async def _handle_select_company_manage(self, event, user_id):
        company_ids = self._get_user_company_ids(user_id)
        
        lines = ["选择要管理的公司：\n"]
        for i, company_id in enumerate(company_ids, 1):
            company = self._get_company(company_id)
            if company:
                lines.append(f"{i}. {company['name']}")
        lines.append("\n0. 返回")
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效编号")
            return
        
        if 1 <= choice <= len(company_ids):
            await self._handle_company_manage(event, company_ids[choice - 1])
        else:
            await event.reply("无效编号")
    
    async def _handle_company_manage(self, event, company_id: str):
        company = self._get_company(company_id)
        if not company:
            await event.reply("公司不存在")
            return
        
        while True:
            npc_count = len(company.get("npc_employees", {}))
            lines = [
                f" 管理中心 - {company['name']}\n",
                f"现金: {company['cash']} 喵币",
                f"玩家员工: {len(company['employees'])}人 | NPC员工: {npc_count}人",
                f"\n1. 公司详情",
                f"2. 招聘玩家员工",
                f"3. 招聘NPC员工",
                f"4. NPC工资结算",
            ]
            
            if not company["listed"] and self._check_ipo_eligibility(company):
                lines.append("5. 申请上市")
            
            if company["listed"]:
                lines.append("5. 发放分红")
            
            lines.append("\n0. 返回")
            
            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            
            if text == "0":
                return
            elif text == "1":
                await self._handle_company_info(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "2":
                await self._handle_recruit_employees(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "3":
                await self._handle_recruit_npc(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "4":
                await self._handle_settle_npc(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "5" and not company["listed"] and self._check_ipo_eligibility(company):
                await self._handle_company_ipo(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "5" and company["listed"]:
                await self._handle_company_dividend(event, company_id, company)
                company = self._get_company(company_id)
            else:
                await event.reply("无效编号")
    
    def _check_ipo_eligibility(self, company: dict) -> bool:
        days_registered = (time.time() - company["registered_time"]) / 86400
        return (days_registered >= COMPANY_IPO_DAYS and
                company["profit"] >= COMPANY_IPO_MIN_PROFIT and
                company["cash"] >= COMPANY_IPO_MIN_CASH and
                company["level"] >= COMPANY_IPO_MIN_LEVEL)
    
    async def _handle_company_ipo(self, event, company_id: str, company: dict):
        lines = [
            f"申请上市 - {company['name']}\n",
            f"上市费用: {COMPANY_IPO_FEE} 喵币",
            f"公司现金: {company['cash']} 喵币",
            f"\n确定要申请上市吗？（y/n）"
        ]
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip().lower()
        
        if text != "y":
            await event.reply("已取消上市申请")
            return
        
        if company["cash"] < COMPANY_IPO_FEE:
            await self._send_reply(
                event,
                f"现金不足！需要 {COMPANY_IPO_FEE} 喵币",
                card_type="danger"
            )
            return
        
        company["cash"] -= COMPANY_IPO_FEE
        company["listed"] = True
        company["listed_time"] = time.time()
        
        company_value = max(company["cash"], 10000)
        company["total_shares"] = min(int(company_value / 10), 5000)
        company["base_price"] = max(int(company_value / company["total_shares"]), 1)
        company["share_price"] = company["base_price"]
        
        stock_name = f"[{company['name']}]股"
        if stock_name not in STOCK_LIST:
            STOCK_LIST.append(stock_name)
            STOCK_BASE_PRICES[stock_name] = company["base_price"]
        
        self._set_company(company_id, company)
        
        await self._send_reply(
            event,
            f"🎉 上市成功！\n\n"
            f"公司名称: {company['name']}\n"
            f"股票名称: {stock_name}\n"
            f"总股本: {company['total_shares']}股\n"
            f"发行价: ¥{company['base_price']}\n"
            f"\n你的股票已开始交易！",
            card_type="success"
        )
    
    async def _handle_company_dividend(self, event, company_id: str, company: dict):
        now = time.time()
        last_dividend = company.get("last_dividend_time", 0)
        
        if (now - last_dividend) < COMPANY_DIVIDEND_CYCLE:
            remaining_days = int((COMPANY_DIVIDEND_CYCLE - (now - last_dividend)) / 86400)
            await self._send_reply(
                event,
                f"分红周期未到，还需 {remaining_days} 天",
                card_type="warning"
            )
            return
        
        if company["profit"] <= 0:
            await self._send_reply(
                event,
                "公司利润为负，无法分红",
                card_type="danger"
            )
            return
        
        lines = [
            f"💰 发放分红 - {company['name']}\n",
            f"累计利润: {company['profit']} 喵币",
            f"当前分红比例: {company['dividend_ratio'] * 100:.0f}%",
            f"\n1. 修改分红比例",
            f"2. 确认发放分红",
            f"\n0. 返回"
        ]
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        elif text == "1":
            reply = await event.wait_reply(
                f"当前分红比例: {company['dividend_ratio'] * 100:.0f}%\n"
                f"请输入新的分红比例 (30-70%):",
                timeout=60
            )
            if reply is None:
                return
            try:
                ratio = int(reply.get_text().strip()) / 100
                if 0.3 <= ratio <= 0.7:
                    company["dividend_ratio"] = ratio
                    self._set_company(company_id, company)
                    await event.reply(f"分红比例已修改为 {ratio * 100:.0f}%")
                else:
                    await event.reply("分红比例必须在30%-70%之间")
            except ValueError:
                await event.reply("请输入有效数字")
        elif text == "2":
            total_dividend = int(company["profit"] * company["dividend_ratio"])
            if company["cash"] < total_dividend:
                await self._send_reply(
                    event,
                    f"现金不足！需要 {total_dividend} 喵币，当前只有 {company['cash']} 喵币",
                    card_type="danger"
                )
                return
            
            company["cash"] -= total_dividend
            company["last_dividend_time"] = now
            
            per_share_dividend = total_dividend // company["total_shares"]
            if per_share_dividend < 1:
                per_share_dividend = 1
            
            company_shares = self.sdk.storage.get(f"nekocare_company_shares:{company_id}") or {}
            shareholder_count = 0
            
            for shareholder_id, share_count in company_shares.items():
                if share_count > 0:
                    dividend_amount = per_share_dividend * share_count
                    self._add_coins(shareholder_id, dividend_amount)
                    shareholder_count += 1
            
            self._set_company(company_id, company)
            
            await self._send_reply(
                event,
                f"💰 分红已发放！\n\n"
                f"总分红金额: {total_dividend} 喵币\n"
                f"每股分红: ¥{per_share_dividend}\n"
                f"分红股东数: {shareholder_count}人",
                card_type="success"
            )
        else:
            await event.reply("无效编号")
    
    def _update_company_daily(self):
        companies = self._get_companies()
        now = time.time()
        
        for company_id, company in companies.items():
            if company.get("listed", False):
                type_data = COMPANY_TYPES[company["type"]]
                
                employee_count = len(company["employees"])
                base_revenue = 100 + employee_count * 50
                level_bonus = (company["level"] - 1) * 0.1
                market_factor = 1.0 + self._get_market_trend_factor()
                
                daily_revenue = int(base_revenue * (1 + level_bonus) * market_factor)
                
                daily_expenses = employee_count * 30 + 50
                
                daily_profit = daily_revenue - daily_expenses
                
                company["revenue"] += daily_revenue
                company["profit"] += daily_profit
                company["cash"] += daily_profit
                
                if company["profit"] >= COMPANY_LEVEL_UP_REVENUE * company["level"]:
                    if company["level"] < COMPANY_MAX_LEVEL:
                        company["level"] += 1
                
                if company["listed"]:
                    stock_name = f"[{company['name']}]股"
                    profit_ratio = company["profit"] / max(company["revenue"], 1)
                    price_change = profit_ratio * 0.2
                    
                    stock_data = self._get_stock_data(stock_name)
                    stock_data["price"] = int(stock_data["price"] * (1 + price_change))
                    self._set_stock_data(stock_name, stock_data)
                    
                    prices = self._get_stock_prices()
                    prices[stock_name] = stock_data["price"]
                    self.sdk.storage.set("nekocare_stock_prices", prices)
                    
                    company["share_price"] = stock_data["price"]
                
                self._set_company(company_id, company)
    
    def _get_market_trend_factor(self) -> float:
        trend_data = self.sdk.storage.get("nekocare_market_trend")
        if trend_data:
            return trend_data.get("coefficient", 0.0)
        return 0.0
    
    def _get_job_applications(self, company_id: str) -> dict:
        apps = self.sdk.storage.get(f"nekocare_job_applications:{company_id}")
        return apps if apps is not None else {}
    
    def _set_job_applications(self, company_id: str, apps: dict):
        self.sdk.storage.set(f"nekocare_job_applications:{company_id}", apps)
    
    def _get_user_application(self, user_id: str) -> Optional[dict]:
        companies = self._get_companies()
        for company_id, company in companies.items():
            apps = self._get_job_applications(company_id)
            if user_id in apps and apps[user_id]["status"] == "pending":
                return {"company_id": company_id, "company_name": company["name"], "application": apps[user_id]}
        return None
    
    async def _handle_recruit_employees(self, event, company_id: str, company: dict):
        while True:
            lines = [
                f"招聘管理 - {company['name']}\n",
                f"当前员工: {len(company['employees'])}人",
                f"\n1. 发布招聘信息",
                f"2. 查看申请列表",
                f"3. 查看员工列表",
                f"4. 员工管理（工资/劝退）",
                f"\n0. 返回"
            ]

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()

            if text == "0":
                return
            elif text == "1":
                await self._handle_post_job(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "2":
                await self._handle_view_applications(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "3":
                await self._handle_view_employees(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "4":
                await self._handle_employee_menu(event, company_id, company)
                company = self._get_company(company_id)
            else:
                await event.reply("无效编号")
    
    async def _handle_post_job(self, event, company_id: str, company: dict):
        lines = [
            f"发布招聘 - {company['name']}\n",
            f"选择职位等级：\n"
        ]

        for level, position in JOB_POSITIONS.items():
            lines.append(f"{level}. {position['name']} - 薪资: {position['salary']} 喵币/次")

        lines.append("\n输入职位等级 (输入0取消):")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()

        if text == "0":
            return

        try:
            position_level = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return

        if position_level not in JOB_POSITIONS:
            await event.reply("无效的职位等级")
            return

        position_info = JOB_POSITIONS[position_level]
        current_postings = self._get_company_postings(company_id)
        same_position_count = sum(1 for p in current_postings.values() if p["position_level"] == position_level)

        if same_position_count >= 1:
            await self._send_reply(
                event,
                f"该职位已在招聘中，请勿重复发布",
                card_type="warning"
            )
            return

        posting = self._add_job_posting(company_id, position_level)

        await self._send_reply(
            event,
            f"招聘信息已发布！\n\n"
            f"公司: {company['name']}\n"
            f"职位: {position_info['name']}\n"
            f"薪资: {position_info['salary']} 喵币/次\n"
            f"\n玩家可以到招聘市场申请该职位",
            card_type="success"
        )
    
    async def _handle_view_applications(self, event, company_id: str, company: dict):
        apps = self._get_job_applications(company_id)
        pending_apps = {uid: app for uid, app in apps.items() if app["status"] == "pending"}

        if not pending_apps:
            await event.reply("当前没有待处理的申请")
            return

        lines = ["待处理申请\n"]
        for i, (user_id, app) in enumerate(pending_apps.items(), 1):
            nick = self._get_nickname(user_id) or user_id
            position = JOB_POSITIONS.get(app["position"], {}).get("name", "未知")
            lines.append(f"{i}. {nick} - 申请: {position}")

        lines.append("\n输入编号查看详情 (输入0返回):")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()

        if text == "0":
            return

        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return

        user_ids = list(pending_apps.keys())
        if 1 <= choice <= len(user_ids):
            await self._handle_review_application(event, company_id, user_ids[choice - 1], company)
        else:
            await event.reply("无效编号")
    
    async def _handle_review_application(self, event, company_id: str, applicant_id: str, company: dict):
        apps = self._get_job_applications(company_id)
        app = apps.get(applicant_id)

        if not app or app["status"] != "pending":
            await event.reply("申请不存在或已处理")
            return

        nick = self._get_nickname(applicant_id) or applicant_id
        position = JOB_POSITIONS.get(app["position"], {}).get("name", "未知")
        attrs = self._get_attrs(applicant_id)

        lines = [
            f"申请详情\n",
            f"申请人: {nick}",
            f"申请职位: {position}",
            f"申请时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(app['apply_time']))}",
            f"\n属性值",
            f"智力: {attrs['int']}",
            f"体力: {attrs['hp']}",
            f"魅力: {attrs['cha']}",
            f"\n1. 接受申请",
            f"2. 拒绝申请",
            f"\n0. 返回"
        ]

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()

        if text == "0":
            return
        elif text == "1":
            position_level = app["position"]
            position_info = JOB_POSITIONS[position_level]

            current_employees = sum(1 for e in company["employees"].values() if e["position"] == position_level)

            if current_employees >= position_info["max_employees"]:
                await self._send_reply(
                    event,
                    f"该职位员工已满（最多{position_info['max_employees']}人）",
                    card_type="warning"
                )
                return

            app["status"] = "accepted"
            apps[applicant_id] = app
            self._set_job_applications(company_id, apps)

            company["employees"][applicant_id] = {
                "position": app["position"],
                "hire_time": time.time(),
                "last_paid": time.time(),
                "salary_paid": 0,
            }
            self._set_company(company_id, company)

            company_postings = self._get_company_postings(company_id)
            for posting_id, posting in company_postings.items():
                if posting["position_level"] == position_level:
                    self._remove_job_posting(posting_id)
                    break

            await self._send_reply(
                event,
                f"已接受 {nick} 的申请！\n"
                f"职位: {position}\n"
                f"薪资: {position_info['salary']} 喵币/天（固定工资）",
                card_type="success"
            )
        elif text == "2":
            app["status"] = "rejected"
            apps[applicant_id] = app
            self._set_job_applications(company_id, apps)

            await event.reply(f"已拒绝 {nick} 的申请")
        else:
            await event.reply("无效编号")
    
    async def _handle_view_employees(self, event, company_id: str, company: dict):
        if not company["employees"]:
            await event.reply("公司还没有玩家员工")

        lines = ["玩家员工列表\n"]
        for user_id, emp in company["employees"].items():
            nick = self._get_nickname(user_id) or user_id
            position = JOB_POSITIONS.get(emp["position"], {}).get("name", "未知")
            hire_time = emp.get("hire_time", emp.get("join_time", time.time()))
            days_worked = self._calculate_salary_days(hire_time)
            position_level = emp["position"]
            salary = JOB_POSITIONS[position_level]["salary"]
            lines.append(f"{nick} - {position} (工作{days_worked}天, 薪资:{salary} 喵币/天)")

        await event.reply("\n".join(lines))
    
    async def _handle_recruit_npc(self, event, company_id: str, company: dict):
        while True:
            npc_employees = company.get("npc_employees", {})
            max_npc = COMPANY_MAX_NPC_PER_COMPANY
            
            lines = [
                f"招聘NPC员工 - {company['name']}\n",
                f"当前NPC员工: {len(npc_employees)}/{max_npc}",
                f"公司等级: {company['level']} (影响高稀有度NPC出现概率)",
                f"\n1. 尝试招聘NPC",
                f"2. 查看NPC员工列表",
                f"3. 解雇NPC员工",
                f"\n0. 返回"
            ]
            
            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()
            
            if text == "0":
                return
            elif text == "1":
                await self._recruit_single_npc(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "2":
                await self._handle_view_npc_employees(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "3":
                await self._handle_fire_npc(event, company_id, company)
                company = self._get_company(company_id)
            else:
                await event.reply("无效编号")
    
    async def _recruit_single_npc(self, event, company_id: str, company: dict):
        npc_employees = company.get("npc_employees", {})
        
        if len(npc_employees) >= COMPANY_MAX_NPC_PER_COMPANY:
            await self._send_reply(
                event,
                f"NPC员工已达上限 ({COMPANY_MAX_NPC_PER_COMPANY}人)",
                card_type="warning"
            )
            return
        
        roll = random.random()
        selected_level = 1
        cumulative = 0
        for level, data in NPC_EMPLOYEE_LEVELS.items():
            prob = self._get_npc_recruit_probability(company["level"], level)
            cumulative += prob
            if roll <= cumulative:
                selected_level = level
                break
        
        npc = self._generate_npc_employee(company["level"])
        npc["level"] = selected_level
        level_data = NPC_EMPLOYEE_LEVELS[selected_level]
        npc["level_name"] = level_data["name"]
        npc["base_salary"] = level_data["salary"]
        
        npc_id = f"npc_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        npc_employees[npc_id] = npc
        
        company["npc_employees"] = npc_employees
        self._set_company(company_id, company)
        
        efficiency_pct = int(npc["efficiency"] * 100)
        await self._send_reply(
            event,
            f"🎉 招聘成功！\n\n"
            f"NPC: {npc['name']}\n"
            f"等级: {npc['level_name']} (稀有度: {level_data['rarity']*100:.0f}%)\n"
            f"效率: {efficiency_pct}%\n"
            f"薪资: {npc['base_salary']} 喵币/天\n\n"
            f"公司等级越高，越容易招募到高稀有度NPC！",
            card_type="success"
        )
    
    async def _handle_view_npc_employees(self, event, company_id: str, company: dict):
        npc_employees = company.get("npc_employees", {})
        
        if not npc_employees:
            await event.reply("公司还没有NPC员工")
            return
        
        lines = ["NPC员工列表\n"]
        total_efficiency = 0
        total_salary = 0
        for i, (npc_id, npc) in enumerate(npc_employees.items(), 1):
            status_emoji = "✓" if npc.get("status") == "active" else "⚠️"
            days_hired = int((time.time() - npc.get("hired_time", time.time())) / 86400)
            efficiency_pct = int(npc.get("efficiency", 1.0) * 100)
            lines.append(
                f"{i}. {npc['name']} [{npc['level_name']}] {status_emoji}\n"
                f"   效率:{efficiency_pct}% 薪资:{npc['base_salary']} 喵币/天 入职{days_hired}天"
            )
            total_efficiency += npc.get("efficiency", 1.0)
            total_salary += npc.get("base_salary", 0)
        
        lines.append(f"\n总计: {len(npc_employees)}人")
        lines.append(f"总效率: {int(total_efficiency * 100)}%")
        lines.append(f"总薪资: {total_salary} 喵币/天")
        
        await event.reply("\n".join(lines))
    
    async def _handle_fire_npc(self, event, company_id: str, company: dict):
        npc_employees = company.get("npc_employees", {})
        
        if not npc_employees:
            await event.reply("没有NPC员工可以解雇")
            return
        
        lines = ["解雇NPC员工\n"]
        for i, (npc_id, npc) in enumerate(npc_employees.items(), 1):
            efficiency_pct = int(npc.get("efficiency", 1.0) * 100)
            lines.append(f"{i}. {npc['name']} [{npc['level_name']}] 效率:{efficiency_pct}%")
        
        lines.append("\n输入编号解雇 (输入0返回):")
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        
        npc_ids = list(npc_employees.keys())
        if 1 <= choice <= len(npc_ids):
            npc_id = npc_ids[choice - 1]
            npc = npc_employees[npc_id]
            del npc_employees[npc_id]
            company["npc_employees"] = npc_employees
            self._set_company(company_id, company)
            await self._send_reply(
                event,
                f"已解雇 {npc['name']} [{npc['level_name']}]",
                card_type="success"
            )
        else:
            await event.reply("无效编号")
    
    async def _handle_settle_npc(self, event, company_id: str, company: dict):
        npc_employees = company.get("npc_employees", {})
        
        if not npc_employees:
            await event.reply("没有NPC员工需要结算")
            return
        
        result = self._daily_settlement_npc(company_id)
        
        if not result["success"]:
            await self._send_reply(
                event,
                result["message"],
                card_type="warning"
            )
            return
        
        stats = result.get("stats", {})
        total_salary = result.get("total_salary", 0)
        total_revenue = result.get("total_revenue", 0)
        
        company = self._get_company(company_id)
        
        lines = [
            f"💰 NPC员工工资结算 - {company['name']}\n",
            f"现金: {company['cash']} 喵币",
            f"\n结算结果：",
            f"正常员工: {stats.get('normal', 0)}人",
            f"摸鱼员工: {stats.get('slacking', 0)}人",
            f"懒惰员工: {stats.get('lazy', 0)}人",
            f"因没钱被解雇: {stats.get('fired', 0)}人",
            f"\n总支出: {total_salary} 喵币",
            f"总收入: {total_revenue} 喵币",
            f"净利润: {total_revenue - total_salary} 喵币",
        ]
        
        if stats.get('slacking', 0) > 0 or stats.get('lazy', 0) > 0:
            lines.append("\n⚠️ 部分员工摸鱼/懒惰，收益减少！")
        
        await self._send_reply(
            event,
            "\n".join(lines),
            card_type="success" if total_revenue > total_salary else "warning"
        )
    
    async def _handle_job_market(self, event, user_id):
        while True:
            lines = ["招聘市场\n"]
            lines.append("1. 查看所有招聘信息")
            lines.append("2. 查看我的申请")
            lines.append("3. 开始工作")
            lines.append("\n0. 返回")

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()

            if text == "0":
                return
            elif text == "1":
                await self._handle_view_job_postings(event, user_id)
            elif text == "2":
                await self._handle_view_my_applications(event, user_id)
            elif text == "3":
                await self._handle_perform_company_work(event, user_id)
            else:
                await event.reply("无效编号")

    async def _handle_view_job_postings(self, event, user_id: str):
        postings = self._get_job_postings()
        lines = ["招聘信息\n"]

        postings_list = sorted(postings.values(), key=lambda x: x["post_time"], reverse=True)

        for i, posting in enumerate(postings_list, 1):
            lines.append(f"{i}. {posting['company_name']} - {posting['position_name']} ({posting['salary']} 喵币/次)")

        if not postings_list:
            await event.reply("当前没有招聘信息")
            return

        lines.append("\n输入编号申请职位 (输入0返回):")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()

        if text == "0":
            return

        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return

        if 1 <= choice <= len(postings_list):
            await self._handle_apply_job(event, user_id, postings_list[choice - 1])
        else:
            await event.reply("无效编号")
    
    async def _handle_apply_job(self, event, user_id: str, posting: dict):
        company = self._get_company(posting["company_id"])
        if not company:
            await event.reply("公司不存在")
            return

        position_info = JOB_POSITIONS[posting["position_level"]]
        current_employees = sum(1 for e in company["employees"].values() if e["position"] == posting["position_level"])

        if current_employees >= position_info["max_employees"]:
            await self._send_reply(
                event,
                "该职位已满员",
                card_type="warning"
            )
            self._remove_job_posting(posting["posting_id"])
            return

        attrs = self._get_attrs(user_id)
        edu_level = self._get_edu(user_id)

        if edu_level < position_info["req_edu"]:
            await self._send_reply(
                event,
                f"学历要求不达标，需要{EDU_LEVELS[position_info['req_edu']]['name']}",
                card_type="warning"
            )
            return

        lines = [
            f"申请职位\n",
            f"公司: {posting['company_name']}",
            f"职位: {posting['position_name']}",
            f"薪资: {posting['salary']} 喵币/次",
            f"固定工资周期: 每天",
            f"\n确定要申请吗？（y/n）"
        ]

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip().lower()

        if text == "y":
            existing = self._get_user_application(user_id)
            if existing:
                await self._send_reply(
                    event,
                    f"你已有待处理的申请：{existing['company_name']}",
                    card_type="warning"
                )
                return

            existing_job = self._get_user_job(user_id)
            if existing_job:
                await self._send_reply(
                    event,
                    f"你已在 {existing_job['company_name']} 工作",
                    card_type="warning"
                )
                return

            apps = self._get_job_applications(posting["company_id"])
            apps[user_id] = {
                "position": posting["position_level"],
                "apply_time": time.time(),
                "status": "pending"
            }
            self._set_job_applications(posting["company_id"], apps)

            await self._send_reply(
                event,
                f"申请已提交！\n\n"
                f"公司: {posting['company_name']}\n"
                f"职位: {posting['position_name']}\n"
                f"\n等待公司审核...",
                card_type="success"
            )
    
    async def _handle_view_my_applications(self, event, user_id: str):
        existing = self._get_user_application(user_id)

        if not existing:
            job = self._get_user_job(user_id)
            if job:
                company = self._get_company(job["company_id"])
                if company:
                    emp_data = company["employees"][user_id]
                    position = JOB_POSITIONS.get(emp_data["position"], {}).get("name", "未知")
                    days_worked = self._calculate_salary_days(emp_data["hire_time"])
                    salary = JOB_POSITIONS[emp_data["position"]]["salary"]

                    lines = [
                        f"我的工作\n",
                        f"公司: {job['company_name']}",
                        f"职位: {position}",
                        f"工作天数: {days_worked}天",
                        f"薪资: {salary} 喵币/天",
                        f"\n1. 离职",
                        f"2. 返回"
                    ]

                    reply = await event.wait_reply("\n".join(lines), timeout=60)
                    if reply is None:
                        return
                    text = reply.get_text().strip()

                    if text == "1":
                        await self._handle_resign(event, user_id)
                    return
            else:
                await event.reply("你没有待处理的申请")
            return

        position = JOB_POSITIONS.get(existing["application"]["position"], {}).get("name", "未知")
        lines = [
            f"我的申请\n",
            f"公司: {existing['company_name']}",
            f"职位: {position}",
            f"状态: 待审核",
            f"\n等待公司审核..."
        ]

        await event.reply("\n".join(lines))
    
    async def _handle_perform_company_work(self, event, user_id: str):
        companies = self._get_companies()
        my_jobs = []
        
        for company_id, company in companies.items():
            if user_id in company["employees"]:
                my_jobs.append({
                    "company_id": company_id,
                    "company_name": company["name"],
                    "employee_data": company["employees"][user_id]
                })
        
        if not my_jobs:
            await self._send_reply(
                event,
                "你还没有入职任何公司",
                card_type="warning"
            )
            return
        
        lines = ["我的工作\n"]
        for i, job in enumerate(my_jobs, 1):
            position = JOB_POSITIONS.get(job["employee_data"]["position"], {}).get("name", "未知")
            lines.append(f"{i}. {job['company_name']} - {position}")
        
        lines.append("\n输入编号开始工作 (输入0返回):")
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        
        if 1 <= choice <= len(my_jobs):
            job = my_jobs[choice - 1]
            await self._do_company_work(event, user_id, job["company_id"], job["employee_data"])
        else:
            await event.reply("无效编号")
    
    async def _do_company_work(self, event, user_id: str, company_id: str, employee_data: dict):
        if not self._check_cooldown(user_id, "work", 3600):
            await self._send_reply(
                event,
                "工作冷却中，请稍后再试",
                card_type="warning"
            )
            return

        position_level = employee_data["position"]
        base_salary = JOB_POSITIONS[position_level]["salary"]
        bonus_earnings = int(base_salary * 0.5)

        attrs = self._get_attrs(user_id)
        stat_key = "int" if position_level <= 2 else ("hp" if position_level <= 3 else "cha")
        stat_val = attrs.get(stat_key, 10)

        bonus = 0
        if stat_val >= 60:
            bonus = int(bonus_earnings * 0.3)

        total_earnings = bonus_earnings + bonus

        self._add_coins(user_id, total_earnings)
        self._set_cooldown(user_id, "work")

        company = self._get_company(company_id)
        company_name = company["name"] if company else "公司"

        await self._send_reply(
            event,
            f"工作完成！\n\n"
            f"基础工资由公司定期发放\n"
            f"本次工作奖励: {bonus_earnings} 喵币\n"
            f"属性加成: {bonus} 喵币\n"
            f"总收入: {total_earnings} 喵币",
            card_type="success"
        )
    
    def _get_company_shares(self, company_id: str) -> dict:
        shares = self.sdk.storage.get(f"nekocare_company_shares:{company_id}")
        return shares if shares is not None else {}
    
    def _set_company_shares(self, company_id: str, shares: dict):
        self.sdk.storage.set(f"nekocare_company_shares:{company_id}", shares)
    
    def _add_share(self, company_id: str, user_id: str, amount: int):
        shares = self._get_company_shares(company_id)
        shares[user_id] = shares.get(user_id, 0) + amount
        self._set_company_shares(company_id, shares)
        
        user_stocks = self._get_user_stocks(user_id)
        company = self._get_company(company_id)
        stock_name = f"[{company['name']}]股"
        user_stocks[stock_name] = user_stocks.get(stock_name, 0) + amount
        self._set_user_stocks(user_id, user_stocks)
    
    def _remove_share(self, company_id: str, user_id: str, amount: int):
        shares = self._get_company_shares(company_id)
        if user_id in shares:
            shares[user_id] -= amount
            if shares[user_id] <= 0:
                del shares[user_id]
            self._set_company_shares(company_id, shares)
        
        user_stocks = self._get_user_stocks(user_id)
        company = self._get_company(company_id)
        stock_name = f"[{company['name']}]股"
        if stock_name in user_stocks:
            user_stocks[stock_name] -= amount
            if user_stocks[stock_name] <= 0:
                del user_stocks[stock_name]
            self._set_user_stocks(user_id, user_stocks)
    
    def _get_user_share_count(self, company_id: str, user_id: str) -> int:
        shares = self._get_company_shares(company_id)
        return shares.get(user_id, 0)
    
    def _get_nickname(self, user_id: str) -> Optional[str]:
        return self.sdk.storage.get(f"nekocare_nickname:{user_id}")
    
    def _get_cooldown(self, user_id: str, action: str) -> float:
        cd = self.sdk.storage.get(f"nekocare_{action}_cd:{user_id}")
        return cd if cd is not None else 0
    
    def _set_cooldown(self, user_id: str, action: str):
        self.sdk.storage.set(f"nekocare_{action}_cd:{user_id}", time.time())
    
    def _check_cooldown(self, user_id: str, action: str, cooldown_period: float) -> bool:
        last_cd = self._get_cooldown(user_id, action)
        if last_cd == 0:
            return True
        return (time.time() - last_cd) >= cooldown_period
    
    async def _handle_buy_company_stock(self, event, user_id: str, company_id: str):
        company = self._get_company(company_id)
        if not company or not company.get("listed"):
            await event.reply("公司不存在或未上市")
            return
        
        stock_name = f"[{company['name']}]股"
        prices = self._get_stock_prices()
        price = prices.get(stock_name, company["share_price"])
        
        lines = [
            f"买入股票 - {company['name']}\n",
            f"当前股价: ¥{price}",
            f"公司现金: {company['cash']} 喵币",
            f"你的钱包: {self._get_coins(user_id)} 喵币",
            f"\n请输入购买数量 (输入0返回):"
        ]
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        try:
            qty = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        
        if qty < 1:
            await event.reply("请输入正整数")
            return
        
        total_cost = price * qty
        coins = self._get_coins(user_id)
        
        if total_cost > coins:
            await self._send_reply(
                event,
                f"喵币不足！需要 {total_cost} 喵币",
                card_type="danger"
            )
            return
        
        self._add_coins(user_id, -total_cost)
        self._add_share(company_id, user_id, qty)
        
        stock_data = self._get_stock_data(stock_name)
        stock_data["volume_buy"] += qty
        self._set_stock_data(stock_name, stock_data)
        
        await self._send_reply(
            event,
            f"买入成功！\n\n"
            f"股票: {stock_name}\n"
            f"数量: {qty}股\n"
            f"单价: ¥{price}\n"
            f"总价: {total_cost} 喵币",
            card_type="success"
        )
    
    async def _handle_sell_company_stock(self, event, user_id: str, company_id: str):
        company = self._get_company(company_id)
        if not company or not company.get("listed"):
            await event.reply("公司不存在或未上市")
            return
        
        stock_name = f"[{company['name']}]股"
        held = self._get_user_share_count(company_id, user_id)
        
        if held <= 0:
            await self._send_reply(
                event,
                f"你没有持有 {stock_name}",
                card_type="warning"
            )
            return
        
        prices = self._get_stock_prices()
        price = prices.get(stock_name, company["share_price"])
        
        lines = [
            f"卖出股票 - {company['name']}\n",
            f"当前股价: ¥{price}",
            f"持有数量: {held}股",
            f"\n请输入卖出数量 (输入0返回):"
        ]
        
        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()
        
        if text == "0":
            return
        
        try:
            qty = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return
        
        if qty < 1 or qty > held:
            await event.reply(f"请输入 1-{held}")
            return
        
        revenue = price * qty
        self._remove_share(company_id, user_id, qty)
        self._add_coins(user_id, revenue)
        
        stock_data = self._get_stock_data(stock_name)
        stock_data["volume_sell"] += qty
        self._set_stock_data(stock_name, stock_data)
        
        profit = revenue - qty * company["base_price"]
        sign = "+" if profit >= 0 else ""
        
        await self._send_reply(
            event,
            f"卖出成功！\n\n"
            f"股票: {stock_name}\n"
            f"数量: {qty}股\n"
            f"单价: ¥{price}\n"
            f"总收入: {revenue} 喵币\n"
            f"盈亏: {sign}{profit} 喵币",
            card_type="success"
        )

    # =============================================================
    #  招聘信息存储
    # =============================================================

    def _get_job_postings(self) -> dict:
        postings = self.sdk.storage.get("nekocare_job_postings")
        return postings if postings is not None else {}

    def _set_job_postings(self, postings: dict):
        self.sdk.storage.set("nekocare_job_postings", postings)

    def _add_job_posting(self, company_id: str, position_level: int):
        postings = self._get_job_postings()
        company = self._get_company(company_id)
        if not company:
            return None

        position_info = JOB_POSITIONS.get(position_level)
        if not position_info:
            return None

        posting_id = f"{company_id}_{position_level}_{int(time.time())}"
        posting = {
            "posting_id": posting_id,
            "company_id": company_id,
            "company_name": company["name"],
            "position_level": position_level,
            "position_name": position_info["name"],
            "salary": position_info["salary"],
            "post_time": time.time()
        }

        postings[posting_id] = posting
        self._set_job_postings(postings)
        return posting

    def _remove_job_posting(self, posting_id: str):
        postings = self._get_job_postings()
        if posting_id in postings:
            del postings[posting_id]
            self._set_job_postings(postings)

    def _remove_company_postings(self, company_id: str):
        postings = self._get_job_postings()
        to_remove = [pid for pid, p in postings.items() if p["company_id"] == company_id]
        for pid in to_remove:
            del postings[pid]
        self._set_job_postings(postings)

    def _get_company_postings(self, company_id: str) -> dict:
        postings = self._get_job_postings()
        return {pid: p for pid, p in postings.items() if p["company_id"] == company_id}

    def _get_user_job(self, user_id: str) -> Optional[dict]:
        companies = self._get_companies()
        for company_id, company in companies.items():
            if user_id in company["employees"]:
                employee_data = company["employees"][user_id]
                return {
                    "company_id": company_id,
                    "company_name": company["name"],
                    "position": employee_data["position"],
                    "hire_time": employee_data["hire_time"]
                }
        return None

    def _calculate_salary_days(self, hire_time: float) -> int:
        now = time.time()
        return int((now - hire_time) / COMPANY_SALARY_INTERVAL)

    def _pay_employee_salary(self, company_id: str, company: dict, user_id: str, employee_data: dict):
        now = time.time()
        hire_time = employee_data["hire_time"]
        last_paid = employee_data.get("last_paid", hire_time)

        days_worked = int((now - last_paid) / COMPANY_SALARY_INTERVAL)

        if days_worked <= 0:
            return 0, False

        position_level = employee_data["position"]
        salary = JOB_POSITIONS[position_level]["salary"]
        total_salary = salary * days_worked

        if company["cash"] < total_salary:
            return total_salary, False

        company["cash"] -= total_salary
        employee_data["last_paid"] = now
        employee_data["salary_paid"] = employee_data.get("salary_paid", 0) + total_salary
        company["employees"][user_id] = employee_data
        self._set_company(company_id, company)

        self._add_coins(user_id, total_salary)
        return total_salary, True
    
    def _pay_npc_salary(self, company_id: str, company: dict, npc_id: str, npc_data: dict) -> Tuple[int, bool, str]:
        now = time.time()
        last_paid = npc_data.get("last_paid", npc_data.get("hired_time", now))
        
        days_worked = int((now - last_paid) / COMPANY_SALARY_INTERVAL)
        
        if days_worked <= 0:
            return 0, False, "normal"
        
        base_salary = npc_data.get("base_salary", 50)
        efficiency = npc_data.get("efficiency", 1.0)
        status = npc_data.get("status", "active")
        
        total_salary = base_salary * days_worked
        
        if company["cash"] < total_salary:
            return total_salary, False, "normal"
        
        slack_chance = COMPANY_SLACK_CHANCE
        lazy_chance = COMPANY_LAZY_CHANCE
        
        if status == "slacking":
            slack_chance *= 2
            lazy_chance *= 2
        
        roll = random.random()
        actual_salary = total_salary
        work_status = "normal"
        
        if roll < lazy_chance:
            actual_salary = int(total_salary * COMPANY_LAZY_PENALTY)
            work_status = "lazy"
            npc_data["status"] = "slacking"
        elif roll < slack_chance + lazy_chance:
            actual_salary = int(total_salary * COMPANY_SLACK_PENALTY)
            work_status = "slacking"
            npc_data["status"] = "slacking"
        
        revenue = int(actual_salary * efficiency * 2)
        profit = revenue - actual_salary
        
        company["cash"] -= actual_salary
        company["revenue"] = company.get("revenue", 0) + revenue
        company["profit"] = company.get("profit", 0) + profit
        
        npc_data["last_paid"] = now
        npc_data["total_earnings"] = npc_data.get("total_earnings", 0) + actual_salary
        
        npc_employees = company.get("npc_employees", {})
        npc_employees[npc_id] = npc_data
        company["npc_employees"] = npc_employees
        self._set_company(company_id, company)
        
        return actual_salary, True, work_status
    
    def _daily_settlement_npc(self, company_id: str) -> dict:
        company = self._get_company(company_id)
        if not company:
            return {"success": False, "message": "公司不存在"}
        
        npc_employees = company.get("npc_employees", {})
        if not npc_employees:
            return {"success": True, "message": "没有NPC员工", "stats": {}}
        
        now = time.time()
        last_settlement = company.get("last_npc_settlement", 0)
        
        if (now - last_settlement) < COMPANY_SALARY_INTERVAL:
            return {"success": False, "message": "结算周期未到"}
        
        total_salary = 0
        total_revenue = 0
        stats = {
            "normal": 0,
            "slacking": 0,
            "lazy": 0,
            "fired": 0,
        }
        
        for npc_id, npc_data in list(npc_employees.items()):
            salary, success, work_status = self._pay_npc_salary(company_id, company, npc_id, npc_data)
            
            if success:
                total_salary += salary
                efficiency = npc_data.get("efficiency", 1.0)
                revenue = int(salary * efficiency * 2)
                total_revenue += revenue
                stats[work_status] = stats.get(work_status, 0) + 1
            else:
                if company["cash"] < npc_data.get("base_salary", 50):
                    del npc_employees[npc_id]
                    stats["fired"] += 1
        
        company["last_npc_settlement"] = now
        company["npc_employees"] = npc_employees
        self._set_company(company_id, company)
        
        return {
            "success": True,
            "message": f"结算完成",
            "stats": stats,
            "total_salary": total_salary,
            "total_revenue": total_revenue,
        }

    async def _handle_employee_menu(self, event, company_id: str, company: dict):
        while True:
            lines = [
                f"员工管理 - {company['name']}\n",
                f"当前员工: {len(company['employees'])}人\n",
                f"1. 查看员工列表",
                f"2. 发放工资",
                f"3. 劝退员工",
                f"\n0. 返回"
            ]

            reply = await event.wait_reply("\n".join(lines), timeout=60)
            if reply is None:
                return
            text = reply.get_text().strip()

            if text == "0":
                return
            elif text == "1":
                await self._handle_view_employees(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "2":
                await self._handle_pay_salaries(event, company_id, company)
                company = self._get_company(company_id)
            elif text == "3":
                await self._handle_fire_employee(event, company_id, company)
                company = self._get_company(company_id)
            else:
                await event.reply("无效编号")

    async def _handle_pay_salaries(self, event, company_id: str, company: dict):
        lines = [
            f"发放工资 - {company['name']}\n",
            f"公司现金: {company['cash']} 喵币\n"
        ]

        employees_to_pay = []
        for user_id, employee_data in company["employees"].items():
            now = time.time()
            hire_time = employee_data["hire_time"]
            last_paid = employee_data.get("last_paid", hire_time)
            days_worked = int((now - last_paid) / COMPANY_SALARY_INTERVAL)

            if days_worked > 0:
                position_level = employee_data["position"]
                salary = JOB_POSITIONS[position_level]["salary"]
                total_salary = salary * days_worked
                nick = self._get_nickname(user_id) or user_id
                employees_to_pay.append({
                    "user_id": user_id,
                    "nick": nick,
                    "days_worked": days_worked,
                    "salary": total_salary
                })

        if not employees_to_pay:
            lines.append("\n当前没有待发放的工资")
            await event.reply("\n".join(lines))
            return

        lines.append("\n待发放工资：")
        total_salary_needed = 0
        for emp in employees_to_pay:
            lines.append(f"{emp['nick']}: {emp['salary']} 喵币 ({emp['days_worked']}天)")
            total_salary_needed += emp['salary']

        lines.append(f"\n总计: {total_salary_needed} 喵币")
        lines.append(f"\n确定要发放吗？（y/n）")

        if total_salary_needed > company["cash"]:
            await self._send_reply(
                event,
                f"公司现金不足，需要 {total_salary_needed} 喵币",
                card_type="danger"
            )
            return

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip().lower()

        if text == "y":
            for emp in employees_to_pay:
                employee_data = company["employees"][emp["user_id"]]
                now = time.time()
                employee_data["last_paid"] = now
                employee_data["salary_paid"] = employee_data.get("salary_paid", 0) + emp["salary"]
                company["employees"][emp["user_id"]] = employee_data
                self._add_coins(emp["user_id"], emp["salary"])

            company["cash"] -= total_salary_needed
            self._set_company(company_id, company)

            await self._send_reply(
                event,
                f"工资发放成功！\n\n共 {len(employees_to_pay)} 人\n总计: {total_salary_needed} 喵币",
                card_type="success"
            )

    async def _handle_fire_employee(self, event, company_id: str, company: dict):
        employees = company["employees"]
        if not employees:
            await event.reply("公司暂无员工")
            return

        lines = ["选择要劝退的员工：\n"]
        employees_list = []
        for i, (user_id, employee_data) in enumerate(employees.items(), 1):
            nick = self._get_nickname(user_id) or user_id
            position = JOB_POSITIONS.get(employee_data["position"], {}).get("name", "未知")
            hire_time = employee_data["hire_time"]
            days_worked = self._calculate_salary_days(hire_time)
            position_level = employee_data["position"]
            salary = JOB_POSITIONS[position_level]["salary"]

            compensation = salary * (days_worked + 1)
            lines.append(f"{i}. {nick} - {position} (工作{days_worked}天)")
            employees_list.append({
                "user_id": user_id,
                "nick": nick,
                "position": position,
                "days_worked": days_worked,
                "compensation": compensation
            })

        lines.append("\n输入编号 (输入0返回):")

        reply = await event.wait_reply("\n".join(lines), timeout=60)
        if reply is None:
            return
        text = reply.get_text().strip()

        if text == "0":
            return

        try:
            choice = int(text)
        except ValueError:
            await event.reply("请输入有效数字")
            return

        if 1 <= choice <= len(employees_list):
            emp = employees_list[choice - 1]

            if company["cash"] < emp["compensation"]:
                await self._send_reply(
                    event,
                    f"公司现金不足，需要支付 N+1 赔偿：{emp['compensation']} 喵币",
                    card_type="danger"
                )
                return

            confirm_lines = [
                f"劝退员工\n\n",
                f"员工: {emp['nick']}",
                f"职位: {emp['position']}",
                f"工作时间: {emp['days_worked']}天",
                f"N+1赔偿: {emp['compensation']} 喵币",
                f"\n确定要劝退吗？（y/n）"
            ]

            reply = await event.wait_reply("\n".join(confirm_lines), timeout=60)
            if reply is None:
                return
            confirm_text = reply.get_text().strip().lower()

            if confirm_text == "y":
                company["cash"] -= emp["compensation"]
                del company["employees"][emp["user_id"]]
                self._set_company(company_id, company)
                self._add_coins(emp["user_id"], emp["compensation"])

                await self._send_reply(
                    event,
                    f"已劝退员工 {emp['nick']}\n\n"
                    f"支付 N+1 赔偿: {emp['compensation']} 喵币",
                    card_type="success"
                )
        else:
            await event.reply("无效编号")

    async def _handle_resign(self, event, user_id: str):
        job = self._get_user_job(user_id)
        if not job:
            await event.reply("你当前没有工作")
            return

        company = self._get_company(job["company_id"])
        if not company:
            await event.reply("公司不存在")
            return

        employee_data = company["employees"][user_id]
        days_worked = self._calculate_salary_days(employee_data["hire_time"])
        position_level = employee_data["position"]
        salary = JOB_POSITIONS[position_level]["salary"]
        unpaid_salary = salary * days_worked

        if unpaid_salary > 0:
            if company["cash"] >= unpaid_salary:
                company["cash"] -= unpaid_salary
                self._add_coins(user_id, unpaid_salary)
                salary_text = f"未发工资: {unpaid_salary} 喵币"
            else:
                await self._send_reply(
                    event,
                    "公司现金不足，无法结算工资",
                    card_type="warning"
                )
                return
        else:
            salary_text = "无未发工资"

        del company["employees"][user_id]
        self._set_company(job["company_id"], company)

        await self._send_reply(
            event,
            f"已离职\n\n"
            f"公司: {job['company_name']}\n"
            f"{salary_text}",
            card_type="success"
        )
