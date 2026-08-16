# 千面御姐 · 顾遥 — AI 写真出图技能包

> **面面不同、芯芯同一、媚而不俗。**

把「千面御姐·顾遥」IP 的设计知识打包成一套**可共享、可复现的写真出图流水线**：
一句需求 → 五层配方自动拼装 → Seedream 大模型出图 → insightface「人不变」校验 → 归档。

**核心闭环**：先出多张候选锁基准图（定「这张脸」）→ 之后所有换装 / 换风格 / 三视图都以基准图为脸参考图生图，**人永远不变**。

---

## ✨ 特性

- **五层设定库**：`形象锚点 × 服装 × 姿势 × 场景 × 质量` 都是独立积木，按黄金公式自由组合
- **人物一致性**：insightface 人脸相似度校验，≥0.45 归档 / 0.35–0.45 存疑 / <0.35 判串味进拒图
- **六面形象**：黛眉 / 冷感职场 / 夜魅 / 飒影 / 慵懒晨光 / 泳池魅影，一套锚点锁死一张脸
- **完整闭环脚本**：`candidates`（出候选）→ `pick`（锁基准）→ `derive`（图生图+校验）→ 视频 / 成片（可选），产物自动归档
- **出视频是可选加工**：`montage` 图集→动态视频（零成本）＋ `video` 首帧→Seedance 图生视频（多镜头）——**图是主产品，视频不强迫**
- **成片 compose**：一条分镜表 = 一条短片——多镜头（图集连帧 / Seedance 原生）+ 音频（BGM 混音 + 火山 TTS 旁白）+ 字幕（字卡烧录 + SRT）+ 成片门
- **六段式创作骨架**：① **策划**（策划案 JSON：文案/姿势/镜头/连贯/音乐一次设计好，`produce` 纯本地展开）→ ② **脚本**（文案原子 copy[]：字幕/旁白绑镜）→ ③ **分镜**（分镜表：末帧接龙 `continue_from` + 统一调色 `grade`）→ ④ **设定**（角色/穿搭/表演/场景/影像 设定库）→ ⑤ **素材**（候选/基准/衍生出图 + 单镜视频）→ ⑥ **成片**（compose 出片）——好作品先把原子内容整体策划好，再排镜头执行
- **可分享**：整包复制到任何工作区即用，不依赖包外任何内容，产物自动落在对方工作区
- **每张图必带负面词**：露而不艳、媚而不俗，低俗 / 风尘 / 过度暴露硬禁

---

## 🧱 黄金公式（永远这个顺序，每一层都是积木）

```
[形象锚点] + [服装] + [姿势] + [场景] + [质量尾缀] + [负面词]
```

| 层 | 设定库 | 管什么 | 示例 |
|----|--------|--------|------|
| **形象锚点** | `设定/01-角色` | 脸 / 发型 / 妆容——选型时原样复制，**一字不改** | 黛眉：黑茶大波浪 + 正红唇 + 含水带媚 |
| **服装** | `设定/02-穿搭` | 服装件 / 制服 + 丝袜 × 高跟 + 配饰 | 护士·御姐版 + 听诊器 + 肉色薄丝袜 + 黑色细高跟 |
| **姿势** | `设定/03-表演` | 体态 × 手势 × 眼神 × 镜头 × 光位 | 侧身回眸 + 指尖轻理发丝 + 含水带媚 |
| **场景** | `设定/04-场景` | 环境 × 光线 × 氛围 × 道具 | 医院走廊，冷白 + 暖光混合 |
| **质量** | `设定/05-影像` | 焦段 × 光位 × 皮肤质感 × 风格块 + **负面词（必带）** | 真实写真人像、浅景深、高清 |

> 挑逗三拍：**眼神先到 → 指尖后收 → 停在临界**。三分留白、七分想象，媚不靠暴露堆。

---

## 🔁 六段式业务流程（策划 → 脚本 → 分镜 → 设定 → 素材 → 成片）

