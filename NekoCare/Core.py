import random
import time
from typing import Optional, Dict, Any, Tuple

import aiohttp

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command

DECAY_RATE = 3
CRITICAL_TIMEOUT = 86400
RESCUE_COST = 50
FOSTER_COST_PER_DAY = 5
FOSTER_MAX_DAYS = 7

SHOP_ITEMS = {
    "小鱼干": {
        "price": 20,
        "desc": "恢复20点饱食度",
        "type": "consumable",
        "effect": {"fullness": 20},
    },
    "高级猫粮": {
        "price": 50,
        "desc": "恢复50点饱食度",
        "type": "consumable",
        "effect": {"fullness": 50},
    },
    "亲密度糖果": {
        "price": 60,
        "desc": "亲密度+10",
        "type": "consumable",
        "effect": {"intimacy": 10},
    },
    "金币加成卡": {
        "price": 100,
        "desc": "下次打工收益翻倍",
        "type": "buff",
        "buff": "work_double",
    },
    "幸运铃铛": {
        "price": 80,
        "desc": "下次抓猫成功率+25%",
        "type": "buff",
        "buff": "catch_boost",
    },
    "急救包": {
        "price": 150,
        "desc": "免费急救一次",
        "type": "buff",
        "buff": "free_rescue",
    },
}

SHOP_ITEM_LIST = list(SHOP_ITEMS.keys())

DEATH_TITLES = {"starve": "饿死大王", "overwork": "劳累过度"}
ABANDON_TITLE = "弃养者"

