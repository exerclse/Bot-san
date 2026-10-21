# -*- coding: utf-8 -*-
import os
import re
import time
import random
import base64
import hashlib
import sqlite3
import threading
import requests
from datetime import datetime, timezone, timedelta

import telebot
from telebot import types
import logging

logging.getLogger("TeleBot").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8613753004:AAEcCeFQkCEqtb3OkSmkUTt94tx0OIzA2wk")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "41315388").split(",") if x.strip()]
DB_PATH = os.environ.get("DB_PATH", "factory.db")
NUMBERS_DIR = os.environ.get("NUMBERS_DIR", "numbers")
OWNER_DIR = os.environ.get("OWNER_DIR", "owner_numbers")
DEFAULT_EARNING = float(os.environ.get("DEFAULT_EARNING", "0.001"))
MIN_WITHDRAW = 5.0
SECRET_KEY = os.environ.get("SECRET_KEY", "otp_factory_v2")
API_POLL = 1
MECCA_TZ = timezone(timedelta(hours=3))
OTP_GROUP_LINK = "https://t.me/+JNCS_chHkzw1NjAy"
MAIN_CHANNEL_LINK = "https://t.me/+JNCS_chHkzw1NjAy"

# كل لوحة لها حسابين (key أساسي + key2)
API_SOURCES = [
    {
        "name": "unixsms_1",
        "base": os.environ.get("API_BASE", "https://agent-api.unixsms.com/v1"),
        "key": os.environ.get("API_KEY", "bsa_live_e80a4f5ba3c0c5f8.QSf2-Frg2KG-FW34x7fi6Qwt_9PgVhYaM-UNnIpL3k8"),
    },
    {
        "name": "unixsms_2",
        "base": os.environ.get("API_BASE", "https://agent-api.unixsms.com/v1"),
        "key": os.environ.get("API_KEY_UNIX_2", "bsa_live_54aede06b72fdc61.UbO-s0J0OE4v-3cvCyNNjJRbUx5O5U2JVjlGmsl76gs"),
    },
    {
        "name": "bluesms_1",
        "base": os.environ.get("API_BASE_2", "https://agent-api.blue-sms.net/v1"),
        "key": os.environ.get("API_KEY_2", "bsa_live_a096654df3643d95.PVEMLRRZqXJrBzKyDEbiBSbHdHXYXisRSQwGV9reb1g"),
    },
    {
        "name": "bluesms_2",
        "base": os.environ.get("API_BASE_2", "https://agent-api.blue-sms.net/v1"),
        "key": os.environ.get("API_KEY_BLUE_2", "bsa_live_b372e57ceedacd55.0gu6d06kEsEXgIh0EJsFcqNUjEwz3rV_xD8qnBB5GbY"),
    },
]
API_SOURCES = [s for s in API_SOURCES if s.get("key") and not str(s["key"]).startswith("PUT_")]

os.makedirs(NUMBERS_DIR, exist_ok=True)
os.makedirs(OWNER_DIR, exist_ok=True)

factory = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=32)
try:
    FACTORY_USERNAME = factory.get_me().username or ""
except Exception:
    FACTORY_USERNAME = ""

admin_state = {}
user_state = {}
child_bots = {}
child_lock = threading.Lock()
pending_deletes = []
pending_lock = threading.Lock()
processed_lock = threading.Lock()
_NUM_CACHE = {}
_NUM_CACHE_LOCK = threading.Lock()
_FORCE_CACHE = {}
_FORCE_CACHE_LOCK = threading.Lock()
_FORCE_TTL = 90
_SERVICES_CACHE = {"t": 0, "rows": None}
_COUNTRIES_CACHE = {}
_CHILD_ME = {}


E_BOT = ("🤖", "5983580310292402968")
E_CHANNEL = ("📢", "6021418126061605425")
E_GROUP = ("👥", "6032609071373226027")
E_TOKEN = ("📖", "6037286673010660132")
E_DEL = ("🗑", "6039522349517115015")
E_PHONE = ("📱", "5373145666597961572")
E_CHECK = ("✅", "5938252440926163756")
E_CROSS = ("❌", "5870657884844462243")
E_LOCK = ("🔒", "5240151566190656407")
E_CHART = ("📊", "5870930636742595124")
E_STAR = ("⭐", "5870801633104891858")
E_MONEY = ("💰", "5870930636742595124")
E_GEAR = ("⚙", "5870982283724328568")
E_FOLDER = ("📁", "5870570722778156940")
E_WEB = ("🌐", "5870718740236079262")
E_REFRESH = ("🔄", "5870982283724328568")
E_PLUS = ("➕", "5870741379008698885")
E_SEND = ("📤", "5873225338984599714")
E_PLANE = ("✈️", "5877700484453634587")
E_DOC = ("📄", "5873153278023307367")
E_USER = ("👤", "5870994129244131212")
E_LINK = ("🔗", "5870527201874546272")
E_MEGA = ("📢", "5873225338984599714")

SERVICE_PREMIUM = {
    "tiktok": ("📱", "5327982530702359565"),
    "facebook": ("📱", "5323261730283863478"),
    "instagram": ("📱", "5319160079465857105"),
    "whatsapp": ("📱", "5334998226636390258"),
    "telegram": ("📱", "5330237710655306682"),
    "discord": ("📱", "5325612636467903082"),
    "gmail": ("📱", "5348494358205207761"),
    "twitter": ("📱", "5330337435500951363"),
    "x": ("📱", "5330337435500951363"),
    "apple": ("📱", "5334955749409834455"),
    "amazon": ("📱", "5346056560537779652"),
    "uber": ("🚖", "5298715455316303708"),
    "imo": ("🚫", "5337155807752524558"),
    "paypal": ("📱", "5364111181415996352"),
    "microsoft": ("📱", "5370857634440170316"),
    "viber": ("📱", "5332449498553663205"),
    "snapchat": ("📱", "5330248916224983855"),
    "default": ("💬", "5443038326535759644"),
}

FLAG_PREMIUM = {
    "AD": ("🇦🇩", "5221987861733061751"), "AE": ("🇦🇪", "5224565851427976312"), "AF": ("🇦🇫", "5222096009009575868"),
    "AG": ("🇦🇬", "5224544866217765554"), "AL": ("🇦🇱", "5224312057515486246"), "AM": ("🇦🇲", "5224369957969603463"),
    "AO": ("🇦🇴", "5224379767674907895"), "AR": ("🇦🇷", "5221980461504411710"), "AT": ("🇦🇹", "5224520754271366661"),
    "AU": ("🇦🇺", "5224659803837574114"), "AZ": ("🇦🇿", "5224426544163728284"), "BA": ("🇧🇦", "5224496092569155254"),
    "BB": ("🇧🇧", "5222156533688712094"), "BD": ("🇧🇩", "5224407289825340729"), "BE": ("🇧🇪", "5224513182244024630"),
    "BF": ("🇧🇫", "5222356541725749790"), "BG": ("🇧🇬", "5222092074819530668"), "BH": ("🇧🇭", "5224492892818518587"),
    "BI": ("🇧🇮", "5224490444687158452"), "BJ": ("🇧🇯", "5222024115552009151"), "BM": ("🇧🇲", "5222482143749353810"),
    "BN": ("🇧🇳", "5224435958732042406"), "BO": ("🇧🇴", "5224675484763170798"), "BR": ("🇧🇷", "5224688610183228070"),
    "BS": ("🇧🇸", "5224504167107668172"), "BT": ("🇧🇹", "5224541065171710147"), "BW": ("🇧🇼", "5224288456670196085"),
    "BY": ("🇧🇾", "5280820319458707404"), "BZ": ("🇧🇿", "5224316292353241916"), "CA": ("🇨🇦", "5222001124592071204"),
    "CD": ("🇨🇩", "5224398158724871677"), "CF": ("🇨🇫", "5222073662294733523"), "CG": ("🇨🇬", "5222104268231684600"),
    "CH": ("🇨🇭", "5224707263226194753"), "CL": ("🇨🇱", "5222350726340032308"), "CM": ("🇨🇲", "5474681124426884947"),
    "CN": ("🇨🇳", "5224435456220868088"), "CO": ("🇨🇴", "5224455152940886669"), "CR": ("🇨🇷", "5222453801260168022"),
    "CV": ("🇨🇻", "5222347737042792258"), "CY": ("🇨🇾", "5222431454545327055"), "CZ": ("🇨🇿", "5222073533445714675"),
    "DE": ("🇩🇪", "5222165617544542414"), "DJ": ("🇩🇯", "5224203012590810589"), "DK": ("🇩🇰", "5222297215342490217"),
    "DM": ("🇩🇲", "5222337489250824921"), "DO": ("🇩🇴", "5224286412265763450"), "DZ": ("🇩🇿", "5224260376174015500"),
    "EC": ("🇪🇨", "5224191188545840926"), "EE": ("🇪🇪", "5222195463272281351"), "EG": ("🇪🇬", "5222161185138292290"),
    "ES": ("🇪🇸", "5222024776976970940"), "ET": ("🇪🇹", "5224467805914542024"), "EU": ("🇪🇺", "5222108911091331711"),
    "FI": ("🇫🇮", "5224282903277482188"), "FJ": ("🇫🇯", "5221962676044838178"), "FM": ("🇫🇲", "5222280486444873367"),
    "FO": ("🇫🇴", "5280985770188885026"), "FR": ("🇫🇷", "5222029789203804982"), "GA": ("🇬🇦", "5224669733801963467"),
    "GB": ("🇬🇧", "5224518800061245598"), "GD": ("🇬🇩", "5222234560359577687"), "GE": ("🇬🇪", "5222152195771742239"),
    "GH": ("🇬🇭", "5224511339703056124"), "GM": ("🇬🇲", "5221949872747330159"), "GN": ("🇬🇳", "5222337588035073000"),
    "GQ": ("🇬🇶", "5222172811614762423"), "GR": ("🇬🇷", "5222463490706389920"), "GT": ("🇬🇹", "5222128302868672826"),
    "GW": ("🇬🇼", "5224705704153066489"), "GY": ("🇬🇾", "5224570532942329532"), "HN": ("🇭🇳", "5222229234600130045"),
    "HR": ("🇭🇷", "5221967765581085099"), "HT": ("🇭🇹", "5224683146984831315"), "HU": ("🇭🇺", "5224691998912427164"),
    "ID": ("🇮🇩", "5224405893960969756"), "IE": ("🇮🇪", "5224257017509588818"), "IL": ("🇮🇱", "5224720599099648709"),
    "IN": ("🇮🇳", "5222300011366200403"), "IQ": ("🇮🇶", "5221980268230882832"), "IR": ("🇮🇷", "5224374154152653367"),
    "IS": ("🇮🇸", "5222063229819172521"), "IT": ("🇮🇹", "5222460101977190141"), "JM": ("🇯🇲", "5222007034467074185"),
    "JO": ("🇯🇴", "5222292177345853436"), "JP": ("🇯🇵", "5222390089715299207"), "KE": ("🇰🇪", "5222089648163009103"),
    "KG": ("🇰🇬", "5224388147156102493"), "KH": ("🇰🇭", "5224189882875785448"), "KI": ("🇰🇮", "5224652244695134610"),
    "KM": ("🇰🇲", "5222398735484466247"), "KR": ("🇰🇷", "5222345550904439270"), "KW": ("🇰🇼", "5221949726718442491"),
    "KZ": ("🇰🇿", "5222276376161171525"), "LA": ("🇱🇦", "5224200843632324642"), "LB": ("🇱🇧", "5222244425899455269"),
    "LC": ("🇱🇨", "5222000927023577045"), "LK": ("🇱🇰", "5224277294050192388"), "LR": ("🇱🇷", "5221998371518034740"),
    "LS": ("🇱🇸", "5224245850594619415"), "LT": ("🇱🇹", "5224245902134226386"), "LU": ("🇱🇺", "5224499567197700690"),
    "LV": ("🇱🇻", "5224401229626484931"), "LY": ("🇱🇾", "5222194286451242896"), "MA": ("🇲🇦", "5224530035695693965"),
    "MC": ("🇲🇨", "5221937224068640464"), "MD": ("🇲🇩", "5224216473018314447"), "ME": ("🇲🇪", "5224463399278096980"),
    "MG": ("🇲🇬", "5222042605386217334"), "MH": ("🇲🇭", "5224538449536624503"), "MK": ("🇲🇰", "5222470435668505656"),
    "ML": ("🇲🇱", "5224322352552096671"), "MM": ("🇲🇲", "5188162778073935826"), "MN": ("🇲🇳", "5224192257992701543"),
    "MQ": ("🇲🇶", "5281027792148909351"), "MT": ("🇲🇹", "5224731388057497620"), "MU": ("🇲🇺", "5224238347286752315"),
    "MV": ("🇲🇻", "5224393700548814960"), "MX": ("🇲🇽", "5221971386238514431"), "MY": ("🇲🇾", "5224312886444174057"),
    "MZ": ("🇲🇿", "5222470388423864826"), "NA": ("🇳🇦", "5224690826386351746"), "NE": ("🇳🇪", "5222099049846420864"),
    "NG": ("🇳🇬", "5224723614166691638"), "NL": ("🇳🇱", "5224516489368841614"), "NO": ("🇳🇴", "5224465228934163949"),
    "NP": ("🇳🇵", "5222444378101925267"), "NZ": ("🇳🇿", "5224573595254009705"), "OM": ("🇴🇲", "5222396686785066306"),
    "PA": ("🇵🇦", "5222111719999945107"), "PE": ("🇵🇪", "5224482026551258766"), "PG": ("🇵🇬", "5224500164198149905"),
    "PH": ("🇵🇭", "5222065042295376892"), "PK": ("🇵🇰", "5224637061985742245"), "PL": ("🇵🇱", "5224670399521892983"),
    "PR": ("🇵🇷", "5224220115150582423"), "PS": ("🇵🇸", "5222041677673282461"), "PT": ("🇵🇹", "5224404094369672274"),
    "PY": ("🇵🇾", "5222152565138929235"), "QA": ("🇶🇦", "5222225596762830469"), "RO": ("🇷🇴", "5222273794885826118"),
    "RS": ("🇷🇸", "5222145396838512729"), "RU": ("🇷🇺", "5280582975270963511"), "RW": ("🇷🇼", "5222449197055227754"),
    "SA": ("🇸🇦", "5224698145010624573"), "SB": ("🇸🇧", "5222290588207954120"), "SC": ("🇸🇨", "5224467496676896871"),
    "SD": ("🇸🇩", "5224372990216514135"), "SE": ("🇸🇪", "5222201098269373561"), "SG": ("🇸🇬", "5224194023224257181"),
    "SI": ("🇸🇮", "5224660718665607511"), "SK": ("🇸🇰", "5222401879400528047"), "SL": ("🇸🇱", "5224420995065983217"),
    "SN": ("🇸🇳", "5224358988623130949"), "SO": ("🇸🇴", "5222370504664428325"), "SR": ("🇸🇷", "5224567367551428669"),
    "SS": ("🇸🇸", "5224618146949773268"), "ST": ("🇸🇹", "5221953304426198315"), "SV": ("🇸🇻", "5224337131534559907"),
    "SY": ("🇸🇾", "5308002793812955097"), "SZ": ("🇸🇿", "5224269666188274723"), "TD": ("🇹🇩", "5222060468155204001"),
    "TG": ("🇹🇬", "5222408051268532030"), "TH": ("🇹🇭", "5224638530864556281"), "TJ": ("🇹🇯", "5222217865821696536"),
    "TL": ("🇹🇱", "5224515905253291409"), "TM": ("🇹🇲", "5224256935905208951"), "TN": ("🇹🇳", "5221991375016310330"),
    "TR": ("🇹🇷", "5224601903383457698"), "TT": ("🇹🇹", "5224391883777651050"), "TZ": ("🇹🇿", "5224397364155923150"),
    "UA": ("🇺🇦", "5222250679371839695"), "UG": ("🇺🇬", "5222464040462200940"), "UN": ("🇺🇳", "5451772687993031127"),
    "US": ("🇺🇸", "5224321781321442532"), "UY": ("🇺🇾", "5222466849370813232"), "UZ": ("🇺🇿", "5222404546575219535"),
    "VA": ("🇻🇦", "5222420266155520507"), "VC": ("🇻🇨", "5224541228380467535"), "VI": ("🇻🇮", "5224395882392201810"),
    "VN": ("🇻🇳", "5222359651282071925"), "VU": ("🇻🇺", "5222126748090512778"), "WS": ("🇼🇸", "5224660353593387686"),
    "XK": ("🇽🇰", "5222197129719592160"), "XX": ("🏳️", None), "YE": ("🇾🇪", "5222300655611294950"),
    "ZA": ("🇿🇦", "5224696216570309138"), "ZM": ("🇿🇲", "5224646626877911277"), "ZW": ("🇿🇼", "5222060442385397848"),
}

