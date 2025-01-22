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
# from rctypes import UserData
from consts import OK, OK_BYTES
from manager import RCManager
from pydantic import BaseModel
import tomllib

USER_ID = -1


class UserProfile(BaseModel):
    roleID: int = 10001
    titleID: int = 0
    headID: int = 100010000
    skinID: int = 0
    model: int = 0
    riichi_stick_id: int = 0
    riichi_effect_id: int = 0
    card_back_id: int = 0
    tablecloth_id: int = 0
    special_effect_id: int = 0
    profile_frame_id: int = 0
    game_music_id: int = 0
    match_music_id: int = 0
    riichi_music_id: int = 0
    card_face_id: int = 0
    table_frame_id: int = 0


class UserData(BaseModel):
    index: int = 0
    profiles: list["UserProfile"] = []

    @property
    def skinID(self):
        return self.profiles[self.index].skinID

    @property
    def model(self):
        return self.profiles[self.index].model

    @property
    def roleID(self):
        return self.profiles[self.index].roleID

    @property
    def titleID(self):
        return self.profiles[self.index].titleID

    @property
    def riichi_stick_id(self):
        return self.profiles[self.index].riichi_stick_id + 13 * 1000

    @property
    def riichi_effect_id(self):
        return self.profiles[self.index].riichi_effect_id + 17 * 1000

    @property
    def card_back_id(self):
        return self.profiles[self.index].card_back_id + 14 * 1000

    @property
    def tablecloth_id(self):
        return self.profiles[self.index].tablecloth_id + 15 * 1000

    @property
    def special_effect_id(self):
        return self.profiles[self.index].special_effect_id + 16 * 1000

    @property
    def profile_frame_id(self):
        return self.profiles[self.index].profile_frame_id + 30 * 1000

    @property
    def game_music_id(self):
        return self.profiles[self.index].game_music_id + 18 * 1000

    @property
    def match_music_id(self):
        return self.profiles[self.index].match_music_id + 19 * 1000

    @property
    def riichi_music_id(self):
        return self.profiles[self.index].riichi_music_id + 20 * 1000

    @property
    def card_face_id(self):
        return self.profiles[self.index].card_face_id + 26 * 1000

    @property
    def table_frame_id(self):
        return self.profiles[self.index].table_frame_id + 36 * 1000


# hexyl = Command("hexyl")

manager = RCManager()

data_path = Path("user_data.toml")
assert data_path.exists()


def reload_user_data():
    global user_data
    user_data = UserData.model_validate(
        tomllib.loads(data_path.read_text(encoding="utf-8"))
    )


reload_user_data()
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
            reload_user_data()
            if message.injected:
                return
            for player in data["data"]["players"]:
                if player["user"]["user_id"] != USER_ID:
                    continue
                player_user = player["user"]
                player_user["role_id"] = user_data.roleID
                player_user["skin_id"] = user_data.skinID
                player_user["title_id"] = user_data.titleID
                player_user["model"] = user_data.model
                for key, val in [
                    ("riichi_stick_id", user_data.riichi_stick_id),
                    ("riichi_effect_id", user_data.riichi_effect_id),
                    ("card_back_id", user_data.card_back_id),
                    ("tablecloth_id", user_data.tablecloth_id),
                    ("special_effect_id", user_data.special_effect_id),
                    ("profile_frame_id", user_data.profile_frame_id),
                    ("game_music_id", user_data.game_music_id),
                    ("match_music_id", user_data.match_music_id),
                    ("riichi_music_id", user_data.riichi_music_id),
                    ("card_face_id", user_data.card_face_id),
                    ("table_frame_id", user_data.table_frame_id),
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
        global USER_ID
        if flow.response is None:
            return
        if not flow.response.content:
            return
        resp = flow.response.json()
        if flow.request.path == "/users/emailLogin":
            USER_ID = resp["data"]["user"]["id"]
            manager.userID = USER_ID


# addons = [Websocket(), Http()]
addons = [Websocket(), Http()]
# addons = []
