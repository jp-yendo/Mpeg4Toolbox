from PyQt5.QtWidgets import (QWizardPage, QVBoxLayout, QRadioButton,
                            QButtonGroup, QMessageBox, QLineEdit)

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
            ("subtitle", "字幕・タグ管理"),
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

        # 選択されたタスクを追跡するための隠しフィールド
        self.selected_task = QLineEdit()
        self.selected_task.hide()
        layout.addWidget(self.selected_task)

        self.setLayout(layout)

        # ボタングループの選択変更時にフィールドを更新
        self.button_group.buttonClicked.connect(self.update_selected_task)

        # 初期値を設定
        self.update_selected_task(self.task_buttons[0])

        # 必須フィールドとして設定（初期値設定後に行う）
        self.registerField("selected_task*", self.selected_task)

    def isComplete(self):
        """ページが完了状態かどうかを判断"""
        # いずれかのラジオボタンが選択されていればTrue
        return self.button_group.checkedButton() is not None

    def initializePage(self):
        """ページの初期化"""
        # ラジオボタンの状態を更新
        current_task = self.selected_task.text()
        for i, (task_id, _) in enumerate(self.tasks):
            if task_id == current_task:
                self.task_buttons[i].setChecked(True)
                break

    def update_selected_task(self, button):
        index = self.button_group.id(button)
        if 0 <= index < len(self.tasks):
            task_id = self.tasks[index][0]
            self.selected_task.setText(task_id)
            # 値が変更されたことを通知
            self.completeChanged.emit()

    def validatePage(self):
        """ページの検証"""
        current_task = self.selected_task.text()
        wizard = self.wizard()

        # FFmpegの設定が必要なタスクの場合
        if current_task in ["info", "subtitle"]:
            if not wizard.config.has_option("Settings", "ffmpeg_path"):
                QMessageBox.warning(self, "警告", "先にFFmpegの設定を行ってください。")
                return False

        return True

    def nextId(self):
        """次のページのIDを決定する"""
        current_task = self.selected_task.text()
        wizard = self.wizard()

        if current_task == "info":
            if not wizard.config.has_option("Settings", "ffmpeg_path"):
                return wizard.ffmpeg_settings_page_id
            return wizard.media_info_page_id
        elif current_task == "subtitle":
            if not wizard.config.has_option("Settings", "ffmpeg_path"):
                return wizard.ffmpeg_settings_page_id
            return wizard.subtitle_management_page_id
        elif current_task == "settings":
            return wizard.ffmpeg_settings_page_id

        return -1
