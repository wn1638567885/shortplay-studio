"""零成本演示生成器。

没有配置 API Key 时，平台使用内置的类型化模板生成大纲、剧本和分镜，
保证整个创作流程可以先跑通、看得见效果，且不消耗任何积分或调用额度。
"""

import hashlib
import random
from html import escape

GENRES = {
    "都市逆袭": {
        "color": "#ff6b4a",
        "tone": "冷调霓虹、雨夜反光、低饱和肤色",
        "tagline": "被踩进泥里的人，翻手就是整座城",
        "logline": "被当众踩进泥里的{p}，在一个雨夜之后开始收回属于自己的一切。",
        "synopsis": "五年前，{p}从这座城市最耀眼的位置跌下来，成了人人可以踩一脚的外卖员。五年后，一枚旧工牌、一支录音笔和一场发布会，把当年那场局重新摆上桌面。他不再解释，只负责一件事——把欠他的，一笔一笔收回来。",
        "cast": [
            {
                "key": "p",
                "name": "林川",
                "role": "男主 · 落魄外卖员",
                "gender": "男",
                "age": "27",
                "appearance": "洗得发白的夹克，手掌有厚茧，眉眼干净，站姿很直",
                "personality": "隐忍克制，算度极准，习惯先低头再出手",
                "arc": "从被当众羞辱，到在发布会上拿回名字与股权",
            },
            {
                "key": "a",
                "name": "周慕云",
                "role": "反派 · 集团太子爷",
                "gender": "男",
                "age": "32",
                "appearance": "定制西装，袖扣反光，笑起来只有嘴角动",
                "personality": "傲慢、体面、擅长把恶意说得像恩赐",
                "arc": "从掌控全局，到在自己布置的局里失去一切",
            },
            {
                "key": "n",
                "name": "苏念",
                "role": "女主 · 急诊科医生",
                "gender": "女",
                "age": "26",
                "appearance": "白大褂下是旧毛衣，眼下有淡青色，说话时看着人的眼睛",
                "personality": "清醒、直接，不轻易心软，但认定的事不退",
                "arc": "从旁观者，到唯一敢在所有人面前站到他身边的人",
            },
        ],
        "locations": ["城中村出租屋", "雨夜天桥", "集团地下车库", "发布会后台", "老城区面馆"],
        "props": ["旧工牌", "被撕碎的合同", "录音笔", "黑色车钥匙", "母亲的手术单"],
        "events": ["当众泼酒", "抢功", "断供医药费", "设局逼签", "身份曝光"],
        "beats": [
            {"t": "雨夜的第一单", "s": "{p}在暴雨里送完最后一单，却在{loc}撞见{a}把{n}逼到墙角。"},
            {"t": "被抢走的功劳", "s": "{p}熬了三个通宵的方案，在会议上被{a}轻描淡写地署上了自己的名字。"},
            {"t": "母亲的缴费单", "s": "{loc}的走廊里，{p}攥着{prop}，手机余额停在两位数。"},
            {"t": "旧友的背刺", "s": "曾经一起打拼的兄弟递来一杯酒，杯底压着一份{prop}。"},
            {"t": "一场鸿门宴", "s": "{a}在{loc}摆下饭局，满桌人等着看{p}低头。"},
            {"t": "她替我挡下", "s": "{n}挡在{p}身前，替他接下那杯泼过来的酒。"},
            {"t": "车库里的对峙", "s": "地下车库里，{p}把{prop}放在{a}的车前盖上。"},
            {"t": "录音笔里的真相", "s": "{prop}里传出的声音，让在场所有人变了脸色。"},
            {"t": "发布会前夜", "s": "{loc}灯火通明，{p}站在门口，最后一次整理袖口。"},
            {"t": "雨停了", "s": "{p}抬头看天，雨停了。属于他的那一局，才刚刚开始。"},
        ],
        "lines": {
            "open": [
                ["a", "这么晚了还送外卖？你们这种人，时间最不值钱。"],
                ["a", "川子，不是兄弟不帮你，这单子真轮不到你。"],
                ["n", "他母亲的缴费单，我已经交了。你别再拿这个说事。"],
                ["p", "钱我会还。但不是今天，也不是还给你。"],
            ],
            "conflict": [
                ["a", "这份方案是我做的，你拿什么跟我争？"],
                ["a", "签了它，你还能留个体面。"],
                ["p", "体面？五年前你就把我的体面踩碎了。"],
                ["n", "周慕云，你再说一遍试试。"],
            ],
            "counter": [
                ["p", "我不争。我只是来拿回属于我的东西。"],
                ["p", "这支录音笔里的声音，你熟不熟？"],
                ["n", "从今天起，你欠他的，一笔一笔还。"],
                ["a", "你以为一段录音就能翻盘？"],
            ],
            "hook": [
                ["p", "明天九点，发布会。你会来的，对吧？"],
                ["p", "雨停了。该轮到我说话了。"],
                [None, "他抬头，第一次笑了。电话那头沉默了三秒，然后挂断。"],
                ["a", "你会后悔的。"],
            ],
        },
    },
    "古装权谋": {
        "color": "#c9a227",
        "tone": "烛火金、宫墙暗红、薄雾与纱帘",
        "tagline": "一纸婚书，半枚玉佩，整个朝局为她翻转",
        "logline": "替嫡姐上轿的庶女{p}，用半枚{prop}撬动了整座朝堂。",
        "synopsis": "沈府庶女{p}被推上花轿，替嫡姐嫁入摄政王府。所有人都等着看她死在后宅，却没人想到，她怀里藏着先帝留下的半枚玉佩。从冷宫到城楼，她一步步把棋盘翻过来，也一步步走进{n}布下的局里。",
        "cast": [
            {
                "key": "p",
                "name": "沈昭",
                "role": "女主 · 沈府庶女",
                "gender": "女",
                "age": "19",
                "appearance": "素色嫁衣，腕上有一道旧疤，眼尾微挑",
                "personality": "冷静、记仇、极会忍，出手不留退路",
                "arc": "从被当作弃子的替嫁庶女，到执掌朝局的掌印人",
            },
            {
                "key": "a",
                "name": "沈婉",
                "role": "反派 · 沈府嫡女",
                "gender": "女",
                "age": "20",
                "appearance": "金线绣裙，笑时眼不弯，护甲修得极尖",
                "personality": "骄矜、善演、把体面看得比命重",
                "arc": "从步步算计，到在金簪断裂声里失去所有筹码",
            },
            {
                "key": "n",
                "name": "萧景珩",
                "role": "盟友 · 摄政王",
                "gender": "男",
                "age": "28",
                "appearance": "玄色蟒袍，指节修长，眼底常年压着一层倦色",
                "personality": "寡言、多疑、一旦许诺便不再回头",
                "arc": "从试探利用，到把兵符亲手交到她手上",
            },
        ],
        "locations": ["沈府正厅", "长街灯会", "东宫偏殿", "冷宫", "城门楼"],
        "props": ["半枚玉佩", "掺了药的合卺酒", "密信", "断掉的金簪", "先帝遗诏"],
        "events": ["替嫁", "当众验身", "被推入池", "宫中设局", "遗诏现世"],
        "beats": [
            {"t": "替嫁之夜", "s": "一顶花轿停在沈府门前，{p}替嫡姐上了轿，怀里只藏着一枚{prop}。"},
            {"t": "一盏毒酒", "s": "合卺酒端上来时，{p}闻到了苦杏仁的味道。"},
            {"t": "灯会惊变", "s": "{loc}人潮如织，有人从背后把{p}推向了池边。"},
            {"t": "冷宫来客", "s": "{n}踏着雪走进冷宫，带来一句足以翻盘的密信。"},
            {"t": "嫡姐的算计", "s": "{a}当众验身，想在一炷香里毁掉{p}所有的退路。"},
            {"t": "半枚玉佩", "s": "{prop}在灯下合拢，缺口严丝合缝——那是先帝的信物。"},
            {"t": "摄政王的试探", "s": "{n}把兵符推到{p}面前：本王要一个答案。"},
            {"t": "金簪落地", "s": "争执间，{a}头上的金簪断成两截，满殿寂静。"},
            {"t": "遗诏现世", "s": "{loc}上，{prop}展开，宣读声压过了所有人的呼吸。"},
            {"t": "城楼对峙", "s": "{p}站在城楼上，第一次以真正的身份俯视{a}。"},
        ],
        "lines": {
            "open": [
                ["a", "妹妹替我嫁过去，委屈你了。"],
                ["a", "进了王府，就没人再护着你了。"],
                ["n", "本王的人，什么时候轮到沈府来训？"],
                ["p", "姐姐放心。我既上了轿，就没打算再回来求谁。"],
            ],
            "conflict": [
                ["a", "把她按住。今日这身，必须验。"],
                ["a", "你拿什么跟我争？父亲？还是这半枚破玉？"],
                ["p", "这玉合不合得上，验过才知道。"],
                ["n", "谁敢碰她，先问过本王。"],
            ],
            "counter": [
                ["p", "你怕的从来不是我，是这半枚玉。"],
                ["p", "金簪断的时候，你听见满殿的声音了吗？"],
                ["n", "兵符在我手里。王爷要的答案，也在我手里。"],
                ["a", "你以为他会护你一辈子？"],
            ],
            "hook": [
                ["p", "遗诏在此，谁敢再言半句？"],
                ["p", "城楼上的风，今夜只吹向我。"],
                [None, "他后退半步，第一次没有还口。远处传来马蹄声，比雪更急。"],
                ["a", "这局还没完。"],
            ],
        },
    },
    "甜宠恋爱": {
        "color": "#ff8fa3",
        "tone": "奶油暖光、浅粉与米白、柔焦",
        "tagline": "合约写得很清楚，唯独没写不许动心",
        "logline": "签了三个月同居合约的{p}，发现合约里唯一没写的条款，是{a}先动了心。",
        "synopsis": "插画师{p}为了房租，搬进了投资人的空房子。三个月的合约写得明明白白：不同桌吃饭、不过问私事、到期搬走。可一杯咖啡、一场暴雨、一副没送出去的钥匙，把每一条都悄悄改写了。",
        "cast": [
            {
                "key": "p",
                "name": "许知意",
                "role": "女主 · 插画师",
                "gender": "女",
                "age": "24",
                "appearance": "宽松卫衣，指尖常沾颜料，头发用铅笔别着",
                "personality": "嘴硬心软，怕麻烦别人，情绪都画在速写本里",
                "arc": "从把喜欢藏在合约背后，到当面把话说清楚",
            },
            {
                "key": "a",
                "name": "陆时衍",
                "role": "男主 · 冷面投资人",
                "gender": "男",
                "age": "30",
                "appearance": "深灰衬衫，袖口卷到小臂，腕表冷光",
                "personality": "克制、别扭、行动远比嘴快",
                "arc": "从只谈条款，到愿意为一顿饭等三个小时",
            },
            {
                "key": "n",
                "name": "唐糖",
                "role": "闺蜜 · 情感军师",
                "gender": "女",
                "age": "24",
                "appearance": "亮色外套，耳环晃，说话时手比嘴快",
                "personality": "热闹、通透、看破不说破",
                "arc": "从起哄者，到把关键那句话递给两人",
            },
        ],
        "locations": ["顶层公寓", "街角咖啡馆", "雨中的便利店", "小画廊", "医院走廊"],
        "props": ["画到一半的速写本", "一条灰色围巾", "没送出的钥匙", "便利店的关东煮", "误发的语音"],
        "events": ["意外同居", "误会", "吃醋", "告白", "合约到期"],
        "beats": [
            {"t": "意外同居", "s": "停电的雨夜，{p}抱着{prop}敲开了公寓的门——开门的却是{a}。"},
            {"t": "一杯咖啡", "s": "{a}把咖啡放在{p}桌上：算我请你的，别多想。"},
            {"t": "吃醋现场", "s": "{p}看见{a}和别的女人走出{loc}，手里的{prop}被捏出了褶。"},
            {"t": "误发的语音", "s": "{p}把一段吐槽{a}的语音，误发到了工作群。"},
            {"t": "关东煮", "s": "凌晨两点的便利店里，两个人分一碗关东煮，谁都没先开口。"},
            {"t": "雨中的等待", "s": "雨下大了，{a}撑伞站在{loc}门口，等了一个小时。"},
            {"t": "没送出的钥匙", "s": "{prop}在{a}口袋里放了三天，边角都被磨热了。"},
            {"t": "合约到期", "s": "合约最后一天，{p}收拾好行李，门却被反锁了。"},
            {"t": "画廊的告白", "s": "{loc}的灯一盏盏亮起，{a}站在{p}的画前说：缺的那个人，是我。"},
            {"t": "围巾", "s": "{p}把围巾绕在{a}脖子上：这次，换我先低头。"},
        ],
        "lines": {
            "open": [
                ["a", "这杯咖啡算我请你的，别多想。"],
                ["a", "你家停电了？先住我这，明天再说。"],
                ["n", "唐糖说你喜欢他，真的假的？"],
                ["p", "我喜欢谁，我自己会去说。"],
            ],
            "conflict": [
                ["a", "我们之间只是合约，你最好记住。"],
                ["a", "他给不了你的，我可以。"],
                ["p", "合约上没写，不许我动心。"],
                ["n", "你再装一次，我就替她说了。"],
            ],
            "counter": [
                ["p", "那你现在，是在吃醋吗？"],
                ["p", "钥匙我放你门口了。要不要，随你。"],
                ["n", "他等了你一整夜，就在楼下。"],
                ["a", "别把同情当成喜欢。"],
            ],
            "hook": [
                ["p", "陆时衍，这次换我先低头。"],
                ["p", "合约到期了，可我不想搬。"],
                [None, "门外，他站了一整夜。手机震了一下：我在楼下。"],
                ["a", "开门，我们谈谈。"],
            ],
        },
    },
    "悬疑复仇": {
        "color": "#5aa9e6",
        "tone": "冷蓝、雨夜反光、高对比阴影",
        "tagline": "监控可以删，尸检报告删不掉",
        "logline": "法医{p}在雨夜发现的一具尸体，把她拉回三年前那场被抹去的大火。",
        "synopsis": "三年前，姐姐死于一场定性为意外的大火。三年后，{p}在{loc}发现一具指甲缝里卡着同款纤维的尸体。缺失的七分钟监控、一盘生锈的录音带，让当年的凶手第一次坐不住。",
        "cast": [
            {
                "key": "p",
                "name": "江眠",
                "role": "女主 · 法医",
                "gender": "女",
                "age": "29",
                "appearance": "白大褂，短发别在耳后，眼神安静得像手术灯",
                "personality": "极度理性，唯独在姐姐的事上不肯退半步",
                "arc": "从只相信证据，到敢把自己也押上赌桌",
            },
            {
                "key": "a",
                "name": "郑铎",
                "role": "反派 · 财团掌权者",
                "gender": "男",
                "age": "48",
                "appearance": "银灰鬓角，深色大衣，握手时从不先松手",
                "personality": "温和、体面，把威胁藏在关心后面",
                "arc": "从稳坐幕后，到在审讯室里第一次沉默",
            },
            {
                "key": "n",
                "name": "陈屿",
                "role": "盟友 · 调查记者",
                "gender": "男",
                "age": "31",
                "appearance": "旧风衣，随身录音笔，胡茬没刮干净",
                "personality": "执拗、话少，认死理",
                "arc": "从独自追查，到把最后一份证据交给{p}",
            },
        ],
        "locations": ["停尸房", "废弃仓库", "雨夜天台", "律所会议室", "老宅地下室"],
        "props": ["被删除的监控硬盘", "生锈的录音带", "一张旧照片", "带血的手套", "尸检报告"],
        "events": ["雨夜抛尸", "证据被毁", "证人失踪", "深夜追踪", "真凶现身"],
        "beats": [
            {"t": "雨夜的尸体", "s": "{loc}发现一具尸体，指甲缝里卡着一小片{prop}。"},
            {"t": "缺失的七分钟", "s": "监控录像在案发前后缺失了七分钟，只有{p}注意到。"},
            {"t": "三年前的火", "s": "{p}翻开旧档案，三年前那场火，烧掉的是一整条证据链。"},
            {"t": "匿名来电", "s": "电话那头只有呼吸声，然后是一句：别查了。"},
            {"t": "编号对不上", "s": "停尸房的编号对不上，{p}发现多出来的一具尸体。"},
            {"t": "记者的照片", "s": "{n}把一沓照片推过来：你姐姐死前，见过{a}。"},
            {"t": "废弃仓库", "s": "{loc}里，{p}在水泥缝里找到了{prop}。"},
            {"t": "反将一军", "s": "审讯室里，{p}把{prop}放在桌上，{a}第一次失去了表情。"},
            {"t": "天台对峙", "s": "雨夜天台，{a}站在栏杆边：你赢了，可你也会失去一切。"},
            {"t": "最后一秒", "s": "录音带转到最后一秒，传来她三年前的声音。"},
        ],
        "lines": {
            "open": [
                ["a", "别再查了。有些事，知道了就回不了头。"],
                ["a", "这份监控少了七分钟。你确定要往下看？"],
                ["n", "你姐姐死前，见过郑铎。"],
                ["p", "三年前那场火，不是意外。"],
            ],
            "conflict": [
                ["a", "证据呢？没有证据，你就是疯子。"],
                ["a", "你以为你在复仇，其实你只是在送死。"],
                ["p", "监控可以删，尸检报告删不掉。"],
                ["n", "把手套给我。这次，我来做污点证人。"],
            ],
            "counter": [
                ["p", "你手上的疤，和照片里那个人一样。"],
                ["p", "我不是来听你解释的，我是来收网的。"],
                ["n", "这盘棋，从三年前就开始下了。"],
                ["a", "你姐姐也是这么说的。"],
            ],
            "hook": [
                ["p", "录音带转到最后一秒了。"],
                ["p", "灯灭的瞬间，谁站在门口？"],
                [None, "录音带里传来她三年前的声音。警报响起，天台上的风停了。"],
                ["a", "你会后悔查下去的。"],
            ],
        },
    },
    "校园青春": {
        "color": "#7bc96f",
        "tone": "午后逆光、校服蓝白、轻微胶片颗粒",
        "tagline": "那年没寄出去的信，替我们说了喜欢",
        "logline": "转学生{p}坐到了全校都不敢坐的位置，也坐进了{a}整个夏天。",
        "synopsis": "高三开学第一天，{p}抱着书站在教室门口，全班只有{a}旁边空着一个座位。一张演唱会门票、一件校服外套、一封没寄出去的信，把两个人的高三写成了一部不敢快进的短剧。",
        "cast": [
            {
                "key": "p",
                "name": "夏枝",
                "role": "女主 · 转学生",
                "gender": "女",
                "age": "18",
                "appearance": "校服洗得很干净，马尾有点歪，书包上挂着一枚旧挂件",
                "personality": "安静、倔，习惯把话写下来而不是说出来",
                "arc": "从躲着所有人，到敢在毕业典礼上喊出他的名字",
            },
            {
                "key": "a",
                "name": "陆星野",
                "role": "男主 · 篮球队长",
                "gender": "男",
                "age": "18",
                "appearance": "校服外套搭在肩上，手腕缠着护腕，笑起来有点欠",
                "personality": "看起来散漫，其实记得每个人说过的话",
                "arc": "从把喜欢藏在玩笑里，到当着全校的面不再躲",
            },
            {
                "key": "n",
                "name": "周小满",
                "role": "同桌 · 情报中心",
                "gender": "女",
                "age": "18",
                "appearance": "圆框眼镜，桌上永远堆着零食和便利贴",
                "personality": "话多、热心、消息比广播还快",
                "arc": "从起哄的旁观者，到偷偷把信塞进邮筒的人",
            },
        ],
        "locations": ["高三教室", "教学楼天台", "篮球场", "旧图书馆", "晚自习走廊"],
        "props": ["写着名字的作业本", "一张演唱会门票", "校服外套", "没寄出的信", "旧挂件"],
        "events": ["转学", "球赛", "家长会", "毕业", "告白"],
        "beats": [
            {"t": "转学第一天", "s": "{p}抱着书站在教室门口，全班只有{a}旁边空着一个座位。"},
            {"t": "没交的作业", "s": "{p}的作业本不见了，却在{a}的抽屉里被翻出来。"},
            {"t": "篮球场的雨", "s": "球赛中途下起雨，{a}把{prop}扔给{p}：替我拿着。"},
            {"t": "天台上的秘密", "s": "{loc}的风很大，{p}听见{a}说：我可能，要走了。"},
            {"t": "一张门票", "s": "课桌里多了一张门票，背面写着：别迟到。"},
            {"t": "晚自习的走廊", "s": "晚自习的灯灭了，{loc}尽头有人倚着墙等她。"},
            {"t": "家长会", "s": "家长会上，{p}第一次知道{a}家里发生了什么。"},
            {"t": "校服外套", "s": "{a}把校服外套盖在睡着的{p}头上，动作轻得像怕惊醒什么。"},
            {"t": "未寄出的信", "s": "{prop}躺在书包最底层，字迹被汗洇开。"},
            {"t": "毕业那天", "s": "{loc}上，{a}当着所有人的面喊出了{p}的名字。"},
        ],
        "lines": {
            "open": [
                ["a", "新来的？坐我旁边吧，位置空着。"],
                ["a", "作业借我抄一下，就一次。"],
                ["n", "别理他，他就是嘴欠。"],
                ["p", "抄可以，错别字自己改。"],
            ],
            "conflict": [
                ["a", "你跟他走那么近，不怕别人说？"],
                ["a", "我们不是一个世界的人。"],
                ["p", "谁说我要跟你一个世界？我自己造一个。"],
                ["n", "你们俩能不能先把我当个人？"],
            ],
            "counter": [
                ["p", "我喜欢的，我认。"],
                ["p", "那你敢不敢，当着全校的面说一遍？"],
                ["n", "票我收下了，人我也要。"],
                ["a", "有些事，你不需要知道。"],
            ],
            "hook": [
                ["p", "晚自习的灯灭了，走廊尽头的人还在等。"],
                ["p", "那封信，我这次不寄了，我当面给你。"],
                [None, "他把校服外套，盖在了她头上。广播里，突然响起他的名字。"],
                ["a", "别迟到。"],
            ],
        },
    },
    "玄幻战神": {
        "color": "#9b7bff",
        "tone": "雷云紫金、祭坛冷光、粒子与火星",
        "tagline": "我废的是经脉，不是骨头",
        "logline": "被废去经脉的战尊{p}，从断魂崖爬回来的第一天，就掀了整个宗门的天。",
        "synopsis": "三年前，{p}被最信任的人推下断魂崖，经脉尽废，战神之名成了笑话。三年后，他提着一柄断裂的战戟走回宗门，演武场上所有人都以为他还是那个废物——直到祖地石碑上，缓缓显出他的名字。",
        "cast": [
            {
                "key": "p",
                "name": "萧天",
                "role": "男主 · 被废战尊",
                "gender": "男",
                "age": "22",
                "appearance": "破旧黑袍，左臂缠着布条，肩背挺直如枪",
                "personality": "沉默、狠，话只说给值得的人听",
                "arc": "从被全宗门耻笑的废人，到一人守下整座宗门",
            },
            {
                "key": "a",
                "name": "姬无夜",
                "role": "反派 · 第一天骄",
                "gender": "男",
                "age": "24",
                "appearance": "银冠紫袍，手中折扇镶着兽骨，笑容很淡",
                "personality": "自负、精致、习惯用规矩杀人",
                "arc": "从高高在上，到在雷云下第一次后退",
            },
            {
                "key": "n",
                "name": "苏璃",
                "role": "女主 · 小师妹",
                "gender": "女",
                "age": "19",
                "appearance": "青色弟子服，腰间挂着药囊，眼神很亮",
                "personality": "直率、护短，认定的人谁都不许碰",
                "arc": "从偷偷送药，到替他挡下第一道天雷",
            },
        ],
        "locations": ["断魂崖", "宗门演武场", "万兽森林", "祭坛", "祖地"],
        "props": ["断裂的战戟", "残缺神格", "血契", "祖地石碑", "一枚叙旧丹"],
        "events": ["废脉", "演武场羞辱", "兽潮", "宗门大比", "祖地觉醒"],
        "beats": [
            {"t": "废脉归来", "s": "{p}被抬下断魂崖，宗门上下都以为他死了。"},
            {"t": "演武场的羞辱", "s": "{loc}上，{a}一脚把{p}踹翻在地：废物也敢上台？"},
            {"t": "残戟认主", "s": "废墟里，那柄断裂的战戟第一次发出嗡鸣。"},
            {"t": "师妹的丹", "s": "{n}偷偷把最后一枚{prop}塞进{p}手里：别死。"},
            {"t": "万兽森林", "s": "{loc}深处，{p}以血为引，唤醒了沉睡的兽王。"},
            {"t": "神格碎片", "s": "{prop}从祭坛裂开，露出一角不属于人间的光。"},
            {"t": "宗门大比", "s": "抽签结果出来的那一刻，整个广场都安静了。"},
            {"t": "血契", "s": "{p}在掌心划开一道口子：这一战，我押自己。"},
            {"t": "祖地石碑", "s": "{loc}的石碑上，缓缓显出{p}的名字。"},
            {"t": "一战封神", "s": "雷云压顶，{p}提着残戟，一个人走向了整个天骄营。"},
        ],
        "lines": {
            "open": [
                ["a", "废了经脉的人，也配站在演武场？"],
                ["a", "萧天，你连剑都提不动了。"],
                ["n", "他的经脉，是我在治。轮不到你下结论。"],
                ["p", "废的是经脉，不是骨头。"],
            ],
            "conflict": [
                ["a", "把神格交出来，我留你全尸。"],
                ["a", "你护得住她一次，护得住一辈子吗？"],
                ["p", "跪下？三年前我跪过一次，够了。"],
                ["n", "师兄，别听他的。"],
            ],
            "counter": [
                ["p", "你怕的不是我，是我回来。"],
                ["p", "这一戟，三年前就该还你。"],
                ["n", "神格认主。你，也配？"],
                ["a", "断魂崖下，没人收尸。"],
            ],
            "hook": [
                ["p", "祖地石碑，裂开了一道缝。"],
                ["p", "下一战，宗门大比。"],
                [None, "血契亮起，天地变色。他缓缓抬头，眼里有火。"],
                ["a", "那就别怪我不留情。"],
            ],
        },
    },
}

