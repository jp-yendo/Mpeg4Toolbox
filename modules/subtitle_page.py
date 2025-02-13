import os
import uuid
import ffmpeg
from PyQt5.QtWidgets import (QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QComboBox, QFileDialog,
                            QMessageBox, QGroupBox, QScrollArea, QWidget)
from .constants import LANGUAGES
from .utils import get_default_temp_dir

class MediaTagManagementPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("字幕管理")
        self.setSubTitle("メディアファイルの字幕を管理します")
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
            'audio': audio_combo
        })

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
            # オーディオストリーム情報を更新
            self.update_audio_streams(file_path)

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

    def process_subtitles(self):
        """字幕の処理を実行"""
        input_file = self.file_edit.text()
        output_file = self.output_edit.text()
        config = self.wizard().config

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

        try:
            # 入力ファイルのストリーム情報を取得
            probe = ffmpeg.probe(input_file)
            input_stream = ffmpeg.input(input_file)
            streams = []
            subtitle_index = 0

            # 元のストリームをマッピング
            streams.append(input_stream['v:0'])
            for i, stream in enumerate(probe['streams']):
                if stream['codec_type'] == 'audio':
                    streams.append(input_stream[f'a:{i}'])

            # 字幕ファイルを処理
            for group in self.subtitle_groups:
                subtitle_file = group['file'].text()
                if not subtitle_file:
                    continue

                # 字幕ファイルを一時ディレクトリにコピー
                temp_subtitle = os.path.join(
                    temp_dir,
                    f"sub_{uuid.uuid4().hex[:16]}{os.path.splitext(subtitle_file)[1]}"
                )
                with open(subtitle_file, 'rb') as src, open(temp_subtitle, 'wb') as dst:
                    dst.write(src.read())

                # 字幕ストリームを追加
                subtitle_stream = ffmpeg.input(temp_subtitle)
                streams.append(subtitle_stream)

                # メタデータを設定
                metadata = {}
                lang_code = group['language'].currentData()
                if lang_code != 'und':
                    metadata[f'metadata:s:s:{subtitle_index}'] = f'language={lang_code}'
                    metadata[f'metadata:s:s:{subtitle_index}'] = f'title={group["language"].currentText()}'

                # 関連付けられたオーディオがある場合
                audio_index = group['audio'].currentData()
                if audio_index is not None:
                    metadata[f'metadata:s:s:{subtitle_index}'] = f'audio_track={audio_index}'

                subtitle_index += 1

            # 出力ファイルを一時ディレクトリに作成
            temp_output = os.path.join(temp_dir, f"output_{uuid.uuid4().hex[:16]}.mp4")

            # FFmpegコマンドを構築して実行
            stream = ffmpeg.output(*streams, temp_output,
                                 acodec='copy',
                                 vcodec='copy',
                                 **metadata)

            ffmpeg.run(stream, overwrite_output=True)

            # 成功したら一時ファイルを最終出力先に移動
            os.replace(temp_output, output_file)

            QMessageBox.information(self, "成功", "字幕の処理が完了しました。")
            return True

        except ffmpeg.Error as e:
            QMessageBox.critical(self, "エラー",
                               f"字幕の処理に失敗しました:\n{str(e)}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "エラー",
                               f"予期せぬエラーが発生しました:\n{str(e)}")
            return False
        finally:
            # 一時ファイルの削除
            for group in self.subtitle_groups:
                subtitle_file = group['file'].text()
                if subtitle_file:
                    temp_subtitle = os.path.join(
                        temp_dir,
                        f"sub_{os.path.splitext(subtitle_file)[1]}"
                    )
                    try:
                        if os.path.exists(temp_subtitle):
                            os.remove(temp_subtitle)
                    except:
                        pass

    def validatePage(self):
        """ページの検証と処理の実行"""
        # 入力ファイルと出力ファイルが選択されているか確認
        if not self.file_edit.text():
            QMessageBox.warning(self, "警告", "入力ファイルを選択してください。")
            return False
        if not self.output_edit.text():
            QMessageBox.warning(self, "警告", "出力ファイルを選択してください。")
            return False

        # 少なくとも1つの字幕が追加されているか確認
        if not self.subtitle_groups:
            QMessageBox.warning(self, "警告", "少なくとも1つの字幕を追加してください。")
            return False

        # 各字幕グループの検証
        for group in self.subtitle_groups:
            if not group['file'].text():
                QMessageBox.warning(self, "警告", "すべての字幕ファイルを選択してください。")
                return False

        # 字幕の処理を実行
        return self.process_subtitles()

    def nextId(self):
        """次のページのIDを返す"""
        return -1  # 最後のページなので-1を返す