NAME_TO_ISO = {
    "afghanistan": "AF", "albania": "AL", "algeria": "DZ", "america": "US", "andorra": "AD", "angola": "AO",
    "antigua": "AG", "argentina": "AR", "armenia": "AM", "australia": "AU", "austria": "AT", "azerbaijan": "AZ",
    "bahamas": "BS", "bahrain": "BH", "bangladesh": "BD", "barbados": "BB", "belarus": "BY", "belgium": "BE",
    "belize": "BZ", "benin": "BJ", "bermuda": "BM", "bhutan": "BT", "bolivia": "BO", "bosnia": "BA",
    "botswana": "BW", "brazil": "BR", "brunei": "BN", "bulgaria": "BG", "burkina faso": "BF", "burma": "MM",
    "burundi": "BI", "cambodia": "KH", "cameroon": "CM", "canada": "CA", "cape verde": "CV",
    "central african republic": "CF", "chad": "TD", "chile": "CL", "china": "CN", "colombia": "CO", "comoros": "KM",
    "congo": "CG", "costa rica": "CR", "croatia": "HR", "cyprus": "CY", "czech republic": "CZ", "czechia": "CZ",
    "denmark": "DK", "djibouti": "DJ", "dominica": "DM", "dominican republic": "DO", "dr congo": "CD",
    "east timor": "TL", "ecuador": "EC", "egypt": "EG", "el salvador": "SV", "england": "GB",
    "equatorial guinea": "GQ", "estonia": "EE", "eswatini": "SZ", "ethiopia": "ET", "european union": "EU",
    "faroe islands": "FO", "fiji": "FJ", "finland": "FI", "france": "FR", "gabon": "GA", "gambia": "GM",
    "georgia": "GE", "germany": "DE", "ghana": "GH", "greece": "GR", "grenada": "GD", "guatemala": "GT",
    "guinea": "GN", "guinea bissau": "GW", "guyana": "GY", "haiti": "HT", "honduras": "HN", "hungary": "HU",
    "iceland": "IS", "india": "IN", "indonesia": "ID", "iran": "IR", "iraq": "IQ", "ireland": "IE", "israel": "IL",
    "italy": "IT", "jamaica": "JM", "japan": "JP", "jordan": "JO", "kazakhstan": "KZ", "kenya": "KE",
    "kiribati": "KI", "korea": "KR", "kosovo": "XK", "kuwait": "KW", "kyrgyzstan": "KG", "laos": "LA",
    "latvia": "LV", "lebanon": "LB", "lesotho": "LS", "liberia": "LR", "libya": "LY", "lithuania": "LT",
    "luxembourg": "LU", "macedonia": "MK", "madagascar": "MG", "malaysia": "MY", "maldives": "MV", "mali": "ML",
    "malta": "MT", "marshall islands": "MH", "martinique": "MQ", "mauritius": "MU", "mexico": "MX",
    "micronesia": "FM", "moldova": "MD", "monaco": "MC", "mongolia": "MN", "montenegro": "ME", "morocco": "MA",
    "mozambique": "MZ", "myanmar": "MM", "namibia": "NA", "nepal": "NP", "netherlands": "NL", "new zealand": "NZ",
    "niger": "NE", "nigeria": "NG", "north macedonia": "MK", "norway": "NO", "oman": "OM", "pakistan": "PK",
    "palestine": "PS", "panama": "PA", "papua new guinea": "PG", "paraguay": "PY", "peru": "PE", "philippines": "PH",
    "poland": "PL", "portugal": "PT", "puerto rico": "PR", "qatar": "QA", "romania": "RO", "russia": "RU",
    "rwanda": "RW", "saint lucia": "LC", "saint vincent": "VC", "samoa": "WS", "sao tome": "ST", "saudi": "SA",
    "senegal": "SN", "serbia": "RS", "seychelles": "SC", "sierra leone": "SL", "singapore": "SG", "slovakia": "SK",
    "slovenia": "SI", "solomon islands": "SB", "somalia": "SO", "south africa": "ZA", "south korea": "KR",
    "south sudan": "SS", "spain": "ES", "sri lanka": "LK", "sudan": "SD", "suriname": "SR", "sweden": "SE",
    "switzerland": "CH", "syria": "SY", "tajikistan": "TJ", "tanzania": "TZ", "thailand": "TH", "timor": "TL",
    "togo": "TG", "trinidad": "TT", "trinidad and tobago": "TT", "tunisia": "TN", "turkey": "TR",
    "turkmenistan": "TM", "uae": "AE", "uganda": "UG", "uk": "GB", "ukraine": "UA", "united nations": "UN",
    "uruguay": "UY", "usa": "US", "uzbekistan": "UZ", "vanuatu": "VU", "vatican": "VA", "vietnam": "VN",
    "virgin islands": "VI", "yemen": "YE", "zambia": "ZM", "zimbabwe": "ZW",
}

def pe(em, eid=None):
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{em}</tg-emoji>'
    return em

def pe_pair(pair):
    return pe(pair[0], pair[1] if len(pair) > 1 else None)

def pe_service(name=None):
    low = (name or "").lower().replace(" ", "").replace("#", "")
    for k, (em, eid) in SERVICE_PREMIUM.items():
        if k != "default" and k in low:
            return pe(em, eid) if eid else em
    em, eid = SERVICE_PREMIUM["default"]
    return pe(em, eid) if eid else em

def service_emoji_id(name):
    low = (name or "").lower().replace(" ", "")
    for k, (em, eid) in SERVICE_PREMIUM.items():
        if k != "default" and k in low and eid:
            return str(eid)
    eid = SERVICE_PREMIUM["default"][1]
    return str(eid) if eid else None

def resolve_iso(name):
    low = (name or "").lower().strip()
    if low in NAME_TO_ISO:
        return NAME_TO_ISO[low]
    for k, v in NAME_TO_ISO.items():
        if k in low or low in k:
            return v
    if len(low) == 2:
        return low.upper()
    return "XX"

def pe_flag(name):
    iso = resolve_iso(name)
    if iso in FLAG_PREMIUM:
        em, eid = FLAG_PREMIUM[iso]
        return pe(em, eid) if eid else em
    return "🏳️"

def plain_flag(name):
    iso = resolve_iso(name)
    if iso in FLAG_PREMIUM:
        return FLAG_PREMIUM[iso][0]
    return "🏳️"

def flag_emoji_id(name):
    iso = resolve_iso(name)
    if iso in FLAG_PREMIUM and FLAG_PREMIUM[iso][1]:
        return str(FLAG_PREMIUM[iso][1])
    return None

def service_hashtag(name):
    n = (name or "").strip()
    if not n:
        return "OTP"
    low = n.lower()
    for k, v in [("tiktok", "TikTok"), ("facebook", "Facebook"), ("instagram", "Instagram"),
                 ("whatsapp", "WhatsApp"), ("telegram", "Telegram"), ("discord", "Discord"),
                 ("gmail", "Gmail"), ("uber", "Uber"), ("paypal", "PayPal")]:
        if k in low:
            return v
    clean = re.sub(r"[^A-Za-z0-9]+", "", n)
    return clean[:20] if clean else "OTP"

def detect_lang(text):
    if not text:
        return "English"
    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"
    return "English"

def detect_service_from_text(text):
    if not text:
        return None
    low = str(text).lower()
    rules = [
        (r"tiktok|tik\s*tok", "TikTok"), (r"facebook|\bfb\b", "Facebook"),
        (r"instagram|\binsta\b", "Instagram"), (r"whatsapp|\bwa\b", "WhatsApp"),
        (r"telegram", "Telegram"), (r"discord", "Discord"), (r"gmail|google", "Gmail"),
        (r"uber", "Uber"), (r"paypal", "PayPal"),
    ]
    for pat, name in rules:
        if re.search(pat, low):
            return name
    return None

def encrypt_token(token):
    raw = token.encode()
    key = hashlib.sha256(SECRET_KEY.encode()).digest()
    xored = bytes(a ^ key[i % len(key)] for i, a in enumerate(raw))
    return base64.urlsafe_b64encode(xored).decode()

def decrypt_token(enc):
    try:
        xored = base64.urlsafe_b64decode(enc.encode())
        key = hashlib.sha256(SECRET_KEY.encode()).digest()
        return bytes(a ^ key[i % len(key)] for i, a in enumerate(xored)).decode()
    except Exception:
        return ""

