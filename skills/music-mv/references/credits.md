# 来源与改动

本技能二次封装自 [opus-video-skills / painted-animation](https://github.com/tuzhechen2005/opus-video-skills/tree/main/skills/painted-animation)，基于 [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) 的 p5.js + p5.brush 模板。

模板的 MIT 许可和版权说明保留于 assets/painted-animation/template/LICENSE。小镇姑娘示例与分镜作为风格参考保留；不包含任何示例歌曲。

新增：Claude Code 斜杠入口、中文参数规范、Windows 工程准备、精确音频裁剪、LRC 时间转换、节拍相位转换、项目内缓存及渲染校验。模板渲染器调整显式浏览器路径、项目内配置目录和 ffmpeg 退出处理，不扫描主目录/系统目录；画面引擎保持原接口。指南加入了歌词字幕例外。

公开发行版移除了作者机器专用的浏览器和 Python 依赖路径。上游许可原文保留于仓库 licenses/，安装包中的引擎许可保留于模板 LICENSE。
