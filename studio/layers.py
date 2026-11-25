"""2.5D: render a scene as separate depth layers (transparent PNGs) and composite them with parallax."""
import math, subprocess
import numpy as np, cv2
from scenes import defs, SW, SH

def svg_layer(body, bg=None):
    under = f'<rect width="100%" height="100%" fill="url(#{bg})"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}" height="{SH}" viewBox="0 0 {SW} {SH}">{defs()}'
            f'<g filter="url(#wc)">{under}{body}</g></svg>')

def render_layer(svg_text, png):
    open(png[:-4] + ".svg", "w").write(svg_text)
    subprocess.run(["rsvg-convert", "-w", str(SW), "-h", str(SH), png[:-4] + ".svg", "-o", png], check=True)

MOVES = {
    "push":  (1.00, 1.12, 0, 0, 0, 0),
    "pull":  (1.12, 1.00, 0, 0, 0, 0),
    "up":    (1.06, 1.12, 0, 0, 0.04, -0.04),
    "down":  (1.06, 1.12, 0, 0, -0.04, 0.04),
    "left":  (1.06, 1.08, 0.05, -0.05, 0, 0),
    "right": (1.06, 1.08, -0.05, 0.05, 0, 0),
}

def ease(t): return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0), 1))

def layer_matrix(e, move, depth, W, H, w, h, cam=None):
    z0, z1, dx0, dx1, dy0, dy1 = MOVES[move]
    if cam:  # shot size / framing: {"zoom":[z0,z1], "focus":[fx,fy] (0..1 of the scene)}
        if "zoom" in cam: z0, z1 = cam["zoom"]
        if "focus" in cam:
            fx, fy = cam["focus"]
            dx0 += fx - 0.5; dx1 += fx - 0.5; dy0 += fy - 0.5; dy1 += fy - 0.5
    base = max(W / w, H / h)
    z = base * (1 + ((z0 + (z1 - z0) * e) - 1) * depth)
    cx = w / 2 + (dx0 + (dx1 - dx0) * e) * w * depth
    cy = h / 2 + (dy0 + (dy1 - dy0) * e) * h * depth
    return np.float32([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]])

def composite(layers, t, move, W, H, cam=None):
    """layers: list of (rgba float32 array, depth). First layer must be opaque."""
    e = ease(t)
    out = None
    for img, depth in layers:
        h, w = img.shape[:2]
        M = layer_matrix(e, move, depth, W, H, w, h, cam)
        warped = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        if out is None:
            out = warped[..., :3].copy()
            if (warped[..., 3] < 250).any():  # fill gaps of the opaque bottom layer
                out = cv2.warpAffine(img[..., :3], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            continue
        a = warped[..., 3:4] / 255.0
        out = out * (1 - a) + warped[..., :3] * a
    return out
