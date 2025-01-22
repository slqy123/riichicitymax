from mitmproxy import http, ctx

# from sh import Command
from io import BytesIO
from struct import unpack, pack
import json
from rich import print
from pathlib import Path
from itertools import chain

import sys

sys.path.append(".")
from rctypes import UserData
from consts import OK, OK_BYTES
from manager import RCManager

# hexyl = Command("hexyl")

manager = RCManager()

data_path = Path("user_data.json")
if data_path.exists():
    user_data = UserData.model_validate_json(data_path.read_text(encoding="utf-8"))
else:
    user_data = UserData()

# manager.userID = user_data.USER_ID


class Websocket:
    def websocket_message(self, flow: http.HTTPFlow):
        assert flow.websocket
        # print(flow.request.path)  # 不重要
        message = flow.websocket.messages[-1]
        content = message.content
        content = BytesIO(content)

        length = unpack(">I", content.read(4))[0]
        assert length >= 0x0F
        if length == 0x0F:
            # 空包
            return

        magic = b"\x00\x0f\x00\x01"
        assert content.read(4) == magic  # 应该是magick number?

        index = unpack(">I", content.read(4))[0]  # 一个自增的ID

        n1, n2 = unpack(">HB", content.read(3))  # 不知道是什么意思

        data = json.loads(content.read())
        print(message.from_client, data)
        if not isinstance(data.get("cmd"), str):
            return
        if data.get("uid") is not None:
            print("UID from", data)
        if data["cmd"].startswith("cmd_"):
            manager.put(data)
        if data.get("cmd") == "cmd_enter_room":
            if message.injected:
                return
            for player in data["data"]["players"]:
                if player["user"]["user_id"] != user_data.USER_ID:
                    continue
                player_user = player["user"]
                player_user["role_id"] = user_data.roleID
                player_user["skin_id"] = user_data.skinID
                player_user["title_id"] = user_data.titleID
                player_user["model"] = user_data.model
                for key, val in [
                    ("riichi_stick_id", user_data.equiped_items[13]),
                    ("riichi_effect_id", user_data.equiped_items[17]),
                    ("card_back_id", user_data.equiped_items[14]),
                    ("tablecloth_id", user_data.equiped_items[15]),
                    ("special_effect_id", user_data.equiped_items[16]),
                    ("profile_frame_id", user_data.equiped_items[30]),
                    ("game_music_id", user_data.equiped_items[19]),
                    ("match_music_id", user_data.equiped_items[19]),
                    ("riichi_music_id", user_data.equiped_items[20]),
                    ("card_face_id", user_data.equiped_items[26]),
                    ("table_frame_id", user_data.equiped_items[36]),
                ]:
                    if val:
                        player_user[key] = val
                player_user["model"] = user_data.model
                break
            else:
                assert False
            modified_data = json.dumps(data).encode("utf-8")
            modified_content = (
                pack(">I", len(modified_data) + 0x0F)
                + magic
                + pack(">IHB", index, n1, n2)
                + modified_data
            )
            message.drop()
            ctx.master.commands.call(
                "inject.websocket",
                flow,
                not message.from_client,
                modified_content,
                False,
            )


class Http:
    def response(self, flow: http.HTTPFlow):
        if flow.response is None:
            return
        if not flow.response.content:
            return
        resp = flow.response.json()
        if flow.request.path == "/users/emailLogin":
            user_data.USER_ID = resp["data"]["user"]["id"]
            manager.userID = user_data.USER_ID
            user_data.save_data()