```
① 策划  策划案 JSON = 创意产物（概念/角色穿搭/文案原子/镜头原子/音乐/连贯）→ 可评审可改
② 脚本  文案原子 copy[]（字幕/旁白，绑镜）嵌在策划案里
③ 分镜  分镜表 = 策划案展开（produce --emit）：末帧接龙 continue_from + 统一调色 grade
④ 设定  角色/穿搭/表演/场景/影像 设定库（只读参考）
⑤ 素材  候选 → 锁基准 → 衍生出图（换装/风格/三视图/封面/栏目图集）+ 单镜视频
⑥ 成片  compose 逐镜渲染 → 拼帧 → 调色 → 混音 → 字幕 → 封装
```

只出图不剪片：走到 ⑤ 就是完整交付；要短片才走 ⑥。核心两步铁律——**先选型定基准，再基于基准衍生；人不变是衍生的硬前提**。

### ⑤ 素材·选型（六步，新形象必走）
1. 该形象**无**基准图 → 走选型
2. 读设定库：锚点**原样复制** + 服装 / 姿势 / 场景 / 质量搭积木
3. 按黄金公式拼完整提示词
4. `candidates` 出候选
5. 用户挑 1 张最好的
6. `pick` 锁基准图 → 过「选型门」（脸合格 + 性感质量门）

### ⑤ 素材·衍生（五步，必须有基准图）
1. 该形象**有**基准图 → 走衍生
2. 读服装 / 姿势 / 场景 / 质量设定（**不读形象锚点**——脸由基准图接管）
3. 拼衍生提示词（不含锚点块）
4. `derive` 以基准图为参考图生图
5. 过「衍生门」：insightface 人不变校验（≥0.45 归档）+ 媚门

> **没有基准图不能直接换装 / 三视图 / 封面**——先选型定基准，再衍生。这是流程硬约束。

---

## 👤 六面形象总览

| 形象 | 一句灵魂 | 气质 | 基准图 |
|------|---------|------|--------|
| **A · 黛眉** | 温柔知性的东方古典，第一眼顾遥 | 温柔知性、暗藏挑逗 | ✅ 已锁 `定妆照/A-黛眉/` |
| **B · 冷感职场** | 一句话，会议室安静 | 高冷、禁欲式挑逗 | 待选型 |
| **C · 夜魅** | 夜晚归她管，酒杯映着眼里的灯 | 慵懒魅惑、直白诱惑 | 待选型 |
| **D · 飒影** | 低头看你一眼，你自动站直 | 威慑、野性挑逗 | 待选型 |
| **E · 慵懒晨光** | 醒来前的第一面，比夜色更私密 | 慵懒、居家诱惑 | 待选型 |
| **F · 泳池魅影** | 湿发和水的交界是最美的一条线 | 明媚、健康野性媚 | 待选型 |

> **形象串味 = 废图**（A 的脸配 C 的妆直接重做）。换形象 = 换整套锚点，不是只换衣服。

---

## 📁 项目结构

