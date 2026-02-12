import sys
import csv
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSplitter, QGroupBox, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFileDialog, QMessageBox, QApplication, QListWidget, QSlider,
                             QCheckBox, QSpinBox, QTabWidget)
from PyQt6.QtGui import QAction, QColor, QIcon
from PyQt6.QtCore import Qt, QSettings

from app.ui.styles import DARK_STYLESHEET
from app.ui.widgets import HistogramWidget, LineProfileWidget
from app.ui.viewer import ImageViewer
from app.core.processor import calculate_image_stats, calculate_line_profile, calculate_grid_stats, create_annotated_image

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
        
        self.setAcceptDrops(True)

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
        
        export_action = QAction("Экспорт результатов", self)
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
        btn_calc.clicked.connect(lambda: self.calculate_stats())
        btn_calc.setStyleSheet("background-color: #264f78; font-weight: bold;")
        controls_layout.addWidget(btn_calc)
        
        # Tools
        controls_layout.addSpacing(20)
        controls_layout.addWidget(QLabel("Инструмент:"))
        
        self.btn_tool_rect = QPushButton("⬛ Область")
        self.btn_tool_rect.setCheckable(True)
        self.btn_tool_rect.setChecked(True)
        self.btn_tool_rect.clicked.connect(lambda: self.set_tool('rect'))
        controls_layout.addWidget(self.btn_tool_rect)

        self.btn_tool_line = QPushButton("📏 Линия")
        self.btn_tool_line.setCheckable(True)
        self.btn_tool_line.clicked.connect(lambda: self.set_tool('line'))
        controls_layout.addWidget(self.btn_tool_line)
        
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
        self.viewer.grid_clicked.connect(self.calculate_stats) 
        self.viewer.item_changed.connect(self.on_item_changed)
        self.viewer.files_dropped.connect(self.load_images)
        splitter.addWidget(self.viewer)

        # Right Panel (Stats + Table)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(right_panel)

        # --- Stats Group ---
        stats_group = QGroupBox("Результаты")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_tabs = QTabWidget()
        stats_layout.addWidget(self.stats_tabs)
        
        # RGB Tab
        self.lbl_rgb = QLabel("Загрузите изображение...")
        self.lbl_rgb.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_rgb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.stats_tabs.addTab(self.lbl_rgb, "RGB")
        
        # HSV Tab
        self.lbl_hsv = QLabel("Данные HSV")
        self.lbl_hsv.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_hsv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.stats_tabs.addTab(self.lbl_hsv, "HSV")

        stats_buttons_layout = QHBoxLayout()

        self.btn_copy = QPushButton("📋 Копировать RGB")
        self.btn_copy.clicked.connect(self.copy_command)
        self.btn_copy.setEnabled(False)
        stats_buttons_layout.addWidget(self.btn_copy)

        self.btn_csv = QPushButton("💾 Сохранить в Excel")
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_csv.setEnabled(False)
        stats_buttons_layout.addWidget(self.btn_csv)
        
        stats_layout.addLayout(stats_buttons_layout)
        
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

        # --- Visualization Group (Histogram + Line Profile) ---
        viz_group = QGroupBox("Графики")
        viz_layout = QVBoxLayout(viz_group)
        
        self.viz_tabs = QTabWidget()
        
        self.histogram = HistogramWidget()
        self.viz_tabs.addTab(self.histogram, "Гистограмма")
        
        self.line_profile = LineProfileWidget()
        self.viz_tabs.addTab(self.line_profile, "Профиль линии")
        
        viz_layout.addWidget(self.viz_tabs)
        right_layout.addWidget(viz_group)

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

        self.btn_export_grid = QPushButton("💾 Экспорт сетки в Excel")
        self.btn_export_grid.clicked.connect(self.export_grid_stats)
        grid_layout.addWidget(self.btn_export_grid)
        
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
        file_names, _ = QFileDialog.getOpenFileNames(self, "Открыть изображения", self.last_dir, "Изображения (*.png *.jpg *.jpeg *.bmp *.tif)")
        if file_names:
            self.load_images(file_names)
            
    def load_images(self, paths):
        """Helper to load list of image paths"""
        if not paths:
            return

        # Update last dir based on first file
        self.last_dir = os.path.dirname(paths[0])
        self.settings.setValue("last_dir", self.last_dir)
        
        added_any = False
        for f in paths:
            if f not in self.image_paths:
                self.image_paths.append(f)
                self.image_list.addItem(os.path.basename(f))
                added_any = True
        
        # Select first one if list was empty or select new one?
        # Logic: if nothing selected, select 0.
        if self.image_list.count() > 0 and self.image_list.currentRow() == -1:
            self.image_list.setCurrentRow(0)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))]
        
        if image_files:
            self.load_images(image_files)

    def clear_images(self):
        self.image_paths = []
        self.image_list.clear()
        self.viewer.scene.clear()
        self.lbl_rgb.setText("Список очищен.")
        self.lbl_hsv.setText("")
        self.histogram.set_data([], [], [])
        self.current_stats = None
        self.last_calculated_params = None

    def on_image_selected(self, index):
        if 0 <= index < len(self.image_paths):
            path = self.image_paths[index]
            self.viewer.load_image(path)
            self.lbl_rgb.setText(f"Загружено: {os.path.basename(path)}")
            
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

    def set_tool(self, mode):
        self.btn_tool_rect.setChecked(mode == 'rect')
        self.btn_tool_line.setChecked(mode == 'line')
        self.viewer.set_tool(mode)
        
        # Switch tabs to match useful info
        if mode == 'rect':
            self.viz_tabs.setCurrentWidget(self.histogram)
            self.calculate_stats()
        else:
            self.viz_tabs.setCurrentWidget(self.line_profile)
            self.calculate_profile()

    def on_item_changed(self):
        if self.viewer.current_tool == 'rect':
            self.calculate_stats()
        elif self.viewer.current_tool == 'line':
            self.calculate_profile()

    def calculate_profile(self):
        line_coords = self.viewer.get_line_coords()
        if not line_coords:
            self.line_profile.set_data([], [], [])
            return

        # Optimization check could be added here similar to stats

        profile_data = calculate_line_profile(self.viewer.image_path, line_coords)
        if profile_data:
            self.line_profile.set_data(profile_data['r'], profile_data['g'], profile_data['b'])
    
    def calculate_stats(self, rect=None):
        if rect is None or isinstance(rect, bool): 
            rect = self.viewer.get_selection_rect()
        
        if hasattr(rect, 'getRect'): 
             r = rect
             # Important: We need to make sure we treat it as relative to image 0,0
             # which our scene assumes since we add Pixmap at 0,0.
             new_rect = (int(r.x()), int(r.y()), int(r.width()), int(r.height()))
             rect = new_rect

        if not rect:
            self.lbl_rgb.setText("Ошибка: Не выделена область или файл не найден.")
            self.btn_copy.setEnabled(False)
            self.btn_csv.setEnabled(False)
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
            
            # RGB Text
            res_text = (
                f"<b>Средний RGB:</b> R={r:.1f}, G={g:.1f}, B={b:.1f}<br>"
                f"<b>Медиана:</b> R={stats['median_r']:.1f}, G={stats['median_g']:.1f}, B={stats['median_b']:.1f}<br>"
                f"<b>Разброс (Шум):</b> R={stats['std_r']:.2f}, G={stats['std_g']:.2f}, B={stats['std_b']:.2f}<br>"
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
                    f"<b>Разница (База - Наложение):</b> <span style='color: {'#ff6b6b' if dr < 0 else '#6bff6b'}'>R={dr:+.1f}</span>, "
                    f"<span style='color: {'#ff6b6b' if dg < 0 else '#6bff6b'}'>G={dg:+.1f}</span>, "
                    f"<span style='color: {'#ff6b6b' if db < 0 else '#6bff6b'}'>B={db:+.1f}</span>"
                )
            
            self.lbl_rgb.setText(res_text)

            # HSV Text
            hsv = stats.get('hsv', {})
            hsv_text = (
                f"<b>Hue (Тон):</b> {hsv.get('avg_h', 0):.1f} (Сред.), {hsv.get('median_h', 0):.1f} (Мед.)<br>"
                f"<b>Saturation (Насыщ.):</b> {hsv.get('avg_s', 0):.1f} (Сред.), {hsv.get('median_s', 0):.1f} (Мед.)<br>"
                f"<b>Value (Яркость):</b> {hsv.get('avg_v', 0):.1f} (Сред.), {hsv.get('median_v', 0):.1f} (Мед.)<br><br>"
                f"<b>Разброс:</b> H={hsv.get('std_h', 0):.2f}, S={hsv.get('std_s', 0):.2f}, V={hsv.get('std_v', 0):.2f}"
            )
            self.lbl_hsv.setText(hsv_text)

            self.btn_copy.setEnabled(True)
            self.btn_csv.setEnabled(True)

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
                 self.lbl_rgb.setText(res_text + f"<br><span style='color: orange'>Показано топ {limit} из {len(unique_colors)} цветов</span>")
            
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
            self.lbl_rgb.setText("Ошибка при обработке изображения.")
            self.btn_copy.setEnabled(False)
            self.btn_csv.setEnabled(False)


    def copy_command(self):
        if self.last_command:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_command)
            self.btn_copy.setText("✅ Скопировано!")

    def export_csv(self):
        if not self.current_stats:
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчет статистики.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить результаты", self.last_dir, "Excel файлы (*.xlsx);;CSV файлы (*.csv)")
        if file_name:
            try:
                if file_name.endswith('.xlsx'):
                     import xlsxwriter
                     
                     workbook = xlsxwriter.Workbook(file_name)
                     worksheet = workbook.add_worksheet()
                     
                     # Formats
                     header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
                     num_format = workbook.add_format({'num_format': '0.00'})
                     bold_format = workbook.add_format({'bold': True})
                     
                     # Writing Stats Table
                     # Header
                     worksheet.write(0, 0, "Статистика", header_format)
                     worksheet.write(0, 1, "R", header_format)
                     worksheet.write(0, 2, "G", header_format)
                     worksheet.write(0, 3, "B", header_format)
                     
                     # Data Rows
                     stats = [
                         ("Среднее", self.current_stats['r'], self.current_stats['g'], self.current_stats['b']),
                         ("Медиана", self.current_stats['median_r'], self.current_stats['median_g'], self.current_stats['median_b']),
                         ("СтдОткл", self.current_stats['std_r'], self.current_stats['std_g'], self.current_stats['std_b'])
                     ]
                     
                     for i, (label, r, g, b) in enumerate(stats, 1):
                         worksheet.write(i, 0, label, bold_format)
                         worksheet.write_number(i, 1, r, num_format)
                         worksheet.write_number(i, 2, g, num_format)
                         worksheet.write_number(i, 3, b, num_format)
                         
                     # Colors Table
                     start_row = 6
                     worksheet.write(start_row, 0, "R", header_format)
                     worksheet.write(start_row, 1, "G", header_format)
                     worksheet.write(start_row, 2, "B", header_format)
                     worksheet.write(start_row, 3, "Количество", header_format)
                     
                     unique_colors = self.current_stats['unique_colors']
                     counts = self.current_stats['counts']
                     
                     for i in range(len(unique_colors)):
                         c = unique_colors[i]
                         row = start_row + 1 + i
                         worksheet.write(row, 0, c[0])
                         worksheet.write(row, 1, c[1])
                         worksheet.write(row, 2, c[2])
                         worksheet.write(row, 3, counts[i])
                     
                     # Auto-width
                     worksheet.set_column(0, 3, 15)
                     
                     workbook.close()
                else: 
                    # CSV Fallback
                    with open(file_name, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        
                        # Header stats
                        writer.writerow(["Статистика", "R", "G", "B"])
                        writer.writerow(["Среднее", self.current_stats['r'], self.current_stats['g'], self.current_stats['b']])
                        writer.writerow(["Медиана", self.current_stats['median_r'], self.current_stats['median_g'], self.current_stats['median_b']])
                        writer.writerow(["СтдОткл", self.current_stats['std_r'], self.current_stats['std_g'], self.current_stats['std_b']])
                        writer.writerow([])
                        
                        # Colors
                        writer.writerow(["R", "G", "B", "Количество"])
                        unique_colors = self.current_stats['unique_colors']
                        counts = self.current_stats['counts']
                        for i in range(len(unique_colors)):
                            c = unique_colors[i]
                            writer.writerow([c[0], c[1], c[2], counts[i]])
                        
                QMessageBox.information(self, "Успех", f"Данные сохранены в {file_name}")
            except ImportError:
                 QMessageBox.critical(self, "Ошибка", "Установите xlsxwriter: pip install xlsxwriter")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def export_grid_stats(self):
        if not self.viewer.image_path:
            QMessageBox.warning(self, "Ошибка", "Изображение не загружено.")
            return

        if not self.cb_grid.isChecked():
            # Ask if user wants to enable grid or proceed with current settings?
            pass

        cell_size = self.sb_cell_size.value()
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить Сетку", self.last_dir, "Excel файлы (*.xlsx);;CSV файлы (*.csv)")
        if not file_name:
            return

        # Show wait cursor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            results = calculate_grid_stats(self.viewer.image_path, cell_size)
            
            if not results:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Ошибка", "Не удалось рассчитать данные сетки.")
                return

            if file_name.endswith('.xlsx'):
                import xlsxwriter
                
                workbook = xlsxwriter.Workbook(file_name)
                worksheet = workbook.add_worksheet()
                
                # Formats
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
                num_format = workbook.add_format({'num_format': '0.00'})
                
                headers = ["X", "Y", "Среднее R", "Среднее G", "Среднее B", "Norm R (G=1)", "Norm B (G=1)", "Стд.Откл R", "Стд.Откл G", "Стд.Откл B"]
                
                # Write Headers
                for col_num, header in enumerate(headers):
                    worksheet.write(0, col_num, header, header_format)
                
                # Write Data
                for row_num, r in enumerate(results, 1):
                    avg_g = r['avg_g']
                    norm_r = r['avg_r'] / avg_g if avg_g != 0 else 0
                    norm_b = r['avg_b'] / avg_g if avg_g != 0 else 0
                    
                    data_row = [
                        r['x'], r['y'],
                        r['avg_r'], r['avg_g'], r['avg_b'],
                        norm_r, norm_b,
                        r['std_r'], r['std_g'], r['std_b']
                    ]
                    
                    for col_num, data in enumerate(data_row):
                        # Apply number format to floats (columns 2 to 9)
                        if 2 <= col_num <= 9:
                            worksheet.write_number(row_num, col_num, data, num_format)
                        else:
                            worksheet.write(row_num, col_num, data)

                # Auto-fit columns
                for i, header in enumerate(headers):
                    worksheet.set_column(i, i, max(len(header) + 2, 10)) # Simple auto-width based on header + padding
                
                # Create and insert annotated image
                try:
                     import tempfile
                     temp_dir = tempfile.gettempdir()
                     temp_img_path = os.path.join(temp_dir, "grid_map_temp.png")
                     
                     if create_annotated_image(self.viewer.image_path, results, cell_size, temp_img_path):
                         map_sheet = workbook.add_worksheet("Карта")
                         map_sheet.insert_image('A1', temp_img_path)
                except Exception as img_err:
                     print(f"Failed to add image map: {img_err}")
                
                workbook.close()

                # Clean up temp file
                if os.path.exists(temp_img_path):
                    try:
                        os.remove(temp_img_path)
                    except: pass

            else:
                # CSV Fallback
                with open(file_name, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';') # Use semicolon for Excel in many regions
                    
                    # Headers
                    writer.writerow(["X", "Y", "Среднее R", "Среднее G", "Среднее B", "Norm R (G=1)", "Norm B (G=1)", "Стд.Откл R", "Стд.Откл G", "Стд.Откл B"])
                    
                    for r in results:
                        # Calculate normalized values
                        avg_g = r['avg_g']
                        norm_r = r['avg_r'] / avg_g if avg_g != 0 else 0
                        norm_b = r['avg_b'] / avg_g if avg_g != 0 else 0

                        writer.writerow([
                            r['x'], r['y'],
                            f"{r['avg_r']:.2f}".replace('.', ','), 
                            f"{r['avg_g']:.2f}".replace('.', ','), 
                            f"{r['avg_b']:.2f}".replace('.', ','),
                            f"{norm_r:.2f}".replace('.', ','),
                            f"{norm_b:.2f}".replace('.', ','),
                            f"{r['std_r']:.2f}".replace('.', ','), 
                            f"{r['std_g']:.2f}".replace('.', ','), 
                            f"{r['std_b']:.2f}".replace('.', ',')
                        ])
            
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Успех", f"Данные сетки ({len(results)} ячеек) сохранены в {file_name}")
            
        except ImportError:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Ошибка", "Для сохранения в Excel требуется библиотека xlsxwriter.\nУстановите её командой: pip install xlsxwriter")
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте:\n{e}")
