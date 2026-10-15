# 来源与许可

本仓库是音乐 MV 工作流的二次封装，未将上游引擎宣称为原创。

| 来源 | 本仓库使用部分 | 许可 |
|---|---|---|
| [tuzhechen2005/opus-video-skills](https://github.com/tuzhechen2005/opus-video-skills) | painted-animation 模板、示例、音乐编排指导、节拍脚本 | [MIT 原文](licenses/opus-video-skills.LICENSE) |
| [JohnHeibel/ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) | p5.js + p5.brush 绘画引擎、角色库、时间轴、渲染器与指南 | [MIT 原文](licenses/ClaudeAnimationBase.LICENSE) |

原模板内的 LICENSE 也完整保留。新封装包含 Claude Code 斜杠入口、素材准备、音频截取、歌词时间转换、显式浏览器路径、项目缓存与输出校验。渲染器的适配说明见技能 references/credits.md。

依赖的 p5.js、p5.brush、puppeteer-core 与运行工具各自遵循其许可证；本仓库不重新授权这些依赖。

《爱你》是案例使用的歌曲，歌曲音频和歌词文件未包含在仓库内。README 中的无声动画预览来自实际案例，已裁去歌词带，不包含音乐音轨。预览中角色形象及可能涉及的商标仍归相应权利人；本 MIT 许可仅覆盖有权授权的软件代码与说明，不授予音乐或第三方商标权利。