def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA temp_store=MEMORY")
        c.execute("PRAGMA cache_size=-8000")
    except Exception:
        pass
    return c

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS factory_users (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, lang TEXT DEFAULT 'ar',
            is_banned INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS child_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
            token_enc TEXT NOT NULL, bot_username TEXT, bot_id INTEGER,
            otp_group TEXT DEFAULT '', otp_group_link TEXT DEFAULT '',
            channel_link TEXT DEFAULT '', total_codes INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER, name TEXT, filename TEXT,
            UNIQUE(service_id, name)
        );
        CREATE TABLE IF NOT EXISTS assigned (
            id INTEGER PRIMARY KEY AUTOINCREMENT, child_id INTEGER, user_id INTEGER,
            country_id INTEGER, phone TEXT, show_plus INTEGER DEFAULT 1, assigned_at REAL
        );
        CREATE TABLE IF NOT EXISTS child_users (
            child_id INTEGER, user_id INTEGER, username TEXT, full_name TEXT,
            balance REAL DEFAULT 0, total_codes INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
            PRIMARY KEY (child_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS code_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, child_id INTEGER, user_id INTEGER,
            phone TEXT, code TEXT, service TEXT, country TEXT, reward REAL, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS factory_force (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT UNIQUE, username TEXT, title TEXT, invite_link TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS global_force (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT UNIQUE, username TEXT, title TEXT, invite_link TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS child_force (
            id INTEGER PRIMARY KEY AUTOINCREMENT, child_id INTEGER, chat_id TEXT, username TEXT, title TEXT, invite_link TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS processed (msg_id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS owner_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, created_at REAL
        );
        CREATE TABLE IF NOT EXISTS owner_countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER, name TEXT, filename TEXT,
            UNIQUE(service_id, name)
        );
        CREATE TABLE IF NOT EXISTS macaron_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, url TEXT, min_otp INTEGER DEFAULT 0,
            repeat_count INTEGER DEFAULT 1, interval_sec INTEGER DEFAULT 3600,
            delete_after INTEGER DEFAULT 3600, is_active INTEGER DEFAULT 1,
            sent_count INTEGER DEFAULT 0, last_sent REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS maker_balance (
            owner_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_earned REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS withdraw_req (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, network TEXT, address TEXT,
            amount REAL, status TEXT DEFAULT 'pending', created_at REAL
        );
        CREATE TABLE IF NOT EXISTS recent_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, code TEXT, service TEXT,
            delivered INTEGER DEFAULT 0, created_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_assigned_child_user ON assigned(child_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_assigned_phone ON assigned(phone);
        CREATE INDEX IF NOT EXISTS idx_countries_svc ON countries(service_id);
        CREATE INDEX IF NOT EXISTS idx_code_log_child ON code_log(child_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_processed ON processed(msg_id);
    """)
    c.commit()
    c.close()

def get_setting(key, default=""):
    c = db()
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return r["value"] if r else default

def set_setting(key, value):
    c = db()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
    c.commit()
    c.close()

_EARN_CACHE = {"t": 0, "v": None}
def get_earning():
    now = time.time()
    if _EARN_CACHE["v"] is not None and (now - _EARN_CACHE["t"]) < 60:
        return _EARN_CACHE["v"]
    try:
        v = float(get_setting("earning", str(DEFAULT_EARNING)))
    except Exception:
        v = DEFAULT_EARNING
    _EARN_CACHE["v"] = v
    _EARN_CACHE["t"] = now
    return v

def is_admin(uid):
    return uid in ADMIN_IDS

def safe_send(bot_obj, chat_id, text, **kwargs):
    try:
        return bot_obj.send_message(chat_id, text, **kwargs)
    except Exception:
        try:
            kwargs.pop("parse_mode", None)
            return bot_obj.send_message(chat_id, text, **kwargs)
        except Exception:
            return None

def safe_reply(bot_obj, msg, text, **kwargs):
    try:
        chat_id = msg.chat.id if hasattr(msg, "chat") else msg
        return bot_obj.send_message(chat_id, text, **kwargs)
    except Exception:
        return None


def norm_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))

def format_phone(phone, show_plus=True):
    n = norm_phone(phone)
    return ("+" + n) if show_plus and n else n

def phones_match(a, b):
    na, nb = norm_phone(a), norm_phone(b)
    if not na or not nb:
        return False
    return na == nb or na.endswith(nb) or nb.endswith(na)

def mask_phone(phone):
    n = norm_phone(phone)
    if len(n) < 6:
        return n
    return n[:5] + "••••" + n[-3:]

def ikb_btn(text, callback_data=None, url=None, copy_text_val=None, emoji_id=None):
    text = str(text)[:64]
    if copy_text_val is not None:
        try:
            if hasattr(types, "CopyTextButton"):
                return types.InlineKeyboardButton(text=text, copy_text=types.CopyTextButton(text=str(copy_text_val)))
        except Exception:
            pass
        return types.InlineKeyboardButton(text=text, callback_data=f"copy:{str(copy_text_val)[:50]}")
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = str(callback_data)[:64]
    if url is not None:
        kwargs["url"] = url
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = str(emoji_id)
    try:
        return types.InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("icon_custom_emoji_id", None)
        return types.InlineKeyboardButton(**kwargs)

def load_numbers(filename):
    if not filename:
        return []
    path = os.path.join(NUMBERS_DIR, filename)
    if not os.path.exists(path):
        return []
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0
    with _NUM_CACHE_LOCK:
        hit = _NUM_CACHE.get(filename)
        if hit and hit[0] == mtime:
            return list(hit[1])
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]
    nums = [l for l in lines if re.match(r"^\+?\d{8,15}$", l.replace(" ", ""))]
    with _NUM_CACHE_LOCK:
        _NUM_CACHE[filename] = (mtime, nums)
    return list(nums)

def save_numbers(filename, numbers):
    with _NUM_CACHE_LOCK:
        _NUM_CACHE.pop(filename, None)
    path = os.path.join(NUMBERS_DIR, filename)
    if not numbers:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(numbers) + "\n")

def extract_otp(text):
    if not text:
        return None, None
    code = None
    for pat in [r"(?:code|код|رمز|otp)[^\d]{0,12}(\d{4,8})", r"\b(\d{4,8})\b"]:
        m = re.search(pat, text, re.I)
        if m:
            code = m.group(1)
            break
    phone = None
    pm = re.search(r"(\+?\d{10,15})", text)
    if pm:
        phone = pm.group(1)
    return phone, code

def ensure_factory_user(uid, username=None, full_name=None):
    c = db()
    c.execute(
        "INSERT OR IGNORE INTO factory_users (user_id, username, full_name) VALUES (?,?,?)",
        (uid, username or "", full_name or "")
    )
    if username or full_name:
        c.execute("UPDATE factory_users SET username=COALESCE(?,username), full_name=COALESCE(?,full_name) WHERE user_id=?",
                  (username, full_name, uid))
    c.commit()
    c.close()

def get_maker_balance(owner_id):
    c = db()
    r = c.execute("SELECT balance FROM maker_balance WHERE owner_id=?", (owner_id,)).fetchone()
    if not r:
        c.execute("INSERT OR IGNORE INTO maker_balance (owner_id, balance, total_earned) VALUES (?,?,0)", (owner_id, 0))
        c.commit()
        c.close()
        return 0.0
    c.close()
    return float(r["balance"] or 0)

def add_maker_balance(owner_id, amount):
    c = db()
    c.execute("INSERT OR IGNORE INTO maker_balance (owner_id, balance, total_earned) VALUES (?,?,0)", (owner_id, 0))
    c.execute("UPDATE maker_balance SET balance=balance+?, total_earned=total_earned+? WHERE owner_id=?",
              (amount, amount, owner_id))
    c.commit()
    c.close()

def factory_admin_kb(lang="ar"):
    """لوحة مالك المصنع — أزرار شفافة ماكرون + إيموجي مميز"""
    L = {
        "ar": {
            "svc": "إضافة خدمة", "cnt": "إضافة دولة+ملف", "delc": "حذف دولة", "dels": "حذف سيرفر",
            "earn": "تعيين أرباح", "ff": "اشتراك إجباري", "fg": "اشتراك للجميع", "dff": "حذف إجباري",
            "dfg": "حذف إجباري للجميع", "bc": "إذاعة", "st": "إحصائيات", "top": "أفضل 5 بوتات",
            "mac": "إشعار الماكرون", "dmac": "حذف الماكرون", "pmac": "نشر الماكرون", "fake": "إشعار وهمي",
            "wd": "طلبات السحب", "list": "عرض الخدمات",
        },
        "en": {
            "svc": "Add Service", "cnt": "Add Country", "delc": "Del Country", "dels": "Del Server",
            "earn": "Set Earning", "ff": "Force Factory", "fg": "Force All", "dff": "Del Force F",
            "dfg": "Del Force All", "bc": "Broadcast", "st": "Stats", "top": "Top 5 Bots",
            "mac": "Macaron Ads", "dmac": "Del Macaron", "pmac": "Publish Macaron", "fake": "Fake OTP",
            "wd": "Withdraws", "list": "Services",
        },
    }[lang if lang in ("ar", "en") else "ar"]
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(ikb_btn(L["svc"], "fa:svc", emoji_id=E_PLUS[1]), ikb_btn(L["cnt"], "fa:cnt", emoji_id=E_DOC[1]))
    kb.row(ikb_btn(L["delc"], "fa:delc", emoji_id=E_DEL[1]), ikb_btn(L["dels"], "fa:dels", emoji_id=E_DEL[1]))
    kb.row(ikb_btn(L["earn"], "fa:earn", emoji_id=E_MONEY[1]), ikb_btn(L["ff"], "fa:ff", emoji_id=E_LOCK[1]))
    kb.row(ikb_btn(L["fg"], "fa:fg", emoji_id=E_LOCK[1]), ikb_btn(L["dff"], "fa:dff", emoji_id=E_CROSS[1]))
    kb.row(ikb_btn(L["dfg"], "fa:dfg", emoji_id=E_CROSS[1]), ikb_btn(L["bc"], "fa:bc", emoji_id=E_MEGA[1]))
    kb.row(ikb_btn(L["st"], "fa:st", emoji_id=E_CHART[1]), ikb_btn(L["top"], "fa:top", emoji_id=E_STAR[1]))
    kb.row(ikb_btn(L["mac"], "fa:mac", emoji_id=E_LINK[1]), ikb_btn(L["dmac"], "fa:dmac", emoji_id=E_DEL[1]))
    kb.row(ikb_btn(L["pmac"], "fa:pmac", emoji_id=E_SEND[1]), ikb_btn(L["fake"], "fa:fake", emoji_id=E_PHONE[1]))
    kb.row(ikb_btn(L["wd"], "fa:wd", emoji_id=E_MONEY[1]), ikb_btn(L["list"], "fa:list", emoji_id=E_FOLDER[1]))
    return kb

def factory_user_kb(lang="ar"):
    """لوحة الصانع — شفافة ماكرون"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    if lang == "en":
        kb.row(ikb_btn("Create Bot", "fu:create", emoji_id=E_BOT[1]))
        kb.row(ikb_btn("My Bots", "fu:mybots", emoji_id=E_GEAR[1]), ikb_btn("My Earnings", "fu:money", emoji_id=E_MONEY[1]))
    else:
        kb.row(ikb_btn("صنع بوت", "fu:create", emoji_id=E_BOT[1]))
        kb.row(ikb_btn("بوتاتي", "fu:mybots", emoji_id=E_GEAR[1]), ikb_btn("أرباحي", "fu:money", emoji_id=E_MONEY[1]))
    return kb

def child_user_kb(lang="en"):
    """لوحة مستخدم البوت المصنوع — مثل الصورة (Reply أسفل)"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == "ar":
        kb.add("Get Number", "Live Traffic")
        kb.add("My Profile", "Withdraw")
        kb.add("Support", "ToP 3")
    else:
        kb.add("Get Number", "Live Traffic")
        kb.add("My Profile", "Withdraw")
        kb.add("Support", "ToP 3")
    return kb

def child_owner_kb(lang="ar"):
    """تم عرض لوحة المشرف الخاصة بك - يمكنك التحكم من خلالها"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    if lang == "en":
        kb.row(ikb_btn("Get Number", "co:get", emoji_id=E_PHONE[1]))
        kb.row(ikb_btn("Force Sub", "co:ff", emoji_id=E_LOCK[1]), ikb_btn("Del Force", "co:dff", emoji_id=E_CROSS[1]))
        kb.row(ikb_btn("Set OTP Group", "co:otp", emoji_id=E_GROUP[1]), ikb_btn("Del OTP Group", "co:dotp", emoji_id=E_DEL[1]))
        kb.row(ikb_btn("Set Channel", "co:ch", emoji_id=E_CHANNEL[1]), ikb_btn("Del Channel", "co:dch", emoji_id=E_DEL[1]))
        kb.row(ikb_btn("My Stats", "co:st", emoji_id=E_CHART[1]), ikb_btn("Broadcast", "co:bc", emoji_id=E_MEGA[1]))
    else:
        kb.row(ikb_btn("طلب رقم", "co:get", emoji_id=E_PHONE[1]))
        kb.row(ikb_btn("اشتراك إجباري", "co:ff", emoji_id=E_LOCK[1]), ikb_btn("حذف الاشتراك", "co:dff", emoji_id=E_CROSS[1]))
        kb.row(ikb_btn("تعيين كروب OTP", "co:otp", emoji_id=E_GROUP[1]), ikb_btn("حذف كروب OTP", "co:dotp", emoji_id=E_DEL[1]))
        kb.row(ikb_btn("تعيين قناة الأزرار", "co:ch", emoji_id=E_CHANNEL[1]), ikb_btn("حذف قناة الأزرار", "co:dch", emoji_id=E_DEL[1]))
        kb.row(ikb_btn("إحصائيات بوتي", "co:st", emoji_id=E_CHART[1]), ikb_btn("إذاعة", "co:bc", emoji_id=E_MEGA[1]))
    return kb

def force_kb(channels):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        title = ch.get("title") or ch.get("username") or ch.get("chat_id") or "Channel"
        url = (ch.get("invite_link") or "").strip()
        if not url and ch.get("username"):
            url = f"https://t.me/{str(ch['username']).lstrip('@')}"
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            kb.add(ikb_btn(title[:28], url=url, emoji_id=E_CHANNEL[1]))
        else:
            kb.add(ikb_btn(title[:28], callback_data="force_check", emoji_id=E_CHANNEL[1]))
    kb.add(ikb_btn("تحقق", callback_data="force_check", emoji_id=E_CHECK[1]))
    return kb

def check_member(bot_obj, chat_id, user_id):
    key = (str(chat_id), int(user_id))
    now = time.time()
    with _FORCE_CACHE_LOCK:
        hit = _FORCE_CACHE.get(key)
        if hit and (now - hit[0]) < _FORCE_TTL:
            return hit[1]
    ok = False
    try:
        m = bot_obj.get_chat_member(chat_id, user_id)
        ok = m.status in ("member", "administrator", "creator", "restricted")
    except Exception:
        ok = False
    with _FORCE_CACHE_LOCK:
        _FORCE_CACHE[key] = (now, ok)
    return ok

def check_force_list(bot_obj, uid, channels):
    if not channels:
        return True, []
    missing = []
    # فحص متوازي سريع
    results = [None] * len(channels)
    def _one(i, ch):
        cid = ch.get("chat_id")
        if not cid:
            results[i] = None
            return
        try:
            cid_use = int(cid) if str(cid).lstrip("-").isdigit() else cid
        except Exception:
            cid_use = cid
        results[i] = ch if not check_member(bot_obj, cid_use, uid) else None
    threads = []
    for i, ch in enumerate(channels):
        th = threading.Thread(target=_one, args=(i, ch), daemon=True)
        th.start()
        threads.append(th)
    for th in threads:
        th.join(timeout=2.5)
    for r in results:
        if r is not None:
            missing.append(r)
    return len(missing) == 0, missing

def get_factory_force():
    c = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM factory_force").fetchall()]
    c.close()
    return rows

def get_global_force():
    c = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM global_force").fetchall()]
    c.close()
    return rows

def resolve_channel(text, bot_obj=None):
    bot_obj = bot_obj or factory
    text = (text or "").strip()
    chat_id = username = title = inv = ""
    if text.startswith("@"):
        username = text.lstrip("@")
        try:
            ch = bot_obj.get_chat(text)
            chat_id = str(ch.id)
            title = ch.title or username
            inv = f"https://t.me/{username}"
        except Exception:
            chat_id = text
            title = username
            inv = f"https://t.me/{username}"
    elif text.lstrip("-").isdigit():
        chat_id = text
        try:
            ch = bot_obj.get_chat(int(text))
            title = ch.title or text
            username = getattr(ch, "username", "") or ""
            if username:
                inv = f"https://t.me/{username}"
        except Exception:
            title = text
    elif "t.me/" in text:
        inv = text if text.startswith("http") else "https://" + text
        title = "Channel"
    return chat_id, username, title, inv

def start_child_bot(child_id):
    c = db()
    row = c.execute("SELECT * FROM child_bots WHERE id=?", (child_id,)).fetchone()
    c.close()
    if not row or not row["is_active"]:
        return False
    token = decrypt_token(row["token_enc"])
    if not token:
        return False
    with child_lock:
        if child_id in child_bots:
            return True
    try:
        b = telebot.TeleBot(token, parse_mode="HTML", threaded=True, num_threads=24)
        register_child_handlers(b, child_id)
        def run():
            while True:
                try:
                    b.infinity_polling(timeout=10, long_polling_timeout=8, skip_pending=True, none_stop=True)
                except Exception:
                    time.sleep(5)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        with child_lock:
            child_bots[child_id] = {"bot": b, "thread": t}
        return True
    except Exception:
        return False

def load_all_children():
    c = db()
    rows = c.execute("SELECT id FROM child_bots WHERE is_active=1").fetchall()
    c.close()
    for r in rows:
        try:
            start_child_bot(r["id"])
        except Exception:
            pass

def get_child_bot(child_id):
    with child_lock:
        info = child_bots.get(child_id)
    return info["bot"] if info else None

def ensure_child_user(child_id, uid, username=None, full_name=None):
    c = db()
    c.execute(
        "INSERT OR IGNORE INTO child_users (child_id, user_id, username, full_name) VALUES (?,?,?,?)",
        (child_id, uid, username or "", full_name or "")
    )
    c.commit()
    c.close()

def is_child_owner(child_id, uid):
    c = db()
    r = c.execute("SELECT owner_id FROM child_bots WHERE id=?", (child_id,)).fetchone()
    c.close()
    return r and r["owner_id"] == uid

def services_ikb():
    now = time.time()
    if _SERVICES_CACHE["rows"] is not None and (now - _SERVICES_CACHE["t"]) < 30:
        rows = _SERVICES_CACHE["rows"]
    else:
        c = db()
        rows = [dict(r) for r in c.execute("SELECT id, name FROM services ORDER BY name").fetchall()]
        c.close()
        _SERVICES_CACHE["rows"] = rows
        _SERVICES_CACHE["t"] = now
    kb = types.InlineKeyboardMarkup(row_width=2)
    row = []
    for r in rows:
        btn = ikb_btn(r["name"], callback_data=f"svc:{r['id']}", emoji_id=service_emoji_id(r["name"]))
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.row(ikb_btn("Back", callback_data="home", emoji_id=E_FOLDER[1]))
    return kb

def owner_services_ikb():
    c = db()
    rows = c.execute("SELECT * FROM owner_services ORDER BY name").fetchall()
    c.close()
    kb = types.InlineKeyboardMarkup(row_width=2)
    row = []
    for r in rows:
        btn = ikb_btn(r["name"], callback_data=f"osvc:{r['id']}", emoji_id=service_emoji_id(r["name"]))
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.row(ikb_btn("Back", callback_data="home", emoji_id=E_FOLDER[1]))
    return kb

def countries_ikb(service_id, prefix="cnt"):
    key = (prefix, int(service_id))
    now = time.time()
    hit = _COUNTRIES_CACHE.get(key)
    if hit and (now - hit[0]) < 20:
        rows = hit[1]
    else:
        c = db()
        if prefix == "ocnt":
            rows = [dict(r) for r in c.execute("SELECT id, name FROM owner_countries WHERE service_id=? ORDER BY name", (service_id,)).fetchall()]
        else:
            rows = [dict(r) for r in c.execute("SELECT id, name FROM countries WHERE service_id=? ORDER BY name", (service_id,)).fetchall()]
        c.close()
        _COUNTRIES_CACHE[key] = (now, rows)
    kb = types.InlineKeyboardMarkup(row_width=2)
    row = []
    for r in rows:
        btn = ikb_btn(r["name"], callback_data=f"{prefix}:{r['id']}", emoji_id=flag_emoji_id(r["name"]))
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.row(ikb_btn("Back", callback_data="back_u", emoji_id=E_FOLDER[1]))
    return kb

def numbers_ikb(child_id, country_id, phones, show_plus=True, svc_name="OTP", country_name="", is_owner_pool=False):
    kb = types.InlineKeyboardMarkup(row_width=1)
    flag = plain_flag(country_name)
    cc = resolve_iso(country_name)
    for p in phones:
        disp = format_phone(p, show_plus)
        kb.add(ikb_btn(f"{flag} {disp}", copy_text_val=disp))
    prefix = "ochg" if is_owner_pool else "chg"
    kb.row(
        ikb_btn("Change Country", callback_data="back_u", emoji_id=E_WEB[1]),
        ikb_btn("Change Number", callback_data=f"{prefix}:{country_id}", emoji_id=E_REFRESH[1]),
    )
    plus_lbl = "Remove CC" if show_plus else "Add CC"
    pfx = "oplus" if is_owner_pool else "plus"
    kb.row(ikb_btn(plus_lbl, callback_data=f"{pfx}:{country_id}", emoji_id=E_CROSS[1] if show_plus else E_PLUS[1]))
    c = db()
    ch = c.execute("SELECT otp_group_link, channel_link FROM child_bots WHERE id=?", (child_id,)).fetchone()
    c.close()
    glink = (ch["otp_group_link"] if ch else "") or OTP_GROUP_LINK
    if glink:
        url = glink if glink.startswith("http") else "https://" + glink
        kb.row(ikb_btn("OTP Group", url=url, emoji_id=E_GROUP[1]))
    reward = get_earning()
    se = pe_service(svc_name)
    text = (
        f"{pe_flag(country_name)} <b>{cc}</b> › ASSIGNED FOR YOU {pe_pair(E_CHECK)}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{se} Service: <b>{service_hashtag(svc_name)}</b>\n"
        f"{pe_pair(E_MONEY)} Reward: <b>{reward} USD</b>"
    )
    return text, kb

def give_numbers(bot_obj, child_id, chat_id, user_id, country_id, edit_msg=None, exclude=None, show_plus=True, owner_pool=False):
    exclude = {norm_phone(p) for p in (exclude or [])}
    c = db()
    if owner_pool:
        country = c.execute("SELECT * FROM owner_countries WHERE id=?", (country_id,)).fetchone()
        svc = None
        if country:
            svc = c.execute("SELECT name FROM owner_services WHERE id=?", (country["service_id"],)).fetchone()
    else:
        country = c.execute("SELECT * FROM countries WHERE id=?", (country_id,)).fetchone()
        svc = None
        if country:
            svc = c.execute("SELECT name FROM services WHERE id=?", (country["service_id"],)).fetchone()
    if not country:
        c.close()
        return False
    svc_name = (svc["name"] if svc else None) or "OTP"
    c.execute("DELETE FROM assigned WHERE child_id=? AND user_id=?", (child_id, user_id))
    all_nums = load_numbers(country["filename"] or "")
    taken = {norm_phone(r["phone"]) for r in c.execute("SELECT phone FROM assigned WHERE child_id=?", (child_id,)).fetchall()}
    available = [n for n in all_nums if norm_phone(n) not in taken and norm_phone(n) not in exclude]
    if not available:
        available = [n for n in all_nums if norm_phone(n) not in taken]
    if not available:
        c.close()
        return False
    if len(available) > 3:
        available = random.sample(available, 3)
    else:
        random.shuffle(available)
        available = available[:3]
    now = time.time()
    for p in available:
        c.execute(
            "INSERT INTO assigned (child_id, user_id, country_id, phone, show_plus, assigned_at) VALUES (?,?,?,?,?,?)",
            (child_id, user_id, country_id, norm_phone(p), 1 if show_plus else 0, now)
        )
    c.commit()
    c.close()
    text, kb = numbers_ikb(child_id, country_id, available, show_plus, svc_name, country["name"], is_owner_pool=owner_pool)
    try:
        if edit_msg:
            bot_obj.edit_message_text(text, chat_id, edit_msg, reply_markup=kb, parse_mode="HTML")
        else:
            bot_obj.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        return True
    except Exception:
        try:
            bot_obj.send_message(chat_id, text, reply_markup=kb)
            return True
        except Exception:
            return False

def post_otp_child(child_id, phone, code, svc_name, country_name, sms_text=""):
    c = db()
    ch = c.execute("SELECT * FROM child_bots WHERE id=?", (child_id,)).fetchone()
    c.close()
    if not ch:
        return False
    bot_obj = get_child_bot(child_id)
    if not bot_obj:
        return False
    otp_gid = (ch["otp_group"] or "").strip()
    if not otp_gid:
        return False
    flag = pe_flag(country_name)
    se = pe_service(svc_name)
    tag = service_hashtag(svc_name)
    masked = mask_phone(phone)
    cc = resolve_iso(country_name)
    code_clean = re.sub(r"\D", "", str(code))
    code_disp = (code_clean[:3] + "-" + code_clean[3:]) if len(code_clean) == 6 else code_clean
    prefix = norm_phone(phone)[:6]
    lang = detect_lang(sms_text)
    if lang == "Arabic":
        body = f"# كود {tag} الخاص بك {code_disp}\nلا تطلع أحداً عليه"
    else:
        body = f"# Your {tag} code {code_disp}\nDont share this code with others"
    gtext = (
        f"{flag} <b>#{cc}</b> {se} {masked} | {pe_pair(E_MEGA)}\n"
        f"<b>{lang}</b>\n"
        f"<blockquote>{body}</blockquote>\n"
        f"<blockquote><b># Prefix:</b> /pre {prefix}</blockquote>"
    )
    gkb = types.InlineKeyboardMarkup()
    ch_url = (ch["channel_link"] or "").strip() or MAIN_CHANNEL_LINK
    gkb.row(
        ikb_btn("Channel", url=ch_url if ch_url.startswith("http") else "https://" + ch_url, emoji_id=E_PLANE[1]),
        ikb_btn(code_clean, copy_text_val=code_clean, emoji_id=None),
    )
    try:
        un = _CHILD_ME.get(child_id)
        if not un:
            un = bot_obj.get_me().username
            if un:
                _CHILD_ME[child_id] = un
        if un:
            gkb.row(ikb_btn("Get Number", url=f"https://t.me/{un}", emoji_id=E_PHONE[1]))
    except Exception:
        pass
    targets = []
    if otp_gid.lstrip("-").isdigit():
        targets.append(int(otp_gid))
    targets.append(otp_gid)
    for tgt in targets:
        try:
            gsent = bot_obj.send_message(tgt, gtext, reply_markup=gkb, parse_mode="HTML")
            with pending_lock:
                pending_deletes.append((bot_obj, gsent.chat.id, gsent.message_id, time.time() + 60))
            return True
        except Exception:
            continue
    return False

def deliver_otp(child_id, user_id, phone, code, svc_name, country_name, sms_text=""):
    reward = get_earning()
    c = db()
    c.execute("UPDATE child_users SET balance=balance+?, total_codes=total_codes+1 WHERE child_id=? AND user_id=?",
              (reward, child_id, user_id))
    c.execute("UPDATE child_bots SET total_codes=total_codes+1 WHERE id=?", (child_id,))
    owner = c.execute("SELECT owner_id FROM child_bots WHERE id=?", (child_id,)).fetchone()
    c.execute(
        "INSERT INTO code_log (child_id, user_id, phone, code, service, country, reward, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (child_id, user_id, phone, code, svc_name, country_name, reward, time.time())
    )
    c.commit()
    c.close()
    if owner:
        add_maker_balance(owner["owner_id"], reward)
    bot_obj = get_child_bot(child_id)
    if bot_obj:
        se = pe_service(svc_name)
        bal = 0
        c = db()
        u = c.execute("SELECT balance FROM child_users WHERE child_id=? AND user_id=?", (child_id, user_id)).fetchone()
        c.close()
        if u:
            bal = u["balance"]
        text = (
            f"{se} <b>{service_hashtag(svc_name)}</b>\n"
            f"-------------------------\n"
            f"{pe_flag(country_name)} {format_phone(phone)}\n"
            f"Reward: {reward} USD\n"
            f"Balance: {bal:.3f} USD"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn(str(code), copy_text_val=str(code)))
        try:
            sent = bot_obj.send_message(user_id, text, reply_markup=kb, parse_mode="HTML")
            with pending_lock:
                pending_deletes.append((bot_obj, sent.chat.id, sent.message_id, time.time() + 180))
        except Exception:
            pass
    post_otp_child(child_id, phone, code, svc_name, country_name, sms_text)
    return True

def try_deliver(phone, code, detected_service=None, sms_text=""):
    if not phone or not code or not re.match(r"^\d{4,8}$", str(code)):
        return False
    c = db()
    rows = c.execute(
        "SELECT a.*, co.name as country_name, s.name as service_name "
        "FROM assigned a "
        "LEFT JOIN countries co ON co.id=a.country_id "
        "LEFT JOIN services s ON s.id=co.service_id "
        "ORDER BY a.id DESC"
    ).fetchall()
    assigned = None
    for r in rows:
        if phones_match(r["phone"], phone):
            assigned = r
            break
    if not assigned:
        rows2 = c.execute(
            "SELECT a.*, oc.name as country_name, os.name as service_name "
            "FROM assigned a "
            "LEFT JOIN owner_countries oc ON oc.id=a.country_id "
            "LEFT JOIN owner_services os ON os.id=oc.service_id "
            "ORDER BY a.id DESC"
        ).fetchall()
        for r in rows2:
            if phones_match(r["phone"], phone):
                assigned = r
                break
    if not assigned:
        c.close()
        return False
    c.execute("DELETE FROM assigned WHERE id=?", (assigned["id"],))
    c.commit()
    c.close()
    svc = detected_service or detect_service_from_text(sms_text) or assigned["service_name"] or "OTP"
    return deliver_otp(
        assigned["child_id"], assigned["user_id"], phone, code,
        svc, assigned["country_name"] or "", sms_text
    )

def process_otp(phone, code, source="", sms_text=""):
    detected = detect_service_from_text(sms_text)
    delivered = try_deliver(phone, code, detected_service=detected, sms_text=sms_text or "")
    if not delivered:
        c = db()
        c.execute(
            "INSERT INTO recent_codes (phone, code, service, delivered, created_at) VALUES (?,?,?,0,?)",
            (norm_phone(phone), str(code), detected or "", time.time())
        )
        c.commit()
        c.close()
    return delivered

def register_child_handlers(bot_obj, child_id):
    @bot_obj.message_handler(commands=["start"])
    def c_start(msg):
        uid = msg.from_user.id
        ensure_child_user(child_id, uid, msg.from_user.username, msg.from_user.full_name)
        channels = get_global_force()
        c = db()
        for r in c.execute("SELECT * FROM child_force WHERE child_id=?", (child_id,)).fetchall():
            channels.append(dict(r))
        c.close()
        if not is_child_owner(child_id, uid) and not is_admin(uid):
            ok, missing = check_force_list(bot_obj, uid, channels)
            if not ok and missing:
                bot_obj.reply_to(msg, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
                return
        if is_child_owner(child_id, uid) or is_admin(uid):
            bot_obj.reply_to(msg, f"{pe_pair(E_BOT)} لوحة المالك", reply_markup=child_owner_kb())
        else:
            bot_obj.reply_to(
                msg,
                f"{pe_pair(E_GEAR)} <b>Welcome!</b>\n"
                f"{pe_pair(E_CHECK)} Premium OTP Stock Bot\n"
                f"{pe_pair(E_CHECK)} Fast & Reliable Service\n"
                f"{pe_pair(E_FOLDER)} Please select an option below:",
                reply_markup=child_user_kb(),
                parse_mode="HTML",
            )

    @bot_obj.message_handler(commands=["otp"])
    def c_otp_cmd(msg):
        if not (is_child_owner(child_id, msg.from_user.id) or is_admin(msg.from_user.id)):
            return
        if msg.chat.type not in ("group", "supergroup"):
            bot_obj.reply_to(msg, "أرسل الأمر داخل الكروب")
            return
        c = db()
        c.execute("UPDATE child_bots SET otp_group=? WHERE id=?", (str(msg.chat.id), child_id))
        c.commit()
        c.close()
        bot_obj.reply_to(msg, f"تم تفعيل كروب OTP - يمكنك من خلالها استقبال كود - يتم حذفة الاشعار بعد 60 ثانية\nID: {msg.chat.id}")

    @bot_obj.message_handler(func=lambda m: m.text and ("Get Number" in m.text or "Get number" in m.text or "طلب رقم" in m.text))
    def c_get_number(msg):
        uid = msg.from_user.id
        chat_id = msg.chat.id
        try:
            ensure_child_user(child_id, uid, getattr(msg.from_user, "username", None), getattr(msg.from_user, "full_name", None))
        except Exception:
            pass
        # اشتراك إجباري سريع (كاش)
        if not is_child_owner(child_id, uid) and not is_admin(uid):
            try:
                channels = get_global_force()
                c = db()
                for r in c.execute("SELECT chat_id, username, title, invite_link FROM child_force WHERE child_id=?", (child_id,)).fetchall():
                    channels.append(dict(r))
                c.close()
                if channels:
                    ok, missing = check_force_list(bot_obj, uid, channels)
                    if not ok and missing:
                        safe_send(bot_obj, chat_id, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
                        return
            except Exception:
                pass
        kb = services_ikb()
        safe_send(bot_obj, chat_id, f"{pe_pair(E_GEAR)} Select a Service:", reply_markup=kb)

    @bot_obj.message_handler(func=lambda m: m.text and "Live Traffic" in m.text)
    def c_live(msg):
        ensure_child_user(child_id, msg.from_user.id)
        since = time.time() - 1800
        c = db()
        rows = c.execute(
            "SELECT country, COUNT(*) as n FROM code_log WHERE child_id=? AND created_at>? GROUP BY country ORDER BY n DESC LIMIT 10",
            (child_id, since)
        ).fetchall()
        c.close()
        text = f"{pe_pair(E_WEB)} <b>Live Traffic - Last 30 Minutes</b>\n\n"
        if not rows:
            text += "No activity."
        else:
            for r in rows:
                name = r["country"] or "Unknown"
                n = r["n"]
                lvl = "HIGH" if n >= 10 else ("MEDIUM" if n >= 3 else "LOW")
                text += f"{plain_flag(name)} {name}: {n} ({lvl})\n"
        bot_obj.reply_to(msg, text, parse_mode="HTML")

    @bot_obj.message_handler(func=lambda m: m.text and "My Profile" in m.text)
    def c_profile(msg):
        uid = msg.from_user.id
        ensure_child_user(child_id, uid, msg.from_user.username, msg.from_user.full_name)
        c = db()
        u = c.execute("SELECT * FROM child_users WHERE child_id=? AND user_id=?", (child_id, uid)).fetchone()
        today0 = time.time() - (time.time() % 86400)
        today_n = c.execute(
            "SELECT COUNT(*) as n FROM code_log WHERE child_id=? AND user_id=? AND created_at>?",
            (child_id, uid, today0)
        ).fetchone()["n"]
        c.close()
        bal = float(u["balance"]) if u else 0
        total = int(u["total_codes"]) if u else 0
        text = (
            f"{pe_pair(E_GEAR)} <b>YOUR SETTINGS & STATS</b>\n\n"
            f"{pe_pair(E_USER)} My ID: <code>{uid}</code>\n"
            f"{pe_pair(E_CHART)} Balance: <b>{bal:.3f} USD</b>\n"
            f"{pe_pair(E_DOC)} Your Today SMS: <b>{today_n}</b>\n"
            f"{pe_pair(E_DOC)} Your Total SMS: <b>{total}</b>"
        )
        kb = types.InlineKeyboardMarkup()
        kb.row(ikb_btn("SMS History", f"cu:hist", emoji_id=E_DOC[1]))
        bot_obj.reply_to(msg, text, reply_markup=kb, parse_mode="HTML")

    @bot_obj.message_handler(func=lambda m: m.text and m.text.strip() == "Withdraw")
    def c_withdraw(msg):
        uid = msg.from_user.id
        ensure_child_user(child_id, uid)
        c = db()
        u = c.execute("SELECT balance FROM child_users WHERE child_id=? AND user_id=?", (child_id, uid)).fetchone()
        c.close()
        bal = float(u["balance"]) if u else 0
        bot_obj.reply_to(
            msg,
            f"{pe_pair(E_CHART)} Balance: <b>{bal:.3f} USD</b>\nMin: 1.0 USD\n\nتواصل مع الأدمن للسحب.",
            parse_mode="HTML",
        )

    @bot_obj.message_handler(func=lambda m: m.text and m.text.strip() == "Support")
    def c_support(msg):
        c = db()
        ch = c.execute("SELECT otp_group_link, channel_link, owner_id FROM child_bots WHERE id=?", (child_id,)).fetchone()
        c.close()
        glink = (ch["otp_group_link"] if ch else "") or OTP_GROUP_LINK
        text = (
            f"{pe_pair(E_HEART) if False else pe_pair(E_USER)} <b>« SUPPORT »</b>\n\n"
            f"Contact admin for any issues.\n"
            f"OTP Group: {glink}"
        )
        kb = types.InlineKeyboardMarkup()
        if glink:
            url = glink if glink.startswith("http") else "https://" + glink
            kb.add(ikb_btn("GROUP OTP", url=url, emoji_id=E_GROUP[1]))
        bot_obj.reply_to(msg, text, reply_markup=kb, parse_mode="HTML")

    @bot_obj.message_handler(func=lambda m: m.text and ("ToP 3" in m.text or "Top 3" in m.text or "أفضل 3" in m.text))
    def c_top3(msg):
        c = db()
        rows = c.execute(
            "SELECT username, full_name, total_codes, user_id FROM child_users WHERE child_id=? AND total_codes>0 ORDER BY total_codes DESC LIMIT 3",
            (child_id,)
        ).fetchall()
        c.close()
        text = f"{pe_pair(E_STAR)} <b>ToP 3</b>\n\n"
        medals = [pe_pair(E_STAR), "🥈", "🥉"]
        for i, r in enumerate(rows):
            name = f"@{r['username']}" if r["username"] else (r["full_name"] or str(r["user_id"]))
            text += f"{medals[i]} - {name} | {r['total_codes']} OTP\n"
        if not rows:
            text += "—"
        bot_obj.reply_to(msg, text, parse_mode="HTML")

    @bot_obj.message_handler(func=lambda m: m.text and m.text == "__disabled_service2__")
    def c_service2(msg):
        ensure_child_user(child_id, msg.from_user.id)
        c = db()
        rows = c.execute("SELECT * FROM owner_services").fetchall()
        c.close()
        if not rows:
            bot_obj.reply_to(msg, "Service 2 فارغ حالياً")
            return
        bot_obj.reply_to(msg, f"{pe_pair(E_GEAR)} Service 2:", reply_markup=owner_services_ikb())

    @bot_obj.callback_query_handler(func=lambda call: True)
    def c_callback(call):
        data = call.data or ""
        uid = call.from_user.id
        try:
            bot_obj.answer_callback_query(call.id, cache_time=0)
        except Exception:
            pass
        # قوائم شفافة للمستخدم / المالك
        if data in ("cu:get", "co:get"):
            uid2 = call.from_user.id
            chat_id = call.message.chat.id
            try:
                ensure_child_user(child_id, uid2, getattr(call.from_user, "username", None), getattr(call.from_user, "full_name", None))
            except Exception:
                pass
            if not is_child_owner(child_id, uid2) and not is_admin(uid2):
                try:
                    channels = get_global_force()
                    c = db()
                    for r in c.execute("SELECT chat_id, username, title, invite_link FROM child_force WHERE child_id=?", (child_id,)).fetchall():
                        channels.append(dict(r))
                    c.close()
                    if channels:
                        ok, missing = check_force_list(bot_obj, uid2, channels)
                        if not ok and missing:
                            safe_send(bot_obj, chat_id, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
                            return
                except Exception:
                    pass
            safe_send(bot_obj, chat_id, f"{pe_pair(E_GEAR)} Select a Service:", reply_markup=services_ikb())
            return
        if data == "cu:live":
            bot_obj.send_message(call.message.chat.id, "Live Traffic — قريباً")
            return
        if data == "cu:prof":
            ensure_child_user(child_id, uid)
            c = db()
            u = c.execute("SELECT * FROM child_users WHERE child_id=? AND user_id=?", (child_id, uid)).fetchone()
            c.close()
            bal = u["balance"] if u else 0
            tc = u["total_codes"] if u else 0
            bot_obj.send_message(call.message.chat.id, f"{pe_pair(E_USER)} Profile\nBalance: {bal:.3f}\nOTP: {tc}")
            return
        if data == "cu:top":
            c = db()
            rows = c.execute(
                "SELECT username, full_name, total_codes, user_id FROM child_users WHERE child_id=? AND total_codes>0 ORDER BY total_codes DESC LIMIT 3",
                (child_id,)
            ).fetchall()
            c.close()
            text = f"{pe_pair(E_STAR)} ToP 3\n\n"
            medals = ["🎖", "🥈", "🥉"]
            for i, r in enumerate(rows):
                name = f"@{r['username']}" if r["username"] else (r["full_name"] or str(r["user_id"]))
                text += f"{medals[i]} {name} | {r['total_codes']}\n"
            bot_obj.send_message(call.message.chat.id, text or "—")
            return
        if data == "cu:wd":
            bot_obj.send_message(call.message.chat.id, "السحب من بوت المصنع ← أرباحي")
            return
        if data == "co:ff":
            if is_child_owner(child_id, uid) or is_admin(uid):
                user_state[uid] = {"step": "child_force", "child_id": child_id}
                bot_obj.send_message(call.message.chat.id, "رفع البوت مشرف في القناة - المجموعة وبعدها ارسال الرابط")
            return
        if data == "co:dff":
            if is_child_owner(child_id, uid) or is_admin(uid):
                c = db()
                rows = c.execute("SELECT * FROM child_force WHERE child_id=?", (child_id,)).fetchall()
                c.close()
                if not rows:
                    bot_obj.send_message(call.message.chat.id, "لا قنوات")
                    return
                text = "أرسل رقم القناة:\n"
                for i, r in enumerate(rows, 1):
                    text += f"f{i} — {r['title'] or r['chat_id']}\n"
                user_state[uid] = {"step": "child_del_force", "child_id": child_id, "rows": [dict(r) for r in rows]}
                bot_obj.send_message(call.message.chat.id, text)
            return
        if data == "co:otp":
            if is_child_owner(child_id, uid) or is_admin(uid):
                user_state[uid] = {"step": "child_otp", "child_id": child_id}
                bot_obj.send_message(call.message.chat.id, "أرسل أيدي الكروب أو رابط الدعوة\nثم /otp داخل الكروب")
            return
        if data == "co:dotp":
            if is_child_owner(child_id, uid) or is_admin(uid):
                c = db()
                c.execute("UPDATE child_bots SET otp_group='', otp_group_link='' WHERE id=?", (child_id,))
                c.commit()
                c.close()
                bot_obj.send_message(call.message.chat.id, "تم حذف كروب OTP")
            return
        if data == "co:ch":
            if is_child_owner(child_id, uid) or is_admin(uid):
                user_state[uid] = {"step": "child_channel", "child_id": child_id}
                bot_obj.send_message(call.message.chat.id, "أرسل رابط القناة لزر Channel")
            return
        if data == "co:dch":
            if is_child_owner(child_id, uid) or is_admin(uid):
                c = db()
                c.execute("UPDATE child_bots SET channel_link='' WHERE id=?", (child_id,))
                c.commit()
                c.close()
                bot_obj.send_message(call.message.chat.id, "تم")
            return
        if data == "co:st":
            c = db()
            ch = c.execute("SELECT total_codes FROM child_bots WHERE id=?", (child_id,)).fetchone()
            users = c.execute("SELECT COUNT(*) as n FROM child_users WHERE child_id=?", (child_id,)).fetchone()
            c.close()
            bot_obj.send_message(call.message.chat.id, f"الأكواد: {ch['total_codes'] if ch else 0}\nالمستخدمين: {users['n'] if users else 0}")
            return
        if data == "co:bc":
            if is_child_owner(child_id, uid) or is_admin(uid):
                user_state[uid] = {"step": "child_bc", "child_id": child_id}
                bot_obj.send_message(call.message.chat.id, "أرسل نص الإذاعة لمستخدمي بوتك:")
            return
        if data == "force_check":
            channels = get_global_force()
            c = db()
            for r in c.execute("SELECT * FROM child_force WHERE child_id=?", (child_id,)).fetchall():
                channels.append(dict(r))
            c.close()
            ok, missing = check_force_list(bot_obj, uid, channels)
            if ok:
                try:
                    bot_obj.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                bot_obj.send_message(
                    call.message.chat.id,
                    f"{pe_pair(E_GEAR)} <b>Welcome!</b>\n{pe_pair(E_CHECK)} Premium OTP Stock Bot\n{pe_pair(E_CHECK)} Fast & Reliable Service\n{pe_pair(E_FOLDER)} Please select an option below:",
                    reply_markup=child_user_kb(),
                    parse_mode="HTML",
                )
            else:
                try:
                    bot_obj.answer_callback_query(call.id, "لم تشترك بعد", show_alert=True)
                except Exception:
                    pass
            return
        if data == "home" or data == "back_u":
            try:
                bot_obj.edit_message_text(f"{pe_pair(E_GEAR)} Select a Service:", call.message.chat.id, call.message.message_id, reply_markup=services_ikb())
            except Exception:
                bot_obj.send_message(call.message.chat.id, "Select a Service:", reply_markup=services_ikb())
            return
        if data.startswith("svc:") or data.startswith("osvc:"):
            sid = int(data.split(":")[1])
            pref = "ocnt" if data.startswith("osvc:") else "cnt"
            chat_id = call.message.chat.id
            mid = call.message.message_id
            def _svc():
                kb = countries_ikb(sid, pref)
                title = "Service 2 — Country:" if pref == "ocnt" else "Select a Country:"
                try:
                    bot_obj.edit_message_text(
                        f"{pe_pair(E_GEAR)} {title}",
                        chat_id, mid, reply_markup=kb, parse_mode="HTML"
                    )
                except Exception:
                    try:
                        bot_obj.send_message(chat_id, title, reply_markup=kb)
                    except Exception:
                        pass
            threading.Thread(target=_svc, daemon=True).start()
            return
        if data.startswith("cnt:") or data.startswith("ocnt:"):
            cid = int(data.split(":")[1])
            owner_pool = data.startswith("ocnt:")
            chat_id = call.message.chat.id
            mid = call.message.message_id
            def _cnt():
                give_numbers(bot_obj, child_id, chat_id, uid, cid, mid, owner_pool=owner_pool)
            threading.Thread(target=_cnt, daemon=True).start()
            return
        if data.startswith("chg:") or data.startswith("ochg:"):
            owner_pool = data.startswith("ochg:")
            cid = int(data.split(":")[1])
            chat_id = call.message.chat.id
            mid = call.message.message_id
            def _chg():
                c = db()
                old = c.execute("SELECT phone, show_plus FROM assigned WHERE child_id=? AND user_id=?", (child_id, uid)).fetchall()
                show_plus = bool(old[0]["show_plus"]) if old else True
                olds = [r["phone"] for r in old]
                c.close()
                give_numbers(bot_obj, child_id, chat_id, uid, cid, mid, olds, show_plus, owner_pool)
            threading.Thread(target=_chg, daemon=True).start()
            return
        if data.startswith("plus:") or data.startswith("oplus:"):
            owner_pool = data.startswith("oplus:")
            cid = int(data.split(":")[1])
            c = db()
            rows = c.execute("SELECT * FROM assigned WHERE child_id=? AND user_id=?", (child_id, uid)).fetchall()
            if not rows:
                c.close()
                return
            new_plus = 0 if rows[0]["show_plus"] else 1
            c.execute("UPDATE assigned SET show_plus=? WHERE child_id=? AND user_id=?", (new_plus, child_id, uid))
            c.commit()
            phones = [r["phone"] for r in rows]
            if owner_pool:
                country = c.execute("SELECT * FROM owner_countries WHERE id=?", (cid,)).fetchone()
                svc = c.execute("SELECT name FROM owner_services WHERE id=?", (country["service_id"],)).fetchone() if country else None
            else:
                country = c.execute("SELECT * FROM countries WHERE id=?", (cid,)).fetchone()
                svc = c.execute("SELECT name FROM services WHERE id=?", (country["service_id"],)).fetchone() if country else None
            c.close()
            text, kb = numbers_ikb(child_id, cid, phones, bool(new_plus), svc["name"] if svc else "OTP", country["name"] if country else "", owner_pool)
            try:
                bot_obj.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            return
        if data.startswith("copy:"):
            try:
                bot_obj.answer_callback_query(call.id, data.split(":", 1)[1], show_alert=True)
            except Exception:
                pass

    @bot_obj.message_handler(func=lambda m: m.text == "تعيين كروب OTP")
    def c_set_otp(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        user_state[msg.from_user.id] = {"step": "child_otp", "child_id": child_id}
        bot_obj.reply_to(msg, "أرسل أيدي الكروب أو رابط الدعوة\nثم أرسل /otp داخل الكروب")

    @bot_obj.message_handler(func=lambda m: m.text == "حذف كروب OTP")
    def c_del_otp(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        c = db()
        c.execute("UPDATE child_bots SET otp_group='', otp_group_link='' WHERE id=?", (child_id,))
        c.commit()
        c.close()
        bot_obj.reply_to(msg, "تم حذف كروب OTP")

    @bot_obj.message_handler(func=lambda m: m.text == "تعيين قناة الأزرار")
    def c_set_ch(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        user_state[msg.from_user.id] = {"step": "child_channel", "child_id": child_id}
        bot_obj.reply_to(msg, "أرسل رابط القناة لزر Channel")

    @bot_obj.message_handler(func=lambda m: m.text == "حذف قناة الأزرار")
    def c_del_ch(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        c = db()
        c.execute("UPDATE child_bots SET channel_link='' WHERE id=?", (child_id,))
        c.commit()
        c.close()
        bot_obj.reply_to(msg, "تم")

    @bot_obj.message_handler(func=lambda m: m.text in ("اشتراك إجباري", "Force Sub"))
    def c_force(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        user_state[msg.from_user.id] = {"step": "child_force", "child_id": child_id}
        bot_obj.reply_to(msg, "رفع البوت مشرف - في القناة ، المجموعة وبعدها قوم في ارسال الرابط ")

    @bot_obj.message_handler(func=lambda m: m.text == "حذف الاشتراك")
    def c_del_force(msg):
        if not is_child_owner(child_id, msg.from_user.id) and not is_admin(msg.from_user.id):
            return
        c = db()
        rows = c.execute("SELECT * FROM child_force WHERE child_id=?", (child_id,)).fetchall()
        if not rows:
            c.close()
            bot_obj.reply_to(msg, "لا قنوات")
            return
        text = "أرسل رقم القناة:\n"
        for i, r in enumerate(rows, 1):
            text += f"f{i} — {r['title'] or r['chat_id']}\n"
        user_state[msg.from_user.id] = {"step": "child_del_force", "child_id": child_id, "rows": [dict(r) for r in rows]}
        c.close()
        bot_obj.reply_to(msg, text)

    @bot_obj.message_handler(func=lambda m: m.text == "إحصائيات بوتي")
    def c_stats(msg):
        c = db()
        ch = c.execute("SELECT total_codes FROM child_bots WHERE id=?", (child_id,)).fetchone()
        users = c.execute("SELECT COUNT(*) as n FROM child_users WHERE child_id=?", (child_id,)).fetchone()
        c.close()
        bot_obj.reply_to(msg, f"الأكواد: {ch['total_codes'] if ch else 0}\nالمستخدمين: {users['n'] if users else 0}")

    @bot_obj.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("child_id") == child_id)
    def c_state(msg):
        st = user_state.get(msg.from_user.id, {})
        step = st.get("step")
        text = (msg.text or "").strip()
        if step == "child_otp":
            if text.startswith("http") or "t.me/" in text:
                c = db()
                c.execute("UPDATE child_bots SET otp_group_link=? WHERE id=?", (text, child_id))
                c.commit()
                c.close()
                bot_obj.reply_to(msg, "تم حفظ الرابط — أرسل /otp داخل الكروب لتفعيل الأيدي")
            else:
                c = db()
                c.execute("UPDATE child_bots SET otp_group=? WHERE id=?", (text, child_id))
                c.commit()
                c.close()
                bot_obj.reply_to(msg, f"تم: {text}")
            user_state.pop(msg.from_user.id, None)
        elif step == "child_channel":
            c = db()
            c.execute("UPDATE child_bots SET channel_link=? WHERE id=?", (text, child_id))
            c.commit()
            c.close()
            user_state.pop(msg.from_user.id, None)
            bot_obj.reply_to(msg, "تم")
        elif step == "child_force":
            chat_id, username, title, inv = resolve_channel(text, bot_obj)
            if not chat_id and not inv:
                bot_obj.reply_to(msg, "تعذر")
                return
            c = db()
            c.execute(
                "INSERT INTO child_force (child_id, chat_id, username, title, invite_link) VALUES (?,?,?,?,?)",
                (child_id, chat_id or inv, username, title, inv)
            )
            c.commit()
            c.close()
            user_state.pop(msg.from_user.id, None)
            bot_obj.reply_to(msg, "تم")
        elif step == "child_del_force":
            rows = st.get("rows") or []
            try:
                i = int(text.lower().lstrip("f")) - 1
                row = rows[i]
                c = db()
                c.execute("DELETE FROM child_force WHERE id=?", (row["id"],))
                c.commit()
                c.close()
                bot_obj.reply_to(msg, "تم الحذف")
            except Exception:
                bot_obj.reply_to(msg, "رقم غير صالح")
            user_state.pop(msg.from_user.id, None)

    @bot_obj.message_handler(func=lambda m: True, content_types=["text"])
    def c_group_otp(msg):
        c = db()
        ch = c.execute("SELECT otp_group FROM child_bots WHERE id=?", (child_id,)).fetchone()
        c.close()
        if not ch or not ch["otp_group"]:
            return
        if str(msg.chat.id) != str(ch["otp_group"]):
            return
        if msg.from_user and msg.from_user.is_bot:
            return
        phone, code = extract_otp(msg.text or "")
        if phone and code:
            process_otp(phone, code, "group", msg.text or "")

# ===================== FACTORY HANDLERS =====================


def _admin_lang(uid):
    return "ar"

@factory.callback_query_handler(func=lambda c: c.data and (c.data.startswith("fa:") or c.data.startswith("fu:")))
def factory_menu_cb(call):
    uid = call.from_user.id
    data = (call.data or "").strip()
    chat_id = call.message.chat.id
    try:
        factory.answer_callback_query(call.id)
    except Exception:
        pass

    # --- صانع: تنفيذ مباشر سريع ---
    if data == "fu:create":
        ensure_factory_user(uid, getattr(call.from_user, "username", None), getattr(call.from_user, "full_name", None))
        c = db()
        rows = c.execute("SELECT id, bot_username FROM child_bots WHERE owner_id=? AND is_active=1", (uid,)).fetchall()
        c.close()
        if len(rows) >= 2 and not is_admin(uid):
            names = ", ".join([("@" + r["bot_username"]) if r["bot_username"] else f"#{r['id']}" for r in rows])
            safe_send(factory, chat_id, f"الحد الأقصى بوتان فقط\nبوتاتك: {names}")
            return
        if rows:
            safe_send(factory, chat_id, f"لديك {len(rows)}/2 بوت — البوت الثاني يحتاج توكن وكروب وقناة جديدة")
        # force check cached — لا يعلّق
        if not is_admin(uid):
            ok, missing = check_force_list(factory, uid, get_factory_force())
            if not ok and missing:
                safe_send(factory, chat_id, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
                return
        user_state[uid] = {"step": "token"}
        safe_send(factory, chat_id, f"{pe_pair(E_BOT)} أرسل توكن البوت من @BotFather")
        return

    if data == "fu:mybots":
        c = db()
        rows = c.execute("SELECT * FROM child_bots WHERE owner_id=?", (uid,)).fetchall()
        c.close()
        if not rows:
            safe_send(factory, chat_id, "لا توجد بوتات")
            return
        for r in rows:
            un = f"@{r['bot_username']}" if r["bot_username"] else f"#{r['id']}"
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                ikb_btn("تغير توكن", callback_data=f"chgtok:{r['id']}", emoji_id=E_TOKEN[1]),
                ikb_btn("تغير كروب", callback_data=f"chggrp:{r['id']}", emoji_id=E_GROUP[1]),
            )
            kb.add(
                ikb_btn("تغير قناة", callback_data=f"chgch:{r['id']}", emoji_id=E_CHANNEL[1]),
                ikb_btn("حذف البوت", callback_data=f"delbot:{r['id']}", emoji_id=E_DEL[1]),
            )
            safe_send(
                factory, chat_id,
                f"{pe_pair(E_BOT)} {un}\nالأكواد: {r['total_codes']}\nكروب: {r['otp_group'] or '-'}",
                reply_markup=kb,
            )
        return

    if data == "fu:money":
        bal = get_maker_balance(uid)
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn("سحب رصيد", callback_data="wd_start", emoji_id=E_MONEY[1]))
        safe_send(factory, chat_id, f"{pe_pair(E_MONEY)} رصيدك: {bal:.3f} USD\nالحد الأدنى: {MIN_WITHDRAW}$", reply_markup=kb)
        return

    if not is_admin(uid):
        return

    mapping = {
        "fa:svc": ("إضافة خدمة", "a_svc"),
        "fa:cnt": ("إضافة دولة+ملف", "a_cnt"),
        "fa:delc": ("حذف دولة", "a_del_cnt"),
        "fa:dels": ("حذف سيرفر", "a_del_cnt"),
        "fa:earn": ("تعيين أرباح", "a_earn"),
        "fa:ff": ("اشتراك إجباري", "a_force"),
        "fa:fg": ("اشتراك إجباري للجميع", "a_gforce"),
        "fa:dff": ("حذف الإجباري", "a_del_force"),
        "fa:dfg": ("حذف الإجباري للجميع", "a_del_gforce"),
        "fa:bc": ("إذاعة", "a_bc"),
        "fa:st": ("إحصائيات", "a_stats"),
        "fa:top": ("أفضل 5 بوتات", "a_top5"),
        "fa:mac": ("إشعار الماكرون", "a_mac"),
        "fa:dmac": ("حذف الماكرون", "a_mac_del"),
        "fa:pmac": ("نشر الماكرون", "a_mac_pub"),
        "fa:fake": ("إشعار وهمي", "a_fake"),
        "fa:wd": ("طلبات السحب", "a_wd"),
        "fa:list": ("عرض الخدمات", "a_list_svc"),
    }
    if data not in mapping:
        return
    text, fn_name = mapping[data]
    class M:
        pass
    m = M()
    m.from_user = call.from_user
    m.chat = call.message.chat
    m.message_id = call.message.message_id
    m.text = text
    m.document = None
    m.content_type = "text"
    fn = globals().get(fn_name)
    if not fn:
        safe_send(factory, chat_id, "أمر غير متاح")
        return
    try:
        fn(m)
    except Exception as e:
        safe_send(factory, chat_id, f"خطأ: {type(e).__name__}: {e}")



@factory.message_handler(commands=["start", "help"])
def f_start(msg):
    uid = msg.from_user.id
    try:
        ensure_factory_user(uid, msg.from_user.username, msg.from_user.full_name)
    except Exception:
        pass
    c = db()
    u = c.execute("SELECT * FROM factory_users WHERE user_id=?", (uid,)).fetchone()
    c.close()
    if u and u["is_banned"]:
        factory.reply_to(msg, "تم حظرك.")
        return
    if not is_admin(uid):
        ok, missing = check_force_list(factory, uid, get_factory_force())
        if not ok and missing:
            safe_reply(factory, msg, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
            return
    if not u or not u["lang"]:
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn("العربية", callback_data="lang:ar"), ikb_btn("English", callback_data="lang:en"))
        factory.reply_to(msg, "اختر اللغة / Choose language:", reply_markup=kb)
        return
    lang = u["lang"] if u else "ar"
    if is_admin(uid):
        factory.reply_to(msg, f"{pe_pair(E_BOT)} لوحة مالك المصنع", reply_markup=factory_admin_kb())
    else:
        factory.reply_to(msg, f"{pe_pair(E_BOT)} مرحباً بك في مصنع بوتات OTP", reply_markup=factory_user_kb(lang))

@factory.callback_query_handler(func=lambda c: c.data and c.data.startswith("lang:"))
def f_lang(call):
    lang = call.data.split(":")[1]
    c = db()
    c.execute("UPDATE factory_users SET lang=? WHERE user_id=?", (lang, call.from_user.id))
    c.commit()
    c.close()
    try:
        factory.answer_callback_query(call.id)
        factory.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    if is_admin(call.from_user.id):
        factory.send_message(call.message.chat.id, f"{pe_pair(E_BOT)} لوحة مالك المصنع", reply_markup=factory_admin_kb())
    else:
        factory.send_message(call.message.chat.id, f"{pe_pair(E_BOT)} مرحباً", reply_markup=factory_user_kb(lang))

@factory.callback_query_handler(func=lambda c: c.data == "force_check")
def f_force_check(call):
    ok, missing = check_force_list(factory, call.from_user.id, get_factory_force())
    if ok:
        try:
            factory.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        factory.send_message(call.message.chat.id, f"{pe_pair(E_BOT)} مرحباً بك في مصنع بوتات OTP", reply_markup=factory_user_kb("ar"))
        factory.answer_callback_query(call.id, "تم")
    else:
        factory.answer_callback_query(call.id, "لم تشترك بعد", show_alert=True)

@factory.message_handler(func=lambda m: m.text in ("صنع بوت", "Create Bot"))
def f_create(msg):
    uid = msg.from_user.id
    ensure_factory_user(uid, msg.from_user.username, msg.from_user.full_name)
    c = db()
    rows = c.execute("SELECT id, bot_username FROM child_bots WHERE owner_id=? AND is_active=1", (uid,)).fetchall()
    c.close()
    if len(rows) >= 2 and not is_admin(uid):
        names = ", ".join([("@" + r["bot_username"]) if r["bot_username"] else f"#{r['id']}" for r in rows])
        safe_reply(factory, msg, f"الحد الأقصى بوتان فقط\nبوتاتك: {names}")
        return
    if rows:
        safe_reply(factory, msg, f"لديك {len(rows)}/2 بوت — البوت الثاني يحتاج توكن وكروب وقناة جديدة")
    ok, missing = check_force_list(factory, uid, get_factory_force())
    if not ok and missing and not is_admin(uid):
        safe_reply(factory, msg, f"{pe_pair(E_LOCK)} يجب الاشتراك أولاً:", reply_markup=force_kb(missing))
        return
    user_state[uid] = {"step": "token"}
    safe_reply(factory, msg, f"{pe_pair(E_BOT)} أرسل توكن البوت من @BotFather")

@factory.message_handler(func=lambda m: m.text in ("بوتاتي", "My Bots"))
def f_mybots(msg):
    c = db()
    rows = c.execute("SELECT * FROM child_bots WHERE owner_id=?", (msg.from_user.id,)).fetchall()
    c.close()
    if not rows:
        safe_reply(factory, msg, "لا توجد بوتات")
        return
    for r in rows:
        un = f"@{r['bot_username']}" if r["bot_username"] else f"#{r['id']}"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            ikb_btn("تغير توكن", callback_data=f"chgtok:{r['id']}", emoji_id=E_TOKEN[1]),
            ikb_btn("تغير كروب", callback_data=f"chggrp:{r['id']}", emoji_id=E_GROUP[1]),
        )
        kb.add(
            ikb_btn("تغير قناة", callback_data=f"chgch:{r['id']}", emoji_id=E_CHANNEL[1]),
            ikb_btn("حذف البوت", callback_data=f"delbot:{r['id']}", emoji_id=E_DEL[1]),
        )
        factory.send_message(
            msg.chat.id,
            f"{pe_pair(E_BOT)} {un}\nالأكواد: {r['total_codes']}\nكروب: {r['otp_group'] or '-'}",
            reply_markup=kb
        )

@factory.message_handler(func=lambda m: m.text in ("أرباحي", "My Earnings", "/money"))
def f_money(msg):
    bal = get_maker_balance(msg.from_user.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(ikb_btn("سحب رصيد", callback_data="wd_start", emoji_id=E_MONEY[1]))
    safe_reply(factory, msg, f"{pe_pair(E_MONEY)} رصيدك: {bal:.3f} USD\nالحد الأدنى: {MIN_WITHDRAW}$", reply_markup=kb)

@factory.callback_query_handler(func=lambda c: c.data == "wd_start")
def wd_start(call):
    if get_maker_balance(call.from_user.id) < MIN_WITHDRAW:
        factory.answer_callback_query(call.id, f"أقل من {MIN_WITHDRAW}$", show_alert=True)
        return
    kb = types.InlineKeyboardMarkup(row_width=2)
    for net in ("TON", "TRX", "نجوم", "آسيا", "BEP20", "أخرى"):
        kb.add(ikb_btn(net, callback_data=f"wdnet:{net}"))
    factory.edit_message_text("اختر الشبكة:", call.message.chat.id, call.message.message_id, reply_markup=kb)
    factory.answer_callback_query(call.id)

@factory.callback_query_handler(func=lambda c: c.data and c.data.startswith("wdnet:"))
def wd_net(call):
    net = call.data.split(":", 1)[1]
    user_state[call.from_user.id] = {"step": "wd_addr", "network": net}
    factory.answer_callback_query(call.id)
    factory.send_message(call.message.chat.id, f"أرسل عنوان {net}:")

@factory.callback_query_handler(func=lambda c: c.data and (c.data.startswith("delbot:") or c.data.startswith("chgtok:") or c.data.startswith("chggrp:") or c.data.startswith("chgch:")))
def f_bot_actions(call):
    action, cid = call.data.split(":")
    cid = int(cid)
    c = db()
    row = c.execute("SELECT * FROM child_bots WHERE id=?", (cid,)).fetchone()
    c.close()
    if not row or (row["owner_id"] != call.from_user.id and not is_admin(call.from_user.id)):
        factory.answer_callback_query(call.id, "غير مسموح", show_alert=True)
        return
    if action == "delbot":
        c = db()
        c.execute("UPDATE child_bots SET is_active=0 WHERE id=?", (cid,))
        c.commit()
        c.close()
        with child_lock:
            child_bots.pop(cid, None)
        factory.answer_callback_query(call.id, "تم الحذف")
        factory.edit_message_text("تم حذف البوت", call.message.chat.id, call.message.message_id)
    elif action == "chgtok":
        user_state[call.from_user.id] = {"step": "chg_token", "child_id": cid}
        factory.answer_callback_query(call.id)
        factory.send_message(call.message.chat.id, "أرسل التوكن الجديد:")
    elif action == "chggrp":
        user_state[call.from_user.id] = {"step": "chg_group", "child_id": cid}
        factory.answer_callback_query(call.id)
        factory.send_message(call.message.chat.id, "أرسل أيدي أو رابط الكروب:")
    elif action == "chgch":
        user_state[call.from_user.id] = {"step": "chg_channel", "child_id": cid}
        factory.answer_callback_query(call.id)
        factory.send_message(call.message.chat.id, "أرسل رابط القناة:")

@factory.callback_query_handler(func=lambda c: c.data in ("wd_ok", "wd_no") or (c.data and (c.data.startswith("wdap:") or c.data.startswith("wdrj:"))))
def wd_confirm_admin(call):
    if call.data in ("wd_ok", "wd_no"):
        st = user_state.pop(call.from_user.id, {})
        if call.data == "wd_no":
            factory.answer_callback_query(call.id, "أُلغي")
            return
        amount = float(st.get("amount") or 0)
        bal = get_maker_balance(call.from_user.id)
        if amount < MIN_WITHDRAW or amount > bal:
            factory.answer_callback_query(call.id, "رصيد غير كافٍ", show_alert=True)
            return
        c = db()
        c.execute("UPDATE maker_balance SET balance=balance-? WHERE owner_id=?", (amount, call.from_user.id))
        c.execute(
            "INSERT INTO withdraw_req (owner_id, network, address, amount, status, created_at) VALUES (?,?,?,?,?,?)",
            (call.from_user.id, st.get("network"), st.get("address"), amount, "pending", time.time())
        )
        c.commit()
        wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.close()
        factory.answer_callback_query(call.id, "تم")
        factory.send_message(call.message.chat.id, f"طلب #{wid} قيد المراجعة")
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn("موافقة", callback_data=f"wdap:{wid}"), ikb_btn("رفض", callback_data=f"wdrj:{wid}"))
        for aid in ADMIN_IDS:
            try:
                factory.send_message(aid, f"سحب #{wid}\nمن: {call.from_user.id}\n{st.get('network')}\n{st.get('address')}\n{amount}$", reply_markup=kb)
            except Exception:
                pass
        return
    if not is_admin(call.from_user.id):
        return
    action, wid = call.data.split(":")
    wid = int(wid)
    c = db()
    row = c.execute("SELECT * FROM withdraw_req WHERE id=?", (wid,)).fetchone()
    if not row or row["status"] != "pending":
        c.close()
        factory.answer_callback_query(call.id, "منتهي")
        return
    if action == "wdap":
        c.execute("UPDATE withdraw_req SET status='paid' WHERE id=?", (wid,))
        c.commit()
        c.close()
        try:
            factory.send_message(row["owner_id"], f"تم تنفيذ السحب #{wid}\n{row['amount']}$")
        except Exception:
            pass
        factory.answer_callback_query(call.id, "موافقة")
    else:
        c.execute("UPDATE withdraw_req SET status='rejected' WHERE id=?", (wid,))
        c.execute("UPDATE maker_balance SET balance=balance+? WHERE owner_id=?", (row["amount"], row["owner_id"]))
        c.commit()
        c.close()
        try:
            factory.send_message(row["owner_id"], f"رُفض السحب #{wid}")
        except Exception:
            pass
        factory.answer_callback_query(call.id, "رفض")

# Admin buttons
@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إضافة خدمة", "Add Service"))
def a_svc(msg):
    admin_state[msg.from_user.id] = {"step": "svc_name"}
    factory.reply_to(msg, "أرسل اسم الخدمة:")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إضافة دولة+ملف", "Add Country+File"))
def a_cnt(msg):
    admin_state[msg.from_user.id] = {"step": "cnt_svc"}
    c = db()
    rows = c.execute("SELECT * FROM services").fetchall()
    c.close()
    text = "أرسل رقم أو اسم الخدمة:\n"
    for r in rows:
        text += f"{r['id']} — {r['name']}\n"
    factory.reply_to(msg, text or "أضف خدمة أولاً")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("حذف دولة", "حذف سيرفر", "Delete Country", "Delete Server"))
def a_del_cnt(msg):
    mode = "1" if msg.text in ("حذف دولة", "Delete Country") else "server"
    admin_state[msg.from_user.id] = {"step": "del_cnt", "del_mode": mode}
    c = db()
    rows = c.execute("SELECT co.id, co.name, s.name as svc FROM countries co JOIN services s ON s.id=co.service_id").fetchall()
    c.close()
    text = "أرسل رقم الدولة:\n"
    for r in rows:
        text += f"{r['id']} — {r['svc']}/{r['name']}\n"
    factory.reply_to(msg, text or "لا دول")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("تعيين أرباح", "Set Earning"))
def a_earn(msg):
    admin_state[msg.from_user.id] = {"step": "earning"}
    factory.reply_to(msg, "أرسل قيمة الربح لكل كود (مثال 0.001):")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("اشتراك إجباري", "Force Sub Factory"))
def a_force(msg):
    admin_state[msg.from_user.id] = {"step": "force"}
    factory.reply_to(msg, "أرسل @يوزر أو أيدي أو رابط (للمصنعين فقط):")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("اشتراك إجباري للجميع", "Force Sub All"))
def a_gforce(msg):
    admin_state[msg.from_user.id] = {"step": "global_force"}
    factory.reply_to(msg, "أرسل @يوزر أو أيدي أو رابط (لكل البوتات المصنوعة):")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("حذف الإجباري", "Del Force Factory"))
def a_del_force(msg):
    c = db()
    rows = c.execute("SELECT * FROM factory_force").fetchall()
    c.close()
    if not rows:
        factory.reply_to(msg, "لا قنوات")
        return
    text = "أرسل f1 أو f2...\n"
    for i, r in enumerate(rows, 1):
        text += f"f{i} — {r['title'] or r['username'] or r['chat_id']}\n"
    admin_state[msg.from_user.id] = {"step": "del_force", "rows": [dict(r) for r in rows]}
    factory.reply_to(msg, text)

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("حذف الإجباري للجميع", "Del Force All"))
def a_del_gforce(msg):
    c = db()
    rows = c.execute("SELECT * FROM global_force").fetchall()
    c.close()
    if not rows:
        factory.reply_to(msg, "لا قنوات")
        return
    text = "أرسل f1 أو f2...\n"
    for i, r in enumerate(rows, 1):
        text += f"f{i} — {r['title'] or r['username'] or r['chat_id']}\n"
    admin_state[msg.from_user.id] = {"step": "del_gforce", "rows": [dict(r) for r in rows]}
    factory.reply_to(msg, text)

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إذاعة", "Broadcast"))
def a_bc(msg):
    admin_state[msg.from_user.id] = {"step": "broadcast"}
    factory.reply_to(msg, "أرسل الإذاعة (نص / صورة / أي شيء):")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إحصائيات", "Stats"))
def a_stats(msg):
    c = db()
    total_codes = c.execute("SELECT COALESCE(SUM(total_codes),0) as n FROM child_bots").fetchone()["n"]
    makers = c.execute("SELECT COUNT(*) as n FROM factory_users").fetchone()["n"]
    children = c.execute("SELECT COUNT(*) as n FROM child_bots WHERE is_active=1").fetchone()["n"]
    users = c.execute("SELECT COUNT(*) as n FROM child_users").fetchone()["n"]
    c.close()
    factory.reply_to(msg, f"{pe_pair(E_CHART)} إحصائيات\n\nأكواد البوتات: {total_codes}\nمصنعين: {makers}\nبوتات نشطة: {children}\nمستخدمين البوتات: {users}")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("أفضل 5 بوتات", "Top 5 Bots"))
def a_top5(msg):
    c = db()
    rows = c.execute("SELECT id, owner_id, bot_username, total_codes FROM child_bots WHERE is_active=1 ORDER BY total_codes DESC LIMIT 5").fetchall()
    c.close()
    text = f"{pe_pair(E_STAR)} أفضل 5 بوتات\n\n"
    for i, r in enumerate(rows, 1):
        un = f"@{r['bot_username']}" if r["bot_username"] else f"#{r['id']}"
        text += f"{i}. {un} | مالك: {r['owner_id']} | {r['total_codes']} OTP\n"
    factory.reply_to(msg, text if rows else "لا بيانات")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "__disabled_own__")
def a_own(msg):
    admin_state[msg.from_user.id] = {"step": "own_svc"}
    factory.reply_to(msg, "أرسل اسم الخدمة (Service 2):")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "__disabled_own_del__")
def a_own_del(msg):
    admin_state[msg.from_user.id] = {"step": "own_del_svc"}
    factory.reply_to(msg, "أرسل اسم الخدمة للحذف:")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إشعار الماكرون", "Macaron Ads"))
def a_mac(msg):
    admin_state[msg.from_user.id] = {"step": "mac_text"}
    factory.reply_to(msg, "أرسل نص الإشعار:")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("حذف الماكرون", "Del Macaron"))
def a_mac_del(msg):
    c = db()
    c.execute("UPDATE macaron_ads SET is_active=0")
    c.commit()
    c.close()
    factory.reply_to(msg, "تم إيقاف الماكرون")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("نشر الماكرون", "Publish Macaron"))
def a_mac_pub(msg):
    c = db()
    ads = c.execute("SELECT * FROM macaron_ads WHERE is_active=1 ORDER BY id DESC LIMIT 5").fetchall()
    children = c.execute("SELECT * FROM child_bots WHERE is_active=1").fetchall()
    c.close()
    if not ads:
        factory.reply_to(msg, "لا إشعارات ماكرون نشطة — أنشئ من إشعار الماكرون أولاً")
        return
    ok_bot = ok_grp = ok_ch = fail = 0
    for ad in ads:
        kb = types.InlineKeyboardMarkup()
        url = (ad["url"] or "").strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        if url:
            kb.add(ikb_btn("افتح", url=url, emoji_id=E_LINK[1]))
        text = ad["text"] or ""
        for ch in children:
            if ad["min_otp"] and (ch["total_codes"] or 0) < ad["min_otp"]:
                continue
            b = get_child_bot(ch["id"])
            if not b:
                fail += 1
                continue
            # to owner via child bot
            try:
                sent = b.send_message(ch["owner_id"], text, reply_markup=kb, parse_mode="HTML")
                ok_bot += 1
                with pending_lock:
                    pending_deletes.append((b, sent.chat.id, sent.message_id, time.time() + (ad["delete_after"] or 3600)))
            except Exception:
                fail += 1
            # OTP group
            gid = (ch["otp_group"] or "").strip()
            if gid:
                try:
                    tgt = int(gid) if gid.lstrip("-").isdigit() else gid
                    sent = b.send_message(tgt, text, reply_markup=kb, parse_mode="HTML")
                    ok_grp += 1
                    with pending_lock:
                        pending_deletes.append((b, sent.chat.id, sent.message_id, time.time() + (ad["delete_after"] or 3600)))
                except Exception:
                    fail += 1
            # channel
            clink = (ch["channel_link"] or "").strip()
            if clink:
                try:
                    # try as @username or id
                    tgt = clink
                    if "t.me/" in clink:
                        tgt = clink.rstrip("/").split("/")[-1]
                        if tgt.startswith("+"):
                            tgt = clink
                        else:
                            tgt = "@" + tgt.lstrip("@")
                    sent = b.send_message(tgt, text, reply_markup=kb, parse_mode="HTML")
                    ok_ch += 1
                    with pending_lock:
                        pending_deletes.append((b, sent.chat.id, sent.message_id, time.time() + (ad["delete_after"] or 3600)))
                except Exception:
                    fail += 1
    factory.reply_to(msg, f"نشر الماكرون\nبوتات: {ok_bot}\nكروبات: {ok_grp}\nقنوات: {ok_ch}\nفشل: {fail}")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("إشعار وهمي", "Fake OTP"))
