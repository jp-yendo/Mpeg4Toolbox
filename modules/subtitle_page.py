import os
import uuid
import ffmpeg
import subprocess
from PyQt5.QtWidgets import (QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QComboBox, QFileDialog,
                            QMessageBox, QGroupBox, QScrollArea, QWidget,
                            QCheckBox)
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
        video_lang_layout = QHBoxLayout()
        self.video_lang_combo = QComboBox()
        for code, name in LANGUAGES:
            self.video_lang_combo.addItem(name, code)
        video_lang_layout.addWidget(QLabel("映像の言語:"))
        video_lang_layout.addWidget(self.video_lang_combo)
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

                # 言語設定
                lang_layout = QHBoxLayout()
                lang_combo = QComboBox()
                for code, name in LANGUAGES:
                    lang_combo.addItem(name, code)
                # 現在の言語を設定
                if 'tags' in stream and 'language' in stream['tags']:
                    current_lang = stream['tags']['language']
                    index = lang_combo.findData(current_lang)
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                lang_layout.addWidget(QLabel("言語:"))
                lang_layout.addWidget(lang_combo)
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

                # 既存の字幕の情報を表示
                info_label = QLabel("既存の字幕ストリーム")
                info_label.setStyleSheet("font-weight: bold;")
                layout.addWidget(info_label)

                # 言語選択
                lang_layout = QHBoxLayout()
                lang_combo = QComboBox()
                for code, name in LANGUAGES:
                    lang_combo.addItem(name, code)
                # 現在の言語を設定
                if 'tags' in stream and 'language' in stream['tags']:
                    current_lang = stream['tags']['language']
                    index = lang_combo.findData(current_lang)
                    if index >= 0:
                        lang_combo.setCurrentIndex(index)
                lang_layout.addWidget(QLabel("言語:"))
                lang_layout.addWidget(lang_combo)
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
                layout.addLayout(audio_layout)

                # フラグ設定
                flags_layout = QHBoxLayout()
                default_check = QCheckBox("デフォルト字幕")
                forced_check = QCheckBox("強制字幕")
                if 'disposition' in stream:
                    if stream['disposition'].get('default', 0) == 1:
                        default_check.setChecked(True)
                    if stream['disposition'].get('forced', 0) == 1:
                        forced_check.setChecked(True)
                flags_layout.addWidget(default_check)
                flags_layout.addWidget(forced_check)
                layout.addLayout(flags_layout)

                # 削除ボタン
                delete_button = QPushButton("この字幕を削除")
                delete_button.clicked.connect(lambda: self.remove_subtitle_group(group))
                layout.addWidget(delete_button)

                group.setLayout(layout)
                self.subtitle_layout.addWidget(group)
                self.subtitle_groups.append({
                    'group': group,
                    'file': None,  # 既存の字幕なのでファイルはない
                    'language': lang_combo,
                    'audio': audio_combo,
                    'default': default_check,
                    'forced': forced_check,
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
        lang_combo = QComboBox()
        for code, name in LANGUAGES:
            lang_combo.addItem(name, code)
        lang_layout.addWidget(QLabel("言語:"))
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
        default_check = QCheckBox("デフォルト字幕")
        forced_check = QCheckBox("強制字幕")
        flags_layout.addWidget(default_check)
        flags_layout.addWidget(forced_check)
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
            'forced': forced_check
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
            "メディアファイル (*.mp4 *.m4v);;すべてのファイル (*.*)")
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
                for stream in probe['streams']:
                    if stream['codec_type'] == 'video':
                        if 'tags' in stream and 'language' in stream['tags']:
                            lang = stream['tags']['language']
                            index = self.video_lang_combo.findData(lang)
                            if index >= 0:
                                self.video_lang_combo.setCurrentIndex(index)
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
            "字幕ファイル (*.srt *.ass);;すべてのファイル (*.*)")
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
            # FFmpegのパスを設定
            if not config.has_option("Settings", "ffmpeg_path"):
                QMessageBox.critical(self, "エラー", "FFmpegの設定が見つかりません。")
                return False

            ffmpeg_path = config.get("Settings", "ffmpeg_path")
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

            # 一時ディレクトリの設定
            temp_dir = config.get("Settings", "temp_dir", fallback=get_default_temp_dir())
            os.makedirs(temp_dir, exist_ok=True)

            # 入力ファイルのストリーム情報を取得
            probe = ffmpeg.probe(input_file)
            input_stream = ffmpeg.input(input_file)
            metadata = {}

            # 映像ストリームの設定
            video_lang = self.video_lang_combo.currentData()
            metadata['metadata:s:v:0'] = f'language={video_lang}'

            # オーディオストリームの設定
            audio_index = 0
            for audio_setting in self.audio_settings:
                lang_code = audio_setting['language'].currentData()
                # オーディオストリームの言語設定
                metadata[f'metadata:s:a:{audio_index}'] = f'language={lang_code}'
                # デフォルトフラグの設定
                if audio_setting['default'].isChecked():
                    metadata[f'disposition:a:{audio_index}'] = 'default'
                audio_index += 1

            # 出力ファイルを一時ディレクトリに作成
            temp_output = os.path.join(temp_dir, f"output_{uuid.uuid4().hex[:16]}.mp4")
            temp_files.append(temp_output)

            # 字幕がない場合は基本のストリームのみ処理
            if not self.subtitle_groups:
                args = [ffmpeg_path, '-i', input_file]
                # 映像とオーディオのマッピング
                args.extend(['-map', '0:v:0'])  # 映像
                for audio_setting in self.audio_settings:
                    args.extend(['-map', f'0:a:{audio_setting["audio_index"]}'])

                # コーデックの設定
                args.extend(['-c:v', 'copy'])  # ビデオコーデック
                args.extend(['-c:a', 'copy'])  # オーディオコーデック

                # 映像の言語設定
                args.extend(['-metadata:s:v:0', f'language={video_lang}'])

                # オーディオの言語とデフォルト設定
                audio_index = 0
                for audio_setting in self.audio_settings:
                    lang_code = audio_setting['language'].currentData()
                    args.extend([f'-metadata:s:a:{audio_index}', f'language={lang_code}'])
                    if audio_setting['default'].isChecked():
                        args.extend([f'-disposition:a:{audio_index}', 'default'])
                    else:
                        args.extend([f'-disposition:a:{audio_index}', '0'])
                    audio_index += 1

                args.extend(['-y', temp_output])
            else:
                # 字幕ストリームを処理
                args = [ffmpeg_path, '-i', input_file]  # メインの入力ファイル

                # 字幕ファイルの入力を追加
                subtitle_files = []
                for group in self.subtitle_groups:
                    if not group.get('is_existing', False) and group['file'].text():
                        subtitle_file = group['file'].text()
                        # 字幕ファイルを一時ディレクトリにコピー
                        temp_subtitle = os.path.join(
                            temp_dir,
                            f"sub_{uuid.uuid4().hex[:16]}{os.path.splitext(subtitle_file)[1]}"
                        )
                        with open(subtitle_file, 'rb') as src, open(temp_subtitle, 'wb') as dst:
                            dst.write(src.read())
                        temp_files.append(temp_subtitle)
                        subtitle_files.append(temp_subtitle)
                        args.extend(['-i', temp_subtitle])

                # ストリームのマッピング
                args.extend(['-map', '0:v:0'])  # 映像
                for audio_setting in self.audio_settings:
                    args.extend(['-map', f'0:a:{audio_setting["audio_index"]}'])

                # 字幕のマッピング
                subtitle_index = 0
                input_index = 1
                for group in self.subtitle_groups:
                    if group.get('is_existing', False):
                        args.extend(['-map', f'0:s:{group["subtitle_index"]}'])
                    else:
                        if group['file'].text():
                            args.extend(['-map', f'{input_index}:0'])
                            input_index += 1
                    subtitle_index += 1

                # コーデックの設定
                args.extend(['-c:v', 'copy'])  # ビデオコーデック
                args.extend(['-c:a', 'copy'])  # オーディオコーデック
                args.extend(['-c:s', 'mov_text'])  # 字幕コーデック

                # 映像の言語設定
                args.extend(['-metadata:s:v:0', f'language={video_lang}'])

                # オーディオの言語とデフォルト設定
                audio_index = 0
                for audio_setting in self.audio_settings:
                    lang_code = audio_setting['language'].currentData()
                    args.extend([f'-metadata:s:a:{audio_index}', f'language={lang_code}'])
                    if audio_setting['default'].isChecked():
                        args.extend([f'-disposition:a:{audio_index}', 'default'])
                    else:
                        args.extend([f'-disposition:a:{audio_index}', '0'])
                    audio_index += 1

                # 字幕の言語とフラグ設定
                subtitle_index = 0
                for group in self.subtitle_groups:
                    lang_code = group['language'].currentData()
                    # 言語設定
                    args.extend([f'-metadata:s:s:{subtitle_index}', f'language={lang_code}'])
                    args.extend([f'-metadata:s:s:{subtitle_index}', f'title={group["language"].currentText()}'])

                    # デフォルトと強制フラグ
                    disposition = []
                    if group['default'].isChecked():
                        disposition.append('default')
                    if group['forced'].isChecked():
                        disposition.append('forced')

                    if disposition:
                        args.extend([f'-disposition:s:{subtitle_index}', '+'.join(disposition)])
                    else:
                        args.extend([f'-disposition:s:{subtitle_index}', '0'])

                    # 関連付けられたオーディオ
                    audio_index = group['audio'].currentData()
                    if audio_index is not None:
                        args.extend([f'-metadata:s:s:{subtitle_index}', f'audio_track={audio_index}'])

                    subtitle_index += 1

                args.extend(['-y', temp_output])

            # FFmpegコマンドを実行
            print("FFmpeg command:", ' '.join(args))
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode() if stderr else "不明なエラー"
                print("FFmpeg error output:", error_message)
                raise ffmpeg.Error('FFmpeg error', stdout, stderr)

            # 成功したら一時ファイルを最終出力先に移動
            os.replace(temp_output, output_file)

            QMessageBox.information(self, "成功", "メディアファイルの処理が完了しました。")
            return True

        except ffmpeg.Error as e:
            error_detail = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
            QMessageBox.critical(self, "エラー",
                               f"メディアファイルの処理に失敗しました:\n{error_detail}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"予期せぬエラーが発生しました:\n{str(e)}")
            return False
        finally:
            # 一時ファイルの削除
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"一時ファイルの削除に失敗しました: {temp_file}\n{str(e)}")

    def nextId(self):
        """次のページのIDを返す"""
        return -1  # 最後のページなので-1を返す
