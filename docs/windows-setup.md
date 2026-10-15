# Windows 安装与运行

先把整个 skills/music-mv 文件夹复制到你的项目 .claude/skills/ 下。不要只复制 SKILL.md。

## 检查环境

需要 Claude Code、Node.js、Python 3.10+、ffmpeg（含 ffprobe）和 Chrome/Chromium。先确认终端能运行：

~~~powershell
node --version
python --version
ffmpeg -version
ffprobe -version
~~~

节拍检测需要 numpy。以下示例全部放在你自己的项目中：

~~~powershell
python -m pip install numpy --target "D:/mv/.claude/skills/music-mv/.deps" --cache-dir "D:/mv/.cache/pip"
~~~

Node 的依赖会在每个动画工程中通过 npm.cmd 安装，缓存使用工程 .cache/npm，不把 node_modules 包进技能。

## 指定浏览器

不自动扫描系统目录。在启动 Claude Code 的同一个终端设置 Chrome 路径：

~~~powershell
$env:CHROME_PATH = "D:/tools/chrome/chrome.exe"
claude
~~~

把路径换成你自己的浏览器。也可以在渲染时传 --chrome=绝对路径，或在生成的 mv-task.json 中设置 browser。

## 开始

把角色图片、歌曲和 LRC 放进项目目录。从这个项目启动 Claude Code：

~~~text
/music-mv 角色="D:/mv/character.png" 歌曲="D:/mv/song.mp3" 歌词="D:/mv/song.lrc" 截取="00:39-01:07" 风格="水彩墨线、甜蜜小镇"
~~~

默认创建新的 outputs/music-mv 子目录。不要先运行原模板的 demo；它只是引擎参考，与自己的作品无关。

## 常见问题

| 现象 | 处理 |
|---|---|
| 找不到 /music-mv | 确认路径是当前项目的 .claude/skills/music-mv/SKILL.md，再重开 Claude Code |
| 找不到 Chrome | 在启动 Claude 的同一终端设置 CHROME_PATH，或传 --chrome |
| BPM 为 null | 查看 mv-task.json 的 bpm_source；安装 numpy 后重新测量，或提供已知 BPM |
| 准备工程中途失败 | 不覆盖重建；检查已生成工程，修复依赖后接着完成，或使用一个新输出目录 |
| 渲染很慢 | 场景复杂度与水彩填充都会影响速度；先减少复杂笔触，必要时再调整分辨率对应的整个绘画系统 |
| 没有 GPU | 可使用 --soft-gl，速度通常更慢；未在所有硬件上验证 |
| 中文字体不对 | 模板默认加载 Google Fonts 的 Ma Shan Zheng，需要网络；若网络不可达，准备已获许可的本地字体并在 studio.html 配置 |

脚本细节见 [production.md](../skills/music-mv/references/production.md)。