def a_fake(msg):
    admin_state[msg.from_user.id] = {"step": "fake_all"}
    factory.reply_to(msg, "الصيغة:\nالدولة|الرقم|الكود|الخدمة")

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("طلبات السحب", "Withdraw Requests"))
def a_wd(msg):
    c = db()
    rows = c.execute("SELECT * FROM withdraw_req WHERE status='pending' ORDER BY id DESC LIMIT 20").fetchall()
    c.close()
    if not rows:
        factory.reply_to(msg, "لا طلبات")
        return
    for r in rows:
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn("موافقة", callback_data=f"wdap:{r['id']}"), ikb_btn("رفض", callback_data=f"wdrj:{r['id']}"))
        factory.send_message(msg.chat.id, f"#{r['id']} | {r['owner_id']}\n{r['network']} | {r['amount']}$\n{r['address']}", reply_markup=kb)

@factory.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("عرض الخدمات", "List Services"))
def a_list_svc(msg):
    c = db()
    rows = c.execute("SELECT s.name, COUNT(co.id) as n FROM services s LEFT JOIN countries co ON co.service_id=s.id GROUP BY s.id").fetchall()
    c.close()
    text = "الخدمات:\n"
    for r in rows:
        text += f"— {r['name']} ({r['n']} دول)\n"
    factory.reply_to(msg, text or "فارغ")