```
SisterIP/
├── .claude/skills/qianmian-yujie-render/   # 技能包（本仓库主体）
│   ├── SKILL.md                            # 技能说明（agent 执行入口）
│   ├── references/                         # 六段式知识库
│   │   ├── 策划/01-策划.md                  # ① 策划：策划案 schema + 编辑 Checklist + 黄金公式拼装
│   │   ├── 脚本/01-脚本.md                  # ② 脚本：文案原子 copy[]（字幕/旁白绑镜）规范
│   │   ├── 分镜/01-分镜.md                  # ③ 分镜：分镜表 schema（三源/接龙/调色/时间轴）+ 功能链
│   │   ├── 设定/                            # ④ 设定：角色 / 穿搭 / 表演 / 场景 / 影像 + 栏目 + 范本
│   │   │   ├── 01-角色.md                   #   6 形象锚点（脸）
│   │   │   ├── 02-穿搭.md                   #   服装 / 丝袜 / 高跟 / 配饰
│   │   │   ├── 03-表演.md                   #   姿势积木 + 三档梯度
│   │   │   ├── 04-场景.md                   #   场景积木 + 6×6 预置
│   │   │   ├── 05-影像.md                   #   质量尾缀 + 负面词 + 边界
│   │   │   ├── 06-栏目.md                   #   6 内容栏目一键出
│   │   │   └── 07-范本.md                   #   E/G 组候选 + 衍生组 few-shot
│   │   ├── 素材/                            # ⑤ 素材：出图 + 单镜视频
│   │   │   ├── 01-出图.md                   #   候选 → 锁基准 → 衍生出图
│   │   │   └── 02-单镜视频.md               #   图集→montage / 首帧→video
│   │   ├── 成片/01-成片.md                  # ⑥ 成片：分镜表 → compose（音频/字幕/成片门/调色）
│   │   ├── 流程.md                          # 六段式业务流程总纲 + 入口矩阵 + 命令对照
│   │   ├── 校验.md                          # 六段门禁：策划/脚本/分镜/设定/素材/成片 + 通用门
│   │   ├── 发帖文案.md                      # 发帖配文（不入图，也不进片）
│   │   └── 产物.md                          # 产物结构与分享
│   └── scripts/
│       ├── generate.py                      # 入口（薄壳，转发到 cli.main()）
│       ├── cli.py                           # CLI 装配：子命令自动发现 + argparse + 统一错误处理
│       ├── config.py                        # 统一配置（图片/视频/音频/字幕/成片，env 可覆盖）
│       ├── archive.py                       # 产物桶 + 命名 + 写入（单点维护）
│       ├── pipeline.py                      # 共享编排：成本/校验档位/读图解码/竖版首帧
│       ├── planning.py                     # 策划：策划案 schema + 校验 + 黄金公式拼装 + 展开分镜表
│       ├── shotlist.py                      # 分镜：分镜表 schema + 校验 + 确定性时序
│       ├── engine/                          # 外部能力适配器
│       │   ├── ark.py                       #   方舟客户端基类（session/重试/退避 去重）
│       │   ├── seedream.py                  #   图片：Seedream（含 Data URI 引用）
│       │   ├── seedance.py                  #   视频：Seedance（异步提交→轮询→下载 + 多镜/接龙）
│       │   ├── tts.py                       #   火山 TTS 旁白（未配凭据降级跳过）
│       │   ├── ffmpeg.py                    #   ffmpeg 封装（concat/混音/封装/盖字卡/调色/末帧，自带二进制）
│       │   └── errors.py                    #   共用错误分类
│       ├── media/                           # 本地媒体加工（纯本地可测）
│       │   ├── montage.py                   #   图集→视频帧渲染（多镜头：cuts/cam/烧字）
│       │   ├── subtitle.py                  #   字卡绘制(PIL+微软雅黑) + SRT 导出
│       │   └── audio.py                     #   BGM 曲库解析 + 旁白轨 + 混音调度
│       ├── commands/                        # 子命令（每模块一个 register，自动发现）
│       │   ├── image.py                     #   candidates / pick / derive / status
│       │   ├── montage.py                   #   图集 → 9:16 动态视频（零成本，薄壳→media）
│       │   ├── video.py                     #   Seedance 图生视频（多镜头，可选增强）
│       │   ├── compose.py                   #   分镜表 → 成片（多镜头+音频+字幕+成片门+调色+接龙）
│       │   └── produce.py                   #   策划案 → 预览 / 逐镜prompt / 分镜表（策划段）
│       ├── validator.py                     # 人不变校验 + 视频抽帧
│       └── requirements.txt                 # 依赖（requests/opencv/insightface/imageio-ffmpeg/Pillow…）
└── qianmian-yujie-render/                   # 出图/出视频产物（作品，自动归档）
    ├── 定妆照/A-黛眉/                        # 已确认基准图
    ├── 候选/                                 # 选型候选批次
    ├── 栏目图/                               # 换装 / 栏目衍生
    ├── 三视图/                               # 三视图衍生
    ├── 视频/                                 # 视频产物（montage 合成 / video 图生视频 / compose 成片）
    ├── 音乐库/                               # BGM 曲库（4 首原创垫乐 + 真曲升级指引）
    ├── 拒图/                                 # 未过人不变校验
    └── 作品集/                               # 成品精选
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
cd .claude/skills/qianmian-yujie-render
uv venv
uv pip install -r scripts/requirements.txt
```

