"""Shared street camera: every object (road, sidewalks, buildings, trees, cars, people) is placed in metres and projected
with the SAME camera, so cars drive straight along the road and all lines meet at one vanishing point."""
import random
from scenes import INK, SW, SH, poly, man, woman
from car3d import car3d

class Cam:
    def __init__(self, f=1100, h=1.7, vx=SW / 2, vy=900):
        self.f, self.h, self.vx, self.vy = f, h, vx, vy
    def project(self, X, Y, Z):
        Z = max(Z, 0.3)
        return (self.vx + self.f * X / Z, self.vy + self.f * (self.h - Y) / Z)
    def scale(self, Z):  # pixels per metre at depth Z
        return self.f / max(Z, 0.3)

def quad(cam, pts, fill, sw=1.2, op=1):
    return poly([cam.project(*p) for p in pts], fill, sw=sw, op=op)

def street3d(cam, road=3.6, walk=2.4, z0=1.0, z1=400, seed=1, bcols=("#ebe4d6", "#e2d8c6", "#d8cdb9"), trees=True):
    r = random.Random(seed); g = ""
    g += quad(cam, [(-60, 0, z1), (60, 0, z1), (60, 0, z0), (-60, 0, z0)], "#ddd6c9", sw=0)          # ground
    g += quad(cam, [(-road, 0, z1), (road, 0, z1), (road, 0, z0), (-road, 0, z0)], "#c9c3b8")      # road
    for sgn in (-1, 1):  # kerbs
        g += quad(cam, [(sgn * road, 0, z1), (sgn * (road + .15), .12, z1), (sgn * (road + .15), .12, z0), (sgn * road, 0, z0)], "#bdb6aa", sw=0.8)
    for k in range(40):  # dashed centre line
        za, zb = 3 + k * 6, 3 + k * 6 + 3
        g += quad(cam, [(-.07, 0.01, zb), (.07, 0.01, zb), (.07, 0.01, za), (-.07, 0.01, za)], "#f1e6b8", sw=0)
    bx = road + walk + .15
    for sgn in (-1, 1):  # building rows (fronts facing the street)
        z = 2.0
        while z < 160:
            d = r.uniform(9, 14); hgt = r.uniform(12, 18); col = r.choice(bcols)
            g += quad(cam, [(sgn * bx, 0, z + d), (sgn * bx, hgt, z + d), (sgn * bx, hgt, z), (sgn * bx, 0, z)], col, sw=1.1)
            for fl in range(1, int(hgt / 3)):
                for wi in range(int(d / 2.6)):
                    za, zb = z + .6 + wi * 2.6, z + .6 + wi * 2.6 + 1.2
                    ya, yb = fl * 3 - .1, fl * 3 + 1.4
                    g += quad(cam, [(sgn * bx, ya, zb), (sgn * bx, yb, zb), (sgn * bx, yb, za), (sgn * bx, ya, za)], "#93a7b8", sw=0.6)
            z += d
    return g

def tree3d(cam, X, Z, hgt=7.0, seed=0):
    from kit2 import tree
    x, y = cam.project(X, 0, Z); s = cam.scale(Z) * hgt / 230
    return tree(x, y, s, seed=seed)

def car_on_road(cam, X, Z, heading=0, **kw):
    """Car standing on the road at lateral X (m, negative = left lane), depth Z; heading 0 = facing the camera."""
    return car3d(0, 0, 1.0, 0, 1, world=(cam, X, Z, heading), **kw)

def person3d(cam, X, Z, kind="man", **kw):
    x, y = cam.project(X, 0, Z); s = cam.scale(Z) * 1.75 / 300
    return man(x, y, s, **kw) if kind == "man" else woman(x, y, s)