@factory.message_handler(func=lambda m: m.from_user.id in user_state or m.from_user.id in admin_state, content_types=["text", "document", "photo", "video", "animation"])
def f_states(msg):
    uid = msg.from_user.id
    text = (msg.text or "").strip()

    # user create bot flow
    st = user_state.get(uid, {})
    if st.get("step") == "token":
        token = text
        try:
            tb = telebot.TeleBot(token, parse_mode="HTML")
            me = tb.get_me()
        except Exception:
            factory.reply_to(msg, "توكن غير صالح")
            return
        st["token"] = token
        st["bot_username"] = me.username
        st["bot_id"] = me.id
        st["step"] = "owner_confirm"
        user_state[uid] = st
        factory.reply_to(msg, f"البوت: @{me.username}\nأرسل أيدي المالك (رقمك أو أيدي آخر):")
        return
    if st.get("step") == "owner_confirm":
        try:
            owner_id = int(text)
        except Exception:
            factory.reply_to(msg, "أيدي غير صالح")
            return
        st["owner_id"] = owner_id
        st["step"] = "otp_group_create"
        user_state[uid] = st
        factory.reply_to(msg, "أرسل أيدي كروب OTP أو رابط الدعوة (أو - لتخطي):")
        return
    if st.get("step") == "otp_group_create":
        otp_group = "" if text == "-" else text
        otp_link = text if ("t.me" in text or text.startswith("http")) else ""
        otp_id = text if text.lstrip("-").isdigit() else ""
        token = st["token"]
        c = db()
        c.execute(
            "INSERT INTO child_bots (owner_id, token_enc, bot_username, bot_id, otp_group, otp_group_link, total_codes, is_active, created_at) VALUES (?,?,?,?,?,?,0,1,?)",
            (st.get("owner_id", uid), encrypt_token(token), st.get("bot_username"), st.get("bot_id"), otp_id, otp_link, time.time())
        )
        c.commit()
        child_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.close()
        user_state.pop(uid, None)
        ok = start_child_bot(child_id)
        factory.reply_to(
            msg,
            f"{pe_pair(E_CHECK)} تم إنشاء البوت\n@{st.get('bot_username')}\n"
            f"{'شغال' if ok else 'تعذر التشغيل — تحقق من التوكن'}\n"
            f"ارفع البوت مشرف بالكروب وأرسل /otp داخله",
            reply_markup=factory_user_kb("ar")
        )
        return
    if st.get("step") == "wd_addr":
        st["address"] = text
        st["step"] = "wd_amount"
        user_state[uid] = st
        bal = get_maker_balance(uid)
        factory.reply_to(msg, f"رصيدك {bal:.3f}$\nأرسل المبلغ (حد أدنى {MIN_WITHDRAW}):")
        return
    if st.get("step") == "wd_amount":
        try:
            amount = float(text.replace(",", "."))
        except Exception:
            factory.reply_to(msg, "مبلغ غير صالح")
            return
        bal = get_maker_balance(uid)
        if amount < MIN_WITHDRAW or amount > bal:
            factory.reply_to(msg, f"بين {MIN_WITHDRAW} و {bal:.3f}")
            return
        st["amount"] = amount
        st["step"] = "wd_confirm"
        user_state[uid] = st
        kb = types.InlineKeyboardMarkup()
        kb.add(ikb_btn("تأكيد", callback_data="wd_ok"), ikb_btn("إلغاء", callback_data="wd_no"))
        factory.reply_to(msg, f"الشبكة: {st.get('network')}\nالعنوان: {st.get('address')}\nالمبلغ: {amount}$", reply_markup=kb)
        return
    if st.get("step") == "chg_token":
        try:
            tb = telebot.TeleBot(text, parse_mode="HTML")
            me = tb.get_me()
        except Exception:
            factory.reply_to(msg, "توكن غير صالح")
            return
        cid = st["child_id"]
        c = db()
        c.execute("UPDATE child_bots SET token_enc=?, bot_username=?, bot_id=? WHERE id=?",
                  (encrypt_token(text), me.username, me.id, cid))
        c.commit()
        c.close()
        with child_lock:
            child_bots.pop(cid, None)
        start_child_bot(cid)
        user_state.pop(uid, None)
        factory.reply_to(msg, f"تم — @{me.username}")
        return
    if st.get("step") == "chg_group":
        cid = st["child_id"]
        c = db()
        if "t.me" in text or text.startswith("http"):
            c.execute("UPDATE child_bots SET otp_group_link=? WHERE id=?", (text, cid))
        else:
            c.execute("UPDATE child_bots SET otp_group=? WHERE id=?", (text, cid))
        c.commit()
        c.close()
        user_state.pop(uid, None)
        factory.reply_to(msg, "تم")
        return
    if st.get("step") == "chg_channel":
        cid = st["child_id"]
        c = db()
        c.execute("UPDATE child_bots SET channel_link=? WHERE id=?", (text, cid))
        c.commit()
        c.close()
        user_state.pop(uid, None)
        factory.reply_to(msg, "تم")
        return

    # admin states
    if not is_admin(uid):
        return
    ast = admin_state.get(uid, {})
    step = ast.get("step")
    if not step:
        return
    if step == "svc_name":
        c = db()
        try:
            c.execute("INSERT INTO services (name) VALUES (?)", (text,))
            c.commit()
            factory.reply_to(msg, f"تمت إضافة: {text}", reply_markup=factory_admin_kb())
        except Exception:
            factory.reply_to(msg, "موجود مسبقاً")
        c.close()
        admin_state.pop(uid, None)
    elif step == "cnt_svc":
        c = db()
        svc = None
        if text.isdigit():
            svc = c.execute("SELECT * FROM services WHERE id=?", (int(text),)).fetchone()
        if not svc:
            svc = c.execute("SELECT * FROM services WHERE lower(name)=lower(?)", (text,)).fetchone()
        c.close()
        if not svc:
            factory.reply_to(msg, "خدمة غير موجودة")
            return
        ast["service_id"] = svc["id"]
        ast["step"] = "cnt_name"
        admin_state[uid] = ast
        factory.reply_to(msg, "أرسل اسم الدولة:")
    elif step == "cnt_name":
        ast["country_name"] = text
        ast["step"] = "cnt_file"
        admin_state[uid] = ast
        factory.reply_to(msg, "أرسل ملف TXT:")
    elif step == "cnt_file":
        if not msg.document:
            factory.reply_to(msg, "أرسل ملف")
            return
        info = factory.get_file(msg.document.file_id)
        data = factory.download_file(info.file_path)
        numbers = []
        for line in data.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if re.match(r"^\+?\d{8,15}$", line.replace(" ", "")):
                numbers.append(line)
        if not numbers:
            factory.reply_to(msg, "لا أرقام")
            return
        fname = f"{ast['service_id']}_{int(time.time())}.txt"
        save_numbers(fname, numbers)
        c = db()
        c.execute("INSERT OR REPLACE INTO countries (service_id, name, filename) VALUES (?,?,?)",
                  (ast["service_id"], ast["country_name"], fname))
        c.commit()
        c.close()
        _COUNTRIES_CACHE.clear()
        _SERVICES_CACHE["rows"] = None
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"تمت: {ast['country_name']} — {len(numbers)}", reply_markup=factory_admin_kb())
    elif step == "earning":
        try:
            set_setting("earning", float(text))
            factory.reply_to(msg, f"تم: {text}$", reply_markup=factory_admin_kb())
        except Exception:
            factory.reply_to(msg, "خطأ")
        admin_state.pop(uid, None)
    elif step == "force":
        chat_id, username, title, inv = resolve_channel(text)
        if not chat_id and not inv:
            factory.reply_to(msg, "تعذر")
            return
        c = db()
        c.execute("INSERT OR REPLACE INTO factory_force (chat_id, username, title, invite_link) VALUES (?,?,?,?)",
                  (chat_id or inv, username, title, inv))
        c.commit()
        c.close()
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"تم: {title or chat_id}", reply_markup=factory_admin_kb())
    elif step == "global_force":
        chat_id, username, title, inv = resolve_channel(text)
        if not chat_id and not inv:
            factory.reply_to(msg, "تعذر")
            return
        c = db()
        c.execute("INSERT OR REPLACE INTO global_force (chat_id, username, title, invite_link) VALUES (?,?,?,?)",
                  (chat_id or inv, username, title, inv))
        c.commit()
        c.close()
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"تم للجميع: {title or chat_id}", reply_markup=factory_admin_kb())
    elif step in ("del_force", "del_gforce"):
        rows = ast.get("rows") or []
        try:
            i = int(text.lower().lstrip("f")) - 1
            row = rows[i]
            c = db()
            table = "factory_force" if step == "del_force" else "global_force"
            c.execute(f"DELETE FROM {table} WHERE id=?", (row["id"],))
            c.commit()
            c.close()
            factory.reply_to(msg, "تم الحذف", reply_markup=factory_admin_kb())
        except Exception:
            factory.reply_to(msg, "رقم غير صالح")
        admin_state.pop(uid, None)
    elif step == "broadcast":
        c = db()
        users = c.execute("SELECT user_id FROM factory_users WHERE is_banned=0").fetchall()
        c.close()
        ok = fail = 0
        for u in users:
            try:
                factory.copy_message(u["user_id"], msg.chat.id, msg.message_id)
                ok += 1
            except Exception:
                try:
                    if text:
                        factory.send_message(u["user_id"], text)
                        ok += 1
                    else:
                        fail += 1
                except Exception:
                    fail += 1
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"نجاح: {ok} | فشل: {fail}", reply_markup=factory_admin_kb())
    elif step == "del_cnt":
        try:
            cid = int(text)
        except Exception:
            factory.reply_to(msg, "رقم")
            return
        c = db()
        co = c.execute("SELECT * FROM countries WHERE id=?", (cid,)).fetchone()
        if not co:
            c.close()
            factory.reply_to(msg, "غير موجود")
            admin_state.pop(uid, None)
            return
        path = os.path.join(NUMBERS_DIR, co["filename"] or "")
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        mode = ast.get("del_mode", "1")
        if mode == "server" or mode == "1":
            c.execute("DELETE FROM countries WHERE id=?", (cid,))
            c.execute("DELETE FROM assigned WHERE country_id=?", (cid,))
            c.commit()
            factory.reply_to(msg, f"حذف سيرفر/دولة: {co['name']}", reply_markup=factory_admin_kb())
        else:
            c.execute("UPDATE countries SET filename='' WHERE id=?", (cid,))
            c.commit()
            factory.reply_to(msg, f"حذف ملف فقط: {co['name']}", reply_markup=factory_admin_kb())
        c.close()
        admin_state.pop(uid, None)
    elif step == "own_svc":
        ast["own_name"] = text
        ast["step"] = "own_country"
        admin_state[uid] = ast
        factory.reply_to(msg, "أرسل اسم الدولة:")
    elif step == "own_country":
        ast["own_country"] = text
        ast["step"] = "own_file"
        admin_state[uid] = ast
        factory.reply_to(msg, "أرسل ملف TXT:")
    elif step == "own_file":
        if not msg.document:
            factory.reply_to(msg, "أرسل ملف")
            return
        info = factory.get_file(msg.document.file_id)
        data = factory.download_file(info.file_path)
        numbers = []
        for line in data.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if re.match(r"^\+?\d{8,15}$", line.replace(" ", "")):
                numbers.append(line)
        if not numbers:
            factory.reply_to(msg, "لا أرقام")
            return
        fname = f"own_{int(time.time())}.txt"
        save_numbers(fname, numbers)
        c = db()
        c.execute("INSERT OR IGNORE INTO owner_services (name, created_at) VALUES (?,?)", (ast.get("own_name"), time.time()))
        sid = c.execute("SELECT id FROM owner_services WHERE name=?", (ast.get("own_name"),)).fetchone()["id"]
        c.execute("INSERT OR REPLACE INTO owner_countries (service_id, name, filename) VALUES (?,?,?)",
                  (sid, ast.get("own_country"), fname))
        c.commit()
        c.close()
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"Service 2: {ast.get('own_name')}/{ast.get('own_country')} ({len(numbers)})", reply_markup=factory_admin_kb())
    elif step == "own_del_svc":
        c = db()
        rows = c.execute("SELECT * FROM owner_services WHERE lower(name)=lower(?)", (text,)).fetchall()
        if not rows:
            c.close()
            factory.reply_to(msg, "غير موجود")
            admin_state.pop(uid, None)
            return
        for r in rows:
            cos = c.execute("SELECT * FROM owner_countries WHERE service_id=?", (r["id"],)).fetchall()
            for co in cos:
                path = os.path.join(NUMBERS_DIR, co["filename"] or "")
                try:
                    if path and os.path.isfile(path):
                        os.remove(path)
                except Exception:
                    pass
            c.execute("DELETE FROM owner_countries WHERE service_id=?", (r["id"],))
            c.execute("DELETE FROM owner_services WHERE id=?", (r["id"],))
        c.commit()
        c.close()
        admin_state.pop(uid, None)
        factory.reply_to(msg, "تم الحذف", reply_markup=factory_admin_kb())
    elif step == "mac_text":
        ast["mac_text"] = text
        ast["step"] = "mac_url"
        admin_state[uid] = ast
        factory.reply_to(msg, "أرسل رابط الزر:")
    elif step == "mac_url":
        ast["mac_url"] = text
        ast["step"] = "mac_otp"
        admin_state[uid] = ast
        factory.reply_to(msg, "عدد OTP المطلوب (0=للجميع):")
    elif step == "mac_otp":
        try:
            ast["mac_otp"] = int(text)
        except Exception:
            factory.reply_to(msg, "رقم")
            return
        ast["step"] = "mac_repeat"
        admin_state[uid] = ast
        factory.reply_to(msg, "عدد التكرار:")
    elif step == "mac_repeat":
        try:
            ast["mac_repeat"] = int(text)
        except Exception:
            factory.reply_to(msg, "رقم")
            return
        ast["step"] = "mac_interval"
        admin_state[uid] = ast
        factory.reply_to(msg, "مدة التكرار بالثواني:")
    elif step == "mac_interval":
        try:
            ast["mac_interval"] = int(text)
        except Exception:
            factory.reply_to(msg, "رقم")
            return
        ast["step"] = "mac_delete"
        admin_state[uid] = ast
        factory.reply_to(msg, "وقت الحذف بالثواني:")
    elif step == "mac_delete":
        try:
            delete_after = int(text)
        except Exception:
            factory.reply_to(msg, "رقم")
            return
        c = db()
        c.execute(
            "INSERT INTO macaron_ads (text, url, min_otp, repeat_count, interval_sec, delete_after, is_active, sent_count, last_sent) VALUES (?,?,?,?,?,?,1,0,0)",
            (ast.get("mac_text"), ast.get("mac_url"), ast.get("mac_otp", 0), ast.get("mac_repeat", 1), ast.get("mac_interval", 3600), delete_after)
        )
        c.commit()
        c.close()
        admin_state.pop(uid, None)
        factory.reply_to(msg, "تم حفظ الماكرون", reply_markup=factory_admin_kb())
    elif step == "fake_all":
        parts = [x.strip() for x in text.split("|")]
        if len(parts) < 4:
            factory.reply_to(msg, "دولة|رقم|كود|خدمة")
            return
        country, phone, code, svc = parts[:4]
        ok = fail = 0
        c = db()
        children = c.execute("SELECT * FROM child_bots WHERE is_active=1").fetchall()
        c.close()
        for ch in children:
            if post_otp_child(ch["id"], phone, code, svc, country, code):
                ok += 1
            else:
                fail += 1
        admin_state.pop(uid, None)
        factory.reply_to(msg, f"نجاح: {ok} | فشل: {fail}", reply_markup=factory_admin_kb())

