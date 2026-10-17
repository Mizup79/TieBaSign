# -*- coding:utf-8 -*-
import os
import requests
import hashlib
import time
import copy
import logging
import random

import smtplib
from email.mime.text import MIMEText


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API_URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

ENV = os.environ

HEADERS = {
    'Host': 'tieba.baidu.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
}
SIGN_DATA = {
    '_client_type': '2',
    '_client_version': '9.7.8.0',
    '_phone_imei': '000000000000000',
    'model': 'MI+5',
    "net_type": "1",
}

# VARIABLE NAME
COOKIE = "Cookie"
BDUSS = "BDUSS"
EQUAL = r'='
EMPTY_STR = r''
TBS = 'tbs'
PAGE_NO = 'page_no'
ONE = '1'
TIMESTAMP = "timestamp"
DATA = 'data'
FID = 'fid'
SIGN_KEY = 'tiebaclient!!!'
UTF8 = "utf-8"
SIGN = "sign"
KW = "kw"

s = requests.Session()


def get_tbs(bduss):
    logger.info("获取tbs开始")
    headers = copy.copy(HEADERS)
    headers.update({COOKIE: EMPTY_STR.join([BDUSS, EQUAL, bduss])})
    try:
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    except Exception as e:
        logger.error("获取tbs出错" + e)
        logger.info("重新获取tbs开始")
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json()[TBS]
    logger.info("获取tbs结束")
    return tbs


def get_favorite(bduss):
    logger.info("获取关注的贴吧开始")
    # 客户端关注的贴吧
    returnData = {}
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error("获取关注的贴吧出错" + e)
        return []
    returnData = res
    if 'forum_list' not in returnData:
        returnData['forum_list'] = []
    if res['forum_list'] == []:
        return {'gconforum': [], 'non-gconforum': []}
    if 'non-gconforum' not in returnData['forum_list']:
        returnData['forum_list']['non-gconforum'] = []
    if 'gconforum' not in returnData['forum_list']:
        returnData['forum_list']['gconforum'] = []
    while 'has_more' in res and res['has_more'] == '1':
        i = i + 1
        data = {
            'BDUSS': bduss,
            '_client_type': '2',
            '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0',
            '_phone_imei': '000000000000000',
            'from': '1008621y',
            'page_no': str(i),
            'page_size': '200',
            'model': 'MI+5',
            'net_type': '1',
            'timestamp': str(int(time.time())),
            'vcode_tag': '11',
        }
        data = encodeData(data)
        try:
            res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        except Exception as e:
            logger.error("获取关注的贴吧出错" + e)
            continue
        if 'forum_list' not in res:
            continue
        if 'non-gconforum' in res['forum_list']:
            returnData['forum_list']['non-gconforum'].append(res['forum_list']['non-gconforum'])
        if 'gconforum' in res['forum_list']:
            returnData['forum_list']['gconforum'].append(res['forum_list']['gconforum'])

    t = []
    for i in returnData['forum_list']['non-gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    for i in returnData['forum_list']['gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    logger.info("获取关注的贴吧结束")
    return t


def encodeData(data):
    s = EMPTY_STR
    keys = data.keys()
    for i in sorted(keys):
        s += i + EQUAL + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({SIGN: str(sign)})
    return data


# 贴吧把「今天已经签过了」也放在 error_code 里回，但它不是失败
ALREADY_SIGNED_CODE = '160002'


def sign_status(res):
    # 缺省或 0 视为签到成功，160002 视为今日已签过，其余才算失败
    code = str(res.get('error_code', ''))
    if code in ('', '0'):
        return 'ok'
    if code == ALREADY_SIGNED_CODE:
        return 'already'
    return 'failed'


def client_sign(bduss, tbs, fid, kw):
    # 客户端签到
    logger.info("开始签到贴吧：" + kw)
    data = copy.copy(SIGN_DATA)
    data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
    data = encodeData(data)
    try:
        res = s.post(url=SIGN_URL, data=data, timeout=5).json()
    except Exception as e:
        logger.error(f"签到贴吧：{kw} 请求异常：{e}")
        return {'error_code': 'request_failed', 'error_msg': str(e)}
    status = sign_status(res)
    if status == 'ok':
        gain = res.get('gain_score') or res.get('sign_num') or ''
        logger.info(f"签到成功：{kw}" + (f"，本次获得 {gain}" if gain else ''))
    elif status == 'already':
        logger.info(f"今日已签过：{kw}（跳过）")
    else:
        logger.warning(f"签到失败：{kw} error_code={res.get('error_code')} error_msg={res.get('error_msg')}")
    return res

def send_email(sign_list):
    if ('HOST' not in ENV or 'FROM' not in ENV or 'TO' not in ENV or 'AUTH' not in ENV):
        logger.error("未配置邮箱")
        return
    HOST = ENV['HOST']
    FROM = ENV['FROM']
    TO = ENV['TO'].split('#')
    AUTH = ENV['AUTH']
    length = len(sign_list)
    subject = f"{time.strftime('%Y-%m-%d', time.localtime())} 签到{length}个贴吧"
    body = """
    <style>
    .child {
      background-color: rgba(173, 216, 230, 0.19);
      padding: 10px;
    }

    .child * {
      margin: 5px;
    }
    </style>
    """
    for i in sign_list:
        body += f"""
        <div class="child">
            <div class="name"> 贴吧名称: { i['name'] }</div>
            <div class="slogan"> 贴吧简介: { i['slogan'] }</div>
        </div>
        <hr>
        """
    msg = MIMEText(body, 'html', 'utf-8')
    msg['subject'] = subject
    smtp = smtplib.SMTP()
    smtp.connect(HOST)
    smtp.login(FROM, AUTH)
    smtp.sendmail(FROM, TO, msg.as_string())
    smtp.quit()

def main():
    if ('BDUSS' not in ENV):
        logger.error("未配置BDUSS")
        return
    b = ENV['BDUSS'].split('#')
    counter = {'ok': 0, 'already': 0, 'failed': 0}
    failed = []
    for n, i in enumerate(b):
        logger.info("开始签到第" + str(n) + "个用户" + i)
        tbs = get_tbs(i)
        favorites = get_favorite(i)
        for j in favorites:
            time.sleep(random.randint(1,5))
            status = sign_status(client_sign(i, tbs, j["id"], j["name"]))
            counter[status] += 1
            if status == 'failed':
                failed.append(j["name"])
        logger.info(f"第{n}个用户签到汇总：共{len(favorites)}个，成功{counter['ok']}个，已签过{counter['already']}个，失败{counter['failed']}个")
        logger.info("完成第" + str(n) + "个用户签到")
    # send_email(favorites)
    logger.info(f"总计{len(b)}个账号，共{sum(counter.values())}个贴吧，成功{counter['ok']}个，已签过{counter['already']}个，失败{counter['failed']}个")
    if failed:
        logger.warning("失败的贴吧：" + "、".join(failed))
    logger.info("所有用户签到结束")


if __name__ == '__main__':
    main()
