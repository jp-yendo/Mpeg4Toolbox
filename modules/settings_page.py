import os
from PyQt5.QtWidgets import (QWizardPage, QLabel, QVBoxLayout, QPushButton,
                            QLineEdit, QFileDialog, QMessageBox, QGroupBox)
from .utils import get_default_temp_dir

class MediaToolSettingsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("メディアツール設定")
        self.setSubTitle("MP4BoxとFFmpegの実行ファイル、および作業ディレクトリのパスを設定してください")

        layout = QVBoxLayout()

        # MP4Boxパス設定
        mp4box_group = QGroupBox("MP4Box実行ファイル")
        mp4box_layout = QVBoxLayout()
        self.mp4box_path_edit = QLineEdit()
        self.mp4box_browse_button = QPushButton("参照...")
        self.mp4box_browse_button.clicked.connect(self.browse_mp4box)
        mp4box_layout.addWidget(QLabel("MP4Boxのパス:"))
        mp4box_layout.addWidget(self.mp4box_path_edit)
        mp4box_layout.addWidget(self.mp4box_browse_button)
        mp4box_group.setLayout(mp4box_layout)
        layout.addWidget(mp4box_group)

        # FFmpegパス設定
        ffmpeg_group = QGroupBox("FFmpeg実行ファイル")
        ffmpeg_layout = QVBoxLayout()
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_browse_button = QPushButton("参照...")
        self.ffmpeg_browse_button.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(QLabel("FFmpegのパス:"))
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_browse_button)
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)

        # 一時ディレクトリ設定
        temp_group = QGroupBox("作業ディレクトリ")
        temp_layout = QVBoxLayout()
        self.temp_edit = QLineEdit()
        self.temp_browse_button = QPushButton("参照...")
        self.temp_browse_button.clicked.connect(self.browse_temp_dir)
        temp_layout.addWidget(QLabel("一時ファイル出力先:"))
        temp_layout.addWidget(self.temp_edit)
        temp_layout.addWidget(self.temp_browse_button)
        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        self.setLayout(layout)

        # 必須フィールドとして設定
        self.registerField("mp4box_path*", self.mp4box_path_edit)
        self.registerField("ffmpeg_path*", self.ffmpeg_path_edit)
        self.registerField("temp_dir*", self.temp_edit)

    def initializePage(self):
        # 設定ファイルからパスを読み込む
        config = self.wizard().config
        if config.has_option("Settings", "mp4box_path"):
            self.mp4box_path_edit.setText(config.get("Settings", "mp4box_path"))
        if config.has_option("Settings", "ffmpeg_path"):
            self.ffmpeg_path_edit.setText(config.get("Settings", "ffmpeg_path"))
        if config.has_option("Settings", "temp_dir"):
            self.temp_edit.setText(config.get("Settings", "temp_dir"))
        else:
            # デフォルトの一時ディレクトリを設定
            default_temp = get_default_temp_dir()
            self.temp_edit.setText(default_temp)

    def validatePage(self):
        """ページの検証と遷移制御"""
        # 設定を保存
        mp4box_path = self.mp4box_path_edit.text()
        ffmpeg_path = self.ffmpeg_path_edit.text()
        temp_dir = self.temp_edit.text()
        wizard = self.wizard()

        # 一時ディレクトリが存在しない場合は作成
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"一時ディレクトリの作成に失敗しました:\n{str(e)}")
            return False

        # 設定を保存
        wizard.config.set("Settings", "mp4box_path", mp4box_path)
        wizard.config.set("Settings", "ffmpeg_path", ffmpeg_path)
        wizard.config.set("Settings", "temp_dir", temp_dir)
        wizard.save_config()
        return True

    def nextId(self):
        """次のページのIDを決定する"""
        # タスク選択ページからの遷移かどうかを確認
        wizard = self.wizard()
        previous_id = wizard.visitedPages()[-2] if len(wizard.visitedPages()) > 1 else -1

        if previous_id == wizard.task_selection_page_id:
            current_task = wizard.task_selection_page.selected_task.text()
            if current_task == "info":
                return wizard.media_info_page_id

        return -1

    def browse_mp4box(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "MP4Boxの選択", "",
            "実行ファイル (MP4Box.exe);;すべてのファイル (*.*)")
        if file_path:
            self.mp4box_path_edit.setText(file_path)

    def browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "FFmpegの選択", "",
            "実行ファイル (ffmpeg.exe);;すべてのファイル (*.*)")
        if file_path:
            self.ffmpeg_path_edit.setText(file_path)

    def browse_temp_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "作業ディレクトリの選択",
            self.temp_edit.text() or get_default_temp_dir())
        if dir_path:
            self.temp_edit.setText(dir_path)
