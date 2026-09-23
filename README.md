# imgproc 批量图像加工

> 仓库：<https://gitee.com/siwpan/imgproc> ｜ 许可：MIT（见 [LICENSE](LICENSE)）

Tkinter  GUI 工具，对文件夹内图像批量执行加工操作，**绝不覆盖原图**，结果输出到 `<输入文件夹>/imgproc_out/`。

## 功能
- **缩放**：按目标宽度(px) 或 百分比
- **格式转换**：png / jpg / webp 互转（jpg 质量可调）
- **文字水印**：文字 / 位置(lt/rt/lb/rb/cc) / 透明度 / 字号
- **灰度化**
- **缩略图**：指定边长，居中贴到白底画布，作为主流程最终输出（与缩放/水印串联）
- **模板重命名**：`{name}` `{i}` `{ext}` 占位

## 运行
```bat
python main.py
```
依赖安装：`pip install Pillow`

## 说明
- 勾选的操作按 缩放→灰度→水印→缩略图→格式转换 的顺序串联，最终输出单一文件。
- 仅处理受支持格式（png/jpg/jpeg/webp/bmp/gif/tiff）。
- 自包含工具，不依赖 tools 组内其他项目。
