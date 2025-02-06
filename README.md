### 操作指南

    设置执行权限（Mac需要）
    chmod 755 ffmpeg/ffmpeg ffmpeg/ffprobe

    运行测试
    python main.py

    Windows打包命令:
    pyinstaller --onefile --windowed --add-data="config;config" --add-data="ffmpeg;ffmpeg" .\main.py

    Mac打包命令(产生的main.app可以删除，不需要):
    pyinstaller --onefile --windowed --add-data="config:config" --add-data="ffmpeg:ffmpeg" main.py

#### 4.常见问题处理
###### Q1: 出现 Permission denied 错误
    # Mac/Linux
    chmod 755 ffmpeg/ffmpeg
    chmod 755 ffmpeg/ffprobe
    
    # Windows
    右键exe文件 → 属性 → 解除锁定

### 目录结构
    your_project/
    ├── README.md
    ├── config
    │   └── settings.ini
    ├── ffmpeg
    │   ├── mac
    │   │   ├── ffmpeg
    │   │   └── ffprobe
    │   └── win
    │       ├── ffmpeg.exe
    │       ├── ffplay.exe
    │       └── ffprobe.exe
    ├── input
    │   ├── 1.mp4
    │   └── 2.mp4
    ├── install_mac_final.sh
    ├── main.py
    ├── output
    ├── requirements.txt
    └── video_tool.log