### 2. 配置密钥

```bash
cp scripts/.env.example scripts/.env   # 然后编辑 .env 填 ARK_API_KEY
```

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `ARK_API_KEY` | **必填**，火山方舟密钥 | — |
| `ARK_MODEL` | 出图模型 | `doubao-seedream-5-0-lite-260128` |
| `ARK_BASE_URL` | API 地址 | `https://ark.cn-beijing.volces.com/api/v3/images/generations` |
| `ARK_VIDEO_MODEL` | 视频模型（Seedance，需在控制台开通） | `doubao-seedance-2-0-260128` |
| `ARK_VIDEO_RATIO` / `ARK_VIDEO_RESOLUTION` | 视频比例 / 分辨率 | `9:16` / `720p` |
| `ARK_FIRSTFRAME_MODE` | 视频首帧方式 | `derive` |
| `ARK_TTS_APPID` / `ARK_TTS_TOKEN` | 火山 TTS 旁白（语音技术控制台申请，非 ARK key；不配则旁白跳过） | 空 |
| `ARK_TTS_VOICE` | TTS 音色 | `BV700_streaming` |
| `QYJ_BGM_DIR` | BGM 曲库目录（compose `audio.bgm` 未命中时自动取） | 空 |
| `QYJ_BGM_VOLUME` / `QYJ_BGM_FADE` | BGM 音量 / 淡入淡出秒数 | `0.5` / `1.0` |
| `QYJ_SUBTITLE_FONT` / `QYJ_SUBTITLE_SIZE` | 字卡字体（空=自动微软雅黑）/ 字号 | 空 / `48` |
| `QYJ_OUTPUT_DIR` | 产物根目录 | `<工作区>/qianmian-yujie-render` |
| `INSIGHTFACE_ROOT` | 人脸模型目录（含 `models/buffalo_l/`）；脚本会自动探测工作区模型，找不到才自动下载 | 自动探测 |

> `.env` 已在 `.gitignore` 中，**永远不会被提交**。

### 3. 出图

**选型（新形象，先定基准）：**
```bash
python scripts/generate.py candidates --prompt "<完整提示词>" --n 4 --tag 形象B
python scripts/generate.py pick <候选目录> <candidate-01.png> --name B-冷感职场
```

**衍生（已有基准图，换装 / 换风格 / 三视图）：**
```bash
python scripts/generate.py derive \
  --base ../../../qianmian-yujie-render/定妆照/A-黛眉/A-黛眉.png \
  --prompt "穿白色护士制服裙，肉色薄丝袜，黑色细高跟，听诊器挂颈，侧身回眸，全身照，医院走廊冷白+暖光混合，真实写真人像，高清画质，不要卡通、动漫、低俗、过度暴露、风尘感" \
  --tag 护士装 --n 2
```

**查看已出图/视频清单：**
```bash
python scripts/generate.py status
```

### 4. 出视频（可选加工，图是主产品）

> **图是主产品，视频不强迫**。两个栏目类栏目适合动态化，两条路都基于已锁基准图：

**图集 → 动态视频（零成本，纯本地，无需开通任何模型）：**
```bash
# 先用 derive 出一组换装图集，再合成 9:16 动态视频（Ken Burns + 淡入淡出）
python scripts/generate.py derive --base ../../../qianmian-yujie-render/定妆照/A-黛眉/A-黛眉.png \
  --prompt "<换装提示词>" --tag 换装秀 --n 3
python scripts/generate.py montage --dir ../../../qianmian-yujie-render/栏目图/换装秀 --tag 换装秀
```

