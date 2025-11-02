"""Color utilities for nicks."""


def nick_to_rgb(nick: str) -> tuple[float, float, float]:
    """
    Deterministically map a nickname to an RGB tuple (0..1 per channel).
    Uses a hash to pick a hue, then tweaks saturation/value to keep colors readable.
    """
    h = 5381
    for ch in nick.lower():
        h = ((h << 5) + h) + ord(ch)
    hue = (h % 360) / 360.0
    s = 0.55
    v = 0.75

    # Yellow hues can look harsh; dial back saturation/value slightly in that band.
    if 45 / 360.0 <= hue <= 70 / 360.0:
        s = 0.4
        v = 0.7

    i = int(hue * 6)
    f = hue * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i %= 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (r, g, b)
