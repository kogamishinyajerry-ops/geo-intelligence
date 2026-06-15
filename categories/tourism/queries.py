"""上海文旅景点的游客高意图问题（fan-out）。

客群分叉 = 让 recon 数据定 → A/B/C 都保留，不写死。
- Segment A（外地国内游客 / 豆包）：来上海旅游问"必去/攻略/行程" —— **当前真实侦察重心**。
- Segment C（本地客 / 豆包）：上海人周末/约会/遛娃/小众，需求与外地客不同 —— 中文真跑。
- Segment B（入境外籍游客 / 英文 AI）：老外来上海玩 —— 暂少量，待 Perplexity/OpenAI key。
theme 用于机会图分组（必去/主题/区域/时长/人群/季节/美食/小众/决策/周边）。

旅游 GEO 的核心信号 = 豆包答案里**推荐了哪些景点、谁排第一、哪些 query 答得泛（空位）**。
named_brands 字段在本项目承载【景点实体】（引擎通用字段，语义见 config/watchlist.yaml）。
"""
from __future__ import annotations

from geo.evidence.schema import BuyerSegment
from geo.recon.queries import ReconQuery

_A = BuyerSegment.A
_B = BuyerSegment.B
_C = BuyerSegment.C

QUERIES: list[ReconQuery] = [
    # ══════════ Segment A · 外地国内游客（主战场）══════════
    # ── 必去 / 通用 ×8 ──
    ReconQuery("上海必去的旅游景点有哪些", _A, theme="必去-通用"),
    ReconQuery("第一次来上海必去的地方推荐", _A, theme="必去-首次"),
    ReconQuery("上海有什么好玩的地方推荐", _A, theme="必去-通用"),
    ReconQuery("上海十大著名景点排名", _A, intent="compare", theme="必去-排名"),
    ReconQuery("来上海旅游必打卡的网红景点", _A, theme="必去-网红"),
    ReconQuery("上海值得去的免费景点有哪些", _A, theme="必去-免费"),
    ReconQuery("上海最有特色的地标景点推荐", _A, theme="必去-地标"),
    ReconQuery("上海适合外地人玩的地方有哪些", _A, theme="必去-外地人"),
    # ── 行程规划 ×7 ──
    ReconQuery("上海一日游怎么安排路线最合理", _A, intent="plan", theme="时长-一日游"),
    ReconQuery("上海两日游行程规划推荐", _A, intent="plan", theme="时长-两日游"),
    ReconQuery("上海三天两夜旅游攻略行程", _A, intent="plan", theme="时长-三日游"),
    ReconQuery("上海周末两天去哪里玩比较好", _A, intent="plan", theme="时长-周末"),
    ReconQuery("上海半天时间适合去哪里玩", _A, intent="plan", theme="时长-半天"),
    ReconQuery("上海经典一日游必去路线", _A, intent="plan", theme="时长-一日游"),
    ReconQuery("上海玩几天比较合适 行程怎么排", _A, intent="plan", theme="时长-玩几天"),
    # ── 主题 ×12 ──
    ReconQuery("上海适合拍照打卡的地方推荐", _A, theme="主题-拍照打卡"),
    ReconQuery("上海看夜景最美的地方在哪里", _A, theme="主题-夜景"),
    ReconQuery("上海citywalk路线推荐", _A, intent="plan", theme="主题-citywalk"),
    ReconQuery("上海适合情侣约会的地方推荐", _A, theme="主题-情侣约会"),
    ReconQuery("上海亲子游带孩子去哪里玩", _A, theme="主题-亲子遛娃"),
    ReconQuery("上海历史文化景点有哪些值得看", _A, theme="主题-历史文化"),
    ReconQuery("上海近代老建筑老洋房在哪里看", _A, theme="主题-老建筑"),
    ReconQuery("上海适合年轻人玩的潮流地方", _A, theme="主题-潮流年轻"),
    ReconQuery("上海有哪些好逛的博物馆推荐", _A, theme="主题-博物馆"),
    ReconQuery("上海看展览艺术馆推荐", _A, theme="主题-艺术展览"),
    ReconQuery("上海哪里适合体验老上海风情", _A, theme="主题-老上海"),
    ReconQuery("上海有什么演出和夜生活推荐", _A, theme="主题-夜生活演出"),
    # ── 区域 ×8 ──
    ReconQuery("上海外滩附近有什么好玩的", _A, theme="区域-外滩"),
    ReconQuery("上海陆家嘴浦东有哪些景点", _A, theme="区域-陆家嘴"),
    ReconQuery("上海徐汇区有什么好玩的地方", _A, theme="区域-徐汇"),
    ReconQuery("上海静安区有哪些值得去的地方", _A, theme="区域-静安"),
    ReconQuery("上海黄浦区景点推荐", _A, theme="区域-黄浦"),
    ReconQuery("上海武康路一带怎么玩", _A, theme="区域-武康路"),
    ReconQuery("上海新天地田子坊怎么样值得去吗", _A, intent="decide", theme="区域-新天地田子坊"),
    ReconQuery("上海虹口区杨浦区有什么好玩的", _A, theme="区域-虹口杨浦"),
    # ── 人群 ×6 ──
    ReconQuery("上海带老人旅游适合去哪些景点", _A, theme="人群-带老人"),
    ReconQuery("学生党穷游上海怎么玩省钱攻略", _A, intent="howto", theme="人群-学生穷游"),
    ReconQuery("上海闺蜜出游适合去哪里玩", _A, theme="人群-闺蜜"),
    ReconQuery("一个人去上海旅游怎么玩", _A, intent="plan", theme="人群-独自旅行"),
    ReconQuery("上海适合带小朋友的室内游乐场所", _A, theme="人群-带娃室内"),
    ReconQuery("上海老年人慢节奏游推荐", _A, theme="人群-老年慢游"),
    # ── 季节/天气 ×6 ──
    ReconQuery("上海几月份去旅游最好", _A, intent="decide", theme="季节-最佳月份"),
    ReconQuery("上海春天去哪里看花踏青", _A, theme="季节-春天赏花"),
    ReconQuery("上海秋天适合去哪里玩", _A, theme="季节-秋天"),
    ReconQuery("上海下雨天适合去哪里玩室内景点", _A, theme="季节-雨天室内"),
    ReconQuery("上海夏天避暑适合去的地方", _A, theme="季节-夏天避暑"),
    ReconQuery("上海冬天有什么好玩的地方", _A, theme="季节-冬天"),
    # ── 美食 ×6 ──
    ReconQuery("上海必吃的本帮菜餐厅推荐", _A, intent="compare", theme="美食-本帮菜"),
    ReconQuery("上海有什么必吃的特色小吃", _A, theme="美食-小吃"),
    ReconQuery("上海城隍庙附近有什么好吃的", _A, theme="美食-城隍庙"),
    ReconQuery("上海值得去的网红餐厅推荐", _A, intent="compare", theme="美食-网红餐厅"),
    ReconQuery("上海老字号美食有哪些", _A, theme="美食-老字号"),
    ReconQuery("上海哪里可以吃到正宗小笼包", _A, intent="compare", theme="美食-小笼包"),
    # ── 特定景点决策/对比 ×8 ──
    ReconQuery("上海迪士尼乐园值得去吗一天够吗", _A, intent="decide", theme="特定-迪士尼"),
    ReconQuery("上海海洋水族馆和海昌海洋公园哪个好", _A, intent="compare", theme="特定-水族馆对比"),
    ReconQuery("东方明珠值得上去吗门票多少钱", _A, intent="decide", theme="特定-东方明珠"),
    ReconQuery("上海豫园值得去吗有什么好玩的", _A, intent="decide", theme="特定-豫园"),
    ReconQuery("上海天文馆值得去吗怎么预约", _A, intent="decide", theme="特定-天文馆"),
    ReconQuery("上海科技馆和自然博物馆哪个更值得去", _A, intent="compare", theme="特定-科技馆对比"),
    ReconQuery("上海野生动物园好玩吗适合带孩子吗", _A, intent="decide", theme="特定-野生动物园"),
    ReconQuery("上海外滩和陆家嘴看夜景哪边更好", _A, intent="compare", theme="特定-夜景对比"),
    # ── 小众/避坑 ×7（内容最易切入的空位）──
    ReconQuery("上海有哪些小众但值得去的景点", _A, theme="小众-小众景点"),
    ReconQuery("上海本地人才知道的好玩地方", _A, theme="小众-本地人推荐"),
    ReconQuery("上海旅游避坑指南哪些景点不值得去", _A, intent="howto", theme="小众-避坑"),
    ReconQuery("上海不踩雷的宝藏景点推荐", _A, theme="小众-宝藏"),
    ReconQuery("上海适合慢慢逛的安静小马路", _A, theme="小众-安静小马路"),
    ReconQuery("上海有什么免费又小众的好去处", _A, theme="小众-免费小众"),
    ReconQuery("上海不商业化的原生态地方推荐", _A, theme="小众-不商业化"),
    # ── 决策/常识 ×6 ──
    ReconQuery("上海旅游值得去吗有什么必看的", _A, intent="decide", theme="决策-值得去吗"),
    ReconQuery("去上海旅游一般预算多少钱", _A, intent="decide", theme="决策-预算"),
    ReconQuery("上海旅游住哪个区比较方便", _A, intent="howto", theme="决策-住哪里"),
    ReconQuery("上海旅游交通怎么玩地铁方便吗", _A, intent="howto", theme="决策-交通"),
    ReconQuery("上海哪些景点需要提前预约", _A, intent="howto", theme="决策-预约"),
    ReconQuery("上海旅游有什么注意事项和建议", _A, intent="howto", theme="决策-注意事项"),
    # ── 周边 ×4 ──
    ReconQuery("上海周边古镇哪个最值得去", _A, intent="compare", theme="周边-古镇"),
    ReconQuery("上海周边两日游推荐去哪里", _A, intent="plan", theme="周边-两日游"),
    ReconQuery("上海到周边水乡怎么玩朱家角七宝", _A, theme="周边-水乡"),
    ReconQuery("上海周边适合自驾游的地方", _A, theme="周边-自驾"),

    # ══════════ Segment C · 本地客（上海人）══════════
    ReconQuery("上海本地人周末去哪里玩", _C, theme="本地-周末去处"),
    ReconQuery("上海适合周末遛娃的好去处", _C, theme="本地-遛娃"),
    ReconQuery("上海小众展览和艺术空间推荐", _C, theme="本地-展览"),
    ReconQuery("上海周末citywalk小众路线", _C, intent="plan", theme="本地-citywalk"),
    ReconQuery("上海适合拍照的小众咖啡馆推荐", _C, theme="本地-咖啡馆"),
    ReconQuery("上海周末适合约会的安静去处", _C, theme="本地-约会"),
    ReconQuery("上海有什么好逛的市集和夜市", _C, theme="本地-市集夜市"),
    ReconQuery("上海周边周末两天自驾去哪里", _C, intent="plan", theme="本地-周边自驾"),
    ReconQuery("上海适合一个人放空的地方", _C, theme="本地-独处放空"),
    ReconQuery("上海冷门但很美的公园推荐", _C, theme="本地-冷门公园"),

    # ══════════ Segment B · 入境外籍游客（英文，少量试探，待 key 规模化）══════════
    ReconQuery("best places to visit in Shanghai for first time", _B, theme="inbound-must-see"),
    ReconQuery("top tourist attractions in Shanghai", _B, intent="compare", theme="inbound-top"),
    ReconQuery("things to do in Shanghai for 3 days itinerary", _B, intent="plan", theme="inbound-itinerary"),
    ReconQuery("hidden gems and local spots in Shanghai", _B, theme="inbound-hidden-gems"),
]