**首帧 → Seedance 图生视频（可选增强，需先开通视频模型）：**
```bash
# 未开通也能 --dry-run 验证前置（首帧准备 + 参数组装）
python scripts/generate.py video \
  --base ../../../qianmian-yujie-render/定妆照/A-黛眉/A-黛眉.png \
  --prompt "慵懒靠着吧台，指尖沿杯沿划过，眼神缓缓上挑，发丝微扬，固定机位" \
  --tag 深夜爵士 --duration 5 --ratio 9:16 --firstframe crop
```

> 开通视频模型：火山方舟控制台 → 开通管理 → 视频生成模型（`doubao-seedance-2-0-260128`，未开通可回退 `doubao-seedance-1-0-lite-i2v-250428`）。动作提示词遵循「动小不动大」；多镜头写法 `--duration 0` + 提示词里 `Shot 1: … / Shot 2: …`（配方见 `references/素材/02-单镜视频.md`）。

**分镜表 → 成片（多镜头 + 音频 + 字幕，compose）：**
```json
// scripts/深夜爵士.json —— 一条分镜表 = 一条短片
{
  "title": "深夜爵士", "ratio": "9:16", "fps": 24,
  "scenes": [
    {"id": "s1", "src": "images", "dir": "栏目图/换装秀", "per": 2.5, "cuts": "hard", "text": "夜晚归她管"},
    {"id": "s2", "src": "seedance", "base": "定妆照/A-黛眉/A-黛眉.png",
     "prompt": "Shot 1: 侧身回眸 发丝微扬 / Shot 2: 指尖划过杯沿 眼神上挑", "dur": -1,
     "firstframe": "derive", "ff_prompt": "9:16 竖版写真", "text": "三点后的爵士"}
  ],
  "audio": {"bgm": "深夜爵士.mp3", "bgm_volume": 0.4,
    "voiceover": [{"scene": "s2", "text": "夜晚归她管，酒杯映着眼里的灯。"}]}
}
```
```bash
python scripts/generate.py compose --script scripts/深夜爵士.json --dry-run   # 零 API 看镜头/成本/音频/字幕
python scripts/generate.py compose --script scripts/深夜爵士.json              # 真合成
```
产物：`视频/<title>-<时间戳>/` 下 `{title}.mp4`（含音轨）+ `subtitle.srt` + `clips/`。分镜表语法见 `references/分镜/01-分镜.md`。

**策划案 → 成片（策划段，推荐起点）**：先整体策划 文案/姿势/镜头/连贯/音乐，再展开分镜表执行：
```bash
python scripts/generate.py produce --inventory                         # 盘点形象库资产（服装/定妆照/曲目）
python scripts/generate.py produce --brief 策划案.json --dry-run       # 创意预览（评审）
python scripts/generate.py produce --brief 策划案.json --prompts       # 逐镜完整 prompt（审查）
python scripts/generate.py produce --brief 策划案.json --emit 分镜表.json # 展开分镜表
python scripts/generate.py compose --script 分镜表.json                # 出片（含末帧接龙 + 统一调色）
```
策划案 = 创意产物（AI 编辑生成 + 手工可精修），schema 见 `references/策划/01-策划.md`；示例见 `scripts/examples/策划案-深夜爵士-顾遥.demo.json`。

### 5. 校验

| 段·门禁 | 门槛 |
|---------|------|
| ① 策划门 | `produce --dry-run` 创意预览评审：立意一句话讲得清 + 功能链完整 |
| ② 脚本门 | 文案原子合规：媚而不俗 + 短句留白 + 与画面同档 + 绑定自洽 |
| ③ 分镜门 | 首镜定调 + 源字段自洽 + seedance 动小不动大 + 连贯可查 |
| ④ 设定门 | 角色基准已锁 + 原子从设定库挑（锚点原样复制） |
| ⑤ 素材门 | 选型门（正脸清晰 + 五官完整 + 锚点语义一致 + 性感质量门）；衍生门（人脸相似度 **≥0.45** 归档 ✅ ／ 0.35–0.45 存疑 🟡 ／ **<0.35** 串味进拒图 ❌）；单镜视频门（抽 50%/90% 帧，阈值同上；首帧=基准图、动小不动大） |
| ⑥ 成片门 | 每个 seedance 镜抽帧人不变（阈值同上）；**任一镜不过 = 整批成片进拒图** |
| 连贯三件套 | 策划期设计（姿势/场景延续）+ `continue_from` 末帧接龙 + `grade` 统一调色 |
| 通用媚门 | 真实写真、腿线 + 高跟在画面、挑逗三拍至少命中一拍、露而不艳 |

