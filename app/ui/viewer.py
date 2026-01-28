from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QCursor
from PyQt6.QtCore import Qt, QRectF

class ResizableRectItem(QGraphicsRectItem):
    handle_size = 8

    def __init__(self, rect=QRectF(0, 0, 100, 100), parent=None):
        super().__init__(rect, parent)
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPen(QPen(Qt.GlobalColor.red, 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 50)))
        self.setAcceptHoverEvents(True)
        self.current_handle = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None

    def hoverMoveEvent(self, event):
        pos = event.pos()
        handle = self.get_handle_at(pos)
        cursor = Qt.CursorShape.ArrowCursor
        if handle in ['top_left', 'bottom_right']:
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif handle in ['top_right', 'bottom_left']:
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif handle in ['top', 'bottom']:
            cursor = Qt.CursorShape.SizeVerCursor
        elif handle in ['left', 'right']:
            cursor = Qt.CursorShape.SizeHorCursor
        elif handle is None:
            cursor = Qt.CursorShape.SizeAllCursor
        self.setCursor(QCursor(cursor))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.current_handle = self.get_handle_at(event.pos())
        if self.current_handle:
            self.mouse_press_pos = event.pos()
            self.mouse_press_rect = self.rect()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_handle:
            rect = self.mouse_press_rect
            pos = event.pos()
            diff = pos - self.mouse_press_pos
            
            new_x, new_y, new_w, new_h = rect.x(), rect.y(), rect.width(), rect.height()

            if 'left' in self.current_handle:
                new_x += diff.x()
                new_w -= diff.x()
            if 'right' in self.current_handle:
                new_w += diff.x()
            if 'top' in self.current_handle:
                new_y += diff.y()
                new_h -= diff.y()
            if 'bottom' in self.current_handle:
                new_h += diff.y()

            if new_w < 10: new_w = 10
            if new_h < 10: new_h = 10
            
            self.setRect(new_x, new_y, new_w, new_h)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.current_handle = None
        super().mouseReleaseEvent(event)

    def get_handle_at(self, pos):
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.handle_size
        
        # Check corners
        if QRectF(x, y, s, s).contains(pos): return 'top_left'
        if QRectF(x+w-s, y, s, s).contains(pos): return 'top_right'
        if QRectF(x, y+h-s, s, s).contains(pos): return 'bottom_left'
        if QRectF(x+w-s, y+h-s, s, s).contains(pos): return 'bottom_right'
        
        # Check sides
        if QRectF(x, y, w, s).contains(pos): return 'top'
        if QRectF(x, y+h-s, w, s).contains(pos): return 'bottom'
        if QRectF(x, y, s, h).contains(pos): return 'left'
        if QRectF(x+w-s, y, s, h).contains(pos): return 'right'
        
        return None
        
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        # Draw handles
        painter.setPen(QPen(Qt.GlobalColor.blue, 1))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.handle_size
        
        handles = [
            (x, y), (x+w-s, y), (x, y+h-s), (x+w-s, y+h-s), # Corners
            (x+w/2-s/2, y), (x+w/2-s/2, y+h-s), (x, y+h/2-s/2), (x+w-s, y+h/2-s/2) # Sides
        ]
        
        for hx, hy in handles:
            painter.drawRect(QRectF(hx, hy, s, s))

class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.image_item = None
        self.rect_item = None
        self.pixmap = None
        self.image_path = None
        
        # Enable mouse tracking for rubber band or custom selection
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor("#222")))

    def load_image(self, path):
        self.image_path = path
        self.pixmap = QPixmap(path)
        self.scene.clear()
        self.image_item = self.scene.addPixmap(self.pixmap)
        self.setSceneRect(QRectF(self.pixmap.rect()))
        
        # Add a default selection rectangle
        self.rect_item = ResizableRectItem(QRectF(0, 0, 100, 100))
        self.scene.addItem(self.rect_item)
        
        # Center the rect
        center = self.pixmap.rect().center()
        self.rect_item.setPos(center.x() - 50, center.y() - 50)
        
        # Fit to view initially
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        # Save the scene pos
        old_pos = self.mapToScene(event.position().toPoint())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        
        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())

        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def get_selection_rect(self):
        if not self.image_path or not self.rect_item:
            return None

        # Get rectangle coordinates relative to the image
        rect_scene_pos = self.rect_item.scenePos()
        rect_rect = self.rect_item.rect()
        
        x = int(rect_scene_pos.x() + rect_rect.x())
        y = int(rect_scene_pos.y() + rect_rect.y())
        w = int(rect_rect.width())
        h = int(rect_rect.height())
        
        return (x, y, w, h)
