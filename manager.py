import json
import queue
import threading
import sh

from rctypes import GameStatus
from mjai.player import MjaiPlayerClient
from logger import logger

from consts import CARD2MJAI


class RCManager:
    def __init__(self):
        self.userID = -1
        self.status = GameStatus()

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
        assert self.userID != -1
        self.status.userID = self.userID
        players = data["players"]
        if data["options"]["player_count"] == 3:
            self.status.is_3p = True
        for player in players:
            position_at = player["position_at"]
            userID = player["user"]["user_id"]
            self.status.seat2id[position_at] = userID
            if userID == self.status.userID:
                self.status.seat = position_at
                self.mjai_msgs.append({"type": "start_game", "id": position_at})
        assert self.status.seat >= 0
        self.mjai_player.launch_bot(self.status.seat, self.status.is_3p)

    def handle_game_start(self, data: dict):
        bakaze = CARD2MJAI[data["quan_feng"]]
        dora_marker = CARD2MJAI[data["bao_pai_card"]]
        kyoku = data["dealer_pos"] + 1  # data['chang_ci'] ?
        honba = data["ben_chang_num"]
        kyotaku = data["li_zhi_bang_num"]
        oya = data["dealer_pos"]
        scores = [player["hand_points"] for player in data["user_info_list"]]
        if self.status.is_3p:
            scores.append(0)
        tehais = [["?"] * 13 for _ in range(4)]
        if len(data["hand_cards"]) == 14:
            my_tehai = data["hand_cards"][:13]
            my_tsumo = data["hand_cards"][13]
        else:
            my_tehai = data["hand_cards"]
            my_tsumo = None
        my_tehai = [CARD2MJAI[card] for card in my_tehai]
        self.status.tehai = my_tehai  # TODO 似乎无用
        tehais[self.status.seat] = my_tehai
        self.mjai_msgs.append(
            {
                "type": "start_kyoku",
                "bakaze": bakaze,
                "dora_marker": dora_marker,
                "kyoku": kyoku,
                "honba": honba,
                "kyotaku": kyotaku,
                "oya": oya,
                "scores": scores,
                "tehais": tehais,
            }
        )
        self.status.dora_markers = []
        self.status.tsumo = my_tsumo
        if my_tsumo is not None:
            my_tsumo = CARD2MJAI[my_tsumo]
            self.mjai_msgs.append(
                {
                    "type": "tsumo",
                    "actor": self.status.seat,
                    "pai": my_tsumo,
                }
            )
            if len(self.mjai_msgs) > 0:
                self.react()
                # logger.warning(f"MJAI <- {self.mjai_msgs}")
                # logger.error(f"MJAI -> {self.react()}")
        else:
            self.mjai_msgs.append(
                {
                    "type": "tsumo",
                    "actor": oya,
                    "pai": "?",
                }
            )

    def handle_in_card_brc(self, data: dict):
        actor = self.status.seat2id.index(data["user_id"])
        pai = CARD2MJAI[data["card"]]
        self.mjai_msgs.append(
            {
                "type": "tsumo",
                "actor": actor,
                "pai": pai,
            }
        )

    def handle_game_action_brc(self, data: dict):
        action_info = data["action_info"]
        for action in action_info:
            match action["action"]:
                case 2 | 3 | 4:
                    # chi_low, chi_mid, chi_high
                    actor = self.status.seat2id.index(action["user_id"])
                    target = (actor - 1) % 4
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append(
                        {
                            "type": "chi",
                            "actor": actor,
                            "target": target,
                            "pai": pai,
                            "consumed": consumed,
                        }
                    )
                case 5:
                    actor = self.status.seat2id.index(action["user_id"])
                    target = self.status.last_dahai_actor
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append(
                        {
                            "type": "pon",
                            "actor": actor,
                            "target": target,
                            "pai": pai,
                            "consumed": consumed,
                        }
                    )
                case 6:
                    actor = self.status.seat2id.index(action["user_id"])
                    target = self.status.last_dahai_actor
                    pai = CARD2MJAI[action["card"]]
                    consumed = [CARD2MJAI[card] for card in action["group_cards"]]
                    self.mjai_msgs.append(
                        {
                            "type": "daiminkan",
                            "actor": actor,
                            "target": target,
                            "pai": pai,
                            "consumed": consumed,
                        }
                    )
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
                    self.mjai_msgs.append(
                        {
                            "type": "end_kyoku",
                        }
                    )
                case 8:
                    actor = self.status.seat2id.index(action["user_id"])
                    # consumed = [CARD2MJAI[action["card"]]] * 4
                    # if consumed[0] in ["5m", "5p", "5s"]:
                    #     consumed[0] += "r"
                    card = CARD2MJAI[action["card"]]
                    if card.startswith("5"):
                        consumed = [card[:2]] * 4
                        consumed[0] += "r"
                    else:
                        consumed = [card] * 4
                    self.mjai_msgs.append(
                        {
                            "type": "ankan",
                            "actor": actor,
                            "consumed": consumed,
                        }
                    )
                case 9:
                    actor = self.status.seat2id.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]]
                    consumed = [pai] * 3
                    if pai in ["5m", "5p", "5s"]:
                        consumed[0] += "r"
                    self.mjai_msgs.append(
                        {
                            "type": "kakan",
                            "actor": actor,
                            "pai": pai,
                            "consumed": consumed,
                        }
                    )
                case 10:
                    # tsumo ron
                    self.mjai_msgs.append(
                        {
                            "type": "end_kyoku",
                        }
                    )
                case 11:
                    actor = self.status.seat2id.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]]
                    tsumogiri = (
                        action["move_cards_pos"][0] == 14
                        if action.get("move_cards_pos") is not None
                        else True
                    )  # 自动打牌的情况下，move_cards_pos不存在
                    if action["is_li_zhi"] and actor != self.status.seat:
                        self.mjai_msgs.append(
                            {
                                "type": "reach",
                                "actor": actor,
                            }
                        )
                    self.mjai_msgs.append(
                        {
                            "type": "dahai",
                            "actor": actor,
                            "pai": pai,
                            "tsumogiri": tsumogiri,
                        }
                    )
                    self.status.last_dahai_actor = actor
                    # move to handle_li_zhi_brc
                    # if action["is_li_zhi"]:
                    #     self.mjai_msgs.append(
                    #         {
                    #             "type": "reach_accepted",
                    #             "actor": actor,
                    #         }
                    #     )
                    if len(self.status.dora_markers) > 0:
                        for dora_marker in self.status.dora_markers:
                            self.mjai_msgs.append(
                                {
                                    "type": "dora",
                                    "dora_marker": dora_marker,
                                }
                            )
                        self.status.dora_markers = []
                case 12:
                    # ryukyoku
                    self.mjai_msgs.append(
                        {
                            "type": "end_kyoku",
                        }
                    )
                case 13:
                    actor = self.status.seat2id.index(action["user_id"])
                    pai = CARD2MJAI[action["card"]]  # Must be "N"
                    self.mjai_msgs.append(
                        {
                            "type": "nukidora",
                            "actor": actor,
                            "pai": pai,
                        }
                    )
                case _:
                    pass

    def handle_li_zhi_brc(self, data: dict):
        actor = self.status.seat2id.index(data["user_id"])
        self.mjai_msgs.append(
            {
                "type": "reach_accepted",
                "actor": actor,
            }
        )

    def handle_send_current_action(self, data: dict):
        pai = CARD2MJAI[data["in_card"]]
        if pai != "?":  # 庄家第一巡不摸牌，此时in_card=0
            self.mjai_msgs.append(
                {
                    "type": "tsumo",
                    "actor": self.status.seat,
                    "pai": pai,
                }
            )
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
        # TODO 一番街里好像不管怎么杠都是先翻宝牌
        dora_marker = CARD2MJAI[data["cards"][-1]]
        self.status.dora_markers.append(dora_marker)

    def handle_room_end(self, data: dict):
        self.mjai_msgs.append(
            {
                "type": "end_game",
            }
        )
        self.mjai_player.delete_bot()
        self.mjai_msgs = []
        self.status = GameStatus()

    def parse(self, item: dict):
        assert "cmd" in item and "data" in item
        cmd: str = item["cmd"]
        assert cmd.startswith("cmd_")
        func = "handle" + cmd[3:]
        if hasattr(self, func):
            logger.debug(f"Handle cmd {cmd}")
            getattr(self, func)(item["data"])
        else:
            logger.debug(f"Ignore cmd: {cmd}")

        return

    def react(self):
        out = self.mjai_player.react(
            str(self.mjai_msgs)
            .replace("'", '"')
            .replace("True", "true")
            .replace("False", "false")
        )
        self.mjai_msgs = []
        json_out = json.loads(out)
        if json_out["type"] == "reach":
            reach = [
                {
                    "type": "reach",
                    "actor": self.status.seat,
                }
            ]
            out = self.mjai_player.react(str(reach).replace("'", '"'))
            json_out = json.loads(out)
            json_out["type"] = "reach"
        notify(json_out)
        return json_out