> 人脸相似度管「脸」，性感质量门管「媚」——**两张都要过**。

---

## 🎨 现有作品

| 栏目 | 形象 | 产物 |
|------|------|------|
| 定妆照 | A·黛眉 | [A-黛眉.png](qianmian-yujie-render/定妆照/A-黛眉/A-黛眉.png) |
| 换装·女仆装 | A·黛眉 | [女仆装-01.png](qianmian-yujie-render/栏目图/女仆装/女仆装-01.png) |
| 换装·护士装 | A·黛眉 | [护士装-01.png](qianmian-yujie-render/栏目图/护士装/护士装-01.png) · [护士装-02.png](qianmian-yujie-render/栏目图/护士装/护士装-02.png) |
| 合成视频（montage 测试） | A·黛眉 | [护士装试合成-montage.mp4](qianmian-yujie-render/视频/护士装试合成-20260816-012645/护士装试合成-montage.mp4) |

---

## ⚠️ 红线（违反 = 废图）

1. **锚点块一字不改**——只在选型用；A 的脸不能配 C 的妆（形象串味 = 废图）
2. **换装不改脸 / 衍生人不变**——衍生永远基于基准图的脸，锚点不重新生成
3. **无基准图不能直接衍生 / 出视频**——三视图 / 换装 / 封面 / `video` / `montage` 先走选型定基准
4. **负面词必带**——露而不艳、媚而不俗；低俗 / 风尘 / 过度暴露 / 油腻硬禁
5. **边界守恒**——诱惑档 ≠ 暴露档；皮肤面积可多，画面依然留白、克制、真实摄影感
6. **文案不入图 / 不入片**——发帖配文单独输出、绝不拼进图提示词；片内字幕/旁白走 `references/脚本/01-脚本.md`，合规才入片
7. **视频动小不动大**——图生视频只写轻微动作（眼神 / 发丝 / 指尖），大幅动作崩脸崩形 = 废片
8. **字幕 / 旁白文案合规**——成片字卡与旁白先过「媚而不俗」底线，低俗 / 引导词 / 违禁词不入片
9. **成片门是硬门**——compose 任一 seedance 镜抽帧人不变不过 = 整条成片不能交付
10. **连贯三件套**——成片先策划期设计 + `continue_from` 末帧接龙 + `grade` 统一调色；缺一个连贯就打折

---

## 🤝 分享 / 安装到其他工作区

1. 复制整个 `qianmian-yujie-render/` 技能包到对方工作区 `.claude/skills/`
2. 对方装依赖 + 复制 `.env.example` 为 `.env` 填自己的 `ARK_API_KEY`
3. 首次 `derive` 人脸校验会自动下载 buffalo_l 模型（约需联网一次）
4. 产物自动落在对方工作区 `qianmian-yujie-render/`

> 技能包是**完整闭环**：配方、脚本、校验、产物路径全在包内，不依赖包外任何内容。

---

## 🔒 安全

- **密钥不入库**：`scripts/.env`（`ARK_API_KEY`）已被 `.gitignore` 排除
- `.venv/`、`models/`（insightface 权重）、`settings.local.json` 均不跟踪
- 分享时对方复制 `.env.example` 填自己的密钥，任何人的密钥都不会进仓库

---

## 📄 许可与声明

本项目为「千面御姐·顾遥」IP 的自用创作工具，产物图片与提示词库属创作者所有。出图模型由火山方舟 Seedream 提供（默认 `doubao-seedream-5-0-lite-260128`，2048×2048，成本约 ¥0.25/张）。
