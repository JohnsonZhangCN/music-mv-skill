---
name: music-mv
description: Use when the user invokes /music-mv with a character image, song, LRC lyrics, source time range and a hand-painted 2D music-video style, including 小镇姑娘.
argument-hint: '角色="图片路径" 歌曲="歌曲路径" 歌词="LRC路径" 截取="00:39-01:07" 风格="小镇姑娘"'
disable-model-invocation: true
---

# Music MV

把用户素材编排为有表演、歌词同步和转场的 2D 手绘 MV，交付可播放的 MP4。内置 painted-animation 的 p5.js + p5.brush 引擎、示例和 Windows 封装；不依赖另一个已安装技能，也不需要外部视频生成 API。

用户本次参数：

$ARGUMENTS

## 解析请求

接受中文自然语言或 key=value。必填：角色图片 image、歌曲 audio、歌词 lyrics、开始 start、结束 end、风格 style。路径含空格时支持引号。时间接受秒数、M:SS 或 H:MM:SS。缺失时一次列出缺项；已有信息不重复问。

默认：1920×1080、24fps、行级歌词、图片中清楚区分的角色全部入镜、输出到当前项目的 outputs/music-mv 下的新目录。用户指定单主角、无字幕、其他帧率时按其要求。复杂人物图先定义模型表并画测试帧；图片是身份与造型参考，不能只做贴图平移或静态幻灯片。

风格=小镇姑娘时读取 references/styles.md，并查看 assets/painted-animation/docs/xiaozhen-sheet.jpg。该名称指示例的水彩纸、墨线、限帧表演、歌词意象与连贯转场，不照搬原歌剧情。其他风格映射到可实现的 2D 绘画语言；写实真人或 3D 需求先说明本引擎的边界。

## 制作

1. 检查三个输入文件，查看角色图。先输出简短方案：角色、故事主线、画面风格、文件位置；遵守项目已有的审批要求。用户已授权完整生成时持续做到成片；只有“先看分镜”才在分镜后停下。
2. 阅读 assets/painted-animation/template/ANIMATION_GUIDE.md 和 references/production.md。音乐编排需要时读取 references/music-video.md；其按小节扩展片段的建议不能覆盖用户的精确截取区间。
   若模式=先看分镜，只读取图片和歌词、测量节拍并写分镜；跳过工程安装、场景创作和渲染，交付分镜后停止。
3. 用文件工具把规范化 JSON 写进当前项目 .cache/music-mv-request.json。必须给 output 一个当前项目内尚不存在的绝对路径。用脚本准备素材和工程：
   ~~~powershell
   python "${CLAUDE_SKILL_DIR}/scripts/prepare_mv.py" --request "<请求JSON绝对路径>" --install
   ~~~
   Windows 依赖、缓存和浏览器见 references/windows.md。辅助脚本只准备工程，场景仍由你创作。
4. 读取生成的 mv-task.json、analysis/lyrics.json；确认 BPM 与 beat_offset。检测失败时修复依赖并测量，或使用用户提供的 BPM；不能把估计值当测量。保留指定音频范围，不擅自加前奏、变速或淡出。普通 LRC 只提供行级时间，歌词填色是行内估计，不能声称逐字精确对齐。
5. 写完整 STORYBOARD.md：每个镜头的片段时间、歌词、动作、构图、转场。创建 src/scenes 内的场景文件，在 studio.html 注册；移除演示场景。角色应有表情、预备动作、重心变化、跟随动作和可读的演出。每帧是时间 t 的纯函数。
6. 用 scripts/render_mv.mjs 渲染每镜头代表帧、动作条和接缝，打开图片检查并修正。无字幕时在 studio.html 移除 karaoke.js 的加载。
7. 渲染完整视频；封装会校验时长、尺寸、帧率和音轨。检查开头、结尾和所有转场，再交付 MP4、分镜和预览图的真实绝对路径。修改场景后重新渲染受影响帧，避免复用旧帧。不得用未打开的预览或未播放/验证的视频声称质量已确认。

默认顺序：素材检查 → 分镜 → 场景创作 → 预览修正 → MP4。不要在正常步骤之间重复请求批准。仅用户明确要求时使用子代理。

## 调用示例

~~~text
/music-mv 角色="D:/mv/character.png" 歌曲="D:/mv/song.mp3" 歌词="D:/mv/song.lrc" 截取="00:39-01:07" 风格="小镇姑娘"
~~~

可追加：角色模式=仅橙色主角、字幕=无、模式=先看分镜。图片中有多位清楚区分的角色时默认全部入镜，并连续做到成片。

来源和许可见 references/credits.md。