GENRE_NAMES = list(GENRES.keys())
STYLES = ["真人写实", "日系动画", "国风水墨", "赛博霓虹", "复古胶片"]
RATIOS = ["9:16", "16:9", "1:1", "4:3"]


def _rng(*parts) -> random.Random:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return random.Random(int(hashlib.sha256(raw).hexdigest()[:16], 16))


def _genre(project: dict) -> dict:
    return GENRES.get(project.get("genre") or "", GENRES["都市逆袭"])


def _ctx(project: dict, idx: int) -> dict:
    g = _genre(project)
    r = _rng(project["id"], idx)
    cast = {c["key"]: c for c in g["cast"]}
    return {
        "p": cast["p"]["name"],
        "a": cast["a"]["name"],
        "n": cast["n"]["name"],
        "loc": r.choice(g["locations"]),
        "prop": r.choice(g["props"]),
        "event": r.choice(g["events"]),
        "title": project.get("title") or "未命名短剧",
        "genre": project.get("genre") or "都市逆袭",
        "style": project.get("style") or "真人写实",
        "ratio": project.get("ratio") or "9:16",
    }


def _fill(text: str, ctx: dict) -> str:
    try:
        return text.format(**ctx)
    except (KeyError, IndexError):
        return text


def _character(project: dict, g: dict, c: dict) -> dict:
    prompt = (
        f"电影感人物设定图，{project.get('ratio', '9:16')} 画幅，"
        f"{project.get('style', '真人写实')}风格，{c['gender']}性，{c['age']}岁，"
        f"{c['appearance']}，气质{c['personality']}，半身像，浅景深，"
        f"{g['tone']}，高细节，真实光影，保持角色一致性"
    )
    return {
        "name": c["name"],
        "role": c["role"],
        "gender": c["gender"],
        "age": c["age"],
        "appearance": c["appearance"],
        "personality": c["personality"],
        "arc": c["arc"],
        "prompt": prompt,
    }


