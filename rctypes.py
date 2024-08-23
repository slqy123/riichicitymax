from pydantic import BaseModel
from collections import defaultdict
from typing import DefaultDict

class UserData(BaseModel):
    USER_ID: int = -1  # will init after 'user/emailLogin'
    roleID: int = 10001
    titleID: int = 0
    headID: int = 100010000
    skinIDs: DefaultDict[int, int] = defaultdict(int)
    models: DefaultDict[int, int] = defaultdict(int)
    equiped_items: DefaultDict[int, int] = defaultdict(int)

    def save_data(self):
        with open("user_data.json", "w") as f:
            print("Saving user data...")
            f.write(self.model_dump_json())

    @property
    def skinID(self):
        return self.skinIDs[self.roleID]

    @skinID.setter
    def skinID(self, value: int):
        self.skinIDs[self.roleID] = value

    @property
    def model(self):
        return self.models[self.roleID]

    @model.setter
    def model(self, value: int):
        self.models[self.roleID] = value


class RCMessage(BaseModel):
    msg_id: int
    msg_type: int
    msg_data: dict


class GameStatus:
    def __init__(self):
        self.uid = -1
        self.seat = -1
        self.tehai = []
        self.tsumo = None

        self.last_dahai_actor = -1

        self.player_list = []
        self.dora_markers = []

        self.is_3p = False
