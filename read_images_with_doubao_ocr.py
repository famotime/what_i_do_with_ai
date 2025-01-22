"""
使用火山引擎OCR模型识别图片中的文字
"""
from pathlib import Path
import base64
import requests
import json
from datetime import datetime
import hmac
import hashlib
from urllib.parse import urlencode

class VolcengineOCR:
    def __init__(self, access_key_id, access_key_secret):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.host = "visual.volcengineapi.com"
        self.endpoint = f"https://{self.host}"
        self.region = "cn-north-1"
        self.service = "cv"

    def _get_canonical_headers(self, content_type):
        """生成规范化请求头"""
        headers = {
            "content-type": content_type,
            "host": self.host,
        }
        return headers

    def _get_signature(self, date_stamp, headers, canonical_request):
        """计算签名"""
        algorithm = "HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/request"

        # 1. 使用原始的 Secret Key，不需要 base64 解码
        secret_key = self.access_key_secret

        # 2. 构建待签字符串
        string_to_sign = (
            f"{algorithm}\n"
            f"{headers.get('x-date')}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # 3. 派生签名密钥
        k_secret = secret_key.encode('utf-8')
        k_date = hmac.new(k_secret, date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, self.region.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, self.service.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()

        # 4. 计算最终签名
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature, credential_scope, ";".join(sorted(headers.keys()))

    def read_image(self, image_path):
        """读取本地图片并进行OCR识别"""
        # 读取图片并转换为base64
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"找不到图片文件: {image_path}")

        with open(img_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()

        # 准备请求参数
        content_type = "application/x-www-form-urlencoded"
        headers = self._get_canonical_headers(content_type)

        # 添加时间戳
        timestamp = datetime.utcnow()
        headers["x-date"] = timestamp.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = timestamp.strftime("%Y%m%d")

        # 分离query参数和body参数
        query_params = {
            "Action": "OCRNormal",
            "Version": "2020-08-26"
        }

        body_params = {
            "image_base64": image_base64
        }

        # 计算请求体的哈希值并添加到头部
        encoded_data = urlencode(body_params)
        payload_hash = hashlib.sha256(encoded_data.encode('utf-8')).hexdigest()
        headers["x-content-sha256"] = payload_hash

        # 生成规范化请求
        canonical_uri = "/"
        canonical_querystring = "&".join([f"{k}={v}" for k, v in sorted(query_params.items())])
        canonical_headers = "\n".join([f"{k}:{v}" for k, v in sorted(headers.items())]) + "\n"
        signed_headers = ";".join(sorted(headers.keys()))

        canonical_request = (
            f"POST\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # 计算签名
        signature, credential_scope, signed_headers = self._get_signature(
            date_stamp, headers, canonical_request
        )

        # 修正：确保 authorization header 格式正确，不包含多余的空格和换行
        authorization = (
            f"HMAC-SHA256 "
            f"Credential={self.access_key_id}/{credential_scope},"
            f"SignedHeaders={signed_headers},"
            f"Signature={signature}"
        ).replace(" ,", ",")  # 移除逗号前的空格

        # 添加授权头
        headers["authorization"] = authorization

        # 添加调试信息
        # print("=== 调试信息 ===")
        # print(f"Final Authorization: {authorization}")
        # print("==============")

        # 发送请求
        try:
            url = f"{self.endpoint}?{canonical_querystring}"
            headers['content-length'] = str(len(encoded_data))

            # 打印完整请求信息
            # print("=== 最终请求信息 ===")
            # print(f"URL: {url}")
            # print("Headers:")
            # for k, v in sorted(headers.items()):
            #     print(f"{k}: {v}")
            # print(f"Body Length: {len(encoded_data)}")
            # print("==================")

            response = requests.post(
                url,
                headers=headers,
                data=encoded_data
            )
            result = response.json()
            # print(f"API响应: {result}")

            if 'ResponseMetadata' in result and 'Error' in result['ResponseMetadata']:
                error = result['ResponseMetadata']['Error']
                raise Exception(f"OCR识别失败: {error.get('Message', '未知错误')}")

            if result.get("code") == 10000:
                return result["data"]["line_texts"]
            else:
                raise Exception(f"OCR识别失败: {result.get('message', '未知错误')}")

        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")


def read_account(account_path, service):
    """从json文件读取帐号秘钥信息"""
    with open(account_path) as f:
        web_accounts = json.load(f)
    huoshan_account = web_accounts[service]
    return huoshan_account['AccessKeyId'], huoshan_account['SecretAccessKey']


if __name__ == "__main__":
    account_path = "../account/web_accounts.json"
    access_key_id, access_key_secret = read_account(account_path, "huoshan")

    ocr = VolcengineOCR(access_key_id, access_key_secret)

    # 指定图片路径
    image_path = r"H:\个人图片及视频\待整理\Hisense A2T相册\截屏录屏\2021年03月\Screenshot_20210308-185251_Chrome.png"

    try:
        result = ocr.read_image(image_path)
        print("识别结果:")
        for line in result:
            print(line)
    except Exception as e:
        print(f"错误: {str(e)}")
