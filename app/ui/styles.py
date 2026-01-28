# --- Dark Theme Stylesheet ---
DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
}
QGroupBox {
    border: 1px solid #555;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #aaa;
}
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px 12px;
    color: #fff;
}
QPushButton:hover {
    background-color: #484b4d;
    border-color: #666;
}
QPushButton:pressed {
    background-color: #252526;
}
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #333;
    border: 1px solid #444;
    selection-background-color: #264f78;
}
QHeaderView::section {
    background-color: #333;
    padding: 4px;
    border: 1px solid #444;
    color: #ccc;
}
QLabel {
    color: #e0e0e0;
}
QSplitter::handle {
    background-color: #444;
}
"""
