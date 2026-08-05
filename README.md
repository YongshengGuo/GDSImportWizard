# GDS2EDB

GDS2EDB 是一个用于将 GDSII 版图数据转换为 Ansys EDB 的工具集，支持命令行与图形界面两种使用方式。

项目目标：

- 将 Tech 文件（CSV/IRCX/ITF/MIPT/ICT）解析为统一技术数据。
- 生成可用于导入 3D Layout 的 Control XML。
- 将 GDSII + Control XML 转换为 .aedb 工程。
- 提供批处理能力和面向日常工程的 UI 向导。

## 主要能力

- 支持 Tech 文件类型：.csv, .ircx, .itf, .mipt, .ict
- 支持输出目标：EDB、Control XML、CSV
- 可通过配置文件 gds2edb.cfg 控制导入与简化策略
- 支持 Layer Map 映射、介质层简化、Via Group、组件识别等选项

## 环境要求

- Python 3.10+
- Windows（当前工程与依赖以 Windows 流程为主）
- 依赖包：pyaedt、pywin32、pythonnet
- 已安装可用的 Ansys Electronics Desktop（用于 EDB 转换流程）

## 安装

推荐先在仓库根目录安装依赖：

```bash
pip install -r requirements.txt
```


## 快速开始

### 1) 启动图形界面

```bash
python gdsImportWizard.py
```

或直接运行源码入口：

```bash
python src/gds2edb/gdsImportWizard.py
```

### 2) 命令行模式

```bash
python gds2edb.py <techFile> <gdsFile> <edbPath> [options]
```

示例：

```bash
python gds2edb.py demo.ircx demo.gds demo.aedb -l layermap.map
```

仅生成 XML：

```bash
python gds2edb.py demo.ircx -t2x
```

仅生成 CSV：

```bash
python gds2edb.py demo.ircx -t2c
```

## CLI 参数

位置参数：

- techFile：技术文件路径
- gdsFile：GDSII 文件路径
- edbPath：输出 EDB 路径

可选参数：

- -l, --layerMap：LayerMap 文件路径
- -t2x, --tech2xml：仅执行 Tech -> XML
- -t2c, --tech2csv：仅执行 Tech -> CSV
- -cfg, --cfgFile：指定配置文件路径
- -v, --AedtVersion：指定 AEDT 版本

## 配置文件说明

默认配置文件位于 src/gds2edb/gds2edb.cfg，常见参数包括：

- SimplifyDieletricMethod：介质层简化策略
- SheetLayerThreshold：薄金属层转 sheet 的阈值
- IgnoreLayersReg：忽略层的正则表达式
- GenerateComponent：是否识别并生成组件
- OpenInAedt：转换完成后是否自动打开 AEDT

建议实践：

- 复制一份 gds2edb.cfg 到工程工作目录再按项目修改。
- 不同工艺或项目分别维护独立 cfg，便于追溯。

## 项目入口

- CLI 源码入口：src/gds2edb/gds2edb.py
- CLI 根启动器：gds2edb.py
- UI 源码入口：src/gds2edb/gdsImportWizard.py
- UI 根启动器：gdsImportWizard.py

说明：根目录两个启动器保持“薄转发”设计，只负责转发到 src 下真实入口。

## 项目结构

```text
src/gds2edb/          核心实现
tests/                测试用例
docs/                 文档、设计、执行计划
scripts/              架构和文档检查脚本
Help/                 生成后的帮助页面
```
