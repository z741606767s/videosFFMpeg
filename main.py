#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import platform
import configparser
import logging
import shutil
import atexit
import time

import cv2
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from moviepy.config import change_settings

# ---------------------------- 日志配置 ----------------------------
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("video_tool.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)


# ------------------------- 配置管理模块 ---------------------------
class ConfigManager:
    """智能配置管理器"""
    CONFIG_NAME = "settings.ini"

    def __init__(self):
        self.base_dir = self._get_base_path()
        self.config_path = self.base_dir / "config" / self.CONFIG_NAME
        self.config = configparser.ConfigParser()
        self._initialize()

    def _get_base_path(self) -> Path:
        """获取基础路径（兼容打包模式）"""
        return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent

    def _get_app_path(self, relative_path: str) -> Path:
        """动态获取应用资源路径（兼容开发模式和打包模式）"""
        if getattr(sys, 'frozen', False):
            # 打包模式
            base_path = Path(sys.executable).parent
        else:
            # 开发模式
            base_path = Path(__file__).parent

        full_path = base_path / relative_path
        logging.debug(f"资源路径解析: {relative_path} → {full_path}")
        return full_path

    def _initialize(self):
        """初始化配置系统"""
        config_dir = self._get_app_path("config")
        config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            self._create_default_config()
        self._load_config()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_default_config(self):
        """创建默认配置"""
        self.config["Paths"] = {
            "input_dir": "./input",
            "output_dir": "./output",
            "overwrite": "false"
        }
        self.config["Region"] = {
            "x": "100",
            "y": "200",
            "width": "300",
            "height": "250"
        }
        self.config["Processing"] = {
            "blur_kernel": "55",
            "blur_sigma": "0",
            "remove_audio": "false"
        }
        self.config["Formats"] = {
            "supported": ".mp4, .avi, .mov, .mkv, .flv, .webm, .ts"
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            self.config.write(f)

    def _load_config(self):
        """加载并验证配置"""
        try:
            self.config.read(self.config_path, encoding="utf-8")
            return self.validate()
        except Exception as e:
            logging.error(f"配置文件加载失败: {str(e)}")
            sys.exit(1)

    @staticmethod
    def _clean_config_value(value: str, is_numeric: bool = False) -> str:
        """改进的配置值清理方法"""
        # 移除行内注释
        cleaned = value.split("#")[0].split(";")[0].strip()

        if is_numeric:
            # 仅对数值型参数过滤特殊字符
            return ''.join(filter(lambda x: x.isdigit() or x in ('-', '+'), cleaned))
        # 对字符串参数保留原始内容
        return cleaned

    def _safe_get_value(self, section: str, option: str,
                        expected_type: type, default: any) -> any:
        """类型安全的配置获取方法（改进版）"""
        try:
            raw_value = self.config.get(section, option)
            is_numeric = expected_type in (int, float)
            cleaned_value = self._clean_config_value(raw_value, is_numeric)

            if expected_type == bool:
                return cleaned_value.lower() in ("true", "yes", "1", "on")
            return expected_type(cleaned_value)
        except (configparser.Error, ValueError, TypeError) as e:
            logging.warning(f"配置项 {section}.{option} 无效，使用默认值 {default}。错误: {str(e)}")
            return default

    def validate(self) -> Dict:
        """配置验证与转换"""
        return {
            "paths": {
                "input": self._get_validated_path("Paths", "input_dir"),
                "output": self._get_validated_path("Paths", "output_dir", create=True),
                "overwrite": self._safe_get_value("Paths", "overwrite", bool, False)
            },
            "region": {
                "x": self._safe_get_value("Region", "x", int, 100),
                "y": self._safe_get_value("Region", "y", int, 200),
                "width": self._safe_get_value("Region", "width", int, 300),
                "height": self._safe_get_value("Region", "height", int, 250)
            },
            "processing": {
                "blur_kernel": self._validate_blur_kernel(),
                "blur_sigma": self._safe_get_value("Processing", "blur_sigma", int, 0),
                "remove_audio": self._safe_get_value("Processing", "remove_audio", bool, False)
            },
            "formats": [
                ext.strip().lower()
                for ext in self._safe_get_value("Formats", "supported", str, "").split(",")
                if ext.strip()
            ]
        }

    def _get_validated_path(self, section: str, option: str, create: bool = False) -> Path:
        path_str = self._safe_get_value(section, option, str, "")

        logging.debug(f"================ {section}.{option} ================")
        logging.debug(f"原始配置值: '{path_str}'")
        logging.debug(f"项目根目录: {self.base_dir}")

        # 处理空路径情况
        if not path_str.strip():
            default_path = self.base_dir / option  # 防止路径为空
            logging.warning(f"配置项 {section}.{option} 为空，使用默认路径: {default_path}")
            path = default_path
        else:
            path = (self.base_dir / path_str).resolve()

        logging.debug(f"最终解析路径: {path}")
        return path

    def _validate_blur_kernel(self) -> int:
        """验证模糊核参数有效性"""
        kernel = self._safe_get_value("Processing", "blur_kernel", int, 55)
        if kernel <= 0 or kernel % 2 == 0:
            raise ValueError(f"模糊核大小必须为正奇数，当前值: {kernel}")
        return kernel

    def _get_app_path(self, relative_path: str) -> Path:
        """动态获取应用资源路径（兼容开发模式和打包模式）"""
        if getattr(sys, 'frozen', False):
            # 打包模式
            base_path = Path(sys.executable).parent
        else:
            # 开发模式
            base_path = Path(__file__).parent

        full_path = base_path / relative_path
        logging.debug(f"资源路径解析: {relative_path} → {full_path}")
        return full_path


# ----------------------- FFmpeg 环境管理 ------------------------
class FFmpegManager:
    """跨平台FFmpeg环境管理器"""

    def __init__(self):
        self.system = platform.system()
        self.base_dir = self._get_base_dir()
        self._setup_paths()
        self._verify_executables()
        self._configure_environment()

    def _get_base_dir(self) -> Path:
        return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent

    def _setup_paths(self):
        """动态设置FFmpeg路径"""
        config = ConfigManager()
        self.bin_dir = config._get_app_path("ffmpeg")
        if self.system == "Darwin":
            platform_dir = "mac"
        else:
            platform_dir = "win"

        self.ffmpeg = self.bin_dir / platform_dir / ("ffmpeg" if self.system == "Darwin" else "ffmpeg.exe")
        self.ffprobe = self.bin_dir / platform_dir / ("ffprobe" if self.system == "Darwin" else "ffprobe.exe")

    def setup(self):
        """配置FFmpeg环境"""
        self._set_binary_paths()
        self._verify_executables()
        self._set_permissions()
        self._configure_environment()
        logging.info("FFmpeg环境初始化完成")

    def _set_binary_paths(self):
        """设置平台相关路径"""
        platform_dir = "mac" if self.system == "Darwin" else "win"
        self.ffmpeg = self.bin_dir / platform_dir / ("ffmpeg.exe" if self.system == "Windows" else "ffmpeg")
        self.ffprobe = self.bin_dir / platform_dir / ("ffprobe.exe" if self.system == "Windows" else "ffprobe")

    def _verify_executables(self):
        """验证二进制文件有效性"""
        for exe in [self.ffmpeg, self.ffprobe]:
            if not exe or not exe.exists():
                raise FileNotFoundError(f"关键文件缺失: {exe if exe else '未知文件'}")

    def _set_permissions(self):
        """设置执行权限（macOS/Linux）"""
        if self.system == "Darwin":
            try:
                self.ffmpeg.chmod(0o755)
                self.ffprobe.chmod(0o755)
                subprocess.run(["xattr", "-cr", str(self.ffmpeg)], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"权限设置失败: {e.stderr.decode()}")

    def _configure_environment(self):
        """配置运行时环境"""
        os.environ.update({
            "IMAGEIO_FFMPEG_EXE": str(self.ffmpeg),
            "FFMPEG_BINARY": str(self.ffmpeg),
            "FFPROBE_BINARY": str(self.ffprobe)
        })
        change_settings({"FFMPEG_BINARY": str(self.ffmpeg)})


# ---------------------- 视频处理核心模块 ------------------------
class VideoProcessor:
    """视频处理引擎"""

    def __init__(self, config: Dict):
        self.cfg = config
        self.system = platform.system()
        self._setup_paths()
        self.temp_dir = self.cfg["paths"]["output"] / "_video_temp"
        self._register_cleanup()

    def _register_cleanup(self):
        """注册退出清理函数"""

        @atexit.register
        def cleanup():
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logging.info("临时文件清理完成")

    def process_all(self):
        """批量处理主入口"""
        input_dir = self.cfg["paths"]["input"]
        logging.info(f"输入目录路径: {input_dir}")
        logging.info(f"目录存在: {input_dir.exists()}")
        logging.info(f"目录内容: {list(input_dir.glob('*'))}")
        if not input_dir.exists():
            logging.error(f"输入目录不存在: {input_dir}")
            return

        video_files = list(self._get_video_files())
        total = len(video_files)
        if total == 0:
            logging.info("没有找到可处理的视频文件")
            return

        success_count = 0
        for idx, video_file in enumerate(video_files, 1):
            try:
                logging.info(f"正在处理 ({idx}/{total}): {video_file.name}: {video_file}")
                self._process_single(video_file)
                success_count += 1
            except Exception as e:
                logging.error(f"处理失败 {video_file.name}: {str(e)}")

        logging.info(f"处理完成: 成功 {success_count}/{total} 个文件")

    def _get_video_files(self):
        """显示文件格式验证详情"""
        valid_files = []
        for p in self.cfg["paths"]["input"].iterdir():
            logging.debug(f"检查文件: {p.name} [后缀: {p.suffix}]")
            if p.suffix.lower() in self.cfg["formats"]:
                valid_files.append(p)
                logging.info(f"发现有效视频文件: {p.name}")
        return valid_files

    def _process_single(self, input_path: Path):
        """处理单个视频文件"""
        output_path = self.cfg["paths"]["output"] / input_path.name
        self._prepare_output(output_path)

        temp_video = self.temp_dir / input_path.name
        self.temp_dir.mkdir(exist_ok=True)

        try:
            self._process_video_stream(input_path, temp_video)
            self._handle_audio(input_path, temp_video, output_path)
        except Exception as e:
            self._cleanup_failed(output_path)
            raise
        finally:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _prepare_output(self, output_path: Path):
        """准备输出路径"""
        if output_path.exists():
            if self.cfg["paths"]["overwrite"]:
                output_path.unlink()
            else:
                raise FileExistsError(f"输出文件已存在: {output_path}")

    def _process_video_stream(self, input_path: Path, output_path: Path):
        """处理视频流"""
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")

        try:
            writer = self._create_video_writer(cap, output_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            for _ in range(frame_count):
                ret, frame = cap.read()
                if not ret:
                    break
                processed = self._apply_mosaic(frame)
                writer.write(processed)
        finally:
            cap.release()
            writer.release()

    def _create_video_writer(self, cap, output_path: Path):
        """创建视频写入器"""
        frame_size = (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )
        fps = cap.get(cv2.CAP_PROP_FPS)
        fourcc = self._get_video_codec(output_path.suffix)

        # 设置编码器参数
        if output_path.suffix.lower() == ".mp4":
            fourcc = cv2.VideoWriter_fourcc(*"avc1")  # 使用 H.264 编码器
            bitrate = int(cap.get(cv2.CAP_PROP_BITRATE))  # 获取原视频比特率
            if bitrate > 0:
                bitrate = max(bitrate // 2, 500000)  # 降低比特率以压缩文件大小
            else:
                bitrate = 1000000  # 默认比特率
        else:
            bitrate = -1  # 不设置比特率

        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            frame_size
        )

        # 设置比特率（仅对某些编码器有效）
        if bitrate > 0:
            writer.set(cv2.CAP_PROP_BITRATE, bitrate)

        return writer

    def _apply_mosaic(self, frame):
        """应用马赛克效果"""
        x, y = self.cfg["region"]["x"], self.cfg["region"]["y"]
        w, h = self.cfg["region"]["width"], self.cfg["region"]["height"]

        # 边界检查
        height, width = frame.shape[:2]
        if x + w > width or y + h > height:
            raise ValueError(f"马赛克区域超出视频尺寸 ({width}x{height})")

        region = frame[y:y + h, x:x + w]
        blurred = cv2.GaussianBlur(
            region,
            (self.cfg["processing"]["blur_kernel"], self.cfg["processing"]["blur_kernel"]),
            self.cfg["processing"]["blur_sigma"]
        )
        frame[y:y + h, x:x + w] = blurred

        # 降低马赛克区域的分辨率（可选）
        mosaic_size = (w // 4, h // 4)  # 缩小到 1/4
        resized = cv2.resize(region, mosaic_size, interpolation=cv2.INTER_LINEAR)
        frame[y:y + h, x:x + w] = cv2.resize(resized, (w, h), interpolation=cv2.INTER_NEAREST)

        return frame

    def _get_video_codec(self, extension: str) -> int:
        """获取视频编码器"""
        codec_map = {
            ".mp4": cv2.VideoWriter_fourcc(*"avc1"),  # H.264
            ".avi": cv2.VideoWriter_fourcc(*"XVID"),  # XviD
            ".mov": cv2.VideoWriter_fourcc(*"mp4v"),  # MPEG-4
            ".mkv": cv2.VideoWriter_fourcc(*"X264"),  # H.264 for MKV
            ".flv": cv2.VideoWriter_fourcc(*"FLV1"),  # Flash Video
            ".webm": cv2.VideoWriter_fourcc(*"VP80"),  # VP8
            ".ts": cv2.VideoWriter_fourcc(*"H264")  # MPEG-TS
        }
        return codec_map.get(extension.lower(), cv2.VideoWriter_fourcc(*"mp4v"))

    def _setup_paths(self):
        """动态设置FFmpeg路径"""
        config = ConfigManager()
        self.bin_dir = config._get_app_path("ffmpeg")
        if self.system == "Darwin":
            platform_dir = "mac"
        else:
            platform_dir = "win"

        self.ffmpeg = self.bin_dir / platform_dir / ("ffmpeg" if self.system == "Darwin" else "ffmpeg.exe")
        self.ffprobe = self.bin_dir / platform_dir / ("ffprobe" if self.system == "Darwin" else "ffprobe.exe")

    def _handle_audio(self, original: Path, video_temp: Path, output: Path):
        """处理音频流"""
        if self.cfg["processing"]["remove_audio"]:
            shutil.move(video_temp, output)
            return

        temp_audio = self.temp_dir / "audio_temp.m4a"

        try:
            logging.info(f"ffmpeg path: {self.ffmpeg}")

            # 提取音频并压缩（设置音频比特率为 128k）
            subprocess.run([
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(original),
                "-vn", "-acodec", "aac", "-b:a", "128k", str(temp_audio)
            ], check=True)

            # 合并音视频
            subprocess.run([
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_temp),
                "-i", str(temp_audio),
                "-c:v", "libx264", "-crf", "23", "-preset", "medium",  # 使用 H.264 编码器，CRF=23
                "-c:a", "aac", "-b:a", "128k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                str(output)
            ], check=True)
        except Exception as e:
            logging.error(f"处理失败：{str(e)}")
        finally:
            if temp_audio.exists():
                temp_audio.unlink()

    def _cleanup_failed(self, output_path: Path):
        """清理失败产生的文件"""
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError as e:
                logging.error(f"清理失败文件 {output_path} 时出错: {str(e)}")


# ------------------------- 主程序入口 --------------------------
def main():
    try:
        FFmpegManager()
        config = ConfigManager().validate()
        processor = VideoProcessor(config)
        processor.process_all()

        logging.info("✅ 视频处理完成！")
        if platform.system() == "Darwin":
            subprocess.run([
                "osascript", "-e",
                'display notification "所有视频处理完成" with title "视频马赛克工具"'
            ])
    except Exception as e:
        logging.error(f"❌ 程序运行失败: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if platform.system() == "Windows":
            # input("按回车键退出...")
            time.sleep(1)
            pass


if __name__ == "__main__":
    main()
