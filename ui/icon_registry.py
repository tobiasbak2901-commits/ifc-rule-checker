from __future__ import annotations

from typing import Dict

from PySide6 import QtCore
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


class ToolIconRegistry:
    """High-contrast, fat icons intended for 56px tool buttons."""

    def __init__(self, render_size: int = 96):
        self._render_size = int(max(48, render_size))
        self._cache: Dict[str, QIcon] = {}

    def icon(self, tool_id: str) -> QIcon:
        key = str(tool_id or "").strip().lower()
        if key in self._cache:
            return self._cache[key]
        pixmap = QPixmap(self._render_size, self._render_size)
        pixmap.fill(QtCore.Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.scale(self._render_size / 24.0, self._render_size / 24.0)
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(2.8)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)

        drawer = getattr(self, f"_draw_{key}", None)
        if callable(drawer):
            drawer(p)
        else:
            self._draw_default(p)

        p.end()
        icon = QIcon(pixmap)
        self._cache[key] = icon
        return icon

    def _draw_default(self, p: QPainter):
        p.drawRoundedRect(5, 5, 14, 14, 3, 3)

    def _draw_orbit(self, p: QPainter):
        p.drawArc(3, 3, 18, 18, 22 * 16, 308 * 16)
        head = QPolygonF([QtCore.QPointF(18.7, 4.4), QtCore.QPointF(20.8, 7.8), QtCore.QPointF(17.0, 7.3)])
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QtCore.Qt.NoPen)
        p.drawPolygon(head)

    def _draw_pan(self, p: QPainter):
        p.drawLine(12, 4, 12, 20)
        p.drawLine(4, 12, 20, 12)
        p.drawLine(12, 4, 10, 6)
        p.drawLine(12, 4, 14, 6)
        p.drawLine(12, 20, 10, 18)
        p.drawLine(12, 20, 14, 18)
        p.drawLine(4, 12, 6, 10)
        p.drawLine(4, 12, 6, 14)
        p.drawLine(20, 12, 18, 10)
        p.drawLine(20, 12, 18, 14)

    def _draw_zoom(self, p: QPainter):
        p.drawEllipse(4.5, 4.5, 10.0, 10.0)
        p.drawLine(12.2, 12.2, 19.5, 19.5)
        p.drawLine(9.5, 9.5, 9.5, 13.0)
        p.drawLine(7.8, 11.2, 11.2, 11.2)

    def _draw_measure_select(self, p: QPainter):
        poly = QPolygonF(
            [
                QtCore.QPointF(5.0, 3.5),
                QtCore.QPointF(5.0, 20.5),
                QtCore.QPointF(9.2, 16.5),
                QtCore.QPointF(12.2, 21.0),
                QtCore.QPointF(14.8, 19.6),
                QtCore.QPointF(11.8, 15.2),
                QtCore.QPointF(17.8, 15.0),
            ]
        )
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawPolygon(poly)

    def _draw_measure_distance(self, p: QPainter):
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(3.0, 8.0, 18.0, 8.0, 2.0, 2.0)
        p.save()
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        cut_pen = QPen(QtCore.Qt.transparent)
        cut_pen.setWidthF(1.3)
        p.setPen(cut_pen)
        for x, h in ((6, 3.2), (8.5, 2.3), (11, 3.2), (13.5, 2.3), (16, 3.2), (18.5, 2.3)):
            p.drawLine(QtCore.QPointF(x, 9.3), QtCore.QPointF(x, 9.3 + h))
        p.restore()

    def _draw_measure_clearance(self, p: QPainter):
        p.drawLine(5, 6, 5, 18)
        p.drawLine(19, 6, 19, 18)
        p.drawLine(8, 12, 16, 12)
        p.drawLine(8, 12, 9.8, 10.4)
        p.drawLine(8, 12, 9.8, 13.6)
        p.drawLine(16, 12, 14.2, 10.4)
        p.drawLine(16, 12, 14.2, 13.6)

    def _draw_measure_min(self, p: QPainter):
        p.drawLine(6, 6, 6, 18)
        p.drawLine(18, 8, 18, 17)
        p.drawLine(6, 15, 18, 10)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(4.5, 13.5, 3.0, 3.0)
        p.drawEllipse(16.5, 8.5, 3.0, 3.0)

    def _draw_section_box(self, p: QPainter):
        p.drawRect(5, 7, 10, 10)
        p.drawRect(9, 3, 10, 10)
        p.drawLine(5, 7, 9, 3)
        p.drawLine(15, 7, 19, 3)
        p.drawLine(5, 17, 9, 13)
        p.drawLine(15, 17, 19, 13)

    def _draw_section_fit_selection(self, p: QPainter):
        self._draw_section_box(p)
        p.drawLine(8, 8, 11, 8)
        p.drawLine(8, 8, 8, 11)
        p.drawLine(16, 16, 13, 16)
        p.drawLine(16, 16, 16, 13)

    def _draw_section_fit_issue(self, p: QPainter):
        self._draw_section_box(p)
        p.drawEllipse(18.1, 15.6, 2.2, 2.2)

    def _draw_section_reset(self, p: QPainter):
        p.drawRect(6, 6, 12, 12)
        p.drawArc(3.5, 3.5, 17.0, 17.0, 182 * 16, 206 * 16)
        p.drawLine(6.1, 4.9, 7.8, 3.9)
        p.drawLine(6.1, 4.9, 7.1, 6.6)

    def _draw_focus(self, p: QPainter):
        p.drawRect(5, 5, 14, 14)
        p.drawLine(12, 7, 12, 17)
        p.drawLine(7, 12, 17, 12)

    def _draw_isolate(self, p: QPainter):
        eye = QPainterPath()
        eye.moveTo(3.2, 12.0)
        eye.quadTo(12.0, 5.0, 20.8, 12.0)
        eye.quadTo(12.0, 19.0, 3.2, 12.0)
        p.drawPath(eye)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(10.0, 10.0, 4.0, 4.0)

    def _draw_show_all(self, p: QPainter):
        p.drawRect(4.5, 4.5, 6, 6)
        p.drawRect(13.5, 4.5, 6, 6)
        p.drawRect(4.5, 13.5, 6, 6)
        p.drawRect(13.5, 13.5, 6, 6)

    def _draw_transparency(self, p: QPainter):
        p.drawRoundedRect(4.5, 6.0, 15.0, 12.0, 2.0, 2.0)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRect(12.0, 7.0, 6.5, 10.0)

    def _draw_detect_clashes(self, p: QPainter):
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QtCore.Qt.NoPen)
        tri = QPolygonF([QtCore.QPointF(12, 3), QtCore.QPointF(21, 20), QtCore.QPointF(3, 20)])
        p.drawPolygon(tri)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        clear_pen = QPen(QtCore.Qt.transparent)
        clear_pen.setWidthF(1.8)
        p.setPen(clear_pen)
        p.drawLine(12, 8, 12, 14)
        p.drawPoint(12, 17)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

    def _draw_generate_issues(self, p: QPainter):
        p.setPen(QPen(QColor("#FFFFFF"), 2.8, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        for y in (7, 12, 17):
            p.drawLine(7.2, y, 20.0, y)
            p.setBrush(QColor("#FFFFFF"))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(3.2, y - 1.8, 3.6, 3.6)
            p.setPen(QPen(QColor("#FFFFFF"), 2.8, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

    def _draw_preview_fix(self, p: QPainter):
        p.drawRect(4.5, 9.5, 7.5, 7.5)
        p.drawRect(12.0, 7.0, 7.5, 7.5)
        p.drawLine(8.0, 20.0, 16.5, 20.0)
        p.drawLine(16.5, 20.0, 14.6, 18.4)
        p.drawLine(16.5, 20.0, 14.6, 21.6)

    def _draw_generate_fixes(self, p: QPainter):
        p.drawEllipse(4.0, 4.0, 7.0, 7.0)
        p.drawLine(9.0, 9.0, 18.5, 18.5)
        p.drawLine(15.8, 18.2, 18.8, 15.3)
        p.drawLine(15.8, 18.2, 18.8, 21.1)

    def _draw_help(self, p: QPainter):
        p.drawEllipse(5, 3.8, 14, 14)
        p.drawArc(8.5, 7.0, 7.0, 7.0, 30 * 16, 235 * 16)
        p.drawLine(12, 12.8, 12, 15.8)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(10.8, 17.6, 2.4, 2.4)
