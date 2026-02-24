from __future__ import annotations

import math
from typing import Tuple


AABB = Tuple[float, float, float, float, float, float]
Point3 = Tuple[float, float, float]


def aabb_from_verts(verts) -> AABB:
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def aabb_expand(aabb: AABB, t: float) -> AABB:
    return (aabb[0] - t, aabb[1] - t, aabb[2] - t, aabb[3] + t, aabb[4] + t, aabb[5] + t)


def aabb_intersects(a: AABB, b: AABB) -> bool:
    return not (
        a[3] < b[0] or a[0] > b[3] or
        a[4] < b[1] or a[1] > b[4] or
        a[5] < b[2] or a[2] > b[5]
    )


def aabb_distance_and_points(a: AABB, b: AABB) -> Tuple[float, Point3, Point3]:
    ax0, ay0, az0, ax1, ay1, az1 = a
    bx0, by0, bz0, bx1, by1, bz1 = b

    # Closest points between two AABBs (distance is 0 when they overlap).
    if ax1 < bx0:
        px = ax1
        qx = bx0
    elif bx1 < ax0:
        px = ax0
        qx = bx1
    else:
        px = qx = max(ax0, bx0)

    if ay1 < by0:
        py = ay1
        qy = by0
    elif by1 < ay0:
        py = ay0
        qy = by1
    else:
        py = qy = max(ay0, by0)

    if az1 < bz0:
        pz = az1
        qz = bz0
    elif bz1 < az0:
        pz = az0
        qz = bz1
    else:
        pz = qz = max(az0, bz0)

    dx = px - qx
    dy = py - qy
    dz = pz - qz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dist, (px, py, pz), (qx, qy, qz)


def normalize(v: Point3) -> Point3:
    x, y, z = v
    mag = math.sqrt(x * x + y * y + z * z)
    if mag == 0:
        return (0.0, 0.0, 0.0)
    return (x / mag, y / mag, z / mag)


def segment_distance_and_points(
    p0: Point3,
    p1: Point3,
    q0: Point3,
    q1: Point3,
) -> Tuple[float, Point3, Point3]:
    # Closest points between two line segments (p0-p1) and (q0-q1).
    ux, uy, uz = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    vx, vy, vz = (q1[0] - q0[0], q1[1] - q0[1], q1[2] - q0[2])
    wx, wy, wz = (p0[0] - q0[0], p0[1] - q0[1], p0[2] - q0[2])

    a = ux * ux + uy * uy + uz * uz
    b = ux * vx + uy * vy + uz * vz
    c = vx * vx + vy * vy + vz * vz
    d = ux * wx + uy * wy + uz * wz
    e = vx * wx + vy * wy + vz * wz
    denom = a * c - b * b
    small = 1e-9

    if a < small and c < small:
        c1 = p0
        c2 = q0
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        dz = c1[2] - c2[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        return dist, c1, c2
    if a < small:
        t = 0.0 if c < small else max(0.0, min(1.0, e / c))
        c1 = p0
        c2 = (q0[0] + t * vx, q0[1] + t * vy, q0[2] + t * vz)
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        dz = c1[2] - c2[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        return dist, c1, c2
    if c < small:
        s = max(0.0, min(1.0, -d / a))
        c1 = (p0[0] + s * ux, p0[1] + s * uy, p0[2] + s * uz)
        c2 = q0
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        dz = c1[2] - c2[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        return dist, c1, c2

    if denom < small:
        s_n = 0.0
        s_d = 1.0
        t_n = e
        t_d = c
    else:
        s_n = (b * e - c * d)
        t_n = (a * e - b * d)
        s_d = denom
        t_d = denom

        if s_n < 0.0:
            s_n = 0.0
            t_n = e
            t_d = c
        elif s_n > s_d:
            s_n = s_d
            t_n = e + b
            t_d = c

    if t_n < 0.0:
        t_n = 0.0
        if -d < 0.0:
            s_n = 0.0
        elif -d > a:
            s_n = s_d
        else:
            s_n = -d
            s_d = a
    elif t_n > t_d:
        t_n = t_d
        if (-d + b) < 0.0:
            s_n = 0.0
        elif (-d + b) > a:
            s_n = s_d
        else:
            s_n = (-d + b)
            s_d = a

    sc = 0.0 if abs(s_n) < small else s_n / s_d
    tc = 0.0 if abs(t_n) < small else t_n / t_d

    c1 = (p0[0] + sc * ux, p0[1] + sc * uy, p0[2] + sc * uz)
    c2 = (q0[0] + tc * vx, q0[1] + tc * vy, q0[2] + tc * vz)

    dx = c1[0] - c2[0]
    dy = c1[1] - c2[1]
    dz = c1[2] - c2[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dist, c1, c2
