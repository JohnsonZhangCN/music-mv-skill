# 生产流程与脚本接口

## 请求 JSON

用文件工具写 UTF-8 JSON，不把未经转义的用户文本拼接为 shell 命令。Windows 路径建议使用正斜杠。

~~~json
{
  "image": "D:/mv/character.png",
  "audio": "D:/mv/song.mp3",
  "lyrics": "D:/mv/song.lrc",
  "start": "00:39",
  "end": "01:07",
  "style": "小镇姑娘",
  "role_mode": "both",
  "output": "D:/mv/outputs/music-mv/first-mv"
}
~~~

默认宽高 1920×1080，fps=24。当前模板的构图/字幕使用这套固定坐标；更换宽高需要先适配 compositor，脚本会拒绝其他尺寸。可提供 bpm 与 source_beat（源歌曲上的一次节拍时间）；不提供时运行 beat_grid.py 自动测量。role_mode 是供分镜使用的说明，不会自动从图中分割角色。

准备脚本：
- 先检查输入、时间、音频长度和歌词，再创建新工程；拒绝覆盖已有目录。
- 复制模板和参考图，抽取准确区间为 assets/clip.m4a；PROJECT.audio 指向这一片段，而非整首歌曲。
- 忽略 LRC 的非时间元数据，支持 BOM、多时间标签、毫秒 offset、同时间原文/译文与空行清屏。
- 行的源时间减 clip_start；跨入片段的行保留负 line_start，显示从 0 开始。片尾显示截止，但 sing 进度保留该句原始时间长度。
- 生成 src/config.js、数组格式的 src/karaoke.js、analysis/lyrics.json 和 mv-task.json；移除 demo 注册并加载 karaoke。
- 不创作镜头、不生成最终 MV；随后由 Claude 编写故事和场景。

## 音乐和表演

先读 ANIMATION_GUIDE.md，按其引擎接口绘制。SHOTS 的时间都是片段时间，最后一镜结束于 PROJECT.duration。布景、角色、道具保持一致；辅助函数放在场景 IIFE 内或稳定的共享对象中，避免覆盖 p5 全局名。

BPM 自动检测是节拍估计；听音频核对快慢拍和动作节奏。不要偷偷改音频速度。普通 LRC 没有词级时间，因此默认填色是行内近似。需要精确口型/逐字字幕时，另做对齐且报告该步骤。

每个歌词意象至少有一次可读表演；极短的歌词可以共享连续镜头。主角在主要表演镜头中要足够大。把字幕区域 y≈960 以下留给歌词；用前景覆盖遮挡人物时保持正确绘制层级。

## 渲染与检查

下面的 <技能目录> 为 ${CLAUDE_SKILL_DIR}，<工程> 来自 mv-task.json。在 Windows 使用有引号的绝对路径。

~~~powershell
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --sheet=0,0.62,2.82,5.18 --out=out/check/first.jpg
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --strip=2.8:3.2 --out=out/check/motion.jpg
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --clip --range=0:1 --out=out/check/one-second.mp4
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --clip --out=out/video.mp4
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --verify=out/video.mp4
~~~

所有动作分别运行。--out 的相对路径相对于工程。现有文件默认拒绝覆盖；显式 --overwrite 可重做已授权的预览。预览也可加 --crop=x,y,w,h、--cols=4、--w=480；采用软件 WebGL 时加 --soft-gl。

完整视频较长时：
~~~powershell
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --frames --workers=4
node "<技能目录>/scripts/render_mv.mjs" "<工程>" --encode --out=out/video.mp4
~~~

--frames 复用现有帧。场景发生变化后，用安全的文件操作删除相关旧帧或整个工程内的 out/frames，再渲染。--encode 校验连续帧数量并显式带入裁剪音轨；不要把不同帧率或不同版本的画面混起来。

检查每镜头代表帧、完整动作条、镜头接缝、首尾、中文字体与歌词遮挡。查看图片后修正，再生成 MP4。视频封装会验证 H.264、音轨、尺寸、帧率和时长；这些技术检查不等于视觉质量确认。完整 MP4 的首次输出仍需播放抽查。

## Preparing after an interrupted installation

If preparation failed after the project was created, inspect mv-task.json and the error. Do not rerun preparation into that existing directory. Resume dependency installation in the project using npm.cmd with npm_config_cache and TEMP/TMP pointing to its .cache, then continue scene creation. If abandoning a partial project, choose a new output directory and keep or remove the old one only within the authorized project.
