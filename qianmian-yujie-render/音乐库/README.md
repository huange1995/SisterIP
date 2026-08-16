# 🎵 音乐库

这里是你成片的 **BGM 曲库**。把 mp3/wav 丢进本目录，`compose` 就会自动命中（未设 `QYJ_BGM_DIR` 时，本目录即默认曲库）。

**用法**：脚本里 `audio.bgm: "深夜爵士-垫乐.mp3"` 精确定位某首；或什么都不写 → 按文件名排序自动取第一首。

## 现有曲目（原创占位垫乐）

下面 4 首是用 numpy+ffmpeg **本地合成**的原创垫乐（全原创 = 零版权风险），按气质分类，先顶上用：

| 文件 | 气质 | 适用场景 |
|---|---|---|
| `深夜爵士-垫乐.mp3` | 御姐 / 夜晚 / 酒吧 | 深夜爵士、酒吧、情绪向 |
| `lofi-慵懒.mp3` | 慵懒 / 换装 | 换装秀、轻慢卡点 |
| `国风-典雅.mp3` | 旗袍 / 典雅 | 国风、旗袍、静谧 |
| `轻快-氛围.mp3` | 日常 / 可爱 | 活泼、轻快日常 |

> 它们是"垫乐"级别（和弦垫 + 律动），够氛围但不惊艳。想要**真正的曲子**，往下用 Pixabay 换真曲。

## 为什么没自动下载真曲

脚本无法从 Pixabay 等主流源直接下文件：Pixabay 有 **Cloudflare 反爬**（浏览器会自动通过，命令行被挡）；SoundCloud / archive.org / ccMixter 国内网络不可达；SoundHelix 能直下但授权是 **GPL v3**（商用 IP 不能碰）。所以真曲需要**你在浏览器里点两下**，见下。

## 换真曲：Pixabay（推荐）

**[pixabay.com/zh/music](https://pixabay.com/zh/music/)** —— 中文界面、**免登录、免署名、可商用**（Pixabay License），国内浏览器可直接访问。

**操作**：点进下面任意链接 → 点试听 → 满意就点 Download → 把 mp3 拖进本目录 → 完成（compose 自动用）。

按气质直达：

- **御姐/深夜爵士**：
  - [Night Jazz（夜间爵士）](https://pixabay.com/zh/music/modern-jazz-night-jazz-583930/)
  - [Jazz Cocktail Bar Music（爵士鸡尾酒吧）](https://pixabay.com/zh/music/modern-jazz-jazz-cocktail-bar-music-556247/)
  - [Lofi Jazz Hip Hop（洛菲爵士）](https://pixabay.com/zh/music/lofi-lofi-jazz-hip-hop-479218/)
  - [Cozy Aesthetics（惬意洛菲）](https://pixabay.com/zh/music/lofi-cozy-aesthetics-472271/)
- **氛围/情绪**：[Aesthetic Chill（美学氛围）](https://pixabay.com/zh/music/electronic-aesthetic-chill-background-music-468806/)
- **轻快**：[Upbeat Jazz Music（明快爵士）](https://pixabay.com/zh/music/comedy-upbeat-jazz-music-349645/)
- **国风/典雅**：站内搜 `chinese` / `guqin` / `pipa` / `oriental` → [chinese 搜索结果](https://pixabay.com/zh/music/search/chinese/)
- **更多爵士**：[blues jazz 搜索结果](https://pixabay.com/zh/music/search/blues%20jazz/)

> 链接如失效，站内搜文件名关键词即可。建议下载时把页面授权声明截图存档（万一有 Content ID 争议可自证）。

## 备选源

| 源 | 授权 | 国内可达 | 备注 |
|---|---|---|---|
| [爱给网 aigei.com](https://www.aigei.com/) | 免费商用走 **CC/CC0** 协议，部分需署名 | ✅ | 需筛「许可协议」，下载通常要登录 |
| [Mixkit](https://mixkit.co/) | 免费商用、免署名 | ✅ | 无需登录；命令行 403，浏览器可下 |
| [Unminus](https://www.unminus.com/) | 个人+商业皆可、免署名 | ⚠️ 页面可达 | 文件托管在 SoundCloud（国内被墙） |
| YouTube 音效库 | 免费，部分需署名 | ❌ | 需梯子，不推荐 |

## 文件命名约定

`<气质>-<曲名>.mp3`，例如 `国风-玉楼春.mp3`。气质标签放前面，一眼可辨；`compose` 支持在脚本里按文件名精确引用。
