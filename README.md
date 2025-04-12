# 猫猫的工具箱
一个多功能工具集合，提供多种实用功能的Web应用。

## 功能特点
### 1. M4S转MP3
将M4S格式的音频文件转换为MP3格式，方便播放和分享。

### 2. 聊天工具
与AI客服小祥进行互动聊天。

### 3. 音频分离器
使用AI技术（Demucs）将歌曲分离为人声和伴奏两个独立轨道。

## 技术栈
- 后端：Flask (Python)
- 前端：HTML, CSS, JavaScript
- 音频处理：FFmpeg, Demucs
- 部署：可本地运行
## 安装与使用
### 环境要求
- Python 3.8+
- FFmpeg
- Demucs
### 安装步骤
1. 克隆仓库
```bash
git clone https://github.com/你的用户名/xiaodengdai-tools.git
cd xiaodengdai-tools
 ```
```

2. 创建并激活虚拟环境
```bash
python -m venv .venv
.venv\Scripts\activate
 ```

3. 安装依赖
```bash
pip install flask
pip install demucs
pip install soundfile sox
 ```

4. 安装FFmpeg
   确保FFmpeg已安装并添加到系统PATH中。
   可从 FFmpeg官网 下载。
### 运行应用
```bash
python app.py
 ```

应用将在 http://localhost:5000 启动。

## 使用说明
### M4S转MP3
1. 访问首页，点击"M4S转MP3"工具
2. 上传M4S文件
3. 点击转换，等待处理完成后自动下载
### 聊天工具
1. 访问首页，点击"和客服小祥聊天"
2. 在输入框中输入消息并发送
3. 与AI客服进行互动
4. ### 音频分离器
1. 访问首页，点击"音频分离器"工具
2. 上传音频文件（支持MP3、WAV、FLAC、OGG格式）
3. 点击"开始分离"，等待AI处理
4. 处理完成后，下载人声和伴奏轨道
## 注意事项
- 音频分离过程可能需要一些时间，取决于文件大小和服务器性能
- 所有上传的文件会在处理后自动删除，不会永久保存
- 分离后的音频文件将在1小时后自动清理

## 许可证
MIT
