# -*-encoding:utf-8-*-
import os
import re
import time
import itchat
import sys
from itchat.content import *

reload(sys)
sys.setdefaultencoding('utf8')

# 说明：可以撤回的有文本文字、语音、视频、图片、位置、名片、分享、附件
# 将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理 | 不接受不具有撤回功能的信息
# [TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE]
msg_dict = {}

# 文件存储临时目录
rev_tmp_dir = "./RecordFiles"
if not os.path.exists(rev_tmp_dir): os.mkdir(rev_tmp_dir)

# 表情有一个问题,接受信息和接受note的msg_id不一致
face_bug = None

#记录私聊消息
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO])
def single_receive_msg(msg):
    handler_receive_msg(msg);

#记录群消息
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO], isGroupChat=True)
def group_receive_msg(msg):
    handler_receive_msg(msg);


def handler_receive_msg(msg):
    global face_bug
    # 获取的是本地时间戳并格式化本地时间戳 e: 2017-04-21 21:30:08
    msg_time_rec = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 消息ID
    msg_id = msg['MsgId']
    # 消息时间
    msg_time = msg['CreateTime']
    # 消息发送人昵称 | 这里也可以使用RemarkName备注　但是自己或者没有备注的人为None
    # msg_from = (itchat.search_friends(userName=msg['FromUserName']))["NickName"]
    member = itchat.search_friends(userName=msg['FromUserName']);
    if member == None:
        member = itchat.search_friends(userName=msg['ActualUserName']);
    msg_from = member["NickName"];
    # 消息内容
    msg_content = None
    # 分享的链接
    msg_share_url = None
    if msg['Type'] == 'Text' \
            or msg['Type'] == 'Friends':
        msg_content = msg['Text']
    elif msg['Type'] == 'Recording' \
            or msg['Type'] == 'Attachment' \
            or msg['Type'] == 'Video' \
            or msg['Type'] == 'Picture':
        msg_content = r"" + msg['FileName']
        # 保存文件
        msg['Text'](rev_tmp_dir + msg['FileName'])
    elif msg['Type'] == 'Card':
        msg_content = msg['RecommendInfo']['NickName'] + r" 的名片"
    elif msg['Type'] == 'Map':
        x, y, location = re.search(
            "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
        if location is None:
            msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
        else:
            msg_content = r"" + location
    elif msg['Type'] == 'Sharing':
        msg_content = msg['Text']
        msg_share_url = msg['Url']
    face_bug = msg_content
    # 更新字典
    msg_dict.update(
        {
            msg_id: {
                "msg_from": msg_from, "msg_time": msg_time, "msg_time_rec": msg_time_rec,
                "msg_type": msg["Type"],
                "msg_content": msg_content, "msg_share_url": msg_share_url
            }
        }
    )

#监听私聊消息
@itchat.msg_register([NOTE])
def single_receive_recall_msg(msg):
    handler_recall_msg(msg);

#监听群消息
@itchat.msg_register([NOTE], isGroupChat=True)
def group_receive_recall_msg(msg):
    handler_recall_msg(msg, True);


def handler_recall_msg(msg, isGroupChat=False):
    global face_bug
    cn_search = re.search(r"\<\!\[CDATA\[.*撤回了一条消息.*\]\]\>", msg['Content']);
    en_search = re.search(r"\<\!\[CDATA\[.*recalled a message.*\]\]\>", msg['Content'])
    if (cn_search is not None) or (en_search is not None):
        # 获取消息的id
        old_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msg_dict.get(old_msg_id, {})
        if len(old_msg_id) < 11:
            itchat.send_file(rev_tmp_dir + face_bug, toUserName='filehelper')
            os.remove(rev_tmp_dir + face_bug)
        else:
            groupStr = ' '
            if isGroupChat:
                groupStr = ' 从群'
            msg_body = old_msg.get('msg_time_rec') + "\n" \
                       + old_msg.get('msg_from') + groupStr + "撤回了 " + old_msg.get("msg_type") + " 消息" + "\n" \
                       + r"" + old_msg.get('msg_content')
            # 如果是分享存在链接
            if old_msg['msg_type'] == "Sharing": msg_body += "\n链接地址➣ " + old_msg.get('msg_share_url')

            # 将撤回消息发送到文件助手
            itchat.send(msg_body, toUserName='filehelper')
            # 有文件的话也要将文件发送回去
            if old_msg["msg_type"] == "Picture" \
                    or old_msg["msg_type"] == "Recording" \
                    or old_msg["msg_type"] == "Video" \
                    or old_msg["msg_type"] == "Attachment":
                file = '@fil@%s' % (rev_tmp_dir + old_msg['msg_content'])
                itchat.send(msg=file, toUserName='filehelper')
                os.remove(rev_tmp_dir + old_msg['msg_content'])
            # 删除字典旧消息
            msg_dict.pop(old_msg_id)


if __name__ == '__main__':
    itchat.auto_login(hotReload=True,enableCmdQR=2)
    itchat.run()