def poll_one_api(src):
    try:
        headers = {"Authorization": f"Bearer {src['key']}", "Accept": "application/json"}
        r = requests.get(f"{src['base']}/cdr", headers=headers, params={"records": 40}, timeout=8)
        if r.status_code != 200:
            return
        data = r.json()
        if isinstance(data, dict) and data.get("success") is False:
            return
        items = []
        if isinstance(data, dict):
            d = data.get("data")
            if isinstance(d, dict):
                items = d.get("items") or d.get("records") or []
            elif isinstance(d, list):
                items = d
            else:
                items = data.get("items") or []
        elif isinstance(data, list):
            items = data
        for item in items or []:
            if not isinstance(item, dict):
                continue
            iid = item.get("id") or item.get("msg_id")
            if not iid:
                continue
            mid = f"{src['name']}_{iid}"
            with processed_lock:
                c = db()
                if c.execute("SELECT 1 FROM processed WHERE msg_id=?", (mid,)).fetchone():
                    c.close()
                    continue
                c.execute("INSERT OR IGNORE INTO processed (msg_id) VALUES (?)", (mid,))
                c.commit()
                c.close()
            phone = str(item.get("number") or item.get("phone") or "")
            code = str(item.get("extracted_code") or item.get("code") or "")
            sms = str(item.get("sms") or item.get("message") or item.get("text") or "")
            if not re.match(r"^\d{4,8}$", str(code)):
                _, code2 = extract_otp(sms)
                if code2:
                    code = code2
            if not phone and sms:
                phone, _ = extract_otp(sms)
            if phone and code and re.match(r"^\d{4,8}$", str(code)):
                process_otp(phone, code, src["name"], sms)
    except Exception:
        pass

