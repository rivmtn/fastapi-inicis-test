import hashlib
import json
import os.path
import random
import string
from base64 import b64encode
from datetime import datetime
from typing import Callable, Annotated, Any
from urllib import parse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from _decimal import Decimal
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import Form
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from pytz import timezone
from starlette.requests import Request
from starlette.responses import JSONResponse

app = FastAPI()

templates = Jinja2Templates(directory="templates")

load_dotenv()
SERVER_IP = os.getenv("SERVER_IP")
SERVER_URL = os.getenv("SERVER_URL")

'''
[테스트 계정 정보]
테스트 MID : INIpayTest
용도 : 일반결제
signkey    : SU5JTElURV9UUklQTEVERVNfS0VZU1RS
INIAPI key : ItEQKi3rY7uvDS8l
INIAPI iv   : HYb3yQ4f65QL89==
모바일 hashkey : 3CB8183A4BE283555ACC8363C0360223
'''

MID = "INIpayTest"
SIGN_KEY = "SU5JTElURV9UUklQTEVERVNfS0VZU1RS"
INI_API_KEY = "ItEQKi3rY7uvDS8l"
INI_API_IV = "HYb3yQ4f65QL89=="

current_milli_time: Callable[[], str] = lambda: str(
    int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000))
sha256_hash: Callable[[str], str] = lambda data: hashlib.sha256(data.encode()).hexdigest()
sha512_hash: Callable[[str], str] = lambda data: hashlib.sha512(data.encode()).hexdigest()
generate_random_string: Callable[[], str] = lambda: ''.join(
    random.choice(string.ascii_letters + string.digits) for _ in range(10))


def aes_128_cbc_encrypt(plain_text, key, iv):
    cipher = AES.new(bytes(key.encode("UTF-8")), AES.MODE_CBC, iv.encode("UTF-8"))
    padded_plain_text = pad(data_to_pad=plain_text.encode("UTF-8"), block_size=AES.block_size)
    encrypted = cipher.encrypt(padded_plain_text)
    return b64encode(encrypted).decode('utf-8')


def get_supply_cost(total_amount: Annotated[Any, lambda x: x.isdecimal()]) -> str:
    return str(round(Decimal(str(total_amount)) * Decimal("0.909")))


def get_tax(total_amount: Annotated[Any, lambda x: x.isdecimal()]) -> str:
    return str(round(Decimal(total_amount) * Decimal("0.091")))

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        name="root.html",
        context=dict(
            request=request,
            SERVER_URL=SERVER_URL,
        )
    )


@app.post("/pay")
async def _(request: Request,
            gopaymethod: str = Form(...),
            price: str = Form(...),
            goodname: str = Form(...),
            buyername: str = Form(...),
            buyertel: str = Form(...),
            buyeremail: str = Form(...)):
    version = "1.0"
    gopaymethod = gopaymethod
    mid = MID
    oid = "ORDER_" + generate_random_string()
    price = price
    timestamp = current_milli_time()
    use_chkfake = "Y"
    signature = sha256_hash(f"oid={oid}&price={price}&timestamp={timestamp}")
    verification = sha256_hash(f"oid={oid}&price={price}&signKey={SIGN_KEY}&timestamp={timestamp}")
    mKey = sha256_hash(SIGN_KEY)
    currency = "WON"
    goodname = goodname
    buyername = buyername
    buyertel = buyertel
    buyeremail = buyeremail
    returnUrl = f"{SERVER_URL}return"
    closeUrlUrl = f"{SERVER_URL}close"
    acceptmethodUrl = "centerCd(Y):HPP(2)"

    return templates.TemplateResponse(
        status_code=200,
        name="pay.html",
        context=dict(
            request=request,
            SERVER_URL=SERVER_URL,
            version=version,
            gopaymethod=gopaymethod,
            mid=mid,
            oid=oid,
            price=price,
            timestamp=timestamp,
            use_chkfake=use_chkfake,
            signature=signature,
            verification=verification,
            mKey=mKey,
            currency=currency,
            goodname=goodname,
            buyername=buyername,
            buyertel=buyertel,
            buyeremail=buyeremail,
            returnUrl=returnUrl,
            closeUrlUrl=closeUrlUrl,
            acceptmethodUrl=acceptmethodUrl,
        )
    )


