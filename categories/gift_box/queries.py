"""礼盒品类的买家高意图问题（fan-out）。

买家分叉 = 让 recon 数据定 → A/B 都保留，不写死（用户已确认）。
- Segment A（中文 / 豆包）：中国人买来送老外客户 —— **当前真实侦察重心**（有凭证）。
- Segment B（英文 / Perplexity·OpenAI）：老外自己买 —— 暂 mock，待 key。
theme 用于机会图分组（通用/场景/地域/价位/品类/定制）。
"""
from __future__ import annotations

from geo.evidence.schema import BuyerSegment
from geo.recon.queries import ReconQuery

# ── Segment A 中文：中国人买来送老外客户 ──
_A = BuyerSegment.A
_B = BuyerSegment.B

QUERIES: list[ReconQuery] = [
    ReconQuery("送外国客户什么伴手礼盒比较高端得体", _A, theme="通用"),
    ReconQuery("商务送礼 送给国外合作伙伴 高端礼盒推荐", _A, theme="通用"),
    ReconQuery("送老外客户的高端中国风伴手礼有哪些", _A, theme="通用"),
    ReconQuery("外贸公司送国外客户的礼品推荐", _A, theme="场景-外贸"),
    ReconQuery("签约仪式送外宾的高端礼盒选什么", _A, theme="场景-签约"),
    ReconQuery("国际展会送客户的中国特色伴手礼推荐", _A, theme="场景-展会"),
    ReconQuery("春节送国外客户的高端礼盒推荐", _A, theme="场景-节日"),
    ReconQuery("送欧美客户的高端商务礼品预算1000元左右", _A, theme="价位/地域-欧美"),
    ReconQuery("送日本客户的商务伴手礼有什么讲究", _A, theme="地域-日本"),
    ReconQuery("适合送外国人的中国非遗手工艺礼盒推荐", _A, theme="品类-非遗"),
    ReconQuery("茶叶礼盒送外国客户选哪个品牌好", _A, theme="品类-茶"),
    ReconQuery("高端定制礼盒送海外VIP客户", _A, theme="定制"),
    # ── Phase 5 扩展（多维盲扫 + 对抗式剪枝，2026-06-14）──
    #   场景 ×4
    ReconQuery("年终答谢外宾送什么高端礼盒比较有面子", _A, theme="场景-年终答谢"),
    ReconQuery("接待来访外宾考察团准备什么伴手礼盒得体", _A, theme="场景-接待考察"),
    ReconQuery("出国出访带给国外客户的见面礼送什么合适", _A, theme="场景-出访见面礼"),
    ReconQuery("圣诞节送国外客户的高端礼盒选什么好", _A, theme="场景-圣诞送礼"),
    #   地域 ×5（对照已有 欧美/日本）
    ReconQuery("送中东客户的高端礼盒选什么 穆斯林忌酒和猪皮制品要避开", _A, intent="howto", theme="地域-中东穆斯林"),
    ReconQuery("送德国客户的商务伴手礼有什么讲究 德国人务实送什么合适", _A, intent="howto", theme="地域-德国"),
    ReconQuery("送美国客户的高端商务礼品推荐 美国人收礼有什么禁忌", _A, intent="howto", theme="地域-美国"),
    ReconQuery("送法国客户的伴手礼选什么 法国人重品味送什么有格调", _A, intent="howto", theme="地域-法国"),
    ReconQuery("送韩国客户的高端伴手礼推荐 韩国商务送礼有什么规矩", _A, intent="howto", theme="地域-韩国"),
    ReconQuery("送印度客户什么礼盒合适 印度教客户忌牛皮要注意吗", _A, intent="howto", theme="地域-印度"),
    #   品类 ×4（对照已查 茶/非遗；白酒=验证品牌占位，低内容优先）
    ReconQuery("送外国客户的高端白酒礼盒选什么牌子好", _A, intent="compare", theme="品类-白酒"),
    ReconQuery("送老外客户的真丝丝绸围巾礼盒哪个牌子上档次", _A, intent="compare", theme="品类-真丝丝绸"),
    ReconQuery("送国外客户的高端陶瓷茶具礼盒推荐", _A, theme="品类-瓷器茶具"),
    ReconQuery("送海外客户的高端文创礼盒有哪些值得入手", _A, theme="品类-文创"),
    #   价位 ×3（补现有 1000 元上下）
    ReconQuery("送外国客户的高端礼盒预算3000元左右选什么好", _A, theme="价位-高端档"),
    ReconQuery("5000元一份的商务伴手礼盒送海外大客户有什么推荐", _A, theme="价位-奢华档"),
    ReconQuery("几百块钱送老外客户的轻礼伴手礼有没有体面的推荐", _A, theme="价位-轻礼档"),
    #   约束 ×4
    ReconQuery("公司要批量采购50份送外国客户的伴手礼盒怎么选性价比高", _A, theme="约束-批量采购"),
    ReconQuery("小批量定制logo的商务礼盒送国外客户大概多少钱一套", _A, theme="约束-定制询价"),
    ReconQuery("送外国客户的礼盒能配英文说明卡吗 茶叶丝绸怎么跟老外介绍", _A, intent="howto", theme="约束-英文说明卡"),
    #   决策 ×2
    ReconQuery("送外国客户的礼盒有现成的英文包装和贺卡服务吗 哪家供应商能一站式做好", _A, theme="决策-一站式服务"),
    ReconQuery("送外国客户选茶叶礼盒还是丝绸礼盒哪个更得体", _A, intent="compare", theme="决策-品类对比"),
    #   （盲扫剪枝时舍弃：『海关报关』=物流咨询无引用抓手；『十大排行榜』=SEO 词构造易引软文）
    # ── Phase 6 扩展（机会面规模化，2026-06-15）：覆盖更多 国家/场景/品类/行业/预算 ──
    #   地域 ×18（每个国家=一篇"送礼禁忌指南"机会，内容可赢）
    ReconQuery("送英国客户的高端伴手礼有什么讲究 选什么得体", _A, intent="howto", theme="地域-英国"),
    ReconQuery("送加拿大客户的商务礼品送什么合适", _A, theme="地域-加拿大"),
    ReconQuery("送澳大利亚客户的高端伴手礼推荐", _A, theme="地域-澳大利亚"),
    ReconQuery("送意大利客户的高端礼盒选什么 意大利人重设计品味", _A, intent="howto", theme="地域-意大利"),
    ReconQuery("送西班牙客户的商务伴手礼送什么好", _A, theme="地域-西班牙"),
    ReconQuery("送荷兰客户的商务礼品有什么禁忌 送什么合适", _A, intent="howto", theme="地域-荷兰"),
    ReconQuery("送瑞士客户的高端商务礼盒推荐", _A, theme="地域-瑞士"),
    ReconQuery("送俄罗斯客户的商务礼品送什么得体", _A, intent="howto", theme="地域-俄罗斯"),
    ReconQuery("送新加坡客户的伴手礼选什么合适", _A, theme="地域-新加坡"),
    ReconQuery("送阿联酋迪拜客户的高端礼盒 穆斯林禁忌要注意什么", _A, intent="howto", theme="地域-阿联酋"),
    ReconQuery("送沙特客户的商务礼品有什么讲究 选什么合适", _A, intent="howto", theme="地域-沙特"),
    ReconQuery("送泰国客户的商务伴手礼推荐", _A, theme="地域-泰国"),
    ReconQuery("送越南客户的商务礼品送什么好", _A, theme="地域-越南"),
    ReconQuery("送马来西亚客户的礼盒选什么合适", _A, theme="地域-马来西亚"),
    ReconQuery("送巴西客户的商务伴手礼推荐", _A, theme="地域-巴西"),
    ReconQuery("送以色列客户的礼品有什么禁忌 犹太教饮食讲究", _A, intent="howto", theme="地域-以色列"),
    ReconQuery("送北欧瑞典客户的高端礼盒推荐", _A, theme="地域-北欧"),
    ReconQuery("送墨西哥客户的商务礼品送什么得体", _A, theme="地域-墨西哥"),
    #   场景 ×10
    ReconQuery("公司周年庆送外国客户的纪念礼盒选什么", _A, theme="场景-周年庆"),
    ReconQuery("客户答谢会送外宾的伴手礼推荐", _A, theme="场景-答谢会"),
    ReconQuery("海外项目交付庆祝送客户什么礼物得体", _A, theme="场景-项目交付"),
    ReconQuery("国际论坛会议送嘉宾的伴手礼推荐", _A, theme="场景-论坛会议"),
    ReconQuery("接待外国政府代表团准备什么礼品得体", _A, intent="howto", theme="场景-政府接待"),
    ReconQuery("商务宴请外宾送什么伴手礼有面子", _A, theme="场景-商务宴请"),
    ReconQuery("海外并购签约送对方高管什么高端礼盒", _A, theme="场景-并购签约"),
    ReconQuery("长期合作老客户续约送什么礼物合适", _A, theme="场景-老客户续约"),
    ReconQuery("第一次见外国客户带什么见面礼合适", _A, intent="howto", theme="场景-初次见面"),
    ReconQuery("外国客户来华考察结束送什么伴手礼", _A, theme="场景-来华考察"),
    #   品类 ×17
    ReconQuery("送外国客户的紫砂壶礼盒哪个牌子好", _A, intent="compare", theme="品类-紫砂壶"),
    ReconQuery("送老外的苏绣刺绣礼品上档次吗 选什么好", _A, theme="品类-苏绣刺绣"),
    ReconQuery("送外国客户的景泰蓝工艺品礼盒推荐", _A, theme="品类-景泰蓝"),
    ReconQuery("送老外客户的玉器礼品合适吗 选什么", _A, theme="品类-玉器"),
    ReconQuery("送外国客户的文房四宝礼盒推荐", _A, theme="品类-文房四宝"),
    ReconQuery("送外国客户的高端普洱茶礼盒选什么牌子", _A, intent="compare", theme="品类-普洱茶"),
    ReconQuery("送外国客户的龙井绿茶礼盒哪个牌子好", _A, intent="compare", theme="品类-龙井绿茶"),
    ReconQuery("送老外的中国白茶礼盒推荐", _A, theme="品类-白茶"),
    ReconQuery("送外国客户的青花瓷摆件礼盒选什么", _A, theme="品类-青花瓷"),
    ReconQuery("送外国客户的漆器工艺品礼盒推荐", _A, theme="品类-漆器"),
    ReconQuery("送外国客户的高端真丝丝巾礼盒哪个牌子上档次", _A, intent="compare", theme="品类-真丝丝巾"),
    ReconQuery("送外国客户的檀香香道礼盒合适吗 选什么", _A, theme="品类-香道"),
    ReconQuery("送外国客户的中式书法字画礼品推荐", _A, theme="品类-书法字画"),
    ReconQuery("送外国客户的茶具加茶叶组合礼盒推荐", _A, theme="品类-茶具组合"),
    ReconQuery("送外国客户的高端月饼礼盒 中秋送老外合适吗", _A, intent="howto", theme="品类-月饼礼盒"),
    ReconQuery("送外国客户的竹编手工艺礼品推荐", _A, theme="品类-竹编"),
    ReconQuery("送外国客户的中国茶叶哪种最受老外欢迎", _A, intent="compare", theme="品类-茶叶选种"),
    #   行业 ×5
    ReconQuery("科技公司送外国客户的伴手礼有什么推荐", _A, theme="行业-科技"),
    ReconQuery("外贸工厂送国外采购商的伴手礼选什么", _A, theme="行业-外贸工厂"),
    ReconQuery("律师事务所送外国客户的高端礼品推荐", _A, theme="行业-律所"),
    ReconQuery("金融公司送海外客户的商务礼盒选什么", _A, theme="行业-金融"),
    ReconQuery("咨询公司送外国客户的伴手礼推荐", _A, theme="行业-咨询"),
    #   价位 ×4
    ReconQuery("送外国客户的礼盒预算500元有什么体面推荐", _A, theme="价位-500元"),
    ReconQuery("送外国客户的礼盒预算2000元选什么好", _A, theme="价位-2000元"),
    ReconQuery("送外国客户的礼盒预算800元推荐", _A, theme="价位-800元"),
    ReconQuery("万元以上送海外大客户的顶级礼盒选什么", _A, theme="价位-万元顶级"),
    #   约束/教育型 ×10（买家教育型问题，内容最易被引用）
    ReconQuery("送外国客户礼物怎么避免踩文化禁忌", _A, intent="howto", theme="约束-避免踩雷"),
    ReconQuery("送外国客户的礼盒怎么搭配显得有文化又得体", _A, intent="howto", theme="约束-搭配显文化"),
    ReconQuery("送外国客户的礼物轻便好携带不易碎有什么推荐", _A, theme="约束-轻便不易碎"),
    ReconQuery("送外国客户的礼盒英文贺卡怎么写得体", _A, intent="howto", theme="约束-英文贺卡"),
    ReconQuery("送外国客户礼物的预算一般定多少合适", _A, intent="howto", theme="约束-预算定多少"),
    ReconQuery("送外国客户的伴手礼怎么挑选不会出错", _A, intent="howto", theme="约束-怎么挑不出错"),
    ReconQuery("送外国客户的礼盒可以带上飞机吗 有什么注意", _A, intent="howto", theme="约束-能否带上飞机"),
    ReconQuery("送外国客户的礼物送单数还是双数有讲究吗", _A, intent="howto", theme="约束-单数双数"),
    ReconQuery("给外国客户回礼送什么合适", _A, theme="约束-回礼"),
    ReconQuery("送外国客户的礼盒怎么做英文说明书介绍中国文化", _A, intent="howto", theme="约束-英文说明书"),
    #   决策/对比 ×4
    ReconQuery("送外国客户选茶叶还是白酒哪个更受欢迎", _A, intent="compare", theme="决策-茶vs酒"),
    ReconQuery("送外国客户选丝绸还是瓷器哪个更有代表性", _A, intent="compare", theme="决策-丝绸vs瓷器"),
    ReconQuery("送外国客户买现成礼盒还是定制礼盒好", _A, intent="compare", theme="决策-现成vs定制"),
    ReconQuery("送外国客户的礼盒选中国风还是国际范好", _A, intent="compare", theme="决策-中国风vs国际范"),
    #   通用深化 ×4
    ReconQuery("有哪些适合送外国客户的高端国货礼盒品牌", _A, theme="通用-国货品牌"),
    ReconQuery("送外国客户既有中国特色又实用的礼物推荐", _A, theme="通用-特色又实用"),
    ReconQuery("送外国客户不踩雷的万能伴手礼有哪些", _A, theme="通用-万能伴手礼"),
    ReconQuery("送外国客户显得有诚意又高端的礼盒推荐", _A, theme="通用-有诚意高端"),

    # ── Segment B 英文：老外自己买（暂 mock）──
    ReconQuery("best luxury corporate gift box for business clients", _B, theme="generic"),
    ReconQuery("premium gift hamper to impress corporate clients", _B, theme="generic"),
    ReconQuery("high-end Chinese gift set for overseas business partners", _B, theme="china-themed"),
    ReconQuery("luxury client appreciation gift ideas for international clients", _B, theme="generic"),
]