def api_loop():
    while True:
        if not API_SOURCES:
            time.sleep(5)
            continue
        threads = []
        for src in API_SOURCES:
            th = threading.Thread(target=poll_one_api, args=(src,), daemon=True)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(timeout=6)
        time.sleep(API_POLL)

def cleanup_loop():
    while True:
        now = time.time()
        with pending_lock:
            still = []
            for item in pending_deletes:
                if len(item) == 4:
                    bot_obj, chat_id, mid, when = item
                else:
                    continue
                if now >= when:
                    try:
                        bot_obj.delete_message(chat_id, mid)
                    except Exception:
                        pass
                else:
                    still.append(item)
            pending_deletes[:] = still
        # macaron ads
        try:
            c = db()
            ads = c.execute("SELECT * FROM macaron_ads WHERE is_active=1").fetchall()
            for ad in ads:
                if ad["sent_count"] >= ad["repeat_count"] and ad["repeat_count"] > 0:
                    continue
                if ad["last_sent"] and (now - ad["last_sent"]) < ad["interval_sec"]:
                    continue
                children = c.execute("SELECT * FROM child_bots WHERE is_active=1").fetchall()
                for ch in children:
                    if ad["min_otp"] and ch["total_codes"] < ad["min_otp"]:
                        continue
                    b = get_child_bot(ch["id"])
                    if not b:
                        continue
                    kb = types.InlineKeyboardMarkup()
                    url = ad["url"] or ""
                    if url and not url.startswith("http"):
                        url = "https://" + url
                    if url:
                        kb.add(ikb_btn("افتح", url=url))
                    try:
                        # send to owner
                        sent = b.send_message(ch["owner_id"], ad["text"], reply_markup=kb)
                        with pending_lock:
                            pending_deletes.append((b, sent.chat.id, sent.message_id, now + ad["delete_after"]))
                    except Exception:
                        pass
                c.execute("UPDATE macaron_ads SET sent_count=sent_count+1, last_sent=? WHERE id=?", (now, ad["id"]))
            c.commit()
            c.close()
        except Exception:
            pass
        time.sleep(5)

if __name__ == "__main__":
    try:
        init_db()
    except Exception:
        pass
    try:
        factory.get_me()
    except Exception:
        pass
    try:
        load_all_children()
    except Exception:
        pass
    threading.Thread(target=cleanup_loop, daemon=True).start()
    threading.Thread(target=api_loop, daemon=True).start()
    while True:
        try:
            factory.infinity_polling(timeout=10, long_polling_timeout=8, skip_pending=True, none_stop=True)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(3)