def outline(project: dict) -> dict:
    g = _genre(project)
    ctx = _ctx(project, 1)
    cast = [_character(project, g, c) for c in g["cast"]]
    count = int(project.get("episode_count") or 12)
    episodes = []
    for i in range(1, count + 1):
        c = _ctx(project, i)
        if i <= len(g["beats"]):
            beat = g["beats"][i - 1]
            title = _fill(beat["t"], c)
            summary = _fill(beat["s"], c)
        else:
            title = f"{c['event']}·续"
            summary = (
                f"{c['event']}之后，{c['a']}再次出手，"
                f"{c['p']}必须在{c['loc']}做出选择。"
            )
        episodes.append({"idx": i, "title": title, "summary": summary})
    return {
        "logline": _fill(g["logline"], ctx),
        "synopsis": _fill(g["synopsis"], ctx),
        "characters": cast,
        "episodes": episodes,
    }


def characters(project: dict) -> list:
    g = _genre(project)
    return [_character(project, g, c) for c in g["cast"]]


def _dialogue_pool(project: dict, key: str, idx: int) -> list:
    return list(_genre(project)["lines"][key])


def _speaker_line(entry: list, ctx: dict) -> str:
    speaker, text = entry
    text = _fill(text, ctx)
    if not speaker:
        return f"（{text}）"
    name = {"p": ctx["p"], "a": ctx["a"], "n": ctx["n"]}[speaker]
    return f"**{name}**：{text}"


