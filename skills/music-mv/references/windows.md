# Windows

使用 Node.js、Python 3.10+、ffmpeg/ffprobe 和 Chromium/Chrome。先检查命令是否可用，不运行 Unix 的 new_project.sh。工程、请求和缓存放在用户选择的项目中。

准备脚本会调用 npm.cmd，并把 npm 缓存及 TEMP/TMP 设置为工程的 .cache。渲染封装把浏览器配置、临时文件和磁盘缓存放在工程 .cache；它不扫描 C 盘寻找浏览器。

浏览器按以下顺序选择：--chrome=绝对路径 → mv-task.json 的 browser → 环境变量 CHROME_PATH。必须设置其中一项，不扫描系统或主目录，不假定用户电脑安装在作者的目录。

在启动 Claude Code 的同一个终端设置，例如：
~~~powershell
$env:CHROME_PATH = "D:/tools/chrome/chrome.exe"
claude
~~~

beat_grid.py 需要 numpy。prepare_mv.py 会把 <技能目录>/.deps 加入 Python 的依赖搜索路径，也可使用已经安装 numpy 的 Python 环境。如果检测失败且缺少 numpy，可安装到技能自己的目录：
~~~powershell
python -m pip install numpy --target "<技能目录>/.deps" --cache-dir "<当前项目>/.cache/pip"
~~~
若项目不允许安装依赖，保留错误原因，使用用户提供的 BPM 或先请求该数据；不要伪造已检测的结果。

输入路径或文件名含中文时使用 JSON、UTF-8 与参数数组，不把路径硬拼成 PowerShell 字符串表达式。权限、审批、项目规则以当前用户要求为准。这个技能不修改 Claude 的全局配置，也不安装到用户主目录。

从包含 .claude/skills/music-mv/SKILL.md 的项目打开 Claude Code，输入 /music-mv。它是项目技能，在别的独立项目里不可见；迁移时复制整个 music-mv 文件夹。
