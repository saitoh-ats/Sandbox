#!/usr/bin/python
# coding:utf-8

import cpickle
import bisect
from pymongo import MongoClient


class BaseInfo:
    def dump_self(self):
        return cpickle.dumps(self)


class ChannelInfo(BaseInfo):
    def __init__(self):
        # {"FF38::1:1": {"datapath1":ChannelSwitchInfoのインスタンス, ... } という形
        self.channel_info = {}
        self.accessor = DatabaseAccessor()

    def add_info(self, mc_addr, data_path, port_no, cid):
        """
          視聴端末を追加。さらに、
            1. ch視聴ユーザが当該swにおける最初の視聴ユーザだった場合、エッジルータへ
               report(ADD_NEW_RESOURCESおよびCHANGE_TO_INCLUDE)を投げる。
               また、エッジSWおよび収容SWへFlowMod
            2. ch視聴ユーザが当該swの当該ポートにおける最初の視聴ユーザだった場合
               (他ポートには既存ユーザがいる)、収容SWへFlowMod
          FlowModは本関数の戻り値で返す？本関数内で送信までやりたくない。もっといえば
          FlowModの組み立ても本関数外でやりたい。BEサービスか品質保証かの判定も外で。
        """

        # チャンネル存在チェック
        if mc_addr not in self.channel_info:
            # 当該チャンネルが存在しない場合
            sw_info = ChannelSwitchInfo(data_path, port_no, cid)
            self.channel_info[mc_addr] = {data_path: sw_info}
            return 2  # エッジSW、収容SW両方へのFlowMod、およびエッジルータへのReport Todo:即値やめろ

        # 当該チャンネルが既に存在する場合
        # DataPath存在チェック
        ch_info = self.channel_info[mc_addr]
        if data_path not in ch_info == False:
            sw_info = ChannelSwitchInfo(data_path, port_no, cid)
            ch_info[data_path] = sw_info
            return 2  # エッジSW、収容SW両方へのFlowMod、およびエッジルータへのReport Todo:即値やめろ

        # 当該チャンネルにこの収容SWの情報がある場合
        ch_sw_info = ch_info[data_path]  # ChannelSwitchInfoクラスのインスタンス
        return ch_sw_info.add_info(port_no, cid)

    def remove_info(self, mc_addr, data_path, port_no, cid):
        """
          視聴端末を削除。さらに、
            1. 当該sw、当該ポートの視聴ユーザが0になった場合、
               収容SWにFlowMod
            2. 当該swの視聴ユーザが0になった場合
               エッジSW、収容SWへFlowMod
               エッジルータへReport(BLOCK_OLD_SOURCES)を投げる
          FlowModは本関数の戻り値で返す？本関数内で送信までやりたくない。もっといえば
          FlowModの組み立ても本関数外でやりたい。BEサービスか品質保証かの判定も外で。
        """

        # チャンネルおよびDataPath存在チェック
        # 存在しなければ何もしない
        if mc_addr not in self.channel_info == False \
           or data_path not in self.channel_info[mc_addr] == False:
            return 0  # FlowModの必要なし Todo: 即値やめろ

        # 存在する場合
        ch_sw_info = channel_info[mc_addr][data_path]
        ret = ch_sw_info.remove_info(port_no_cid)
        if ret == 2:
            # 当該SWの視聴ユーザが0の場合、DataPathに対応する情報を削除する
            channel_info[mc_addr].pop(data_path)

        return ret


class ChannelSwitchInfo(BaseInfo):
    def __init__(self, data_path, port_no=-1, cid=-1):
        self.data_path = data_path
        self.port_info = {}
        if cid != 1:
            self.port_info[port_no] = [cid]

    def add_info(self, port_no, cid):
        # port_infoにユーザ情報を追加
        if port_no in self.port_info:
            # 当該ポートに視聴ユーザが存在する場合
            # 当該CIDが存在しない場合はCIDを追加
            # ソートを維持して挿入しておく(探索時にbinary searchを使いたい)
            cid_list = self.port_info[port_no]
            if self.find(cid_list, cid) == -1:
                pos = bisect.bisect(cid_list, cid)
                bisect.insort(cid_list, cid)
            # Todo: 既にCIDが存在する場合に無視する処理でよいか精査
            return 0  # FlowMod必要なし Todo: 即値やめろ
        else:
            # 当該ポートに視聴ユーザが存在しない場合
            self.port_info[port_no] = [cid]
            return 1  # 収容SWへのFlowModが必要 Todo: 即値やめろ

    def remove_info(self, port_no, cid):
        # port_infoから当該ユーザ情報を検索し削除
        # ch_infoを更新
        #   当該chを視聴しているユーザがいなくなった場合
        if port_no not in self.port_info == False:
            # 当該ポートにユーザがそもそも存在しない場合
            # 何もせず抜ける Todo: 本当にそれでよいか精査
            return 0  # FlowMod必要なし Todo: 即値やめろ

        # 当該ポートにユーザが存在する場合
        # cidを探索し、存在すれば削除
        # ユーザが0になればポート情報も削除
        cid_list = self.port_info[port_no]
        idx = self.find(cid_list, cid)
        if idx == -1:
            # 指定されたCIDが存在しなければ何もせず抜ける Todo: 本当にそれでよいか精査
            return 0  # FlowMod必要なし Todo: 即値やめろ
        cid_list.pop(idx)
        if len(cid_list) == 0:
            self.port_info.pop(port_no)
            return 1  # 収容SWへのFlowModが必要 Todo: 即値やめろ
        if len(self.port_info) == 0:
            return 2  # エッジSW、収容SW両方へのFlowMod、およびエッジルータへのReport Todo:即値やめろ

    """
    ソート済み配列からキー値を探索
    arrayはソート済みであること
    Todo: 共通クラスに移動すべきか検討
    """
    def find(array, value):
        idx = bisect.bisect_left(array, value)
        if idx != len(array) and array[idx] == value:
            return idx
        return -1


class DatabaseAccessor:
    def __init__(self, connect_str):
        self.client = MongoClient(connect_str)
        # Todo: DB名、コレクション名は別途検討
        self.db = self.client.viewerdb
        self.col = self.db.serialized_data

    def insert(key, inserted_obj):
        # Todo: DB上のデータ形式は別途検討
        dump = inserted_obj.dump_self(inserted_obj)
        self.col.update({key: dump})

    def query(key):
        result = self.col.find_one()
        dump = result[key]
        return cpickle.loads(dump)

"""
class UserInfo:
    def __init__(self, port_no=-1):
        self.port_no = port_no
        self.float = float
        self.array = [1, 2, "123"]
        self.dict = {"key1": page(), "key2": page(str="test")}

if '__main__' == __name__:
    a = hoge(int=5)
    b = hoge()
    b.int = 2
    print a.int
    print b.int

    # open mongodb
    client = MongoClient("mongodb://localhost:27017")
    db = client.testdb
    col = db.posts

    # serialize
    dump_a = cpickle.dumps(a)
    dump_b = cpickle.dumps(b)

    c = cpickle.loads(dump_a)

    # insert
    for i in range(0, 10000):
        dict_a = {"switch_name": "s1", "data": dump_a}
        col.update({"switch_name": "s1"}, \
                   {"$set": {"data": dump_a}}, \
                   upsert=True)

    # query
    result = col.find_one({"switch_name": "s1"})
    dump_result = result["data"]
    load_result = cpickle.loads(dump_result)

    # check
    print load_result.int
    print load_result.float
    print load_result.dict["key1"].str
    print load_result.dict["key2"].str
"""