def script(project: dict, episode: dict) -> str:
    idx = int(episode["idx"])
    c1 = _ctx(project, idx)
    c2 = _ctx(project, idx * 10 + 1)
    c3 = _ctx(project, idx * 10 + 2)
    c4 = _ctx(project, idx * 10 + 3)

    op = _dialogue_pool(project, "open", idx)
    cf = _dialogue_pool(project, "conflict", idx)
    ct = _dialogue_pool(project, "counter", idx)
    hk = _dialogue_pool(project, "hook", idx)

    def scene(title_line: str, picture: str, dialogue: list, ctx: dict) -> list:
        out = [title_line, "", f"**画面**：{picture}", ""]
        for entry in dialogue:
            out += [_speaker_line(entry, ctx), ""]
        return out

    lines = [
        f"# 第{idx}集 · {episode['title']}",
        "",
        f"> 本集摘要：{episode['summary']}",
        "",
    ]
    lines += scene(
        f"## 场 1 ｜ {c1['loc']} · 夜 · 内",
        f"雨声压着窗。{c1['p']}停在门口，衣角还在滴水，{c1['prop']}被攥在手里，指节发白。",
        op, c1,
    )
    lines += ["（没有人先动。镜头从{c0}微微后仰的脸上，慢慢推近。）".format(c0=c1["a"]), ""]
    lines += scene(
        f"## 场 2 ｜ {c2['loc']} · 夜 · 外",
        f"{c2['loc']}的灯牌忽明忽暗。{c2['p']}站在光与暗的交界，身后传来脚步声。",
        cf[:3], c2,
    )
    lines += [f"（{c2['p']}没有退。镜头从他攥紧的手，切到对方忽然收住的笑。）", ""]
    lines += scene(
        f"## 场 3 ｜ {c3['loc']} · 夜 · 内",
        f"{c3['loc']}。所有人都在等{c3['p']}低头。他把{c3['prop']}推到灯光下，"
        f"声音不高，却让四周安静下来。",
        [ct[0], cf[3], ct[1], ct[2]], c3,
    )
    lines += ["（快门声、杯子落地的声音、有人倒吸一口气，混在一起。）", ""]
    lines += scene(
        f"## 场 4 ｜ {c4['loc']} · 夜 · 外",
        f"{c4['loc']}，风比刚才更冷。{c4['p']}背对镜头，肩线慢慢挺直。",
        hk, c4,
    )
    lines += [f"**【本集钩子】** {_fill(hk[0][1], c4)}", ""]
    return "\n".join(lines)


