import json
import queue
import threading

from rctypes import GameStatus
from mjai.player import MjaiPlayerClient
from logger import logger

from consts import CARD2MJAI



class RCManager:
    def __init__(self, userID: int):
        self.game_status = GameStatus()
        self.game_status.uid = userID


        self.mjai_msgs = []
        self.mjai_player = MjaiPlayerClient()

        self.q: queue.Queue[dict] = queue.Queue()
        self.running = True
        self.t = threading.Thread(target=self.run)
        self.t.start()

    def run(self):
        while self.running:
            try:
                item = self.q.get(timeout=1)
                self.parse(item)
                self.q.task_done()
            except queue.Empty:
                pass

    def put(self, item):
        self.q.put(item)

    def stop(self):
        self.running = False
        self.t.join()

    def __del__(self):
        self.stop()

    def handle_enter_room(self, data: dict):
        players = data["players"]
        if data["options"]["player_count"] == 3:
            self.game_status.is_3p = True
        for idx, player in enumerate(players):
            self.game_status.player_list.append(player["user"]["user_id"])
            if player["user"]["user_id"] == self.game_status.uid:
                position_at = player['position_at']
                self.game_status.seat = position_at
                self.mjai_msgs.append({"type": "start_game", "id": position_at})
                self.mjai_player.launch_bot(position_at, self.game_status.is_3p)
        if self.game_status.is_3p:
            self.game_status.player_list.append(-1)

    def handle_game_start(self, data: dict):
        bakaze = CARD2MJAI[data["quan_feng"]]
        dora_marker = CARD2MJAI[data["bao_pai_card"]]
        kyoku = data["dealer_pos"]+1
        honba = data["ben_chang_num"]
        kyotaku = data["li_zhi_bang_num"]
        oya = data["dealer_pos"]
        scores = [player["hand_points"] for player in data["user_info_list"]]
        if self.game_status.is_3p:
            scores.append(0)
        tehais = [["?"]*13 for _ in range(4)]
        if len(data["hand_cards"]) == 14:
            my_tehai = data["hand_cards"][:13]
            my_tsumo = data["hand_cards"][13]
        else:
            my_tehai = data["hand_cards"]
            my_tsumo = None
        my_tehai = [CARD2MJAI[card] for card in my_tehai]
        self.game_status.tehai = my_tehai
        tehais[self.game_status.seat] = my_tehai
        self.mjai_msgs.append({
            "type": "start_kyoku",
            "bakaze": bakaze,
            "dora_marker": dora_marker,
            "kyoku": kyoku,
            "honba": honba,
            "kyotaku": kyotaku,
            "oya": oya,
            "scores": scores,
            "tehais": tehais,
        })
        self.game_status.dora_markers = []
        self.game_status.tsumo = my_tsumo
        if my_tsumo is not None:
            my_tsumo = CARD2MJAI[my_tsumo]
            self.mjai_msgs.append({
                "type": "tsumo",
                "actor": self.game_status.seat,
                "pai": my_tsumo,
            })
            if len(self.mjai_msgs) > 0:
                self.react()
                # logger.warning(f"MJAI <- {self.mjai_msgs}")
                # logger.error(f"MJAI -> {self.react()}")
        else:
            self.mjai_msgs.append({
                "type": "tsumo",
                "actor": oya,
                "pai": "?",
            })

    def handle_in_card_brc(self, data: dict):
        actor = self.game_status.player_list.index(data["user_id"])
        pai = CARD2MJAI[data["card"]]
        self.mjai_msgs.append({
            "type": "tsumo",
            "actor": actor,
            "pai": pai,
        })

    def handle_game_action_brc(self, data: dict):
        action_info = data["action_info"]
        for action in action_info:
            match action["action"]:
                case 2 | 3 | 4:
                    # chi_low, chi_mid, chi_high
                    actor = self.game_status.player_list.index(action["user_id"])
                    target = (actor - 1) % 4
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append({
                        "type": "chi",
                        "actor": actor,
                        "target": target,
                        "pai": pai,
                        "consumed": consumed,
                    })
                case 5:
                    actor = self.game_status.player_list.index(action["user_id"])
                    target = self.game_status.last_dahai_actor
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append({
                        "type": "pon",
                        "actor": actor,
                        "target": target,
                        "pai": pai,
                        "consumed": consumed,
                    })
                case 6:
                    actor = self.game_status.player_list.index(action["user_id"])
                    target = self.game_status.last_dahai_actor
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append({
                        "type": "daiminkan",
                        "actor": actor,
                        "target": target,
                        "pai": pai,
                        "consumed": consumed,
                    })
                case 7:
                    # actor = self.game_status.player_list.index(action["user_id"])
                    # target = self.game_status.last_dahai_actor
                    # pai = CARD2MJAI[action["card"]]
                    # self.mjai_msgs.append({
                    #     "type": "hora",
                    #     "actor": actor,
                    #     "target": target,
                    #     "pai": pai,
                    # })     
                    self.mjai_msgs.append({
                        "type": "end_kyoku",
                    })
                case 8:
                    actor = self.game_status.player_list.index(action["user_id"])
                    consumed = [CARD2MJAI[action["card"]]]*4
                    if consumed[0] in ["5m", "5p", "5s"]:
                        consumed[0] += "r"
                    self.mjai_msgs.append({
                        "type": "ankan",
                        "actor": actor,
                        "consumed": consumed,
                    })
                case 9:
                    actor = self.game_status.player_list.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]]
                    consumed = [pai]*3
                    if pai in ["5m", "5p", "5s"]:
                        consumed[0] += "r"
                    self.mjai_msgs.append({
                        "type": "kakan",
                        "actor": actor,
                        "pai": pai,
                        "consumed": consumed,
                    })
                case 10:
                    # tsumo ron
                    self.mjai_msgs.append({
                        "type": "end_kyoku",
                    })
                case 11:
                    actor = self.game_status.player_list.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]]
                    tsumogiri = action["move_cards_pos"][0] == 14
                    if action["is_li_zhi"]:
                        self.mjai_msgs.append({
                            "type": "reach",
                            "actor": actor,
                        })
                    self.mjai_msgs.append({
                        "type": "dahai",
                        "actor": actor,
                        "pai": pai,
                        "tsumogiri": tsumogiri,
                    })
                    self.game_status.last_dahai_actor = actor
                    if action["is_li_zhi"]:
                        self.mjai_msgs.append({
                            "type": "reach_accepted",
                            "actor": actor,
                        })
                    if len(self.game_status.dora_markers) > 0:
                        for dora_marker in self.game_status.dora_markers:
                            self.mjai_msgs.append({
                                "type": "dora",
                                "dora_marker": dora_marker,
                            })
                        self.game_status.dora_markers = []
                case 12:
                    # ryukyoku
                    self.mjai_msgs.append({
                        "type": "end_kyoku",
                    })
                case 13:
                    actor = self.game_status.player_list.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]] # Must be "N"
                    self.mjai_msgs.append({
                        "type": "nukidora",
                        "actor": actor,
                        "pai": pai,
                    })
                case _:
                    pass
    
    def handle_send_current_action(self, data: dict):
        pai = CARD2MJAI[data["in_card"]]
        if pai != "?":
            self.mjai_msgs.append({
                "type": "tsumo",
                "actor": self.game_status.seat,
                "pai": pai,
            })
        if len(self.mjai_msgs) > 0:
            self.react()
            # logger.warning(f"MJAI <- {self.mjai_msgs}")
            # logger.error(f"MJAI -> {self.react()}")

    def handle_send_other_action(self, data: dict):
        if len(self.mjai_msgs) > 0:
            self.react()
            # logger.warning(f"MJAI <- {self.mjai_msgs}")
            # logger.error(f"MJAI -> {self.react()}")
    def handle_gang_bao_brc(self, data: dict):
        dora_marker = CARD2MJAI[data["cards"][-1]]
        self.game_status.dora_markers.append(dora_marker)

    def handle_room_end(self, data: dict):
        self.mjai_msgs.append({
            "type": "end_game",
        })
        self.mjai_player.delete_bot()
        self.mjai_msgs = []
        self.game_status = GameStatus()


    def parse(self, item: dict):
        assert "cmd" in item and "data" in item
        cmd: str = item["cmd"]
        assert cmd.startswith("cmd_")
        func = getattr(self, 'handle' + cmd[3:])
        if func is not None:
            func(item["data"])


        return
        if "cmd" in item.msg_data:
            match item.msg_data["cmd"]:
                case "cmd_enter_room":
                    pass
                case "cmd_game_start":
                    pass
                case "cmd_in_card_brc":
                    pass
                case "cmd_game_action_brc":
                    pass
                case "cmd_send_current_action":
                    pass
                case "cmd_send_other_action":
                    pass
                case "cmd_gang_bao_brc":
                    pass
                case "cmd_room_end":
                    pass
                case _:
                    pass
            # self.send_mjai(self.mjai_msgs)
        pass

    def react(self):
        out = self.mjai_player.react(str(self.mjai_msgs).replace("\'", "\"").replace("True", "true").replace("False", "false"))
        self.mjai_msgs = []
        json_out = json.loads(out)
        if json_out["type"] == "reach":
            reach = [{
                'type': 'reach',
                'actor': self.game_status.seat,
            }]
            out = self.mjai_player.react(str(reach).replace("\'", "\""))
            json_out = json.loads(out)
            json_out["type"] = "reach"
        logger.info(json_out)
        return json_out
