from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsPixmapItem, QGraphicsOpacityEffect, QGraphicsItem, QGraphicsLineItem
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QCursor, QPainter
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QLineF


class ResizableRectItem(QGraphicsRectItem):
    # Target size in screen pixels
    screen_handle_size = 14 

    def __init__(self, rect=QRectF(0, 0, 100, 100), parent=None):
        super().__init__(rect, parent)
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        pen = QPen(Qt.GlobalColor.red, 2)
        pen.setCosmetic(True)
        self.setPen(pen)
        
        self.setBrush(QBrush(QColor(255, 0, 0, 50)))
        self.setAcceptHoverEvents(True)
        self.current_handle = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None

    def get_handle_size(self):
        """Calculate handle size in scene coordinates to maintain constant screen size"""
        if not self.scene() or not self.scene().views():
             return 20.0 # Fallback
        
        view = self.scene().views()[0]
        # Get scale from transform (m11 is x scale)
        scale = view.transform().m11()
        
        if scale <= 0: return 20.0
        
        # We want screen_handle_size pixels on screen
        # size_scene * scale = size_screen
        # size_scene = size_screen / scale
        return self.screen_handle_size / scale

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

            if new_w < 30: new_w = 30
            if new_h < 30: new_h = 30
            
            self.setRect(new_x, new_y, new_w, new_h)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.current_handle = None
        super().mouseReleaseEvent(event)

    def get_handle_at(self, pos):
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.get_handle_size() # Dynamic size
        
        # Check corners (with some tolerance maybe? no, s is already screen size adjusted)
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
        pen = QPen(Qt.GlobalColor.blue, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.get_handle_size()
        
        handles = [
            (x, y), (x+w-s, y), (x, y+h-s), (x+w-s, y+h-s), # Corners
            (x+w/2-s/2, y), (x+w/2-s/2, y+h-s), (x, y+h/2-s/2), (x+w-s, y+h/2-s/2) # Sides
        ]
        
        for hx, hy in handles:
            painter.drawRect(QRectF(hx, hy, s, s))

class LineItem(QGraphicsLineItem):
    screen_handle_size = 14

    def __init__(self, line, parent=None):
        super().__init__(line, parent)
        self.setFlags(QGraphicsLineItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsLineItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        pen = QPen(Qt.GlobalColor.green, 2)
        pen.setCosmetic(True)
        self.setPen(pen)
        
        self.setAcceptHoverEvents(True)
        self.current_handle = None
        self.mouse_press_pos = None
        self.mouse_press_line = None

    def get_handle_size(self):
        if not self.scene() or not self.scene().views(): return 20.0
        view = self.scene().views()[0]
        scale = view.transform().m11()
        if scale <= 0: return 20.0
        return self.screen_handle_size / scale

    def hoverMoveEvent(self, event):
        pos = event.pos()
        handle = self.get_handle_at(pos)
        if handle:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor)) # Move whole line
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.current_handle = self.get_handle_at(event.pos())
        if self.current_handle:
            self.mouse_press_pos = event.pos()
            self.mouse_press_line = self.line()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_handle:
            pos = event.pos()
            line = self.line()
            
            p1 = line.p1()
            p2 = line.p2()
            
            # Map pos to scene coordinates?
            # event.pos() is in item coordinates. 
            # Our line is defined in item coordinates.
            # But wait, QGraphicsLineItem draws from p1 to p2. 
            # Usually we set pos to (0,0) and define line relative to that.
            
            if self.current_handle == 'p1':
                p1 = pos
            elif self.current_handle == 'p2':
                p2 = pos
            
            self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.current_handle = None
        super().mouseReleaseEvent(event)

    def get_handle_at(self, pos):
        line = self.line()
        s = self.get_handle_size()
        
        p1 = line.p1()
        p2 = line.p2()
        
        if QRectF(p1.x() - s/2, p1.y() - s/2, s, s).contains(pos): return 'p1'
        if QRectF(p2.x() - s/2, p2.y() - s/2, s, s).contains(pos): return 'p2'
        
        return None

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        # Draw handles
        s = self.get_handle_size()
        line = self.line()
        
        pen = QPen(Qt.GlobalColor.green, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        
        p1 = line.p1()
        p2 = line.p2()
        
        painter.drawEllipse(p1, s/2, s/2)
        painter.drawEllipse(p2, s/2, s/2)

class GridOverlayItem(QGraphicsItem):
    def __init__(self, rect, cell_size, callback, parent=None):
        super().__init__(parent)
        self.rect_area = rect
        self.cell_size = cell_size
        self.callback = callback
        self.setZValue(80) # Grid below selection (100) but above overlay (50)
        # Accept hover events to show highlight? Maybe later.
        
    def boundingRect(self):
        return self.rect_area
    
    def paint(self, painter, option, widget=None):
        # Draw grid lines
        pen = QPen(QColor(0, 255, 255, 100), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        
        l, t, w, h = self.rect_area.x(), self.rect_area.y(), self.rect_area.width(), self.rect_area.height()
        
        # Vertical lines
        x = l
        while x <= l + w:
            painter.drawLine(QPointF(x, t), QPointF(x, t + h))
            x += self.cell_size
            
        # Horizontal lines
        y = t
        while y <= t + h:
            painter.drawLine(QPointF(l, y), QPointF(l + w, y))
            y += self.cell_size

    def mousePressEvent(self, event):
        pos = event.pos()
        if self.rect_area.contains(pos):
            # Calculate cell rect
            rel_x = pos.x() - self.rect_area.x()
            rel_y = pos.y() - self.rect_area.y()
            
            col = int(rel_x // self.cell_size)
            row = int(rel_y // self.cell_size)
            
            cell_x = self.rect_area.x() + col * self.cell_size
            cell_y = self.rect_area.y() + row * self.cell_size
            
            # Ensure we don't go out of bounds (shouldn't happen with contains check but good to clamp)
            # Actually, standard grid logic is fine.
            
            cell_rect = QRectF(cell_x, cell_y, self.cell_size, self.cell_size)
            
            # intersect with image rect to handle edges? 
            # self.rect_area IS the image rect usually.
            cell_rect = cell_rect.intersected(self.rect_area)
            
            if self.callback:
                self.callback(cell_rect)
                
            event.accept()


class ImageViewer(QGraphicsView):
    grid_clicked = pyqtSignal(QRectF) 
    item_changed = pyqtSignal() # Signal when roi changes (release)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.image_item = None
        self.overlay_item = None
        self.rect_item = None
        self.line_item = None
        
        self.pixmap = None
        self.overlay_pixmap = None
        self.image_path = None
        self.overlay_path = None
        
        self.grid_item = None
        self.grid_cell_size = 50
        self.is_grid_enabled = False
        
        self.current_tool = 'rect' # 'rect' or 'line'
        self.is_drawing_line = False
        
        # Enable mouse tracking
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor("#222")))

    def set_tool(self, tool_mode):
        self.current_tool = tool_mode
        self.update_tool_visibility()
        
        if tool_mode == 'line':
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            
        self.item_changed.emit()

    def update_tool_visibility(self):
        if self.rect_item:
            self.rect_item.setVisible(self.current_tool == 'rect')
        # Line item is visible only if we have one, but we might hide it if it's invalid?
        # Actually, let's keep it visible if it exists, but maybe we want to hide it if we are switching to rect?
        # Yes, standard behavior:
        if self.line_item:
            self.line_item.setVisible(self.current_tool == 'line')

    def mousePressEvent(self, event):
        # Allow items to handle event first (e.g. handles)
        super().mousePressEvent(event)
        
        if event.isAccepted(): return

        if self.current_tool == 'line' and self.image_item:
            # Start drawing line
            sp = self.mapToScene(event.pos())
            # Ensure coordinates are within image? Or allow drawing outside?
            # Better to clamp to image rect?
            # For now, raw coords.
            
            if not self.line_item:
                self.line_item = LineItem(QLineF(sp, sp))
                self.line_item.setZValue(100)
                self.scene.addItem(self.line_item)
            else:
                self.line_item.setLine(QLineF(sp, sp))
                self.line_item.setPos(0, 0) # Reset pos since we set absolute line coords
                self.line_item.setVisible(True)
            
            self.is_drawing_line = True
            event.accept()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        if self.is_drawing_line and self.line_item:
            sp = self.mapToScene(event.pos())
            line = self.line_item.line()
            line.setP2(sp)
            self.line_item.setLine(line)
            # Optional: dynamic update of profile while dragging? 
            # Might be heavy, let's wait for release or timer.
            # self.item_changed.emit() 

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        
        if self.is_drawing_line:
            self.is_drawing_line = False
            self.item_changed.emit()

    def get_line_coords(self):
        if not self.line_item or not self.image_path: return None
        
        # Line is relative to its pos.
        line = self.line_item.line()
        pos = self.line_item.pos()
        
        p1 = line.p1() + pos
        p2 = line.p2() + pos
        
        return (int(p1.x()), int(p1.y()), int(p2.x()), int(p2.y()))

    def get_overlay_info(self):
        if self.overlay_item and self.overlay_path:
            return self.overlay_path, self.overlay_item.pos()
        return None

    def load_image(self, path):
        self.image_path = path
        self.pixmap = QPixmap(path)
        
        # Save current overlay settings
        current_overlay_pixmap = self.overlay_pixmap
        current_overlay_opacity = 1.0
        if self.overlay_item:
            current_overlay_opacity = self.overlay_item.opacity()

        # Save current rect settings
        current_rect = None
        if self.rect_item:
            current_rect = self.rect_item.rect()
            current_pos = self.rect_item.pos()
            
        # Save current line settings
        current_line = None
        if self.line_item:
            current_line = self.line_item.line()
            current_line_pos = self.line_item.pos()

        self.scene.clear()
        self.image_item = self.scene.addPixmap(self.pixmap)
        self.image_item.setZValue(0)
        
        self.setSceneRect(QRectF(self.pixmap.rect()))
        
        # Restore overlay if it existed
        self.overlay_item = None
        if current_overlay_pixmap:
            self.overlay_pixmap = current_overlay_pixmap
            self.overlay_item = QGraphicsPixmapItem(self.overlay_pixmap)
            self.overlay_item.setOpacity(current_overlay_opacity)
            self.overlay_item.setZValue(50)
            self.scene.addItem(self.overlay_item)
            
            # Center overlay
            base_center = self.pixmap.rect().center()
            overlay_rect = self.overlay_pixmap.rect()
            x = base_center.x() - overlay_rect.width() / 2
            y = base_center.y() - overlay_rect.height() / 2
            self.overlay_item.setPos(x, y)

        # Restore or create selection rectangle
        if current_rect:
            self.rect_item = ResizableRectItem(current_rect)
            self.rect_item.setPos(current_pos)
        else:
            self.rect_item = ResizableRectItem(QRectF(0, 0, 100, 100))
            center = self.pixmap.rect().center()
            self.rect_item.setPos(center.x() - 50, center.y() - 50)
            
        self.rect_item.setZValue(100) 
        self.scene.addItem(self.rect_item)
        
        # Restore or create line item
        if current_line:
            self.line_item = LineItem(current_line)
            self.line_item.setPos(current_line_pos)
        else:
            # Default line across middle
            w = self.pixmap.width()
            h = self.pixmap.height()
            self.line_item = LineItem(QLineF(w*0.2, h/2, w*0.8, h/2))
            
        self.line_item.setZValue(100)
        self.scene.addItem(self.line_item)
        
        self.update_tool_visibility() # Apply current tool
        
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # Restore grid if enabled
        if self.is_grid_enabled:
            self.refresh_grid()

    def set_grid(self, enabled, cell_size=None):
        self.is_grid_enabled = enabled
        if cell_size:
            self.grid_cell_size = cell_size
        self.refresh_grid()

    def refresh_grid(self):
        if self.grid_item:
            self.scene.removeItem(self.grid_item)
            self.grid_item = None
            
        if self.is_grid_enabled and self.pixmap:
            rect = QRectF(self.pixmap.rect())
            self.grid_item = GridOverlayItem(rect, self.grid_cell_size, self.on_grid_click)
            self.scene.addItem(self.grid_item)
            
    def on_grid_click(self, cell_rect):
        # We also want to update the red selection rect to match the cell
        if self.rect_item:
            self.rect_item.setRect(cell_rect)
            self.rect_item.setPos(0, 0) # Reset pos because ResizableRectItem uses rect relative to its pos
            # Actually ResizableRectItem usually has pos at top-left of rect if created that way?
            # Let's check ResizableRectItem implementation.
            # It takes a rect in __init__.
            # And we setPos in load_image.
            
            # To set it exactly to cell_rect:
            # We can just set the rect of the item to be (0,0,w,h) and move the item to (x,y)
            self.rect_item.setPos(cell_rect.x(), cell_rect.y())
            self.rect_item.setRect(0, 0, cell_rect.width(), cell_rect.height())

        self.grid_clicked.emit(cell_rect)

    def set_overlay(self, path):
        if not path:
            if self.overlay_item:
                self.scene.removeItem(self.overlay_item)
                self.overlay_item = None
                self.overlay_path = None
            return

        self.overlay_path = path
        self.overlay_pixmap = QPixmap(path)
        if self.overlay_item:
            self.overlay_item.setPixmap(self.overlay_pixmap)
        else:
            self.overlay_item = QGraphicsPixmapItem(self.overlay_pixmap)
            self.scene.addItem(self.overlay_item)
        
        self.overlay_item.setZValue(50) # Between base (0) and rect (100)
        
        # Center overlay on base image
        if self.pixmap:
            base_center = self.pixmap.rect().center()
            overlay_rect = self.overlay_pixmap.rect()
            
            # We want to center the overlay. 
            # Position of item is top-left.
            # x = base_center.x - overlay_width/2
            # y = base_center.y - overlay_height/2
            
            x = base_center.x() - overlay_rect.width() / 2
            y = base_center.y() - overlay_rect.height() / 2
            
            self.overlay_item.setPos(x, y)

    def set_overlay_opacity(self, opacity):
        if self.overlay_item:
            self.overlay_item.setOpacity(opacity)

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