def storyboard(project: dict, episode: dict) -> list:
    g = _genre(project)
    idx = int(episode["idx"])
    c = _ctx(project, idx)
    cf = _dialogue_pool(project, "conflict", idx)
    ct = _dialogue_pool(project, "counter", idx)
    hk = _dialogue_pool(project, "hook", idx)
    style = project.get("style") or "真人写实"
    ratio = project.get("ratio") or "9:16"

    rows = [
        ("大全景", "缓慢推入", 5.0, f"{c['loc']}。夜色压得很低，{c['p']}从画面深处走来，轮廓被灯牌勾出。", ""),
        ("中景", "手持跟拍", 4.0, f"{c['p']}脚步停下，{c['prop']}在他手里晃了一下。", ""),
        ("特写", "固定", 3.0, f"{c['prop']}的细节被放大，边缘有旧磨损和一道新裂痕。", ""),
        ("近景", "过肩", 4.5, f"{c['a']}挡住去路，语气轻慢，身后的人都在看。", _fill(cf[0][1], c)),
        ("中景", "快速推镜", 4.0, f"{c['p']}抬眼，第一次没有回避。", _fill(ct[0][1], c)),
        ("特写", "微距", 3.0, f"{c['p']}的眼睛里映出灯光，呼吸慢下来。", ""),
        ("全景", "环绕", 5.0, f"{c['loc']}里气氛骤变，{c['n']}下意识向前半步。", ""),
        ("近景", "仰拍", 4.5, f"{c['p']}把{c['prop']}举起，声音不高却压住全场。", _fill(ct[1][1], c)),
        ("特写", "慢动作", 3.5, f"{c['prop']}落下的瞬间，所有人的表情凝固。", ""),
        ("大全景", "缓慢拉开", 5.5, f"{c['loc']}灯光一盏盏亮起，{c['p']}走向画面深处。", _fill(hk[0][1], c)),
    ]

    shots = []
    for i, (shot_type, camera, duration, desc, dialogue) in enumerate(rows, start=1):
        prompt = (
            f"{style}，竖屏 {ratio} 电影级画面，{shot_type}，{camera}，{desc}，"
            f"{g['tone']}，人物保持角色一致性，超清细节，真实材质"
        )
        shots.append(
            {
                "idx": i,
                "shot_type": shot_type,
                "camera": camera,
                "duration": duration,
                "location": c["loc"],
                "description": desc,
                "dialogue": dialogue,
                "prompt": prompt,
            }
        )
    return shots


