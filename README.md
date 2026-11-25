# BlendFlow

一款开源 Blender 效率插件，集成场景检查与修复、资产缩略图生成、多平台批量导出、渲染参数对比及多画幅构图。

**当前版本：0.6.3 · 实验性版本 · GPL-3.0-or-later**

[English documentation](README.en.md) · [下载安装包](dist/blendflow-0.6.3.zip) · [测试说明](TESTING.md)

## 安装

1. 下载上面的 `blendflow-0.6.3.zip`（文件页点击 Download raw file）。不要将 GitHub 的源码 Download ZIP 当作安装包。
2. Blender 偏好设置 → Get Extensions → Install from Disk，选择 ZIP 并启用。
3. 3D 视图按 **N**，进入 **BlendFlow**。四个功能面板可独立展开和收起。

Manifest 声明最低 Blender 4.2；开发测试使用过 5.1 和 5.3，尚未完成所有版本兼容验收。建议先在场景副本中使用。旧版启用失败后，请保存工作并重启 Blender 再安装。

## 功能

### Smart Inspector — 场景检查

- 分类检查未应用缩放、零顶点 Mesh、缺失外部图片，显示问题数量。
- 点击结果选中对象，Select & Frame Object 定位并聚焦。
- 支持单个/批量应用缩放、删除空网格、重新链接图片及按文件名查找图片。

扫描本身只读；对象检查覆盖当前场景，图片检查覆盖整个文件。结果是快照，编辑后需要重新扫描。空网格是零顶点 Mesh，不是 Empty 对象；带修改器的空网格可能生成可见几何，因此删除会跳过它。应用缩放会跳过共享网格、子对象、动画、约束、形态键等情况。打包图片不报缺失，UDIM、序列与影片暂不检查。

### Smart Thumb Preview — 资产缩略图

- 按选中对象或 Collection 批量生成透明 PNG，自动构图。
- 三分之四、正面（-Y）、侧面（+X）、俯视（+Z）四个机位。
- Soft / Neutral / Contrast 三套灯光、AgX 色彩管理、EV 曝光补偿。
- 同名图片自动编号，不覆盖已有输出。

推荐从 **Soft Studio + Three Quarter + 0 EV** 开始。原材质会保留，自发光材质可能需要降低 EV。Collection 模式为每个直接子集合生成一张（含后代对象）；无子集合时使用自身，有子集合时不单独处理根集合直属对象。

### Export Guard — 检查与导出

- Object / Collection 批量导出 FBX、GLB。
- 导出前检查、问题定位、文件名冲突阻断及 JSON 报告。
- Generic、Unity、Unreal Engine、Godot 平台预设，可编辑并通过 Save Platform 覆盖保存，Restore Defaults 恢复默认。
- 支持坐标轴、FBX 缩放/单位/Smoothing、GLB Y-Up、材质、Animation、面数警告与命名前缀。
- 独立后台 Blender 进程执行导出，使用复制数据，避免直接修改源资产。

平台预设是起始配置，**不是经过目标引擎认证的导入方案**。目前支持独立 Mesh 的 Action 动画；骨骼、父级、修改器、约束、NLA、驱动器、形态键等复杂依赖会阻断。导出时重新检查当前选择，定位问题后请重新选定批次。文件冲突阻断整个批次；运行中失败不会回滚已完成文件。文件提交需要目标文件系统支持硬链接。

### Smart Render — 测试渲染与多画幅构图

**Render Optimizer**：Cycles 下比较 512 / 1024 / 2048 Samples，分别开启/关闭降噪，另渲染 4096 Samples 参考图。输出耗时、中央细节裁切、非降噪差异图、HTML/JSON 报告与推荐配置。仅点击 Apply Recommendation 才改变原渲染参数。

**Smart Composition**：按选中主体或指定 Collection，为 16:9、1:1、9:16 创建独立相机和预览。支持主体位置及留白比例，保留原相机方向。新相机自定义属性记录所需分辨率，正式使用时需同步设置场景分辨率。

推荐依据图像误差与单次耗时；参考图仍有噪声，计时含预热影响，不能替代主观画质判断。测试关闭合成器、序列编辑器和区域渲染；新构图关闭景深与相机偏移。

## 当前限制

- 实验性版本，复杂生产场景仍需人工验收。
- 渲染同步执行，界面会等待；Optimizer 一次生成七张测试渲染，耗时较长。
- 未完整支持集合/粒子实例、未实现的 Geometry Nodes 实例及依赖外部坐标的复杂材质。
- 导出的文件不会被 Ctrl+Z 删除。
- 暂无增量导出、自动 LOD、骨骼重定向、材质烘焙、Asset Browser 同步。
- UI 背景遵循 Blender 原生主题。

## 开发与构建

源码位于 `blendflow/`：扫描 `scanner.py`、修复 `actions.py`、缩略图 `preview.py`、导出 `export_guard.py`、平台预设 `export_presets.py`、渲染 `smart_render.py`、界面 `ui.py`、生命周期 `__init__.py`。

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py
blender --background --factory-startup --python-exit-code 1 --python tests/restricted_enable.py
blender --background --factory-startup --python-exit-code 1 --python tests/lifecycle.py
blender --background --factory-startup --python-exit-code 1 --python tests/export_guard.py
blender --command extension validate blendflow
blender --command extension build --source-dir blendflow --output-dir dist
```

测试脚本仅应在新的后台 Blender 中执行，不要在生产场景里运行。使用 Blender 内置 Python/numpy，无需额外 pip 依赖。

## 参与贡献

欢迎 Issues 与 Pull Requests。反馈请提供 Blender 版本、系统、复现步骤、预期和实际结果；可附不含机密内容的最小场景。请勿上传客户模型、商业贴图或凭据。修改需保持扫描只读，并为影响场景的数据操作补充回归测试。

## 许可证

采用 [GNU GPL v3 或更新版本](LICENSE)。贡献代码同样按此许可证分发。
