import sys
import csv
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSplitter, QGroupBox, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFileDialog, QMessageBox, QApplication)
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtCore import Qt, QSettings

from app.ui.styles import DARK_STYLESHEET
from app.ui.widgets import HistogramWidget
from app.ui.viewer import ImageViewer
from app.core.processor import calculate_image_stats

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RGB Анализатор")
        self.resize(1200, 900)
        self.setStyleSheet(DARK_STYLESHEET)
        
        self.settings = QSettings("RGBTools", "RGBAnalyzer")
        self.last_dir = self.settings.value("last_dir", "")
        self.current_stats = None

        self.setup_ui()

    def setup_ui(self):
        # Menu Bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        
        export_action = QAction("Экспорт в CSV", self)
        export_action.triggered.connect(self.export_csv)
        file_menu.addAction(export_action)

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar / Controls
        controls_layout = QHBoxLayout()
        
        btn_open = QPushButton("📂 Открыть фото")
        btn_open.clicked.connect(self.open_image)
        controls_layout.addWidget(btn_open)
        
        btn_fit = QPushButton("⤢ Вписать в окно")
        btn_fit.clicked.connect(self.fit_image)
        controls_layout.addWidget(btn_fit)

        btn_calc = QPushButton("▶ Рассчитать")
        btn_calc.clicked.connect(self.calculate_stats)
        btn_calc.setStyleSheet("background-color: #264f78; font-weight: bold;")
        controls_layout.addWidget(btn_calc)
        
        main_layout.addLayout(controls_layout)

        # Splitter for Image and Results
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Viewer
        self.viewer = ImageViewer()
        splitter.addWidget(self.viewer)

        # Right Panel (Stats + Table)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(right_panel)

        # --- Stats Group ---
        stats_group = QGroupBox("Результаты")
        stats_layout = QVBoxLayout(stats_group)
        
        self.lbl_results = QLabel("Загрузите изображение и выделите область.")
        self.lbl_results.setStyleSheet("font-size: 14px; padding: 5px;")
        self.lbl_results.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_results.setWordWrap(True)
        stats_layout.addWidget(self.lbl_results)
        
        self.btn_copy = QPushButton("📋 Копировать команду")
        self.btn_copy.clicked.connect(self.copy_command)
        self.btn_copy.setEnabled(False)
        stats_layout.addWidget(self.btn_copy)
        
        right_layout.addWidget(stats_group)

        # --- Histogram Group ---
        hist_group = QGroupBox("Гистограмма RGB")
        hist_layout = QVBoxLayout(hist_group)
        self.histogram = HistogramWidget()
        hist_layout.addWidget(self.histogram)
        right_layout.addWidget(hist_group)

        # --- Colors Table ---
        table_group = QGroupBox("Детализация цветов")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["R", "G", "B", "Кол-во", "Цвет"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table)
        
        right_layout.addWidget(table_group)

        # Set initial splitter sizes (65% image, 35% stats)
        splitter.setSizes([800, 450])

        self.last_command = ""

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", self.last_dir, "Images (*.png *.jpg *.jpeg *.bmp *.tif)")
        if file_name:
            self.last_dir = os.path.dirname(file_name)
            self.settings.setValue("last_dir", self.last_dir)
            
            self.viewer.load_image(file_name)
            self.lbl_results.setText("Изображение загружено.\nПереместите красный квадрат на серую область.")
            self.table.setRowCount(0)
            self.histogram.set_data([], [], [])
            self.btn_copy.setEnabled(False)
            self.current_stats = None

    def fit_image(self):
        if self.viewer.scene:
            self.viewer.fitInView(self.viewer.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def calculate_stats(self):
        rect = self.viewer.get_selection_rect()
        if not rect:
            self.lbl_results.setText("Ошибка: Не выделена область или файл не найден.")
            self.btn_copy.setEnabled(False)
            return

        stats = calculate_image_stats(self.viewer.image_path, rect)
        if stats:
            self.current_stats = stats
            r = stats['r']
            g = stats['g']
            b = stats['b']
            
            # Normalize to Green = 1.0
            norm_r = r / g if g != 0 else 0
            norm_g = 1.0
            norm_b = b / g if g != 0 else 0
            
            self.last_command = f"R,B {norm_r:.2f},{norm_b:.2f}"
            
            res_text = (
                f"<b>Средний RGB:</b> R={r:.1f}, G={g:.1f}, B={b:.1f}<br>"
                f"<b>Медиана:</b> R={stats['median_r']:.1f}, G={stats['median_g']:.1f}, B={stats['median_b']:.1f}<br>"
                f"<b>StdDev (Шум):</b> R={stats['std_r']:.2f}, G={stats['std_g']:.2f}, B={stats['std_b']:.2f}<br>"
                f"<b>Нормализация (G=1.0):</b> R={norm_r:.4f}, G={norm_g:.4f}, B={norm_b:.4f}<br>"
                f"<div style='font-size: 16px; color: #4ec9b0; margin-top: 5px;'><b>{self.last_command}</b></div><br>"
                f"<b>Всего пикселей:</b> {stats['count']}<br>"
                f"<b>Уникальных цветов:</b> {len(stats['unique_colors'])}"
            )
            self.lbl_results.setText(res_text)
            self.btn_copy.setEnabled(True)

            # Update Histogram
            self.histogram.set_data(*stats['hist'])

            # Populate table
            unique_colors = stats['unique_colors']
            counts = stats['counts']
            
            # Limit to top 10000 to avoid freezing UI
            limit = 10000
            count_shown = min(len(unique_colors), limit)
            self.table.setRowCount(count_shown)
            
            if len(unique_colors) > limit:
                 self.lbl_results.setText(res_text + f"<br><span style='color: orange'>Показано топ {limit} из {len(unique_colors)} цветов</span>")
            
            for i in range(self.table.rowCount()):
                color = unique_colors[i]
                count = counts[i]
                
                self.table.setItem(i, 0, QTableWidgetItem(str(color[0])))
                self.table.setItem(i, 1, QTableWidgetItem(str(color[1])))
                self.table.setItem(i, 2, QTableWidgetItem(str(color[2])))
                self.table.setItem(i, 3, QTableWidgetItem(str(count)))
                
                # Color preview item
                color_item = QTableWidgetItem()
                color_item.setBackground(QColor(int(color[0]), int(color[1]), int(color[2])))
                self.table.setItem(i, 4, color_item)
        else:
            self.lbl_results.setText("Ошибка при обработке изображения.")
            self.btn_copy.setEnabled(False)

    def copy_command(self):
        if self.last_command:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_command)
            self.btn_copy.setText("✅ Скопировано!")

    def export_csv(self):
        if not self.current_stats:
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчет статистики.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", self.last_dir, "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Header stats
                    writer.writerow(["Statistic", "R", "G", "B"])
                    writer.writerow(["Mean", self.current_stats['r'], self.current_stats['g'], self.current_stats['b']])
                    writer.writerow(["Median", self.current_stats['median_r'], self.current_stats['median_g'], self.current_stats['median_b']])
                    writer.writerow(["StdDev", self.current_stats['std_r'], self.current_stats['std_g'], self.current_stats['std_b']])
                    writer.writerow([])
                    
                    # Colors
                    writer.writerow(["R", "G", "B", "Count"])
                    unique_colors = self.current_stats['unique_colors']
                    counts = self.current_stats['counts']
                    for i in range(len(unique_colors)):
                        c = unique_colors[i]
                        writer.writerow([c[0], c[1], c[2], counts[i]])
                        
                QMessageBox.information(self, "Успех", f"Данные сохранены в {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