@app.post(path="/return")
async def _(request: Request,
            resultCode: str = Form(None),
            resultMsg: str = Form(None),
            mid: str = Form(None),
            orderNumber: str = Form(None),
            authToken: str = Form(None),
            idc_name: str = Form(None),
            authUrl: str = Form(None),
            netCancelUrl: str = Form(None),
            charset: str = Form(None),
            merchantData: str = Form(None), ):
    if resultCode != "0000":
        return JSONResponse(status_code=200, content=jsonable_encoder(dict(인증결과="실패")))

    mid = mid
    authToken = authToken
    timestamp = current_milli_time()
    signature = sha256_hash(f"authToken={authToken}&timestamp={timestamp}")
    verification = sha256_hash(f"authToken={authToken}&signKey={SIGN_KEY}&timestamp={timestamp}")
    charset = charset
    format = "JSON"

    response = requests.post(
        url=authUrl,
        headers={"Content-type": "application/x-www-form-urlencoded"},
        data=dict(
            mid=mid,
            authToken=authToken,
            timestamp=timestamp,
            signature=signature,
            verification=verification,
            charset=charset,
            format=format,
        )
    )

    confirm_data = json.loads(response.text)

    return templates.TemplateResponse(
        status_code=200,
        name="return.html",
        context=dict(
            request=request,

            auth_resultCode=resultCode,
            auth_resultMsg=resultMsg,
            auth_mid=mid,
            auth_orderNumber=orderNumber,
            auth_authToken=authToken,
            auth_idc_name=idc_name,
            auth_authUrl=authUrl,
            auth_netCancelUrl=netCancelUrl,
            auth_charset=charset,
            auth_merchantData=merchantData,

            confirm_resultCode=confirm_data.get("resultCode"),
            confirm_resultMsg=confirm_data.get("resultMsg"),
            confirm_tid=confirm_data.get("tid"),
            confirm_mid=confirm_data.get("mid"),
            confirm_MOID=confirm_data.get("MOID"),
            confirm_TotPrice=confirm_data.get("TotPrice"),
            confirm_goodName=confirm_data.get("goodName"),
            confirm_payMethod=confirm_data.get("payMethod"),
            confirm_applDate=confirm_data.get("applDate"),
            confirm_applTime=confirm_data.get("applTime"),
            confirm_EventCode=confirm_data.get("EventCode"),
            confirm_buyerName=confirm_data.get("buyerName"),
            confirm_buyerTel=confirm_data.get("buyerTel"),
            confirm_buyerEmail=confirm_data.get("buyerEmail"),
            confirm_custEmail=confirm_data.get("custEmail"),
        )
    )


@app.get(path="/close")
async def _():
    return JSONResponse(status_code=200, content=jsonable_encoder(dict(message="결제 중단")))


@app.post(path="/net-cancel")
async def _(netCancelUrl: str = Form(...),
            mid: str = Form(...),
            authToken: str = Form(...),
            charset: str = Form(...), ):
    url = netCancelUrl
    mid = mid
    authToken = authToken
    timestamp = current_milli_time()
    signature = sha256_hash(f"authToken={authToken}&timestamp={timestamp}")
    verification = sha256_hash(f"authToken={authToken}&signKey={SIGN_KEY}&timestamp={timestamp}")
    charset = charset
    format = "JSON"

    response = requests.post(
        url=url,
        headers={"Content-type": "application/x-www-form-urlencoded"},
        data=dict(
            mid=mid,
            authToken=authToken,
            timestamp=timestamp,
            signature=signature,
            verification=verification,
            charset=charset,
            format=format,
        )
    )
    json_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(json_data))


