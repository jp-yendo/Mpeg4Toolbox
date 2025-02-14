import sys
import os
import configparser
from PyQt5.QtWidgets import QApplication, QWizard
from modules import (MediaToolSettingsPage, TaskSelectionPage, MediaInfoPage,
                    MediaTagManagementPage)

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
        self.media_tool_settings_page = MediaToolSettingsPage()
        self.media_info_page = MediaInfoPage()
        self.subtitle_management_page = MediaTagManagementPage()

        # ページIDを保存
        self.task_selection_page_id = self.addPage(self.task_selection_page)
        self.media_tool_settings_page_id = self.addPage(self.media_tool_settings_page)
        self.media_info_page_id = self.addPage(self.media_info_page)
        self.subtitle_management_page_id = self.addPage(self.subtitle_management_page)

        # サイズの設定
        self.resize(800, 600)

        # 完了とキャンセルの処理を設定
        self.finished.connect(self.on_finished)
        self.rejected.connect(self.on_rejected)

        # ページ遷移時の処理を設定
        self.currentIdChanged.connect(self.on_page_changed)

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
            # 現在のページを取得
            current_page = self.currentPage()
            # 処理が成功した場合のみ最初のページに戻る
            if isinstance(current_page, MediaTagManagementPage):
                # 字幕・タグ管理ページの場合は、validatePageの結果に基づいて処理
                if not current_page.validatePage():
                    # 処理が失敗した場合は現在のページにとどまる
                    self.show()
                    return
            # 処理が成功した場合は最初のページに戻る
            self.restart()
            self.show()

    def on_rejected(self):
        """キャンセル（閉じる）ボタンが押されたときの処理"""
        # プログラムを終了
        QApplication.quit()

    def on_page_changed(self, page_id):
        """ページが変更されたときの処理"""
        current_page = self.currentPage()
        if current_page == self.task_selection_page:
            self.setButtonLayout([
                QWizard.Stretch,
                QWizard.NextButton,
                QWizard.CancelButton
            ])
        elif current_page == self.media_tool_settings_page:
            self.setButtonLayout([
                QWizard.BackButton,
                QWizard.Stretch,
                QWizard.FinishButton,
                QWizard.CancelButton
            ])
        elif current_page == self.media_info_page:
            self.setButtonLayout([
                QWizard.BackButton,
                QWizard.Stretch,
                QWizard.FinishButton,
                QWizard.CancelButton
            ])
        elif current_page == self.subtitle_management_page:
            self.setButtonLayout([
                QWizard.BackButton,
                QWizard.Stretch,
                QWizard.FinishButton,
                QWizard.CancelButton
            ])

def main():
    app = QApplication(sys.argv)
    wizard = Mpeg4Wizard()
    wizard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
