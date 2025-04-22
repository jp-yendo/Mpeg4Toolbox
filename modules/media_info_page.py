import os
import ffmpeg
from PyQt5.QtWidgets import (QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QTextEdit, QFileDialog,
                            QMessageBox, QWizard)
from .utils import format_duration, format_bitrate

class MediaInfoPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("メディア情報")
        self.setSubTitle("MPEG4ファイルの詳細情報を表示します")

        layout = QVBoxLayout()

        # ファイル選択部分
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.browse_button = QPushButton("ファイルを選択...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel("ファイル:"))
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(self.browse_button)

        # 情報表示部分
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)

        layout.addLayout(file_layout)
        layout.addWidget(self.info_text)

        self.setLayout(layout)

        # 必須フィールドとして設定
        self.registerField("media_file*", self.file_edit)

    def initializePage(self):
        """ページの初期化"""
        # ファイル選択をクリア
        self.file_edit.clear()
        self.info_text.clear()

    def validatePage(self):
        # ファイルが選択されていない場合はエラー
        if not self.file_edit.text():
            QMessageBox.warning(self, "警告", "ファイルを選択してください。")
            return False
        return True

    def nextId(self):
        # 最後のページなので-1を返す
        return -1

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "メディアファイルの選択", "",
            "メディアファイル (*.mp4 *.m4v *.mkv);;すべてのファイル (*.*)")
        if file_path:
            self.file_edit.setText(file_path)
            self.show_media_info(file_path)

    def show_media_info(self, file_path):
        try:
            # FFmpegのパスを設定
            config = self.wizard().config
            if config.has_option("Settings", "ffmpeg_path"):
                ffmpeg_dir = os.path.dirname(config.get("Settings", "ffmpeg_path"))
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

            # メディア情報を取得
            probe = ffmpeg.probe(file_path)

            # 情報を整形して表示
            info_text = "【ファイル情報】\n"
            format_info = probe['format']
            info_text += f"コンテナフォーマット: {format_info['format_name']}\n"
            info_text += f"フォーマット詳細: {format_info['format_long_name']}\n"
            info_text += f"時間: {format_duration(float(format_info['duration']))}\n"
            info_text += f"サイズ: {int(format_info['size']) / (1024*1024):.2f} MB\n"
            if 'bit_rate' in format_info:
                info_text += f"総ビットレート: {format_bitrate(float(format_info['bit_rate']))}\n"

            # メタデータ情報
            if 'tags' in format_info:
                info_text += "\n【メタデータ】\n"
                for key, value in format_info['tags'].items():
                    info_text += f"{key}: {value}\n"

            # ストリーム情報
            for stream in probe['streams']:
                stream_type = stream['codec_type'].upper()
                info_text += f"\n【{stream_type}ストリーム #{stream['index']}】\n"
                info_text += f"コーデック: {stream['codec_name']} ({stream['codec_long_name']})\n"
                info_text += f"コーデックタグ: {stream.get('codec_tag_string', 'N/A')} ({stream.get('codec_tag', 'N/A')})\n"

                if stream_type == 'VIDEO':
                    info_text += f"解像度: {stream['width']}x{stream['height']}\n"
                    if 'display_aspect_ratio' in stream:
                        info_text += f"アスペクト比: {stream['display_aspect_ratio']}\n"
                    if 'r_frame_rate' in stream:
                        num, den = map(int, stream['r_frame_rate'].split('/'))
                        fps = num / den
                        info_text += f"フレームレート: {fps:.3f} fps\n"
                    if 'avg_frame_rate' in stream:
                        num, den = map(int, stream['avg_frame_rate'].split('/'))
                        fps = num / den if den != 0 else 0
                        info_text += f"平均フレームレート: {fps:.3f} fps\n"
                    if 'bit_rate' in stream:
                        info_text += f"ビットレート: {format_bitrate(float(stream['bit_rate']))}\n"
                    info_text += f"ピクセルフォーマット: {stream.get('pix_fmt', 'N/A')}\n"
                    if 'profile' in stream:
                        info_text += f"プロファイル: {stream['profile']}\n"
                    if 'level' in stream:
                        info_text += f"レベル: {stream['level']}\n"
                    if 'color_space' in stream:
                        info_text += f"カラースペース: {stream['color_space']}\n"
                    if 'color_transfer' in stream:
                        info_text += f"色変換: {stream['color_transfer']}\n"
                    if 'color_primaries' in stream:
                        info_text += f"色域: {stream['color_primaries']}\n"

                elif stream_type == 'AUDIO':
                    if 'bit_rate' in stream:
                        info_text += f"ビットレート: {format_bitrate(float(stream['bit_rate']))}\n"
                    info_text += f"サンプルレート: {stream['sample_rate']} Hz\n"
                    info_text += f"チャンネル: {stream['channels']}\n"
                    if 'channel_layout' in stream:
                        info_text += f"チャンネルレイアウト: {stream['channel_layout']}\n"
                    if 'sample_fmt' in stream:
                        info_text += f"サンプルフォーマット: {stream['sample_fmt']}\n"
                    if 'profile' in stream:
                        info_text += f"プロファイル: {stream['profile']}\n"

                elif stream_type == 'SUBTITLE':
                    if 'width' in stream and 'height' in stream:
                        info_text += f"解像度: {stream['width']}x{stream['height']}\n"

                # ストリームのメタデータ
                if 'tags' in stream:
                    info_text += "メタデータ:\n"
                    for key, value in stream['tags'].items():
                        info_text += f"  {key}: {value}\n"

                # ディスポジション情報
                if 'disposition' in stream:
                    dispositions = [k for k, v in stream['disposition'].items() if v == 1]
                    if dispositions:
                        info_text += f"ディスポジション: {', '.join(dispositions)}\n"

            self.info_text.setText(info_text)

        except ffmpeg.Error as e:
            QMessageBox.critical(self, "エラー",
                               f"メディア情報の取得に失敗しました:\n{str(e)}")
            self.info_text.clear()
        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"予期せぬエラーが発生しました:\n{str(e)}")
            self.info_text.clear()
