import sys
import csv
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSplitter, QGroupBox, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFileDialog, QMessageBox, QApplication, QListWidget, QSlider,
                             QCheckBox, QSpinBox)
from PyQt6.QtGui import QAction, QColor, QIcon
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
        self.image_paths = []
        self.current_image_index = -1

        # Set Window Icon
        icon_path = self.get_resource_path(os.path.join("assets", "image.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setup_ui()

    def get_resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

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

        btn_clear = QPushButton("🗑 Очистить список")
        btn_clear.clicked.connect(self.clear_images)
        controls_layout.addWidget(btn_clear)
        
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

        # Image List
        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)
        splitter.addWidget(self.image_list)

        # Viewer
        self.viewer = ImageViewer()
        self.viewer.grid_clicked.connect(self.calculate_stats) # Init calculate stats on grid click
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

        # --- Overlay Group ---
        overlay_group = QGroupBox("Наложение")
        overlay_layout = QVBoxLayout(overlay_group)
        
        btn_set_overlay = QPushButton("📌 Сделать наложением")
        btn_set_overlay.clicked.connect(self.set_overlay)
        overlay_layout.addWidget(btn_set_overlay)
        
        btn_remove_overlay = QPushButton("❌ Убрать наложение")
        btn_remove_overlay.clicked.connect(self.remove_overlay)
        overlay_layout.addWidget(btn_remove_overlay)
        
        overlay_layout.addWidget(QLabel("Прозрачность:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        overlay_layout.addWidget(self.opacity_slider)
        
        right_layout.addWidget(overlay_group)

        # --- Histogram Group ---
        hist_group = QGroupBox("Гистограмма RGB")
        hist_layout = QVBoxLayout(hist_group)
        self.histogram = HistogramWidget()
        hist_layout.addWidget(self.histogram)
        right_layout.addWidget(hist_group)

        # --- Grid Group ---
        grid_group = QGroupBox("Сетка")
        grid_layout = QVBoxLayout(grid_group)
        
        self.cb_grid = QCheckBox("Показать сетку")
        self.cb_grid.stateChanged.connect(self.toggle_grid)
        grid_layout.addWidget(self.cb_grid)
        
        grid_controls = QHBoxLayout()
        grid_controls.addWidget(QLabel("Размер ячейки:"))
        self.sb_cell_size = QSpinBox()
        self.sb_cell_size.setRange(10, 10000)
        self.sb_cell_size.setValue(50)
        self.sb_cell_size.valueChanged.connect(self.update_grid_size)
        grid_controls.addWidget(self.sb_cell_size)
        grid_layout.addLayout(grid_controls)
        
        right_layout.addWidget(grid_group)


        # --- Colors Table ---
        table_group = QGroupBox("Детализация цветов")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["R", "G", "B", "Кол-во", "Цвет"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table)
        
        right_layout.addWidget(table_group)

        # Set initial splitter sizes (15% list, 55% image, 30% stats)
        splitter.setSizes([200, 700, 350])

        self.last_command = ""
        self.last_calculated_params = None

    def open_image(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Открыть изображения", self.last_dir, "Images (*.png *.jpg *.jpeg *.bmp *.tif)")
        if file_names:
            self.last_dir = os.path.dirname(file_names[0])
            self.settings.setValue("last_dir", self.last_dir)
            
            for f in file_names:
                if f not in self.image_paths:
                    self.image_paths.append(f)
                    self.image_list.addItem(os.path.basename(f))
            
            if self.image_list.count() > 0 and self.image_list.currentRow() == -1:
                self.image_list.setCurrentRow(0)

    def clear_images(self):
        self.image_paths = []
        self.image_list.clear()
        self.viewer.scene.clear()
        self.lbl_results.setText("Список очищен.")
        self.table.setRowCount(0)
        self.histogram.set_data([], [], [])
        self.current_stats = None
        self.last_calculated_params = None

    def on_image_selected(self, index):
        if 0 <= index < len(self.image_paths):
            path = self.image_paths[index]
            self.viewer.load_image(path)
            self.lbl_results.setText(f"Загружено: {os.path.basename(path)}")
            
            # Auto-calculate stats if we have a rect
            if self.viewer.get_selection_rect():
                self.calculate_stats()
            else:
                self.table.setRowCount(0)
                self.histogram.set_data([], [], [])
                self.current_stats = None
            
            # Reset overlay opacity slider if needed, or keep it?
            # Keeping it allows persistent overlay settings.

    def set_overlay(self):
        row = self.image_list.currentRow()
        if row >= 0:
            path = self.image_paths[row]
            self.viewer.set_overlay(path)
            self.viewer.set_overlay_opacity(self.opacity_slider.value() / 100.0)
            QMessageBox.information(self, "Наложение", f"Изображение '{os.path.basename(path)}' установлено как наложение.")

    def remove_overlay(self):
        self.viewer.set_overlay(None)

    def change_opacity(self, value):
        self.viewer.set_overlay_opacity(value / 100.0)

    def fit_image(self):
        if self.viewer.scene:
            self.viewer.fitInView(self.viewer.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def toggle_grid(self, state):
        self.viewer.set_grid(self.cb_grid.isChecked(), self.sb_cell_size.value())

    def update_grid_size(self, value):
        if self.cb_grid.isChecked():
            self.viewer.set_grid(True, value)

    def calculate_stats(self, rect=None):
        if rect is None or isinstance(rect, bool): # Handle direct call or click event if no rect passed (though signal passes rect)
            # Check if arg is rect or just a connector triggered bool
            # If triggered from button, rect is False.
            rect = self.viewer.get_selection_rect()
        
        # If rect came from signal (QRectF), convert to tuple
        if hasattr(rect, 'getRect'): # It is a QRectF
             # Convert QRectF to x, y, w, h
             # BUT wait, calculate_stats expects int tuple relative to image?
             # viewer.get_selection_rect() returns (x, y, w, h) ints.
             # viewer.on_grid_click emits cell_rect which is QRectF in scene coords (which matches image coords)
             
             # Let's align.
             r = rect
             # Important: We need to make sure we treat it as relative to image 0,0
             # which our scene assumes since we add Pixmap at 0,0.
             new_rect = (int(r.x()), int(r.y()), int(r.width()), int(r.height()))
             rect = new_rect

        if not rect:
            self.lbl_results.setText("Ошибка: Не выделена область или файл не найден.")
            self.btn_copy.setEnabled(False)
            return

        # Optimization: Check if we are recalculating the same thing
        current_params = (self.viewer.image_path, rect)
        if hasattr(self, 'last_calculated_params') and self.last_calculated_params == current_params:
            return
        self.last_calculated_params = current_params

        # Base Image Stats
        stats = calculate_image_stats(self.viewer.image_path, rect)
        
        # Overlay Stats
        overlay_stats = None
        overlay_info = self.viewer.get_overlay_info()
        if overlay_info:
            overlay_path, overlay_pos = overlay_info
            
            # Calculate rect relative to overlay
            # rect is (x, y, w, h) in base image coordinates (which matches scene coords for base image at 0,0)
            # overlay is at overlay_pos
            
            ox = int(rect[0] - overlay_pos.x())
            oy = int(rect[1] - overlay_pos.y())
            ow = rect[2]
            oh = rect[3]
            
            overlay_stats = calculate_image_stats(overlay_path, (ox, oy, ow, oh))

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
            
            if overlay_stats:
                or_ = overlay_stats['r']
                og = overlay_stats['g']
                ob = overlay_stats['b']
                
                dr = r - or_
                dg = g - og
                db = b - ob
                
                res_text += (
                    f"<br><hr><br>"
                    f"<b>Наложение RGB:</b> R={or_:.1f}, G={og:.1f}, B={ob:.1f}<br>"
                    f"<b>Delta (Base - Overlay):</b> <span style='color: {'#ff6b6b' if dr < 0 else '#6bff6b'}'>R={dr:+.1f}</span>, "
                    f"<span style='color: {'#ff6b6b' if dg < 0 else '#6bff6b'}'>G={dg:+.1f}</span>, "
                    f"<span style='color: {'#ff6b6b' if db < 0 else '#6bff6b'}'>B={db:+.1f}</span>"
                )

            self.lbl_results.setText(res_text)
            self.btn_copy.setEnabled(True)

            # Update Histogram (Base only for now, or maybe combined?)
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
