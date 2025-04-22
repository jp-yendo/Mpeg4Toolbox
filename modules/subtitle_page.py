import os
import uuid
import ffmpeg
import subprocess
from PyQt5.QtWidgets import (QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QComboBox, QFileDialog,
                            QMessageBox, QGroupBox, QScrollArea, QWidget,
                            QCheckBox, QWizard, QApplication)
from PyQt5.QtCore import Qt
from .constants import LANGUAGES
from .utils import get_default_temp_dir

class MediaTagManagementPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("字幕・タグ管理")
        self.setSubTitle("メディアファイルの言語設定とメタデータを管理します")
        self.subtitle_groups = []

        # メインレイアウト
        main_layout = QVBoxLayout()

        # ファイル選択部分
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.browse_button = QPushButton("ファイルを選択...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel("入力ファイル:"))
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(self.browse_button)
        main_layout.addLayout(file_layout)

        # 出力ファイル選択部分
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_browse_button = QPushButton("出力先を選択...")
        self.output_browse_button.clicked.connect(self.browse_output)
        output_layout.addWidget(QLabel("出力ファイル:"))
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.output_browse_button)
        main_layout.addLayout(output_layout)

        # 映像言語設定
        video_group = QGroupBox("映像設定")
        video_layout = QVBoxLayout()
        # 映像情報表示
        video_info = QLabel()
        video_info.setStyleSheet("QLabel { color: gray; }")
        video_layout.addWidget(video_info)
        # 言語設定
        video_lang_layout = QHBoxLayout()
        video_lang_layout.addWidget(QLabel("言語:"))
        self.video_lang_label = QLabel("")  # 検出された言語コードを表示するラベル
        video_lang_layout.addWidget(self.video_lang_label)
        self.video_lang_combo = QComboBox()
        for code, name in LANGUAGES:
            self.video_lang_combo.addItem(f"{name} ({code})", code)
        video_lang_layout.addWidget(self.video_lang_combo)
        video_lang_layout.addStretch()
        video_layout.addLayout(video_lang_layout)
        video_group.setLayout(video_layout)
        main_layout.addWidget(video_group)

        # オーディオ設定
        audio_group = QGroupBox("オーディオ設定")
        audio_layout = QVBoxLayout()
        self.audio_settings = []  # オーディオ設定を保持
        audio_group.setLayout(audio_layout)
        main_layout.addWidget(audio_group)

        # 字幕追加ボタン
        add_button = QPushButton("字幕を追加")
        add_button.clicked.connect(self.add_subtitle_group)
        main_layout.addWidget(add_button)

        # スクロール可能な字幕グループコンテナ
        scroll = QScrollArea()
        self.subtitle_container = QWidget()
        self.subtitle_layout = QVBoxLayout(self.subtitle_container)
        scroll.setWidget(self.subtitle_container)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

        # 必須フィールドとして設定
        self.registerField("input_file*", self.file_edit)
        self.registerField("output_file*", self.output_edit)

        # レイアウトを保持
        self.audio_layout = audio_layout

    def initializePage(self):
        """ページの初期化"""
        # ファイル選択をクリア
        self.file_edit.clear()
        self.output_edit.clear()

        # 映像言語をデフォルトに設定
        self.video_lang_combo.setCurrentIndex(0)
        self.video_lang_label.setText("検出: 未設定")
        # 映像情報をクリア
        for widget in self.findChildren(QLabel):
            if widget.parent() and isinstance(widget.parent(), QGroupBox) and widget.parent().title() == "映像設定":
                widget.setText("")
                break

        # オーディオ設定をクリア
        for setting in self.audio_settings:
            for widget in setting.values():
                if isinstance(widget, QWidget):
                    widget.deleteLater()
        self.audio_settings.clear()

        # 字幕グループをクリア
        for group in self.subtitle_groups:
            group['group'].deleteLater()
        self.subtitle_groups.clear()

        # 完了ボタンのテキストを「出力」に変更
        self.wizard().setButtonText(QWizard.FinishButton, "出力")

    def update_audio_settings(self, probe_data):
        """オーディオ設定を更新"""
        # 既存の設定をクリア
        for setting in self.audio_settings:
            for widget in setting.values():
                if isinstance(widget, QWidget):
                    widget.deleteLater()
        self.audio_settings.clear()

        # オーディオストリームごとに設定を追加
        audio_index = 0
        for i, stream in enumerate(probe_data['streams']):
            if stream['codec_type'] == 'audio':
                group = QGroupBox(f"オーディオ #{audio_index}")
                layout = QVBoxLayout()

                # オーディオ情報表示
                info_text = []
                if 'codec_name' in stream:
                    info_text.append(f"コーデック: {stream['codec_name']}")
                if 'channels' in stream:
                    info_text.append(f"チャンネル: {stream['channels']}ch")
                if 'sample_rate' in stream:
                    info_text.append(f"サンプルレート: {stream['sample_rate']}Hz")
                if 'bit_rate' in stream:
                    bit_rate = int(stream['bit_rate'])
                    info_text.append(f"ビットレート: {bit_rate//1000}kbps")

                info_label = QLabel(" | ".join(info_text))
                info_label.setStyleSheet("QLabel { color: gray; }")
                layout.addWidget(info_label)

                # 言語設定
                lang_layout = QHBoxLayout()
                lang_layout.addWidget(QLabel("言語:"))
                detected_lang = "未設定"
                lang_combo = QComboBox()
                for code, name in LANGUAGES:
                    lang_combo.addItem(f"{name} ({code})", code)
                if 'tags' in stream and 'language' in stream['tags']:
                    current_lang = stream['tags']['language']
                    detected_lang = current_lang
                    index = lang_combo.findData(current_lang)
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                    else:
                        # 言語コードが見つからない場合は'und'を設定
                        index = lang_combo.findData('und')
                        if index >= 0:
                            lang_combo.setCurrentIndex(index)
                else:
                    # 言語タグがない場合は'und'を設定
                    index = lang_combo.findData('und')
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                lang_label = QLabel(f"検出: {detected_lang}")
                lang_layout.addWidget(lang_label)
                lang_layout.addWidget(lang_combo)
                lang_layout.addStretch()
                layout.addLayout(lang_layout)

                # デフォルトフラグ
                default_check = QCheckBox("デフォルトオーディオ")
                if 'disposition' in stream and stream['disposition'].get('default', 0) == 1:
                    default_check.setChecked(True)
                layout.addWidget(default_check)

                group.setLayout(layout)
                self.audio_layout.addWidget(group)
                self.audio_settings.append({
                    'group': group,
                    'language': lang_combo,
                    'default': default_check,
                    'stream_index': i,
                    'audio_index': audio_index
                })
                audio_index += 1

    def update_existing_subtitles(self, probe_data):
        """既存の字幕ストリームを字幕グループとして追加"""
        subtitle_index = 0
        for i, stream in enumerate(probe_data['streams']):
            if stream['codec_type'] == 'subtitle':
                group = QGroupBox(f"字幕 #{len(self.subtitle_groups) + 1}")
                layout = QVBoxLayout()

                # 字幕情報表示（エクスポートボタンを含む）
                info_layout = QHBoxLayout()
                info_text = []
                if 'codec_name' in stream:
                    info_text.append(f"コーデック: {stream['codec_name']}")
                if 'disposition' in stream:
                    dispositions = []
                    if stream['disposition'].get('default', 0) == 1:
                        dispositions.append("デフォルト")
                    if stream['disposition'].get('forced', 0) == 1:
                        dispositions.append("強制")
                    if dispositions:
                        info_text.append(f"設定: {', '.join(dispositions)}")

                info_label = QLabel(" | ".join(info_text))
                info_label.setStyleSheet("QLabel { color: gray; }")
                info_layout.addWidget(info_label)
                info_layout.addStretch()

                # エクスポートボタン
                export_button = QPushButton("エクスポート")
                export_button.clicked.connect(lambda checked, s=stream: self.export_subtitle(s))
                info_layout.addWidget(export_button)
                layout.addLayout(info_layout)

                # 言語選択
                lang_layout = QHBoxLayout()
                lang_layout.addWidget(QLabel("言語:"))
                detected_lang = "未設定"
                lang_combo = QComboBox()
                for code, name in LANGUAGES:
                    lang_combo.addItem(f"{name} ({code})", code)
                if 'tags' in stream and 'language' in stream['tags']:
                    current_lang = stream['tags']['language']
                    detected_lang = current_lang
                    index = lang_combo.findData(current_lang)
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                    else:
                        # 言語コードが見つからない場合は'und'を設定
                        index = lang_combo.findData('und')
                        if index >= 0:
                            lang_combo.setCurrentIndex(index)
                else:
                    # 言語タグがない場合は'und'を設定
                    index = lang_combo.findData('und')
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                lang_label = QLabel(f"検出: {detected_lang}")
                lang_layout.addWidget(lang_label)
                lang_layout.addWidget(lang_combo)
                lang_layout.addStretch()
                layout.addLayout(lang_layout)

                # 関連付けるオーディオ選択
                audio_layout = QHBoxLayout()
                audio_combo = QComboBox()
                audio_combo.addItem("なし", None)
                for setting in self.audio_settings:
                    audio_index = setting['audio_index']
                    lang = setting['language'].currentText()
                    audio_combo.addItem(f"オーディオ #{audio_index} ({lang})", setting['stream_index'])
                audio_layout.addWidget(QLabel("関連付けるオーディオ:"))
                audio_layout.addWidget(audio_combo)
                audio_layout.addStretch()
                layout.addLayout(audio_layout)

                # フラグ設定
                flags_layout = QHBoxLayout()
                output_check = QCheckBox("出力")
                output_check.setChecked(True)  # デフォルトで出力対象
                default_check = QCheckBox("デフォルト字幕")
                forced_check = QCheckBox("強制字幕")
                if 'disposition' in stream:
                    if stream['disposition'].get('default', 0) == 1:
                        default_check.setChecked(True)
                    if stream['disposition'].get('forced', 0) == 1:
                        forced_check.setChecked(True)
                flags_layout.addWidget(output_check)
                flags_layout.addWidget(default_check)
                flags_layout.addWidget(forced_check)
                flags_layout.addStretch()
                layout.addLayout(flags_layout)

                group.setLayout(layout)
                self.subtitle_layout.addWidget(group)
                self.subtitle_groups.append({
                    'group': group,
                    'file': None,  # 既存の字幕なのでファイルはない
                    'language': lang_combo,
                    'audio': audio_combo,
                    'default': default_check,
                    'forced': forced_check,
                    'output': output_check,  # 出力対象フラグを追加
                    'stream_index': i,  # 元のストリームのインデックスを保持
                    'subtitle_index': subtitle_index,  # 字幕のインデックスを保持
                    'is_existing': True  # 既存の字幕であることを示すフラグ
                })
                subtitle_index += 1

    def add_subtitle_group(self):
        """字幕グループを追加"""
        group = QGroupBox(f"字幕 #{len(self.subtitle_groups) + 1}")
        layout = QVBoxLayout()

        # 字幕ファイル選択
        file_layout = QHBoxLayout()
        file_edit = QLineEdit()
        file_edit.setReadOnly(True)
        browse_button = QPushButton("字幕を選択...")
        browse_button.clicked.connect(lambda: self.browse_subtitle(file_edit))
        file_layout.addWidget(QLabel("字幕ファイル:"))
        file_layout.addWidget(file_edit)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)

        # 言語選択
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("言語:"))
        lang_combo = QComboBox()
        for code, name in LANGUAGES:
            lang_combo.addItem(f"{name} ({code})", code)
        lang_layout.addWidget(lang_combo)
        layout.addLayout(lang_layout)

        # 関連付けるオーディオ選択
        audio_layout = QHBoxLayout()
        audio_combo = QComboBox()
        audio_combo.addItem("なし", None)
        audio_layout.addWidget(QLabel("関連付けるオーディオ:"))
        audio_layout.addWidget(audio_combo)
        layout.addLayout(audio_layout)

        # フラグ設定
        flags_layout = QHBoxLayout()
        output_check = QCheckBox("出力")
        output_check.setChecked(True)  # デフォルトで出力対象
        default_check = QCheckBox("デフォルト字幕")
        forced_check = QCheckBox("強制字幕")
        flags_layout.addWidget(output_check)
        flags_layout.addWidget(default_check)
        flags_layout.addWidget(forced_check)
        flags_layout.addStretch()
        layout.addLayout(flags_layout)

        # 削除ボタン
        delete_button = QPushButton("この字幕を削除")
        delete_button.clicked.connect(lambda: self.remove_subtitle_group(group))
        layout.addWidget(delete_button)

        group.setLayout(layout)
        self.subtitle_layout.addWidget(group)
        self.subtitle_groups.append({
            'group': group,
            'file': file_edit,
            'language': lang_combo,
            'audio': audio_combo,
            'default': default_check,
            'forced': forced_check,
            'output': output_check  # 出力対象フラグを追加
        })

        # オーディオストリーム情報を更新
        if self.file_edit.text():
            self.update_audio_streams(self.file_edit.text())

    def remove_subtitle_group(self, group):
        """字幕グループを削除"""
        for i, g in enumerate(self.subtitle_groups):
            if g['group'] == group:
                self.subtitle_groups.pop(i)
                group.deleteLater()
                break
        # 残りのグループの番号を振り直す
        for i, g in enumerate(self.subtitle_groups, 1):
            g['group'].setTitle(f"字幕 #{i}")

    def browse_file(self):
        """入力ファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "メディアファイルの選択", "",
            "メディアファイル (*.mp4 *.m4v *.mkv);;すべてのファイル (*.*)")
        if file_path:
            self.file_edit.setText(file_path)
            # 出力ファイル名を自動設定
            dir_name = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.output_edit.setText(os.path.join(dir_name, f"{base_name}_output.mp4"))

            try:
                # FFmpegのパスを設定
                config = self.wizard().config
                if config.has_option("Settings", "ffmpeg_path"):
                    ffmpeg_dir = os.path.dirname(config.get("Settings", "ffmpeg_path"))
                    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

                # メディア情報を取得
                probe = ffmpeg.probe(file_path)

                # 映像言語を設定
                detected_video_lang = "未設定"
                video_info_text = []
                for stream in probe['streams']:
                    if stream['codec_type'] == 'video':
                        # コーデック情報
                        if 'codec_name' in stream:
                            video_info_text.append(f"コーデック: {stream['codec_name']}")
                        if 'profile' in stream:
                            video_info_text.append(f"プロファイル: {stream['profile']}")
                        if 'level' in stream:
                            video_info_text.append(f"レベル: {stream['level']}")

                        # 解像度とフレームレート
                        if 'width' in stream and 'height' in stream:
                            video_info_text.append(f"解像度: {stream['width']}x{stream['height']}")
                        if 'r_frame_rate' in stream:
                            num, den = map(int, stream['r_frame_rate'].split('/'))
                            fps = num / den if den != 0 else 0
                            video_info_text.append(f"フレームレート: {fps:.2f}fps")

                        # ビットレートとその他の情報
                        if 'bit_rate' in stream:
                            bit_rate = int(stream['bit_rate'])
                            video_info_text.append(f"ビットレート: {bit_rate//1000}kbps")
                        if 'pix_fmt' in stream:
                            video_info_text.append(f"ピクセルフォーマット: {stream['pix_fmt']}")
                        if 'color_space' in stream:
                            video_info_text.append(f"カラースペース: {stream['color_space']}")
                        if 'color_transfer' in stream:
                            video_info_text.append(f"カラートランスファー: {stream['color_transfer']}")
                        if 'color_primaries' in stream:
                            video_info_text.append(f"カラープライマリ: {stream['color_primaries']}")

                        # 言語設定
                        if 'tags' in stream and 'language' in stream['tags']:
                            lang = stream['tags']['language']
                            detected_video_lang = lang
                            index = self.video_lang_combo.findData(lang)
                            if index >= 0:
                                self.video_lang_combo.setCurrentIndex(index)
                            else:
                                # 言語コードが見つからない場合は'und'を設定
                                index = self.video_lang_combo.findData('und')
                                if index >= 0:
                                    self.video_lang_combo.setCurrentIndex(index)
                        break
                self.video_lang_label.setText(f"検出: {detected_video_lang}")
                # 映像情報を表示
                for widget in self.findChildren(QLabel):
                    if widget.parent() and isinstance(widget.parent(), QGroupBox) and widget.parent().title() == "映像設定":
                        widget.setText(" | ".join(video_info_text))
                        break

                # 既存の字幕グループをクリア
                for group in self.subtitle_groups:
                    group['group'].deleteLater()
                self.subtitle_groups.clear()

                # オーディオ設定を更新
                self.update_audio_settings(probe)

                # 既存の字幕を追加
                self.update_existing_subtitles(probe)

                # オーディオストリーム情報を更新
                self.update_audio_streams(file_path)

            except ffmpeg.Error as e:
                QMessageBox.warning(self, "警告",
                                  f"メディア情報の取得に失敗しました:\n{str(e)}")
            except Exception as e:
                QMessageBox.warning(self, "警告",
                                  f"予期せぬエラーが発生しました:\n{str(e)}")

    def browse_output(self):
        """出力ファイルを選択"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "出力ファイルの選択", self.output_edit.text(),
            "MP4ファイル (*.mp4);;すべてのファイル (*.*)")
        if file_path:
            self.output_edit.setText(file_path)

    def browse_subtitle(self, edit):
        """字幕ファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "字幕ファイルの選択", "",
            "字幕ファイル (*.srt *.ass *.ssa *.txt *.vtt *.smi *.sup *.dvb *.ttx *.tx3g);;すべてのファイル (*.*)")
        if file_path:
            edit.setText(file_path)

    def update_audio_streams(self, file_path):
        """オーディオストリーム情報を更新"""
        try:
            # FFmpegのパスを設定
            config = self.wizard().config
            if config.has_option("Settings", "ffmpeg_path"):
                ffmpeg_dir = os.path.dirname(config.get("Settings", "ffmpeg_path"))
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

            # メディア情報を取得
            probe = ffmpeg.probe(file_path)
            audio_streams = []
            for i, stream in enumerate(probe['streams']):
                if stream['codec_type'] == 'audio':
                    title = f"オーディオ #{i}"
                    if 'tags' in stream:
                        lang = stream['tags'].get('language', 'und')
                        title = f"{title} ({lang})"
                    audio_streams.append((title, i))

            # 各字幕グループのオーディオ選択を更新
            for group in self.subtitle_groups:
                combo = group['audio']
                current = combo.currentData()
                combo.clear()
                combo.addItem("なし", None)
                for title, index in audio_streams:
                    combo.addItem(title, index)
                # 以前の選択を復元
                if current is not None:
                    index = combo.findData(current)
                    if index >= 0:
                        combo.setCurrentIndex(index)

        except ffmpeg.Error as e:
            QMessageBox.warning(self, "警告",
                              f"オーディオストリーム情報の取得に失敗しました:\n{str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "警告",
                              f"予期せぬエラーが発生しました:\n{str(e)}")

    def validatePage(self):
        """ページの検証と処理の実行"""
        # MP4BoxとFFmpegのパス設定を確認
        config = self.wizard().config
        if not config.has_option("Settings", "mp4box_path") or not config.has_option("Settings", "ffmpeg_path"):
            QMessageBox.warning(self, "警告", "MP4BoxとFFmpegのパスを設定してください。")
            return False

        # 入力ファイルと出力ファイルが選択されているか確認
        if not self.file_edit.text():
            QMessageBox.warning(self, "警告", "入力ファイルを選択してください。")
            return False
        if not self.output_edit.text():
            QMessageBox.warning(self, "警告", "出力ファイルを選択してください。")
            return False

        # 字幕グループがある場合は検証
        for group in self.subtitle_groups:
            # 既存の字幕の場合はファイル選択のチェックをスキップ
            if not group.get('is_existing', False):
                if not group['file'].text():
                    QMessageBox.warning(self, "警告", "すべての字幕ファイルを選択してください。")
                    return False

        # 字幕の処理を実行
        return self.process_subtitles()

    def process_subtitles(self):
        """字幕の処理を実行"""
        input_file = self.file_edit.text()
        output_file = self.output_edit.text()
        config = self.wizard().config
        temp_files = []  # 一時ファイルのパスを保持

        try:
            # MP4Boxのパスを設定
            if not config.has_option("Settings", "mp4box_path"):
                QMessageBox.critical(self, "エラー", "MP4Boxの設定が見つかりません。")
                return False

            mp4box_path = config.get("Settings", "mp4box_path")
            mp4box_dir = os.path.dirname(mp4box_path)
            os.environ["PATH"] = mp4box_dir + os.pathsep + os.environ["PATH"]

            # 一時ディレクトリの設定
            temp_dir = config.get("Settings", "temp_dir", fallback=get_default_temp_dir())
            os.makedirs(temp_dir, exist_ok=True)

            # MP4Boxコマンドの構築
            args = [mp4box_path]

            # 新しいMP4ファイルを作成
            args.extend(['-add', input_file])

            # 映像言語の設定
            video_lang = self.video_lang_combo.currentData()
            args.extend(['-lang', '1=' + video_lang])

            # オーディオ言語とデフォルト設定
            for i, audio_setting in enumerate(self.audio_settings):
                lang_code = audio_setting['language'].currentData()
                args.extend(['-lang', f'{i+2}={lang_code}'])
                if audio_setting['default'].isChecked():
                    args.extend(['-def', str(i+2)])

            # 字幕の処理
            subtitle_index = len(self.audio_settings) + 2  # ビデオ(1) + オーディオ数 + 1
            for group in self.subtitle_groups:
                # 出力対象外の字幕はスキップ
                if not group['output'].isChecked():
                    continue

                if not group.get('is_existing', False):
                    if group['file'].text():
                        subtitle_file = group['file'].text()
                        # 字幕ファイルを一時ディレクトリにコピー
                        temp_subtitle = os.path.join(
                            temp_dir,
                            f"sub_{uuid.uuid4().hex[:16]}{os.path.splitext(subtitle_file)[1]}"
                        )
                        with open(subtitle_file, 'rb') as src, open(temp_subtitle, 'wb') as dst:
                            dst.write(src.read())
                        temp_files.append(temp_subtitle)

                        # 字幕の追加（字幕ファイルの種類に応じて適切なオプションを追加）
                        ext = os.path.splitext(subtitle_file)[1].lower()
                        if ext == '.srt':
                            args.extend(['-add', f'{temp_subtitle}:fmt=tx3g'])
                        else:
                            args.extend(['-add', temp_subtitle])

                        # 言語設定
                        args.extend(['-lang', f'{subtitle_index}={group["language"].currentData()}'])

                        # デフォルトと強制フラグの設定
                        if group['default'].isChecked():
                            args.extend(['-def', str(subtitle_index)])
                        if group['forced'].isChecked():
                            args.extend(['-force', str(subtitle_index)])

                        subtitle_index += 1

            # 出力ファイルを指定
            args.extend(['-new', '-out', output_file])

            # コマンドを表示
            print("\nMP4Boxコマンド:")
            print(" ".join(args))

            # 進捗表示用のダイアログを作成
            progress_dialog = QMessageBox(self)
            progress_dialog.setWindowTitle("処理中")
            progress_dialog.setText("MP4Boxでファイルを処理中...")
            progress_dialog.setStandardButtons(QMessageBox.NoButton)
            progress_dialog.show()

            # MP4Boxコマンドを実行
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            # 進捗情報を表示
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    progress_dialog.setText(f"MP4Boxでファイルを処理中...\n\n{output.strip()}")
                    QApplication.processEvents()

            # エラー出力を確認
            stderr_output = process.stderr.read()
            if process.returncode != 0:
                error_message = stderr_output if stderr_output else "不明なエラー"
                progress_dialog.close()
                raise Exception(error_message)

            progress_dialog.close()
            QMessageBox.information(self, "成功", "メディアファイルの処理が完了しました。")
            return True

        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"メディアファイルの処理に失敗しました:\n{str(e)}")
            return False
        finally:
            # 一時ファイルの削除
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    pass

    def export_subtitle(self, stream):
        """字幕ストリームをエクスポート"""
        try:
            # 出力ファイル名を提案
            input_file = self.file_edit.text()
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            stream_index = stream['index']
            codec_name = stream.get('codec_name', 'sub')

            # コーデックに応じたデフォルトの拡張子を設定
            default_ext = {
                'subrip': 'srt',
                'ass': 'ass',
                'ssa': 'ssa',
                'mov_text': 'txt',
                'text': 'txt',
                'dvd_subtitle': 'sup',
                'hdmv_pgs_subtitle': 'sup',
                'dvb_subtitle': 'dvb',
                'dvb_teletext': 'ttx',
                'webvtt': 'vtt',
                'sami': 'smi',
                'tx3g': 'tx3g'
            }.get(codec_name, 'sub')

            # 出力ファイルの選択
            file_path, _ = QFileDialog.getSaveFileName(
                self, "字幕のエクスポート",
                f"{base_name}_subtitle_{stream_index}.{default_ext}",
                "字幕ファイル (*.srt *.ass *.ssa *.txt *.vtt *.smi *.sup *.dvb *.ttx *.tx3g);;すべてのファイル (*.*)"
            )

            if file_path:
                # FFmpegで字幕をエクスポート
                config = self.wizard().config
                if config.has_option("Settings", "ffmpeg_path"):
                    ffmpeg_dir = os.path.dirname(config.get("Settings", "ffmpeg_path"))
                    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

                # 進捗表示用のダイアログを作成
                progress_dialog = QMessageBox(self)
                progress_dialog.setWindowTitle("処理中")
                progress_dialog.setText("字幕をエクスポート中...")
                progress_dialog.setStandardButtons(QMessageBox.NoButton)
                progress_dialog.show()

                # コーデックに応じた出力形式を設定
                output_format = {
                    'subrip': 'srt',
                    'ass': 'ass',
                    'ssa': 'ssa',
                    'mov_text': 'text',
                    'text': 'text',
                    'dvd_subtitle': 'dvdsub',
                    'hdmv_pgs_subtitle': 'copy',
                    'dvb_subtitle': 'dvbsub',
                    'dvb_teletext': 'dvbtxt',
                    'webvtt': 'webvtt',
                    'sami': 'sami',
                    'tx3g': 'tx3g'
                }.get(codec_name, 'copy')

                # FFmpegコマンドを構築
                ffmpeg_args = [
                    'ffmpeg', '-i', input_file,
                    '-map', f'0:{stream_index}'
                ]

                # 出力形式に応じたエンコーダーオプションを追加
                if output_format != 'copy':
                    ffmpeg_args.extend(['-c:s', output_format])
                else:
                    ffmpeg_args.extend(['-c:s', 'copy'])

                # 特殊な形式の場合の追加オプション
                if codec_name in ['dvd_subtitle', 'hdmv_pgs_subtitle']:
                    # SUP形式の場合、フレームレートを指定
                    ffmpeg_args.extend(['-r', '23.976'])

                ffmpeg_args.append(file_path)

                # コマンドを表示
                print("\nFFmpegコマンド:")
                print(" ".join(ffmpeg_args))

                # FFmpegコマンドを実行
                process = subprocess.Popen(
                    ffmpeg_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW  # Windowsの場合、コンソールウィンドウを表示しない
                )

                # 進捗情報を表示（タイムアウト付き）
                import time
                start_time = time.time()
                timeout = 30  # 30秒のタイムアウト

                while True:
                    # タイムアウトチェック
                    if time.time() - start_time > timeout:
                        process.kill()
                        progress_dialog.close()
                        raise Exception("処理がタイムアウトしました")

                    # プロセスの状態をチェック
                    if process.poll() is not None:
                        break

                    # 出力を読み取り
                    output = process.stdout.readline()
                    if output:
                        progress_dialog.setText(f"字幕をエクスポート中...\n\n{output.strip()}")
                        QApplication.processEvents()

                    # エラー出力をチェック
                    error = process.stderr.readline()
                    if error:
                        progress_dialog.setText(f"字幕をエクスポート中...\n\nエラー: {error.strip()}")
                        QApplication.processEvents()

                    # 少し待機してCPU負荷を下げる
                    time.sleep(0.1)

                # 残りのエラー出力を確認
                stderr_output = process.stderr.read()
                if process.returncode != 0:
                    error_message = stderr_output if stderr_output else "不明なエラー"
                    progress_dialog.close()
                    raise Exception(error_message)

                progress_dialog.close()
                QMessageBox.information(self, "成功", "字幕のエクスポートが完了しました。")

        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"字幕のエクスポートに失敗しました:\n{str(e)}")

    def nextId(self):
        """次のページのIDを返す"""
        return -1  # 最後のページなので-1を返す
