import sys
import os
import configparser
import json
import ffmpeg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWizard, QWizardPage,
                            QLabel, QVBoxLayout, QRadioButton, QButtonGroup,
                            QFileDialog, QMessageBox, QLineEdit, QPushButton,
                            QTextEdit, QScrollArea, QWidget, QHBoxLayout)
from PyQt5.QtCore import Qt

class FFmpegSettingsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("FFmpeg設定")
        self.setSubTitle("FFmpegの実行ファイルのパスを設定してください")

        layout = QVBoxLayout()

        self.path_edit = QLineEdit()
        self.browse_button = QPushButton("参照...")
        self.browse_button.clicked.connect(self.browse_ffmpeg)

        layout.addWidget(QLabel("FFmpegのパス:"))
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_button)

        self.setLayout(layout)

        # 必須フィールドとして設定
        self.registerField("ffmpeg_path*", self.path_edit)

    def initializePage(self):
        # 設定ファイルからパスを読み込む
        config = self.wizard().config
        if config.has_option("Settings", "ffmpeg_path"):
            self.path_edit.setText(config.get("Settings", "ffmpeg_path"))

        # 設定ページ用のボタンレイアウト
        wizard = self.wizard()
        wizard.setButtonLayout([
            QWizard.BackButton,
            QWizard.Stretch,
            QWizard.FinishButton,
            QWizard.CancelButton
        ])

    def validatePage(self):
        """ページの検証と遷移制御"""
        # 設定を保存
        ffmpeg_path = self.path_edit.text()
        wizard = self.wizard()
        wizard.config.set("Settings", "ffmpeg_path", ffmpeg_path)
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

    def browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "FFmpegの選択", "",
            "実行ファイル (ffmpeg.exe);;すべてのファイル (*.*)")
        if file_path:
            self.path_edit.setText(file_path)

class TaskSelectionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("タスク選択")
        self.setSubTitle("実行したいタスクを選択してください")

        layout = QVBoxLayout()
        self.button_group = QButtonGroup()

        # タスクの選択肢
        self.tasks = [
            ("info", "詳細情報表示"),
            ("subtitle", "字幕管理"),
            ("settings", "FFmpeg設定")
        ]

        self.task_buttons = []
        for i, (task_id, task_name) in enumerate(self.tasks):
            radio = QRadioButton(task_name)
            self.button_group.addButton(radio, i)
            layout.addWidget(radio)
            self.task_buttons.append(radio)
            if i == 0:  # 最初のオプションをデフォルトで選択
                radio.setChecked(True)

        self.setLayout(layout)

        # 選択されたタスクを追跡するための隠しフィールド
        self.selected_task = QLineEdit()
        self.selected_task.hide()
        layout.addWidget(self.selected_task)
        self.registerField("selected_task*", self.selected_task)

        # ボタングループの選択変更時にフィールドを更新
        self.button_group.buttonClicked.connect(self.update_selected_task)

        # 初期値を設定
        self.update_selected_task(self.task_buttons[0])

    def initializePage(self):
        """ページの初期化"""
        # 最初のページ用のボタンレイアウト
        wizard = self.wizard()
        wizard.setButtonLayout([
            QWizard.Stretch,
            QWizard.NextButton,
            QWizard.CancelButton
        ])

        # ラジオボタンの状態を更新
        current_task = self.selected_task.text()
        for i, (task_id, _) in enumerate(self.tasks):
            if task_id == current_task:
                self.task_buttons[i].setChecked(True)
                break

    def update_selected_task(self, button):
        index = self.button_group.id(button)
        if 0 <= index < len(self.tasks):
            self.selected_task.setText(self.tasks[index][0])

    def validatePage(self):
        """ページの検証"""
        current_task = self.selected_task.text()

        # 字幕管理が選択された場合（未実装）
        if current_task == "subtitle":
            QMessageBox.warning(self, "警告", "この機能は現在実装中です。")
            return False

        # FFmpegの設定が必要なタスクの場合
        if current_task in ["info", "subtitle"]:
            wizard = self.wizard()
            if not wizard.config.has_option("Settings", "ffmpeg_path"):
                QMessageBox.warning(self, "警告", "先にFFmpegの設定を行ってください。")
                return False

        return True

    def nextId(self):
        """次のページのIDを決定する"""
        current_task = self.selected_task.text()
        wizard = self.wizard()

        # FFmpegの設定が必要なタスクの場合
        if current_task in ["info", "subtitle"]:
            if not wizard.config.has_option("Settings", "ffmpeg_path"):
                return wizard.ffmpeg_settings_page_id
            elif current_task == "info":
                return wizard.media_info_page_id
        elif current_task == "settings":
            return wizard.ffmpeg_settings_page_id

        return -1

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
            "メディアファイル (*.mp4 *.m4v);;すべてのファイル (*.*)")
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
            info_text += f"フォーマット: {probe['format']['format_name']}\n"
            info_text += f"時間: {float(probe['format']['duration']):.2f}秒\n"
            info_text += f"サイズ: {int(probe['format']['size']) / 1024 / 1024:.2f}MB\n\n"

            # ストリーム情報
            for stream in probe['streams']:
                stream_type = stream['codec_type'].upper()
                info_text += f"【{stream_type}ストリーム】\n"
                info_text += f"コーデック: {stream['codec_name']}\n"

                if stream_type == 'VIDEO':
                    info_text += f"解像度: {stream['width']}x{stream['height']}\n"
                    if 'bit_rate' in stream:
                        info_text += f"ビットレート: {int(stream['bit_rate']) / 1000:.0f}kbps\n"
                    if 'r_frame_rate' in stream:
                        num, den = map(int, stream['r_frame_rate'].split('/'))
                        fps = num / den
                        info_text += f"フレームレート: {fps:.2f}fps\n"

                elif stream_type == 'AUDIO':
                    if 'bit_rate' in stream:
                        info_text += f"ビットレート: {int(stream['bit_rate']) / 1000:.0f}kbps\n"
                    info_text += f"サンプルレート: {stream['sample_rate']}Hz\n"
                    info_text += f"チャンネル: {stream['channels']}\n"

                elif stream_type == 'SUBTITLE':
                    if 'tags' in stream:
                        if 'language' in stream['tags']:
                            info_text += f"言語: {stream['tags']['language']}\n"
                        if 'title' in stream['tags']:
                            info_text += f"タイトル: {stream['tags']['title']}\n"
                        if 'handler_name' in stream['tags']:
                            info_text += f"ハンドラ: {stream['tags']['handler_name']}\n"

                info_text += "\n"

            self.info_text.setText(info_text)

        except ffmpeg.Error as e:
            QMessageBox.critical(self, "エラー",
                               f"メディア情報の取得に失敗しました:\n{str(e)}")
            self.info_text.clear()
        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"予期せぬエラーが発生しました:\n{str(e)}")
            self.info_text.clear()

class Mpeg4Wizard(QWizard):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MPEG4 ツールボックス")
        self.setWizardStyle(QWizard.ModernStyle)

        # ボタンのテキストを変更
        self.setButtonText(QWizard.CancelButton, "閉じる")
        self.setButtonText(QWizard.FinishButton, "完了")

        # 設定ファイルの読み込み
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(os.path.dirname(__file__), "mpeg4toolbox.ini")
        self.load_config()

        # ページの追加
        self.task_selection_page = TaskSelectionPage()
        self.ffmpeg_settings_page = FFmpegSettingsPage()
        self.media_info_page = MediaInfoPage()

        # ページIDを保存
        self.task_selection_page_id = self.addPage(self.task_selection_page)
        self.ffmpeg_settings_page_id = self.addPage(self.ffmpeg_settings_page)
        self.media_info_page_id = self.addPage(self.media_info_page)

        # サイズの設定
        self.resize(800, 600)

        # 完了とキャンセルの処理を設定
        self.finished.connect(self.on_finished)
        self.rejected.connect(self.on_rejected)

        # 最初のページを設定
        self.setStartId(self.task_selection_page_id)

    def load_config(self):
        """設定ファイルを読み込む"""
        self.config.read(self.config_path)
        if not self.config.has_section("Settings"):
            self.config.add_section("Settings")

    def save_config(self):
        """設定ファイルを保存する"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            self.config.write(f)

    def on_finished(self, result):
        """ウィザードが完了したときの処理"""
        if result == QWizard.Accepted:
            # 設定を保存
            self.save_config()
            # 最初のページに戻る
            self.restart()
            self.show()

    def on_rejected(self):
        """キャンセル（閉じる）ボタンが押されたときの処理"""
        # プログラムを終了
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    wizard = Mpeg4Wizard()
    wizard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