def _wrap(text: str, width: int = 14) -> list:
    lines = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= width:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines[:4]


def placeholder_svg(title: str, subtitle: str, color: str, ratio: str = "9:16", badge: str = "分镜示意") -> str:
    if ratio == "16:9":
        w, h = 960, 540
    elif ratio == "1:1":
        w, h = 800, 800
    elif ratio == "4:3":
        w, h = 880, 660
    else:
        w, h = 720, 1280

    lines = _wrap(subtitle, 15)
    tspans = "".join(
        f'<tspan x="{w/2}" dy="{0 if i == 0 else 34}">{escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    font_size = 26 if ratio == "9:16" else 24

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101018"/>
      <stop offset="0.55" stop-color="{color}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#07070b"/>
    </linearGradient>
    <radialGradient id="r" cx="0.3" cy="0.2" r="0.8">
      <stop offset="0" stop-color="{color}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{color}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="p" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="#ffffff" fill-opacity="0.10"/>
    </pattern>
  </defs>
  <rect width="{w}" height="{h}" fill="#0a0a10"/>
  <rect width="{w}" height="{h}" fill="url(#g)"/>
  <rect width="{w}" height="{h}" fill="url(#r)"/>
  <rect width="{w}" height="{h}" fill="url(#p)"/>
  <rect x="26" y="26" width="{w-52}" height="{h-52}" fill="none" stroke="#ffffff" stroke-opacity="0.22"/>
  <text x="{w/2}" y="{h/2-120}" text-anchor="middle" fill="#ffffff" fill-opacity="0.92"
        font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="{font_size+18}" font-weight="700">{escape(title)}</text>
  <text x="{w/2}" y="{h/2-60}" text-anchor="middle" fill="#ffffff" fill-opacity="0.68"
        font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="18" letter-spacing="6">{escape(badge)}</text>
  <text x="{w/2}" y="{h/2+10}" text-anchor="middle" fill="#ffffff" fill-opacity="0.86"
        font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="{font_size}">{tspans}</text>
  <text x="{w/2}" y="{h-48}" text-anchor="middle" fill="#ffffff" fill-opacity="0.5"
        font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="16">零积分演示画面 · 配置图像模型后可生成真实画面</text>
</svg>"""
