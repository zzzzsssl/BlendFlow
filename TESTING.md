# 测试说明

测试脚本使用 Blender 内置 Python。请在全新进程中运行，不要在生产场景执行。

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py
```

将最后的脚本路径替换为所需测试：

| 脚本 | 检查内容 |
| --- | --- |
| smoke.py | 检查规则、定位、隐藏/锁定对象处理 |
| actions.py | 应用缩放后的世界坐标保留、空网格删除 |
| lifecycle.py | 重复注册、模块重载、残留注册清理 |
| restricted_enable.py | Blender 受限启用阶段及禁用清理 |
| presets.py | 平台预设覆盖、切换、持久化及恢复默认 |
| export_guard.py | GLB/FBX 导出、覆盖阻断和源数据保留 |
| animation.py | 对象 Action 导出及 GLB 动画数据存在 |
| preview.py | 透明 PNG、原场景数据保留 |
| preview_presets.py | 四种机位实际渲染 |
| smart_render.py | 采样报告、差异输出和三画幅构图 |

## 验证记录与范围

开发过程中分别在 Blender 5.1 / 5.3 运行过上述相关测试。0.6.3 的四机位渲染及安装包校验通过。这里不宣称每个脚本均已在每个 Blender 版本运行，也不宣称覆盖完整生产场景。

## 手工验收

1. 从 dist 中的 ZIP 安装、启用、禁用、重新安装，检查四个折叠面板。
2. 检查分类筛选、定位、单个/批量修复，以及撤销。
3. 检查隐藏、锁定、共享网格、动画和层级对象的提示。
4. 验证贴图路径、打包图片、缺失图片及批量重链接。
5. 测试不同尺寸和材质的对象/Collection 缩略图。
6. 在目标引擎中导入 FBX/GLB，检查坐标、材质、动画及单位。
7. 检查渲染对比报告、多画幅相机和原场景状态。
8. Blender 4.2 最低兼容目标尚需验收；不同平台及文件系统需要测试。

构建与校验：

```sh
blender --command extension validate blendflow
blender --command extension build --source-dir blendflow --output-dir dist
```