TILE_LIST = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C", 
    "5mr", "5pr", "5sr"
]

TILE_LIST_CN = [
        "一万", "二万", "三万", "四万", "五万", "六万", "七万", "八万", "九万",
        "一饼", "二饼", "三饼", "四饼", "五饼", "六饼", "七饼", "八饼", "九饼",
        "一索", "二索", "三索", "四索", "五索", "六索", "七索", "八索", "九索",
        "东",  "南",  "西",  "北",  "白",  "发",  "中",
        "赤五萬", "赤五饼", "赤五索"
        ]

TILE_2_CN = dict(zip(TILE_LIST, TILE_LIST_CN))
def notify(msg: dict):
    content = ''
    type_ = msg.get('type') or ''
    if msg.get('type') == 'reach':
        content += '[立直]'
    elif type_ == '':
        content += '跳过'
    elif type_ == 'dahai':
        if msg['tsumogiri']:
            content += '摸切'
        else:
            content += '切'
    elif type_ == 'chi':
        content += '吃'
    elif type_ == 'pon':
        content += '碰'
    elif type_ in ('kakan', 'ankan', 'daiminkan'):
        content += '杠'
    elif type_ == 'none':
        return msg
    else:
        content += type_
    content += ' '


    pai = msg.get('pai') or ''
    content += TILE_2_CN.get(pai, '')

    if msg.get('type') == 'chi':
        content += ' '
        content += '使用 '
        consumed = msg.get('consumed') or []
        content += ' '.join([TILE_2_CN.get(p, '') for p in consumed]) or ''
        # content += '| '
    sh.Command('notify-send')(content, r=29480, a='mjai')