MENU_STYLE = (
    "padding:10px;border-radius:8px;font-size:14px;"
    "line-height:1.6;font-family:sans-serif;"
)
HEADER_STYLE = "font-size:16px;font-weight:bold;margin-bottom:8px;color:#e91e63;"
SUBHEADER_STYLE = (
    "text-align:center;font-weight:bold;padding:6px 0;"
    "color:#495057;border-bottom:2px solid #dee2e6;margin:8px 0;"
)
ITEM_STYLE = "padding:3px 6px;color:#495057;border-radius:4px;margin:1px 0;"
KV_STYLE = "margin-bottom:2px;font-size:13px;"
KV_KEY_STYLE = "color:#9e9e9e;"
WARN_STYLE = (
    "padding:8px 10px;background:#fff3cd;border-radius:6px;"
    "font-size:13px;color:#856404;margin:6px 0;"
)
DANGER_STYLE = (
    "padding:8px 10px;background:#f8d7da;border-radius:6px;"
    "font-size:13px;color:#721c24;margin:6px 0;"
)
SUCCESS_STYLE = (
    "padding:8px 10px;background:#d4edda;border-radius:6px;"
    "font-size:13px;color:#155724;margin:6px 0;"
)
MUTED_STYLE = "color:#9e9e9e;font-size:13px;"
BODY_STYLE = "margin-bottom:3px;font-size:14px;color:#343a40;"
COL_STYLE = "display:flex;gap:8px;font-size:13px;font-family:monospace;"
COL_ITEM_STYLE = "flex:1;white-space:pre;"


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

        @command("猫图", help="随机猫图")
        async def cat_image_cmd(cmd_event):
            categories = list(self.image_categories.keys())
            category = random.choice(categories)
            url = await self._fetch_image(category)
            if url:
                await self._send_reply(cmd_event, "随机猫图", image_url=url)
            else:
                await self._send_reply(cmd_event, "获取图片失败~")

        self.logger.info("NekoCare 模块加载成功")

    async def on_unload(self, event):
        self.logger.info("NekoCare 模块已卸载")

    # ================================================================
    #  菜单处理
    # ================================================================

    async def _handle_main_menu(self, event):
        user_id = event.get_user_id()

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
                    header = "欢迎来到猫猫世界!"

                menu = f"{header}\n\n1. 领养一只猫猫\n0. 退出"
                await self._send_reply(event, menu)

                reply = await event.wait_reply(timeout=60)
                if not reply:
                    break
                choice = reply.get_text().strip()

                if choice == "0":
                    await self._send_reply(event, "下次再来玩哦~")
                    break
                elif choice == "1":
                    if cat_data is not None and status == "dead":
                        self.sdk.storage.delete(f"nekocare:{user_id}")
                    success = await self._handle_adopt(event)
                    if not success:
                        continue
                else:
                    await self._send_reply(event, "无效选项，请重新选择")

            elif status == "critical":
                critical_hours = self._get_critical_remaining(cat_data)
                menu = (
                    f"[{cat_data['name']}] 在宠物医院!  金币:{coins}\n\n"
                    f"!! 猫猫饿晕了! 剩余 {critical_hours} 小时 !!\n"
                    f"请尽快急救!\n\n"
                    f"1. 急救抢救 ({RESCUE_COST}金币)\n"
                    f"2. 查看状态\n"
                    f"3. 背包/商城\n"
                    f"0. 退出"
                )
                await self._send_reply(event, menu)

                reply = await event.wait_reply(timeout=60)
                if not reply:
                    break
                choice = reply.get_text().strip()

                if choice == "0":
                    await self._send_reply(event, "下次再来玩哦~")
                    break
                elif choice == "1":
                    await self._handle_rescue(event, user_id)
                elif choice == "2":
                    await self._handle_status(event, cat_data, user_id)
                elif choice == "3":
                    await self._handle_bag_menu(event, user_id)
                else:
                    await self._send_reply(event, "无效选项，请重新选择")

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

                reply = await event.wait_reply(timeout=60)
                if not reply:
                    break
                choice = reply.get_text().strip()

                if choice == "0":
                    await self._send_reply(event, "下次再来玩哦~")
                    break
                elif choice == "1":
                    await self._handle_unfoster(event, user_id, cat_data)
                elif choice == "2":
                    await self._handle_status(event, cat_data, user_id)
                elif choice == "3":
                    await self._handle_bag_menu(event, user_id)
                else:
                    await self._send_reply(event, "无效选项，请重新选择")

            else:
                fullness = cat_data["fullness"]
                fl, fc = self._get_stat_style("fullness", fullness)
                menu = (
                    f"[{cat_data['name']}] 今天做什么呢?\n\n"
                    f"饱食度: {fl}  金币:{coins}\n\n"
                    f"1. 查看状态\n"
                    f"2. 去打工\n"
                    f"3. 抓别的猫来打工\n"
                    f"4. 喂食/互动\n"
                    f"5. 背包/商城\n"
                    f"6. 寄养猫猫\n"
                    f"7. 其他设置\n"
                    f"0. 退出"
                )
                await self._send_reply(event, menu)

                reply = await event.wait_reply(timeout=60)
                if not reply:
                    break
                choice = reply.get_text().strip()

                if choice == "0":
                    await self._send_reply(event, "下次再来玩哦~")
                    break
                elif choice == "1":
                    await self._handle_status(event, cat_data, user_id)
                elif choice == "2":
                    await self._handle_work(event, user_id)
                elif choice == "3":
                    await self._handle_catch(event, user_id)
                elif choice == "4":
                    await self._handle_feed_menu(event, user_id)
                elif choice == "5":
                    await self._handle_bag_menu(event, user_id)
                elif choice == "6":
                    await self._handle_foster(event, user_id, cat_data)
                elif choice == "7":
                    await self._handle_settings_menu(event, user_id, cat_data)
                else:
                    await self._send_reply(event, "无效选项，请重新选择")

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
            menu = (
                f"喂食 / 互动\n\n"
                f"饱食度: {fl}\n\n"
                f"1. 喂食 (今日剩余{feed_left}次)\n"
                f"2. 贴贴\n"
                f"3. 摸摸\n"
                f"0. 返回"
            )
            await self._send_reply(event, menu)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                return
            choice = reply.get_text().strip()

            if choice == "0":
                return
            elif choice == "1":
                await self._do_feed(event, user_id, cat_data)
            elif choice == "2":
                await self._do_cuddle(event, user_id, cat_data)
            elif choice == "3":
                await self._do_pat(event, user_id, cat_data)
            else:
                await self._send_reply(event, "无效选项")

    async def _handle_bag_menu(self, event, user_id):
        while True:
            coins = self._get_coins(user_id)
            bag_text = self._build_bag_display(user_id, coins)

            actions = "\n1.使用道具  2.前往商城  3.查看增益  4.查看头衔\n0. 返回"
            full = f"{bag_text}{actions}"
            await self._send_reply(event, full)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                return
            choice = reply.get_text().strip()

            if choice == "0":
                return
            elif choice == "1":
                await self._handle_use_item(event, user_id)
            elif choice == "2":
                await self._handle_shop_menu(event, user_id)
            elif choice == "3":
                await self._show_buffs(event, user_id)
            elif choice == "4":
                await self._handle_titles(event, user_id)
            else:
                await self._send_reply(event, "无效选项")

    async def _handle_shop_menu(self, event, user_id):
        while True:
            coins = self._get_coins(user_id)
            shop_text = self._build_shop_display(coins)
            shop_text += "\n输入编号购买 | 0 返回"
            await self._send_reply(event, shop_text)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                return
            choice = reply.get_text().strip()

            if choice == "0":
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(SHOP_ITEM_LIST):
                    item_name = SHOP_ITEM_LIST[idx]
                    await self._do_buy(event, user_id, item_name)
                else:
                    await self._send_reply(event, "无效编号")
            except ValueError:
                await self._send_reply(event, "请输入数字编号")

    async def _handle_settings_menu(self, event, user_id, cat_data):
        while True:
            active_title = self._get_active_title(user_id)
            title_text = f" [{active_title}]" if active_title else ""
            menu = (
                f"其他设置\n"
                f"当前猫猫: [{cat_data['name']}]{title_text}\n\n"
                f"1. 改名\n"
                f"2. 查看/设置头衔\n"
                f"3. 弃养猫猫\n"
                f"0. 返回"
            )
            await self._send_reply(event, menu)

            reply = await event.wait_reply(timeout=60)
            if not reply:
                return
            choice = reply.get_text().strip()

            if choice == "0":
                return
            elif choice == "1":
                await self._handle_rename(event, user_id, cat_data)
            elif choice == "2":
                await self._handle_titles(event, user_id)
            elif choice == "3":
                result = await self._handle_abandon(event, user_id, cat_data)
                if result:
                    return
            else:
                await self._send_reply(event, "无效选项")

    async def _handle_use_item(self, event, user_id):
        inventory = self._get_inventory(user_id)
        coins = self._get_coins(user_id)

        available = []
        for i, name in enumerate(SHOP_ITEM_LIST):
            count = inventory.get(name, 0)
            if count > 0:
                item = SHOP_ITEMS[name]
                available.append((i + 1, name, count, item))

        if not available:
            await self._send_reply(event, "背包空空如也~去商城逛逛吧!")
            return

        lines = [f"=== 使用道具 ===  金币:{coins}\n"]
        for idx, name, count, item in available:
            lines.append(f"{idx}. {name}  x{count}  {item['desc']}")
        lines.append("\n输入编号使用 | 0 返回")
        await self._send_reply(event, "\n".join(lines))

        reply = await event.wait_reply(timeout=60)
        if not reply:
            return
        choice = reply.get_text().strip()

        if choice == "0":
            return

        try:
            selected_idx = int(choice)
        except ValueError:
            await self._send_reply(event, "请输入数字编号")
            return

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
                        await self._send_reply(event, "猫猫正在寄养中，无法使用道具")
                        return

                    effect = item["effect"]
                    if "fullness" in effect:
                        cat_data["fullness"] = min(
                            100, cat_data["fullness"] + effect["fullness"]
                        )
                    if "intimacy" in effect:
                        cat_data["intimacy"] = min(
                            100, cat_data["intimacy"] + effect["intimacy"]
                        )

                    if status == "critical" and cat_data["fullness"] > 0:
                        cat_data["status"] = "alive"
                        cat_data["critical_since"] = 0
                        cat_data["last_decay"] = time.time()

                    self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
                    self._remove_inventory(user_id, name, 1)

                    parts = []
                    if "fullness" in effect:
                        parts.append(f"饱食度+{effect['fullness']}")
                    if "intimacy" in effect:
                        parts.append(f"亲密度+{effect['intimacy']}")
                    url = await self._fetch_image("happy")
                    await self._send_reply(
                        event,
                        f"使用了【{name}】! {', '.join(parts)}",
                        image_url=url,
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
                    )
                return

        await self._send_reply(event, "无效编号")

    async def _handle_titles(self, event, user_id):
        titles = self._get_titles(user_id)
        active = self._get_active_title(user_id)

        if not titles:
            await self._send_reply(event, "你还没有获得任何头衔~")
            return

        lines = ["=== 我的头衔 ===\n"]
        for i, title in enumerate(titles, 1):
            marker = " <<" if title == active else ""
            lines.append(f"{i}. {title}{marker}")
        lines.append(f"\n当前佩戴: {active or '无'}")
        lines.append("\n输入编号佩戴 | 0. 取消佩戴 | 其他返回")
        await self._send_reply(event, "\n".join(lines))

        reply = await event.wait_reply(timeout=60)
        if not reply:
            return
        choice = reply.get_text().strip()

        if choice == "0":
            self._set_active_title(user_id, "")
            await self._send_reply(event, "已取消佩戴头衔")
            return

        try:
            idx = int(choice)
            if 1 <= idx <= len(titles):
                self._set_active_title(user_id, titles[idx - 1])
                await self._send_reply(event, f"已佩戴头衔【{titles[idx - 1]}】!")
            else:
                await self._send_reply(event, "无效编号")
        except ValueError:
            pass

    # ================================================================
    #  动作处理
    # ================================================================

    async def _handle_adopt(self, event) -> bool:
        await self._send_reply(event, "请给你的猫猫取个名字（限20字内）：")
        reply = await event.wait_reply(timeout=120)
        if not reply:
            await self._send_reply(event, "领养超时啦~")
            return False

        name = reply.get_text().strip()
        if len(name) > 20:
            await self._send_reply(event, "名字太长了，最多20个字符~")
            return False

        if not name:
            name = f"猫猫_{event.get_user_id()[-4:]}"

        user_id = event.get_user_id()
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
        await self._send_reply(
            event, f"领养成功! [{name}] 来到了你身边~记得每天喂食哦!", image_url=url
        )
        return True

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
            await self._send_reply(event, msg, image_url=url)
        else:
            cat_data["status"] = "dead"
            cat_data["death_cause"] = "starve"
            cat_data["death_time"] = now
            self._add_title(user_id, DEATH_TITLES["starve"])
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
            await self._send_reply(event, msg, image_url=url)

    async def _handle_work(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~")
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
            await self._send_reply(event, "猫猫太饿了，先喂食吧!")
            return

        earnings = random.randint(10, 30)
        fullness_loss = random.randint(10, 20)

        buffs = self._get_buffs(user_id)
        if buffs.get("work_double"):
            earnings *= 2
            buffs["work_double"] = False
            self._set_buffs(user_id, buffs)

        cat_data["fullness"] = max(0, cat_data["fullness"] - fullness_loss)

        if cat_data["fullness"] == 0 and random.random() < 0.2:
            cat_data["status"] = "dead"
            cat_data["death_cause"] = "overwork"
            cat_data["death_time"] = now
            self._add_title(user_id, DEATH_TITLES["overwork"])
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._add_coins(user_id, earnings)
            self._inc_stat(user_id, "work_count")
            self._set_work_cooldown(user_id)
            self._check_achievement_titles(user_id)

            url = await self._fetch_image("cry")
            msg = (
                f"[{cat_data['name']}] 在打工途中因过度劳累倒下了...\n"
                f"它带着赚到的 {earnings} 金币，永远地去了喵星。\n"
                f"获得头衔【{DEATH_TITLES['overwork']}】"
            )
            await self._send_reply(event, msg, image_url=url)
            return

        self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
        self._add_coins(user_id, earnings)
        self._inc_stat(user_id, "work_count")
        self._set_work_cooldown(user_id)
        self._check_achievement_titles(user_id)

        url = await self._fetch_image("happy")
        msgs = [
            f"猫猫打工回来啦! 赚了 {earnings} 金币，消耗 {fullness_loss} 饱食度~",
            f"辛苦打工! {earnings} 金币入袋!",
            f"打工完成! +{earnings} 金币 猫猫有点累呢~",
        ]
        await self._send_reply(event, random.choice(msgs), image_url=url)

    async def _handle_catch(self, event, user_id):
        cat_data, status = self._apply_hunger_decay(user_id)
        if not cat_data:
            await self._send_reply(event, "你还没有猫猫呢~")
            return
        if status == "dead":
            await self._send_dead_message(event, cat_data)
            return
        if status == "critical":
            await self._send_critical_message(event, cat_data)
            return

        await self._send_reply(event, "请 @你想抓的猫猫的主人:")
        reply = await event.wait_reply(timeout=60)
        if not reply:
            return

        args = reply.get_text().strip()
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
            await self._send_reply(event, "你的猫猫太饿了，先喂食!")
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
                died = True

            self.sdk.storage.set(f"nekocare:{target_id}", target_cat)
            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._add_coins(user_id, earnings)
            self._inc_stat(user_id, "catch_count")
            self._set_catch_cooldown(user_id)
            self._check_achievement_titles(user_id)

            if died:
                url = await self._fetch_image("cry")
                msg = (
                    f"成功抓到 [{target_cat['name']}]! 赚了 {earnings} 金币!\n"
                    f"但 [{cat_data['name']}] 因体力不支倒下了...\n"
                    f"获得头衔【{DEATH_TITLES['overwork']}】"
                )
                await self._send_reply(event, msg, image_url=url)
                return

            url = await self._fetch_image("neko")
            msgs = [
                f"成功抓到 [{target_cat['name']}] 打工! +{earnings} 金币!",
                f"[{target_cat['name']}] 被抓去打工啦! 收获 {earnings} 金币!",
            ]
            await self._send_reply(event, random.choice(msgs), image_url=url)
        else:
            my_loss = random.randint(5, 10)
            cat_data["fullness"] = max(0, cat_data["fullness"] - my_loss)

            if cat_data["fullness"] == 0 and random.random() < 0.1:
                cat_data["status"] = "dead"
                cat_data["death_cause"] = "overwork"
                cat_data["death_time"] = now
                self._add_title(user_id, DEATH_TITLES["overwork"])
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
                await self._send_reply(event, msg, image_url=url)
                return

            self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
            self._set_catch_cooldown(user_id)

            url = await self._fetch_image("cry")
            msgs = [
                f"[{target_cat['name']}] 挣脱跑掉了! 还累了 {my_loss} 饱食度~",
                f"抓捕失败! [{target_cat['name']}] 太机灵了!",
            ]
            await self._send_reply(event, random.choice(msgs), image_url=url)

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

        reply = await event.wait_reply(timeout=60)
        if not reply or reply.get_text().strip() != "1":
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

        reply = await event.wait_reply(timeout=60)
        if not reply or reply.get_text().strip() != "1":
            await self._send_reply(event, "已取消")
            return

        if coins < cost:
            await self._send_reply(
                event, f"金币不足! 需要 {cost} 枚，你只有 {coins} 枚"
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
        )

    async def _handle_status(self, event, cat_data, user_id):
        coins = self._get_coins(user_id)
        adopt_days = int((time.time() - cat_data["adopt_time"]) / 86400)
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
            f"饱食度: {fl}",
            f"亲密度: {il}",
            f"金币: {coins} 枚",
            f"今日喂食: {cat_data['feed_count']}/5 次",
        ]

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

        await self._send_reply(event, "\n".join(lines))

    async def _handle_abandon(self, event, user_id, cat_data) -> bool:
        menu = (
            f"!! 确定要弃养 [{cat_data['name']}] 吗? !!\n\n"
            f"这将是不可逆的操作...\n\n"
            f"1. 确认弃养\n"
            f"0. 我再想想"
        )
        await self._send_reply(event, menu)

        reply = await event.wait_reply(timeout=60)
        if not reply or reply.get_text().strip() != "1":
            await self._send_reply(event, "好好珍惜你的猫猫吧~")
            return False

        self._add_title(user_id, ABANDON_TITLE)
        self.sdk.storage.delete(f"nekocare:{user_id}")
        self._check_achievement_titles(user_id)

        url = await self._fetch_image("cry")
        msg = (
            f"你把 [{cat_data['name']}] 送走了...\n"
            f"猫猫回头看了你一眼，眼中满是不解。\n"
            f"获得头衔【{ABANDON_TITLE}】"
        )
        await self._send_reply(event, msg, image_url=url)
        return True

    async def _handle_rename(self, event, user_id, cat_data):
        await self._send_reply(event, "请输入新名字（限20字内）：")
        reply = await event.wait_reply(timeout=120)
        if not reply:
            await self._send_reply(event, "改名超时~")
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
        await self._send_reply(event, random.choice(msgs), image_url=url)

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
            f"猫猫蹭了蹭你，好温暖~",
        ]
        await self._send_reply(event, random.choice(msgs), image_url=url)

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
        await self._send_reply(event, f"猫猫舒服地咕噜咕噜~亲密度+{ig}", image_url=url)

    async def _do_buy(self, event, user_id, item_name):
        item = SHOP_ITEMS[item_name]
        coins = self._get_coins(user_id)

        if coins < item["price"]:
            await self._send_reply(
                event,
                f"金币不足! 【{item_name}】{item['price']}金币，你只有 {coins} 枚",
            )
            return

        self._add_coins(user_id, -item["price"])
        self._add_inventory(user_id, item_name, 1)

        url = await self._fetch_image("happy")
        await self._send_reply(
            event,
            f"购买了【{item_name}】! 已放入背包。\n用「使用道具」来使用它。",
            image_url=url,
        )

    async def _show_buffs(self, event, user_id):
        buffs = self._get_buffs(user_id)
        active = {k: v for k, v in buffs.items() if v}

        if not active:
            await self._send_reply(event, "当前没有活跃的增益效果")
            return

        lines = ["=== 活跃增益 ===\n"]
        for buff_name in active:
            label = self._get_buff_label(buff_name)
            if label:
                lines.append(f"- {label}")
        await self._send_reply(event, "\n".join(lines))

    # ================================================================
    #  饥饿衰减 / 生命系统
    # ================================================================

    def _apply_hunger_decay(self, user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        cat_data = self._get_cat(user_id)
        if not cat_data:
            return None, None

        status = cat_data.get("status", "alive")

        if status == "dead":
            return cat_data, "dead"

        if status == "fostered":
            now = time.time()
            foster_time = cat_data.get("foster_time", now)
            if (now - foster_time) / 86400 > FOSTER_MAX_DAYS:
                cat_data["status"] = "alive"
                cat_data["fullness"] = cat_data.get(
                    "foster_fullness", cat_data["fullness"]
                )
                cat_data["last_decay"] = now
                cat_data.pop("foster_time", None)
                cat_data.pop("foster_fullness", None)
                self.sdk.storage.set(f"nekocare:{user_id}", cat_data)
                return cat_data, "alive"
            return cat_data, "fostered"

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
            event, stories.get(cause, stories["starve"]), image_url=url
        )

    async def _send_critical_message(self, event, cat_data: dict):
        hours = self._get_critical_remaining(cat_data)
        url = await self._fetch_image("cry")
        msg = (
            f"!! [{cat_data['name']}] 饿晕了，被送往宠物医院 !!\n\n"
            f"请 {hours} 小时内使用急救!\n"
            f"急救费用: {RESCUE_COST} 金币 (50%成功率)"
        )
        await self._send_reply(event, msg, image_url=url)

    # ================================================================
    #  存储工具
    # ================================================================

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

    def _check_achievement_titles(self, user_id: str):
        stats = self._get_stats(user_id)
        coins = self._get_coins(user_id)
        cat_data = self._get_cat(user_id)

        if stats.get("work_count", 0) >= 50:
            self._add_title(user_id, "打工狂魔")
        if stats.get("catch_count", 0) >= 20:
            self._add_title(user_id, "捕猫达人")
        if stats.get("rescue_count", 0) >= 5:
            self._add_title(user_id, "神医再世")
        if coins >= 1000:
            self._add_title(user_id, "富可敌国")

        if cat_data and cat_data.get("status") == "alive":
            days = int((time.time() - cat_data["adopt_time"]) / 86400)
            if days >= 30:
                self._add_title(user_id, "好主人")

    # ================================================================
    #  显示工具
    # ================================================================

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
        name_w = max(self._str_width(n) for n in SHOP_ITEM_LIST) + 2

        header = self._pad("=== 背包 ===", 22) + f"金币:{coins}"
        lines = [header, ""]

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

        return "\n".join(lines)

    def _build_shop_display(self, coins: int) -> str:
        name_w = max(self._str_width(n) for n in SHOP_ITEM_LIST) + 2

        header = self._pad("=== 商城 ===", 22) + f"金币:{coins}"
        lines = [header, ""]

        for i, name in enumerate(SHOP_ITEM_LIST):
            item = SHOP_ITEMS[name]
            item_str = self._pad(f"{i + 1}.{name}  {item['price']}金币", name_w + 10)
            lines.append(f"{item_str} {item['desc']}")

        return "\n".join(lines)

    # ================================================================
    #  富文本渲染
    # ================================================================

    def _render_line_html(self, line: str, is_first: bool) -> str:
        stripped = line.strip()
        if not stripped:
            return ""

        if stripped.startswith("===") and stripped.endswith("==="):
            title = stripped.strip("= ").strip()
            return f'<div style="{SUBHEADER_STYLE}">{title}</div>'

        if stripped.startswith("!!") and stripped.endswith("!!"):
            text = stripped.strip("! ").strip()
            return f'<div style="{DANGER_STYLE}">{text}</div>'

        if is_first:
            return f'<div style="{HEADER_STYLE}">{stripped}</div>'

        if stripped.startswith("|"):
            cols = stripped.strip("|").split("|")
            inner = ""
            for col in cols:
                c = col.strip()
                if not c:
                    continue
                inner += f'<div style="{COL_ITEM_STYLE}">{c}</div>'
            return f'<div style="{COL_STYLE}">{inner}</div>' if inner else ""

        if len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in ". ":
            return f'<div style="{ITEM_STYLE}">{stripped}</div>'

        if "|" in stripped and not stripped[0].isdigit():
            cols = stripped.split("|")
            inner = ""
            for col in cols:
                c = col.strip()
                if not c:
                    continue
                inner += f'<div style="{COL_ITEM_STYLE}">{c}</div>'
            return f'<div style="{COL_STYLE}">{inner}</div>' if inner else ""

        if ":" in stripped:
            idx = stripped.index(":")
            key = stripped[:idx].strip()
            val = stripped[idx + 1 :].strip()
            if key and val:
                return (
                    f'<div style="{KV_STYLE}">'
                    f'<span style="{KV_KEY_STYLE}">{key}:</span> {val}'
                    f"</div>"
                )

        return f'<div style="{BODY_STYLE}">{stripped}</div>'

    def _build_html(self, text: str, image_url: Optional[str] = None) -> str:
        raw_lines = text.strip().split("\n")
        html = f'<div style="{MENU_STYLE}">'

        if image_url:
            html += (
                f'<div style="text-align:center;margin-bottom:10px;">'
                f'<img src="{image_url}" style="'
                f"max-width:100%;max-height:300px;"
                f'border-radius:8px;" /></div>'
            )

        for i, raw_line in enumerate(raw_lines):
            rendered = self._render_line_html(raw_line, i == 0)
            if rendered:
                html += rendered

        html += "</div>"
        return html

    def _build_markdown(self, text: str, image_url: Optional[str] = None) -> str:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        md = ""

        for i, line in enumerate(lines):
            s = line.strip()

            if s.startswith("===") and s.endswith("==="):
                title = s.strip("= ").strip()
                md += f"### {title}\n\n"
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

    # ================================================================
    #  基础工具
    # ================================================================

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

    async def _send_reply(self, event, content: str, image_url: Optional[str] = None):
        platform = event.get_platform()
        supported = self._get_supported_methods(platform)

        if image_url:
            if "Html" in supported:
                try:
                    await event.reply(
                        self._build_html(content, image_url), method="HTML"
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"HTML 发送失败: {e}")

            if "Markdown" in supported:
                try:
                    await event.reply(
                        self._build_markdown(content, image_url), method="Markdown"
                    )
                    return
                except Exception as e:
                    self.logger.warning(f"Markdown 发送失败: {e}")

            if "Image" in supported:
                try:
                    await event.reply(image_url, method="Image")
                    await event.reply(content)
                    return
                except Exception as e:
                    self.logger.warning(f"Image 发送失败: {e}")

            await event.reply(content)
        else:
            if "Html" in supported:
                try:
                    await event.reply(self._build_html(content), method="HTML")
                    return
                except Exception as e:
                    self.logger.warning(f"HTML 发送失败: {e}")

            if "Markdown" in supported:
                try:
                    await event.reply(self._build_markdown(content), method="Markdown")
                    return
                except Exception as e:
                    self.logger.warning(f"Markdown 发送失败: {e}")

            await event.reply(content)

    def _get_supported_methods(self, platform: str) -> list:
        if hasattr(self.sdk.adapter, "list_sends"):
            methods = self.sdk.adapter.list_sends(platform)
            return methods
        return []