# class Http:
#     def response(self, flow: http.HTTPFlow):
#         # print(flow.request.path)
#         if flow.response is None:
#             return
#         if not flow.response.content:
#             return
#
#         resp = flow.response.json()
#
#         if flow.request.path == "/users/getRoleInfo":
#             roles = resp["data"]["roleList"]
#             # print(roles)
#             for role in roles:
#                 role["isOwn"] = True
#                 role["model"] = user_data.models[role["roleID"]]
#                 role["recentSkinId"] = user_data.skinIDs[role["roleID"]]
#                 role["FeelValue"] = 5000
#                 role["oathValue"] = 5000
#                 role["cultivateStatus"] = 5
#                 role["exp"] = 200
#                 if role.get("taskStatus") is not None:
#                     role["taskStatus"] = 0
#
#             resp["data"]["useModel"] = user_data.model
#             resp["data"]["useRoleID"] = user_data.roleID
#             resp["data"]["useSkinID"] = user_data.skinID
#         elif flow.request.path == "/users/homeUserData":
#             resp["data"]["roleID"] = user_data.roleID
#             resp["data"]["skinID"] = user_data.skinID
#         elif flow.request.path == "/activity/viewAction":
#             # print('resp', flow.request.path, resp)
#             resp = OK
#         elif flow.request.path == "/users/updateRoleInfo":
#             assert flow.response.content == OK_BYTES
#         elif flow.request.path == "/users/getSkinInfo":
#             skins = resp["data"]
#             req_roleID = flow.request.json()["roleID"]
#             for skin in skins:
#                 skin["isOwn"] = True
#                 skin["ownemoticon"] = True
#                 if skin["skinID"] == user_data.skinIDs[req_roleID]:
#                     skin["isRecentWear"] = True
#         elif flow.request.path == "/users/userBaseData":
#             if flow.request.json()["userID"] == user_data.USER_ID:
#                 resp["data"]["roleID"] = user_data.roleID
#                 resp["data"]["skinID"] = user_data.skinID
#                 resp["data"]["model"] = user_data.model
#                 resp["data"]["titleID"] = user_data.titleID
#                 resp["profileFrameID"] = user_data.equiped_items[30]
#         elif flow.request.path == "/users/emailLogin":
#             user_data.USER_ID = resp["data"]["user"]["id"]
#             manager.userID = user_data.USER_ID
#             user_data.save_data()
#         elif flow.request.path == "/backpack/userItemList":
#             resp["data"] = self.extend_items(resp["data"])
#         elif flow.request.path == "backpack/userEquip":
#             for item in resp["data"]:
#                 user_data.equiped_items[item["itemType"]] = (
#                     user_data.equiped_items.get(item["itemType"]) or item["itemID"]
#                 )
#         elif flow.request.path == "/backpack/userProfileFrame":
#             for profile_item in resp["data"]:
#                 assert profile_item["itemType"] == 30
#                 profile_item["isCanEquip"] = True
#                 profile_item["isExpired"] = False
#                 profile_item["num"] = 1
#                 profile_item["isEquip"] = (
#                     False
#                     if user_data.equiped_items[30] != profile_item["itemID"]
#                     else True
#                 )
#             if not user_data.equiped_items[30]:
#                 user_data.equiped_items[30] = resp["data"][0]["itemID"]
#                 resp["data"][0]["isEquip"] = True
#                 user_data.save_data()
#         elif flow.request.path == "/users/getTitleList":
#             for title in resp["data"]:
#                 title["titleState"] = 1  # 1: 拥有, 2: 使用, 3: 未拥有
#                 if title["titleID"] == user_data.titleID:
#                     title["titleState"] = 2
#         elif flow.request.path == "/users/getHeadList":
#             resp["data"] = self.extend_head_list(resp["data"])
#
#         elif flow.request.path == "/lobbys/enterFriendMatch":
#             for player in resp["data"]["players"]:
#                 if player["userID"] != user_data.USER_ID:
#                     continue
#                 player["model"] = user_data.model
#                 player["roleId"] = user_data.roleID  # 小写d，离谱
#                 player["skinId"] = user_data.skinID
#                 player["titleID"] = user_data.titleID
#
#         else:
#             # print('resp', flow.request.path, resp)
#             pass
#
#         flow.response.set_content(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
#
#         # else:
#         #     print(flow.request.path)
#         #     print(resp)
#         # print(flow.response.json())
#
#         # hexyl(_in=message.content, _out=sys.stdout)
#
#     def request(self, flow: http.HTTPFlow):
#         # print(flow.request.method, flow.request.path)
#         # print(flow.request.content)
#         # print(flow.request.json())
#         try:
#             data = flow.request.json() if flow.request.content else {}
#         except json.JSONDecodeError:
#             print("json decode error", flow.request.text)
#             return
#
#         if flow.request.path == "/users/updateRoleInfo":
#             user_data.roleID = data["roleID"]
#             user_data.skinID = data["skinID"]
#             user_data.model = data["model"]
#             user_data.save_data()
#
#             flow.response = http.Response.make(content=OK_BYTES)
#         elif flow.request.path == "/backpack/equipItem":
#             user_data.equiped_items[data["itemID"] // 1000] = data["itemID"]
#             user_data.save_data()
#             flow.response = http.Response.make(content=OK_BYTES)
#         elif flow.request.path == "/users/updateTitle":
#             user_data.titleID = data["titleID"]
#             user_data.save_data()
#             flow.response = http.Response.make(content=OK_BYTES)
#         elif flow.request.path == "/users/updateHead":
#             user_data.headID = data["headID"]
#             user_data.save_data()
#             flow.response = http.Response.make(content=OK_BYTES)
#         elif flow.request.path == "/mixed_client/clearRedDot":
#             flow.response = http.Response.make(content=OK_BYTES)
#
#         # elif flow.request.path == '/backpack/userItemList':
#         #     if flow.is_replay == "request":
#         #         return
#         #     flow_org = flow
#         #     flow = flow.copy()
#         #     flow_org.wait_for_resume
#         #     # Only interactive tools have a view. If we have one, add a duplicate entry
#         #     # for our flow.
#         #     if "view" in ctx.master.addons:
#         #         ctx.master.commands.call("view.flows.duplicate", [flow])
#         #     flow.request.path = "/backpack/userProfileFrame"
#         #     ctx.master.commands.call("replay.client", [flow])
#
#         #     flow_org.intercept()
#         #     self.intercepted_userItem_flow = flow_org
#
#     def extend_items(self, items: list[dict]):
#         def add_item(item_type: int, item_count: int):
#             for item_index in range(item_count):
#                 item_id = item_index + item_type * 1000
#
#                 items_dict[item_id] = {
#                     "createTime": 0,
#                     "expiredAt": 0,
#                     "feelValue": 0,
#                     "giftContent": [],
#                     "isCanEquip": True,
#                     "isEquip": False,
#                     "isExpired": False,
#                     "isLock": False,
#                     "itemID": item_id,
#                     "itemType": item_type,
#                     "label": 0,
#                     "name": "",
#                     "num": 1,
#                     "recycleNum": 0,
#                     "source": 0,
#                 }
#
#         items_dict = {item["itemID"]: item for item in items}
#
#         # 10 道具
#         # 11 礼物
#         # 12 觉醒材料
#         add_item(13, 47)  # 立直棒
#         add_item(14, 195)  # 牌背
#         add_item(15, 113)  # 桌布
#         add_item(16, 20)  # 胡牌特效
#         add_item(17, 10)  # 立直特效
#         add_item(18, 11)  # BGM(大厅)
#         add_item(19, 11)  # BGM(对局中)
#         add_item(20, 9)  # BGM(立直)
#         add_item(24, 7)  # 大厅场景
#         add_item(25, 7)  # 主界面特效
#         add_item(26, 6)  # 牌面
#         # add_item(30, 20)  # 不知道是啥
#         add_item(36, 8)  # 桌框
#
#         # 显示已装备的物品
#         # for _, item_id in user_data.equiped_items.items():
#         #     if item_id in items_dict:
#         #         items_dict[item_id]["isEquip"] = True
#         for item_type in chain(range(13, 21), [24, 25, 26, 30, 36]):
#             if user_data.equiped_items[item_type]:
#                 item = items_dict.get(user_data.equiped_items[item_type])
#                 if item is not None:
#                     item["isEquip"] = True
#             else:
#                 items_dict[item_type * 1000 + 1]["isEquip"] = True
#
#         return list(items_dict.values())
#
#     def extend_head_list(self, head_list):
#         head_dict = {head["headID"]: head for head in head_list}
#         for i in range(1, 100):
#             hid = (10000 + i) * 10000
#             head_dict[hid] = {
#                 "createAt": 0,
#                 "expiredAt": 0,
#                 "headID": hid,
#                 "headState": 1,
#                 "model": 0,
#                 "roleID": 10001,
#                 "skinID": 0,
#                 "type": 3,  # 不知道什么意思
#             }
#         for i in range(1, 20):
#             hid = 37000 + i
#             head_dict[hid] = head_dict[(10000 + i) * 10000] | {"headID": hid}
#         head_dict[user_data.headID]["headState"] = 2
#         return list(head_dict.values())


# addons = [Websocket(), Http()]
addons = [Websocket(), Http()]
# addons = []