@app.post(path="/all-cancel")
async def _(paymethod: str = Form(...),
            mid: str = Form(...),
            tid: str = Form(...),
            msg: str = Form(...), ):
    type = "Refund"
    paymethod = paymethod
    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d%H%M%S")
    clientIp = SERVER_IP
    mid = mid
    tid = tid
    msg = msg
    hashData = sha512_hash(f"{INI_API_KEY}{type}{paymethod}{timestamp}{clientIp}{mid}{tid}")

    data = dict(
        type=type,
        paymethod=paymethod,
        timestamp=timestamp,
        clientIp=clientIp,
        mid=mid,
        tid=tid,
        msg=msg,
        hashData=hashData
    )
    encoded_data = parse.urlencode(data)
    response = requests.post(
        url="https://iniapi.inicis.com/api/v1/refund",
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=encoded_data,
    )
    json_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(json_data))


@app.post(path="/part-cancel")
async def _(paymethod: str = Form(...),
            mid: str = Form(...),
            tid: str = Form(...),
            msg: str = Form(...),
            price: str = Form(...),
            TotPrice: str = Form(...), ):
    type = "PartialRefund"
    paymethod = paymethod
    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d%H%M%S")
    clientIp = SERVER_IP
    mid = mid
    tid = tid
    msg = msg
    price = price
    confirmPrice = str(int(TotPrice) - int(price))
    hashData = sha512_hash(f"{INI_API_KEY}{type}{paymethod}{timestamp}{clientIp}{mid}{tid}{price}{confirmPrice}")

    data = dict(
        type=type,
        paymethod=paymethod,
        timestamp=timestamp,
        clientIp=clientIp,
        mid=mid,
        tid=tid,
        msg=msg,
        price=price,
        confirmPrice=confirmPrice,
        hashData=hashData
    )
    encoded_data = parse.urlencode(data)
    response = requests.post(
        url="https://iniapi.inicis.com/api/v1/refund",
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=encoded_data,
    )
    json_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(json_data))


@app.post("/receipt")
async def _(crPrice: str = Form(...),
            goodName: str = Form(...),
            buyerName: str = Form(...),
            buyerEmail: str = Form(...),
            regNum: str = Form(...)):
    type = "Issue"
    paymethod = "Receipt"
    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d%H%M%S")
    clientIp = SERVER_IP
    mid = MID
    crPrice = crPrice
    supPrice = get_supply_cost(total_amount=crPrice)
    tax = get_tax(total_amount=crPrice)
    srcvPrice = str(0)
    goodName = goodName
    buyerName = buyerName
    buyerEmail = buyerEmail
    regNum = aes_128_cbc_encrypt(plain_text=regNum, key=INI_API_KEY, iv=INI_API_IV)
    useOpt = "1"
    hashData = sha512_hash(
        f"{INI_API_KEY}{type}{paymethod}{timestamp}{clientIp}{mid}{crPrice}{supPrice}{srcvPrice}{regNum}"
    )

    data = dict(
        type=type,
        paymethod=paymethod,
        timestamp=timestamp,
        clientIp=clientIp,
        mid=mid,
        crPrice=crPrice,
        supPrice=supPrice,
        tax=tax,
        srcvPrice=srcvPrice,
        goodName=goodName,
        buyerName=buyerName,
        buyerEmail=buyerEmail,
        regNum=regNum,
        useOpt=useOpt,
        hashData=hashData,
    )
    encoded_data = parse.urlencode(data)
    response = requests.post(
        url="https://iniapi.inicis.com/api/v1/receipt",
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=encoded_data,
    )
    json_data = json.loads(response.text)
    return JSONResponse(status_code=200, content=jsonable_encoder(json_data))


if __name__ == '__main__':
    # INIStdPay.js 코드 보기
    print(requests.post(url="https://stdpay.inicis.com/stdjs/INIStdPay.js",
                        headers={"Content-type": "application/x-www-form-urlencoded", "charset": "utf-8"}).text)
