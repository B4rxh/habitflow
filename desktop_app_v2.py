import math
import random
import sqlite3
import time
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from plyer import notification
except ImportError:
    notification = None

WATER_GOAL = 8
SLEEP_GOAL = 8.0
FOCUS_GOAL = 120
STUDY_GOAL = 180
FIT_GOAL = 30
WATER_EVERY = dt.timedelta(hours=2)
WATER_REPING = dt.timedelta(minutes=30)
AWAKE_FROM = 7
AWAKE_UNTIL = 22
BEDTIME_REMINDER = "22:30"
CHECK_EVERY_MS = 20000
PREFER_NATIVE = True

BG = "#0d1020"
PANEL = "#141830"
CARD = "#1b2040"
HOVER = "#242b55"
TRACK = "#323a70"
TEXT = "#eef0ff"
MUTED = "#8f96c0"
ACCENT = "#8b8dff"
GREEN = "#4ade80"
BLUE = "#38bdf8"
AMBER = "#fbbf24"
PINK = "#f472b6"
ROSE = "#fb7185"
INK = "#0b0e1c"
FONT = "Segoe UI"

SCHEMA = """
create table if not exists water (
    id integer primary key autoincrement,
    day text,
    logged_at text
);
create table if not exists tasks (
    id integer primary key autoincrement,
    day text,
    title text,
    at text,
    done integer default 0
);
create table if not exists focus (
    id integer primary key autoincrement,
    day text,
    label text,
    minutes integer
);
create table if not exists study (
    id integer primary key autoincrement,
    day text,
    subject text,
    minutes integer
);
create table if not exists sleep (
    day text primary key,
    bed text,
    wake text,
    hours real,
    quality integer
);
create table if not exists fitness (
    id integer primary key autoincrement,
    day text,
    activity text,
    minutes integer,
    notes text
);
"""


def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(ra, rb))


def ease_out(t):
    return 1 - (1 - t) ** 3


def parse_time(text):
    try:
        return dt.datetime.strptime(text.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def round_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    return canvas.create_polygon(round_points(x1, y1, x2, y2, r), smooth=True, **kw)


def tween(widget, start, end, duration, step, done=None):
    began = time.time()
    state = {"job": None}

    def frame():
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        t = min(1.0, (time.time() - began) / duration)
        step(start + (end - start) * ease_out(t))
        if t < 1.0:
            state["job"] = widget.after(16, frame)
        elif done:
            done()

    frame()
    return state


class Animated:
    def animate(self, start, end, duration, step, done=None):
        self.stop_animation()
        self._anim = tween(self, start, end, duration, step, done)

    def stop_animation(self):
        state = getattr(self, "_anim", None)
        if state and state["job"]:
            try:
                self.after_cancel(state["job"])
            except tk.TclError:
                pass
        self._anim = None


def confetti(canvas, count=80):
    colors = [ACCENT, GREEN, BLUE, AMBER, PINK, ROSE]
    width = float(canvas.winfo_width() or canvas["width"])
    height = float(canvas.winfo_height() or canvas["height"])
    pieces = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 10)
        size = random.randint(4, 8)
        item = canvas.create_rectangle(
            width / 2, height / 2, width / 2 + size, height / 2 + size,
            fill=random.choice(colors), outline="",
        )
        pieces.append([item, math.cos(angle) * speed, math.sin(angle) * speed - 4])
    began = time.time()

    def frame():
        if time.time() - began > 2.2:
            for piece in pieces:
                canvas.delete(piece[0])
            return
        for piece in pieces:
            piece[2] += 0.35
            piece[1] *= 0.985
            canvas.move(piece[0], piece[1], piece[2])
        canvas.after(16, frame)

    frame()


def add_hover(card, base, lifted):
    state = {"color": base, "tween": None}

    def paint(color):
        state["color"] = color
        card.configure(bg=color)
        for child in card.winfo_children():
            try:
                child.configure(bg=color)
            except tk.TclError:
                pass

    def inside(event):
        widget = card.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget is card:
                return True
            widget = widget.master
        return False

    def blend(target):
        origin = state["color"]
        if state["tween"] and state["tween"]["job"]:
            card.after_cancel(state["tween"]["job"])
        state["tween"] = tween(card, 0, 1, 0.18, lambda t: paint(mix(origin, target, t)))

    def enter(event):
        blend(lifted)

    def leave(event):
        if not inside(event):
            blend(base)

    for widget in [card, *card.winfo_children()]:
        widget.bind("<Enter>", enter, add="+")
        widget.bind("<Leave>", leave, add="+")


class FancyButton(tk.Canvas, Animated):
    def __init__(self, parent, text, command, color=ACCENT, width=140, height=38, bg=PANEL):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=bg, highlightthickness=0, cursor="hand2")
        self.command = command
        self.base = color
        self.lifted = mix(color, "#ffffff", 0.2)
        self.pressed = mix(color, "#000000", 0.22)
        self.current = color
        self.w = width
        self.h = height
        self.shape = round_rect(self, 2, 2, width - 2, height - 2, 12, fill=color, outline="")
        self.create_text(width / 2, height / 2, text=text, fill=INK, font=(FONT, 10, "bold"))
        self.bind("<Enter>", lambda e: self.fade(self.lifted))
        self.bind("<Leave>", lambda e: self.fade(self.base))
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<ButtonRelease-1>", self.release)

    def fade(self, target):
        origin = self.current

        def step(v):
            self.current = mix(origin, target, v)
            self.itemconfigure(self.shape, fill=self.current)

        self.animate(0, 1, 0.18, step)

    def press(self, event):
        self.stop_animation()
        self.current = self.pressed
        self.itemconfigure(self.shape, fill=self.pressed)

    def release(self, event):
        inside = 0 <= event.x <= self.w and 0 <= event.y <= self.h
        self.current = self.lifted if inside else self.base
        self.itemconfigure(self.shape, fill=self.current)
        if inside:
            self.command()


class Ring(tk.Canvas, Animated):
    def __init__(self, parent, size=260, thickness=16, color=ACCENT, bg=PANEL, main_size=40, sub_size=11, percent=False):
        tk.Canvas.__init__(self, parent, width=size, height=size, bg=bg, highlightthickness=0)
        self.size = size
        self.thickness = thickness
        self.color = color
        self.bgc = bg
        self.percent = percent
        self.value = 0.0
        self.cx = self.cy = size / 2
        self.r = size / 2 - thickness / 2 - 12
        r = self.r
        box = (self.cx - r, self.cy - r, self.cx + r, self.cy + r)
        outer = r + thickness / 2 + 5
        self.glow = self.create_oval(self.cx - outer, self.cy - outer, self.cx + outer, self.cy + outer, outline=bg, width=2)
        self.track = self.create_oval(*box, outline=TRACK, width=thickness)
        self.arc = self.create_arc(*box, start=90, extent=0, style="arc", outline=color, width=thickness, state="hidden")
        self.head = self.create_oval(0, 0, 0, 0, fill=color, outline=color, state="hidden")
        self.tail = self.create_oval(0, 0, 0, 0, fill=color, outline=color, state="hidden")
        self.main = self.create_text(self.cx, self.cy - main_size * 0.2, text="", fill=TEXT, font=(FONT, main_size, "bold"))
        self.sub = self.create_text(self.cx, self.cy + main_size * 0.75, text="", fill=MUTED, font=(FONT, sub_size))
        self.draw(0.0)

    def draw(self, value):
        self.value = max(0.0, min(1.0, value))
        v = self.value
        if v <= 0.003:
            for item in (self.arc, self.head, self.tail):
                self.itemconfigure(item, state="hidden")
        else:
            self.itemconfigure(self.arc, state="normal", extent=-359.9 * v)
            angle = 2 * math.pi * v
            hx = self.cx + self.r * math.sin(angle)
            hy = self.cy - self.r * math.cos(angle)
            rad = self.thickness / 2
            self.coords(self.head, hx - rad, hy - rad, hx + rad, hy + rad)
            self.coords(self.tail, self.cx - rad, self.cy - self.r - rad, self.cx + rad, self.cy - self.r + rad)
            self.itemconfigure(self.head, state="normal")
            self.itemconfigure(self.tail, state="normal")
        if self.percent:
            self.itemconfigure(self.main, text=f"{int(round(v * 100))}%")

    def glide(self, target, duration=0.9, replay=False):
        start = 0.0 if replay else self.value
        self.animate(start, target, duration, self.draw)

    def set_color(self, color):
        self.color = color
        self.itemconfigure(self.arc, outline=color)
        self.itemconfigure(self.head, fill=color, outline=color)
        self.itemconfigure(self.tail, fill=color, outline=color)

    def text(self, main=None, sub=None):
        if main is not None:
            self.itemconfigure(self.main, text=main)
        if sub is not None:
            self.itemconfigure(self.sub, text=sub)

    def pulse(self, t):
        self.itemconfigure(self.glow, outline=mix(self.bgc, self.color, 0.1 + 0.45 * t))


class MeterBar(tk.Canvas, Animated):
    def __init__(self, parent, width=200, height=8, color=ACCENT, bg=CARD):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=bg, highlightthickness=0)
        self.w = width
        self.h = height
        self.value = 0.0
        self.track = round_rect(self, 0, 0, width, height, height / 2, fill=TRACK, outline="")
        self.fill = round_rect(self, 0, 0, height, height, height / 2, fill=color, outline="")

    def draw(self, value):
        self.value = max(0.0, min(1.0, value))
        right = max(self.h, self.w * self.value)
        self.coords(self.fill, *round_points(0, 0, right, self.h, self.h / 2))

    def to(self, target, replay=False):
        start = 0.0 if replay else self.value
        self.animate(start, target, 0.9, self.draw)


class CountLabel(tk.Label, Animated):
    def __init__(self, parent, fmt, empty_text=None, **kw):
        tk.Label.__init__(self, parent, **kw)
        self.fmt = fmt
        self.empty_text = empty_text
        self.current = 0.0

    def show(self, value):
        self.current = value
        self.configure(text=self.fmt(value))

    def to(self, target, replay=False):
        if target == 0 and self.empty_text:
            self.stop_animation()
            self.current = 0.0
            self.configure(text=self.empty_text)
            return
        start = 0.0 if replay else self.current
        self.animate(start, target, 0.9, self.show)


class WaterGlass(tk.Canvas, Animated):
    def __init__(self, parent, width=240, height=290, bg=PANEL):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=bg, highlightthickness=0)
        self.level = 0.0
        self.phase = 0.0
        self.top = 24
        self.bottom = height - 16
        self.lt, self.rt = 48, width - 48
        self.lb, self.rb = 74, width - 74
        self.water = self.create_polygon(0, 0, 0, 0, 0, 0, fill=BLUE, outline="", state="hidden")
        self.shine = self.create_line(0, 0, 0, 0, fill=mix(BLUE, "#ffffff", 0.45), width=3, state="hidden")
        self.bubbles = []
        for _ in range(6):
            item = self.create_oval(0, 0, 0, 0, outline=mix(BLUE, "#ffffff", 0.55), width=1, state="hidden")
            self.bubbles.append([item, random.random(), random.random(), random.uniform(0.004, 0.01)])
        self.create_line(
            self.lt, self.top, self.lb, self.bottom, self.rb, self.bottom, self.rt, self.top,
            fill=MUTED, width=4, joinstyle="round", capstyle="round",
        )
        for i in range(1, WATER_GOAL):
            y = self.bottom - (self.bottom - self.top) * i / WATER_GOAL
            left, _ = self.x_bounds(y)
            self.create_line(left + 3, y, left + 14, y, fill=TRACK, width=2)
        self.loop()

    def x_bounds(self, y):
        f = (y - self.top) / (self.bottom - self.top)
        return self.lt + (self.lb - self.lt) * f, self.rt + (self.rb - self.rt) * f

    def set_level(self, target):
        self.animate(self.level, target, 1.1, lambda v: setattr(self, "level", v))

    def loop(self):
        if self.winfo_viewable():
            self.redraw()
        self.after(40, self.loop)

    def redraw(self):
        self.phase += 0.14
        span = self.bottom - self.top
        if self.level <= 0.004:
            for item in [self.water, self.shine] + [b[0] for b in self.bubbles]:
                self.itemconfigure(item, state="hidden")
            return
        surface = self.bottom - span * self.level
        left, right = self.x_bounds(surface)
        amp = 4.5 if self.level < 0.98 else 2.5
        points = []
        steps = 28
        for i in range(steps + 1):
            x = left + (right - left) * i / steps
            y = max(self.top, surface + amp * math.sin(self.phase + i * 0.55))
            points += [x, y]
        points += [self.rb, self.bottom, self.lb, self.bottom]
        self.coords(self.water, *points)
        self.itemconfigure(self.water, state="normal")
        sx = left + 10 + (self.lb - self.lt) * 0.2
        self.coords(self.shine, sx, surface + 14, sx + (self.lb - self.lt) * 0.1, self.bottom - 20)
        self.itemconfigure(self.shine, state="normal")
        for bubble in self.bubbles:
            item, fx, fy, speed = bubble
            bubble[2] = fy - speed
            if bubble[2] < 0:
                bubble[2] = 1.0
                bubble[1] = random.random()
            y = self.bottom - 10 - (self.bottom - surface - 24) * (1 - bubble[2])
            lx, rx = self.x_bounds(y)
            x = lx + 12 + (rx - lx - 24) * bubble[1]
            size = 3 + bubble[1] * 3
            if y < surface + 8:
                self.itemconfigure(item, state="hidden")
            else:
                self.coords(item, x - size, y - size, x + size, y + size)
                self.itemconfigure(item, state="normal")


class BarChart(tk.Canvas, Animated):
    def __init__(self, parent, color=ACCENT, goal=None, goal_text="", fmt=None, height=170, bg=PANEL):
        tk.Canvas.__init__(self, parent, height=height, bg=bg, highlightthickness=0)
        self.color = color
        self.goal = goal
        self.goal_text = goal_text
        self.fmt = fmt or (lambda v: f"{v:g}")
        self.labels = []
        self.values = []
        self.grow = 1.0
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, labels, values):
        self.labels = labels
        self.values = values
        self.animate(0.0, 1.0, 0.9, self.set_grow)

    def set_grow(self, g):
        self.grow = g
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or not self.values:
            return
        left, right, top, bottom = 18, w - 18, 26, h - 28
        peak = max(max(self.values), self.goal or 0, 1) * 1.1
        n = len(self.values)
        slot = (right - left) / n
        bar_w = slot * 0.46
        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            cx = left + slot * (i + 0.5)
            is_today = i == n - 1
            color = self.color if is_today else mix(self.color, PANEL, 0.55)
            bh = (bottom - top) * value / peak * self.grow
            if bh >= 3:
                radius = min(9, bar_w / 2, bh / 2)
                round_rect(self, cx - bar_w / 2, bottom - bh, cx + bar_w / 2, bottom, radius, fill=color, outline="")
            else:
                self.create_line(cx - bar_w / 2, bottom - 1, cx + bar_w / 2, bottom - 1, fill=TRACK, width=2)
            if value > 0 and self.grow > 0.6:
                self.create_text(cx, bottom - bh - 10, text=self.fmt(value), fill=TEXT if is_today else MUTED, font=(FONT, 9, "bold"))
            self.create_text(cx, bottom + 14, text=label, fill=TEXT if is_today else MUTED, font=(FONT, 9))
        if self.goal:
            y = bottom - (bottom - top) * self.goal / peak
            self.create_line(left, y, right, y, fill=AMBER, dash=(5, 5), width=1)
            self.create_text(right, y - 8, text=self.goal_text, fill=AMBER, font=(FONT, 8), anchor="e")


def make_tree(parent, columns, widths, height=8):
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=height, selectmode="browse")
    for col, width in zip(columns, widths):
        tree.heading(col, text=col.title())
        tree.column(col, width=width, anchor="w")
    tree.tag_configure("odd", background="#1f2548")
    tree.tag_configure("done", foreground=MUTED)
    tree.pack(fill="both", expand=True, padx=18, pady=(8, 14))
    return tree


def labeled_entry(parent, text, var, width=18, row=0, col=0):
    ttk.Label(parent, text=text, foreground=MUTED).grid(row=row, column=col, padx=6, pady=5, sticky="w")
    entry = ttk.Entry(parent, textvariable=var, width=width)
    entry.grid(row=row, column=col + 1, padx=6, pady=5, sticky="w")
    return entry


class App:
    def __init__(self, root):
        self.root = root
        root.title("Habit Tracker")
        root.geometry("940x800")
        root.minsize(860, 740)
        self.setup_style()

        self.db = sqlite3.connect("habits.db")
        self.db.executescript(SCHEMA)
        self.db.commit()

        self.started_at = dt.datetime.now()
        self.last_water_ping = None
        self.notified_tasks = set()
        self.bed_pinged_on = None
        self.open_popups = 0
        self.task_total = 0

        self.running = False
        self.timer_left = 0.0
        self.timer_total = 0.0
        self.end_at = 0.0
        self.timer_job = None

        self.build_header()
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)

        self.build_dashboard()
        self.build_focus()
        self.build_planner()
        self.build_water()
        self.build_study()
        self.build_sleep()
        self.build_fitness()

        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab)
        self.refresh_all(replay=True)
        self.preview_focus()
        self.tick()

    @property
    def today(self):
        return dt.date.today().isoformat()

    def setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        self.root.configure(bg=BG)
        style.configure(".", background=PANEL, foreground=TEXT, font=(FONT, 10))
        style.configure("TFrame", background=PANEL)
        style.configure("TLabel", background=PANEL, foreground=TEXT)
        style.configure("Accent.TLabel", background=PANEL, foreground=ACCENT, font=(FONT, 11, "bold"))
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(22, 8, 22, 0))
        style.configure("TNotebook.Tab", background=BG, foreground=MUTED, padding=(20, 10), font=(FONT, 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
        style.configure(
            "Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
            rowheight=32, borderwidth=0, font=(FONT, 10),
        )
        style.configure("Treeview.Heading", background=HOVER, foreground=MUTED, relief="flat", font=(FONT, 9, "bold"), padding=8)
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", INK)])
        style.map("Treeview.Heading", background=[("active", TRACK)])
        field = dict(fieldbackground=CARD, foreground=TEXT, insertcolor=TEXT, bordercolor=TRACK, lightcolor=CARD, darkcolor=CARD, padding=6)
        for name in ("TEntry", "TSpinbox", "TCombobox"):
            style.configure(name, **field)
        style.configure("TSpinbox", arrowcolor=MUTED, background=CARD)
        style.configure("TCombobox", arrowcolor=MUTED, background=CARD)
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", CARD)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", CARD)],
            selectforeground=[("readonly", TEXT)],
        )
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", INK)

    def build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 4))
        tk.Label(header, text="Habit", bg=BG, fg=TEXT, font=(FONT, 20, "bold")).pack(side="left")
        tk.Label(header, text="Tracker", bg=BG, fg=ACCENT, font=(FONT, 20, "bold")).pack(side="left", padx=(6, 0))
        self.clock_text = tk.StringVar()
        tk.Label(header, textvariable=self.clock_text, bg=BG, fg=MUTED, font=(FONT, 12)).pack(side="right")
        self.tick_clock()

    def tick_clock(self):
        now = dt.datetime.now()
        sep = ":" if now.second % 2 == 0 else " "
        self.clock_text.set(f"{now:%a, %d %b}   {now:%H}{sep}{now:%M}")
        self.root.after(500, self.tick_clock)

    def run(self, sql, args=()):
        self.db.execute(sql, args)
        self.db.commit()

    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return (row[0] if row else 0) or 0

    def fill(self, tree, sql, args=()):
        tree.delete(*tree.get_children())
        for i, row in enumerate(self.db.execute(sql, args).fetchall()):
            tree.insert("", "end", iid=str(row[0]), values=row[1:], tags=("odd",) if i % 2 else ())

    def week_series(self, sql):
        start = (dt.date.today() - dt.timedelta(days=6)).isoformat()
        found = dict(self.db.execute(sql, (start,)).fetchall())
        days = [dt.date.today() - dt.timedelta(days=i) for i in range(6, -1, -1)]
        labels = [d.strftime("%a") for d in days]
        values = [float(found.get(d.isoformat(), 0) or 0) for d in days]
        return labels, values

    def notify(self, title, message):
        self.root.bell()
        if PREFER_NATIVE and notification is not None:
            try:
                notification.notify(title=title, message=message, app_name="Habit Tracker", timeout=10)
                return
            except Exception:
                pass
        self.popup(title, message)

    def popup(self, title, message):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        win.configure(bg=ACCENT)
        body = tk.Frame(win, bg=CARD)
        body.pack(fill="both", expand=True, padx=(5, 0))
        tk.Label(body, text=title, bg=CARD, fg=TEXT, font=(FONT, 11, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(body, text=message, bg=CARD, fg=MUTED, font=(FONT, 10), anchor="w", justify="left", wraplength=300).pack(fill="x", padx=14)
        width, height = 340, 96
        screen_w = win.winfo_screenwidth()
        y = 70 + 108 * self.open_popups
        self.open_popups += 1
        win.geometry(f"{width}x{height}+{screen_w}+{y}")
        closing = {"on": False}

        def slide(v):
            win.geometry(f"{width}x{height}+{int(v)}+{y}")
            try:
                win.attributes("-alpha", min(1.0, (screen_w - v) / (width + 20)))
            except tk.TclError:
                pass

        def close(event=None):
            if closing["on"]:
                return
            closing["on"] = True

            def fade(v):
                try:
                    win.attributes("-alpha", v)
                except tk.TclError:
                    pass

            def finish():
                self.open_popups = max(0, self.open_popups - 1)
                win.destroy()

            tween(win, 1.0, 0.0, 0.4, fade, finish)

        tween(win, screen_w, screen_w - width - 20, 0.5, slide)
        for widget in [win, body, *body.winfo_children()]:
            widget.bind("<Button-1>", close)
        win.after(6500, close)

    def build_dashboard(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Dashboard")
        hero = tk.Frame(frame, bg=PANEL)
        hero.pack(fill="x", padx=28, pady=(22, 6))
        text_box = tk.Frame(hero, bg=PANEL)
        text_box.pack(side="left", fill="y")
        self.greeting = tk.Label(text_box, bg=PANEL, fg=TEXT, font=(FONT, 24, "bold"), anchor="w")
        self.greeting.pack(anchor="w")
        self.quote = tk.Label(text_box, bg=PANEL, fg=MUTED, font=(FONT, 11), anchor="w")
        self.quote.pack(anchor="w", pady=(6, 0))
        self.score_ring = Ring(hero, size=136, thickness=11, color=GREEN, main_size=20, sub_size=9, percent=True)
        self.score_ring.pack(side="right")
        self.score_ring.text(sub="today")

        grid = tk.Frame(frame, bg=PANEL)
        grid.pack(fill="both", expand=True, padx=20, pady=10)
        specs = [
            ("Water", BLUE, lambda v: f"{int(round(v))} / {WATER_GOAL}", "glasses today", None),
            ("Focus", ACCENT, lambda v: f"{int(round(v))} min", f"goal {FOCUS_GOAL} min", None),
            ("Study", PINK, lambda v: f"{int(round(v))} min", f"goal {STUDY_GOAL} min", None),
            ("Fitness", GREEN, lambda v: f"{int(round(v))} min", f"goal {FIT_GOAL} min", None),
            ("Sleep", AMBER, lambda v: f"{v:.1f} h", f"goal {SLEEP_GOAL:g} h", "not logged"),
            ("Tasks", ROSE, lambda v: f"{int(round(v))} / {self.task_total}", "done today", None),
        ]
        self.cards = {}
        for i, (name, color, fmt, caption, empty) in enumerate(specs):
            card = tk.Frame(grid, bg=CARD, padx=22, pady=18)
            card.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            tk.Label(card, text=name.upper(), bg=CARD, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
            value = CountLabel(card, fmt, empty_text=empty, bg=CARD, fg=TEXT, font=(FONT, 24, "bold"), anchor="w")
            value.pack(anchor="w", fill="x", pady=(6, 10))
            bar = MeterBar(card, width=200, color=color, bg=CARD)
            bar.pack(anchor="w")
            tk.Label(card, text=caption, bg=CARD, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(10, 0))
            add_hover(card, CARD, HOVER)
            self.cards[name] = (value, bar)
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="cards")
        for r in range(2):
            grid.rowconfigure(r, weight=1)

    def refresh_dashboard(self, replay=False):
        glasses = self.one("select count(*) from water where day=?", (self.today,))
        focus = self.one("select sum(minutes) from focus where day=?", (self.today,))
        study = self.one("select sum(minutes) from study where day=?", (self.today,))
        fit = self.one("select sum(minutes) from fitness where day=?", (self.today,))
        sleep = self.one("select hours from sleep where day=?", (self.today,))
        done = self.one("select count(*) from tasks where day=? and done=1", (self.today,))
        self.task_total = self.one("select count(*) from tasks where day=?", (self.today,))
        values = {
            "Water": (glasses, glasses / WATER_GOAL),
            "Focus": (focus, focus / FOCUS_GOAL),
            "Study": (study, study / STUDY_GOAL),
            "Fitness": (fit, fit / FIT_GOAL),
            "Sleep": (sleep, sleep / SLEEP_GOAL),
            "Tasks": (done, done / self.task_total if self.task_total else 0),
        }
        for name, (value, fraction) in values.items():
            label, bar = self.cards[name]
            label.to(value, replay)
            bar.to(min(1.0, fraction), replay)
        score = sum(min(1.0, f) for _, f in values.values()) / len(values)
        self.score_ring.glide(score, replay=replay)
        hour = dt.datetime.now().hour
        self.greeting.configure(text="Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening")
        if score < 0.3:
            self.quote.configure(text="A fresh start. Pick one habit and begin.")
        elif score < 0.7:
            self.quote.configure(text="Good momentum. Keep it going.")
        else:
            self.quote.configure(text="Brilliant day. You are nearly there.")

    def build_focus(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Focus")
        form = ttk.Frame(frame)
        form.pack(pady=(16, 4))
        self.focus_minutes = tk.IntVar(value=25)
        self.focus_label = tk.StringVar(value="Deep work")
        ttk.Label(form, text="Minutes", foreground=MUTED).grid(row=0, column=0, padx=6)
        ttk.Spinbox(form, from_=1, to=180, textvariable=self.focus_minutes, width=6).grid(row=0, column=1, padx=6)
        labeled_entry(form, "Task", self.focus_label, width=24, row=0, col=2)
        self.focus_minutes.trace_add("write", lambda *args: self.preview_focus())
        self.focus_label.trace_add("write", lambda *args: self.preview_focus())

        self.focus_ring = Ring(frame, size=290, thickness=18, color=ACCENT, main_size=46, sub_size=12)
        self.focus_ring.pack(pady=6)

        buttons = ttk.Frame(frame)
        buttons.pack(pady=6)
        FancyButton(buttons, "Start / Resume", self.start_focus, color=ACCENT, width=150).grid(row=0, column=0, padx=8)
        FancyButton(buttons, "Pause", self.pause_focus, color=AMBER, width=110).grid(row=0, column=1, padx=8)
        FancyButton(buttons, "Reset", self.reset_focus, color=MUTED, width=110).grid(row=0, column=2, padx=8)

        self.focus_tree = make_tree(frame, ("label", "minutes"), (460, 100), height=4)

    def focus_minutes_value(self):
        try:
            return max(1, int(self.focus_minutes.get()))
        except (tk.TclError, ValueError):
            return 25

    def preview_focus(self):
        if self.running or self.timer_left > 0:
            return
        self.focus_ring.set_color(ACCENT)
        self.focus_ring.draw(0.0)
        self.focus_ring.text(main=f"{self.focus_minutes_value():02d}:00", sub=self.focus_label.get().strip() or "ready")

    def start_focus(self):
        if self.running:
            return
        if self.timer_left <= 0:
            self.timer_total = self.focus_minutes_value() * 60.0
            self.timer_left = self.timer_total
        self.end_at = time.time() + self.timer_left
        self.running = True
        self.focus_ring.set_color(ACCENT)
        self.focus_ring.text(sub="focusing")
        self.countdown()

    def countdown(self):
        if not self.running:
            return
        remaining = self.end_at - time.time()
        if remaining <= 0:
            self.finish_focus()
            return
        self.timer_left = remaining
        seconds = math.ceil(remaining)
        self.focus_ring.draw(1 - remaining / self.timer_total)
        self.focus_ring.text(main=f"{seconds // 60:02d}:{seconds % 60:02d}")
        self.focus_ring.pulse((math.sin(time.time() * 2.4) + 1) / 2)
        self.timer_job = self.root.after(50, self.countdown)

    def pause_focus(self):
        if not self.running:
            return
        self.running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_left = max(0.0, self.end_at - time.time())
        self.focus_ring.set_color(AMBER)
        self.focus_ring.pulse(0.3)
        self.focus_ring.text(sub="paused")

    def reset_focus(self):
        self.running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_left = 0.0
        self.timer_total = 0.0
        self.focus_ring.pulse(0.0)
        self.focus_ring.glide(0.0, 0.5)
        self.preview_focus()

    def finish_focus(self):
        self.running = False
        minutes = int(round(self.timer_total / 60))
        label = self.focus_label.get().strip() or "Focus"
        self.run("insert into focus (day, label, minutes) values (?,?,?)", (self.today, label, minutes))
        self.focus_ring.draw(1.0)
        self.focus_ring.set_color(GREEN)
        self.focus_ring.text(main="00:00", sub="complete")
        self.focus_ring.pulse(0.5)
        confetti(self.focus_ring)
        self.notify("Focus session complete", f"{minutes} minutes of {label}. Take a short break.")
        self.timer_left = 0.0
        self.timer_total = 0.0
        self.refresh_all()

    def refresh_focus(self):
        self.fill(self.focus_tree, "select id, label, minutes from focus where day=? order by id desc", (self.today,))

    def build_planner(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Planner")
        form = ttk.Frame(frame)
        form.pack(pady=(16, 4))
        self.task_date = tk.StringVar(value=self.today)
        self.task_time = tk.StringVar(value="09:00")
        self.task_title = tk.StringVar()
        labeled_entry(form, "Date", self.task_date, width=12, row=0, col=0)
        labeled_entry(form, "Time (HH:MM)", self.task_time, width=8, row=0, col=2)
        FancyButton(form, "Load date", self.refresh_planner, color=MUTED, width=110, height=34).grid(row=0, column=4, padx=8)
        labeled_entry(form, "Task", self.task_title, width=34, row=1, col=0).grid(columnspan=3, sticky="w")
        FancyButton(form, "Add task", self.add_task, color=ACCENT, width=110, height=34).grid(row=1, column=4, padx=8)

        self.task_tree = make_tree(frame, ("time", "task", "done"), (110, 560, 80), height=12)
        actions = ttk.Frame(frame)
        actions.pack(pady=(0, 14))
        FancyButton(actions, "Mark done / undone", self.toggle_task, color=GREEN, width=170, height=34).grid(row=0, column=0, padx=8)
        FancyButton(actions, "Delete", self.delete_task, color=ROSE, width=110, height=34).grid(row=0, column=1, padx=8)

    def add_task(self):
        title = self.task_title.get().strip()
        at = parse_time(self.task_time.get())
        try:
            day = dt.date.fromisoformat(self.task_date.get().strip()).isoformat()
        except ValueError:
            day = None
        if not title or not at or not day:
            messagebox.showwarning("Planner", "Enter a task, a time like 09:30 and a date like 2026-10-08.")
            return
        self.run("insert into tasks (day, title, at, done) values (?,?,?,0)", (day, title, at))
        self.task_title.set("")
        self.refresh_all()

    def selected_task(self):
        picked = self.task_tree.selection()
        return int(picked[0]) if picked else None

    def toggle_task(self):
        tid = self.selected_task()
        if tid is not None:
            self.run("update tasks set done = 1 - done where id=?", (tid,))
            self.refresh_all()

    def delete_task(self):
        tid = self.selected_task()
        if tid is not None:
            self.run("delete from tasks where id=?", (tid,))
            self.refresh_all()

    def refresh_planner(self):
        self.task_tree.delete(*self.task_tree.get_children())
        rows = self.db.execute(
            "select id, at, title, done from tasks where day=? order by at", (self.task_date.get().strip(),)
        ).fetchall()
        for i, (tid, at, title, done) in enumerate(rows):
            tags = ("odd",) if i % 2 else ()
            if done:
                tags += ("done",)
            self.task_tree.insert("", "end", iid=str(tid), values=(at, title, "✔" if done else ""), tags=tags)

    def build_water(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Water")
        self.water_count = CountLabel(
            frame, lambda v: f"{int(round(v))} / {WATER_GOAL} glasses", bg=PANEL, fg=TEXT, font=(FONT, 34, "bold")
        )
        self.water_count.pack(pady=(26, 4))
        self.glass = WaterGlass(frame)
        self.glass.pack(pady=4)
        self.water_note = tk.StringVar()
        ttk.Label(frame, textvariable=self.water_note, foreground=MUTED).pack(pady=4)
        buttons = ttk.Frame(frame)
        buttons.pack(pady=14)
        FancyButton(buttons, "I drank a glass", self.add_water, color=BLUE, width=170, height=42).grid(row=0, column=0, padx=8)
        FancyButton(buttons, "Undo last", self.undo_water, color=MUTED, width=120, height=42).grid(row=0, column=1, padx=8)

    def add_water(self):
        now = dt.datetime.now().isoformat(timespec="seconds")
        self.run("insert into water (day, logged_at) values (?,?)", (self.today, now))
        glasses = self.one("select count(*) from water where day=?", (self.today,))
        self.refresh_all()
        if glasses == WATER_GOAL:
            self.root.after(900, lambda: confetti(self.glass))

    def undo_water(self):
        self.run("delete from water where id=(select max(id) from water where day=?)", (self.today,))
        self.refresh_all()

    def refresh_water(self):
        glasses = self.one("select count(*) from water where day=?", (self.today,))
        last = self.db.execute("select max(logged_at) from water where day=?", (self.today,)).fetchone()[0]
        self.water_count.to(glasses)
        self.glass.set_level(min(1.0, glasses / WATER_GOAL))
        if glasses >= WATER_GOAL:
            self.water_note.set("Daily goal reached. Nice work.")
        elif last:
            self.water_note.set("Last glass at " + dt.datetime.fromisoformat(last).strftime("%H:%M"))
        else:
            self.water_note.set("No water logged yet today.")

    def build_study(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Study")
        form = ttk.Frame(frame)
        form.pack(pady=(16, 4))
        self.study_subject = tk.StringVar()
        self.study_minutes = tk.IntVar(value=45)
        labeled_entry(form, "Subject", self.study_subject, width=28, row=0, col=0)
        ttk.Label(form, text="Minutes", foreground=MUTED).grid(row=0, column=2, padx=6)
        ttk.Spinbox(form, from_=5, to=600, increment=5, textvariable=self.study_minutes, width=6).grid(row=0, column=3)
        FancyButton(form, "Log", self.add_study, color=PINK, width=90, height=34).grid(row=0, column=4, padx=10)
        self.study_chart = BarChart(
            frame, color=PINK, goal=STUDY_GOAL, goal_text=f"goal {STUDY_GOAL} min", fmt=lambda v: f"{int(v)}"
        )
        self.study_chart.pack(fill="x", padx=18, pady=(10, 0))
        self.study_tree = make_tree(frame, ("subject", "minutes"), (560, 120), height=5)

    def add_study(self):
        subject = self.study_subject.get().strip()
        if not subject:
            return
        try:
            minutes = int(self.study_minutes.get())
        except (tk.TclError, ValueError):
            return
        self.run("insert into study (day, subject, minutes) values (?,?,?)", (self.today, subject, minutes))
        self.study_subject.set("")
        self.refresh_all()

    def refresh_study(self):
        self.fill(self.study_tree, "select id, subject, minutes from study where day=? order by id desc", (self.today,))
        labels, values = self.week_series("select day, sum(minutes) from study where day>=? group by day")
        self.study_chart.set(labels, values)

    def build_sleep(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Sleep")
        form = ttk.Frame(frame)
        form.pack(pady=(16, 4))
        self.sleep_day = tk.StringVar(value=self.today)
        self.sleep_bed = tk.StringVar(value="23:00")
        self.sleep_wake = tk.StringVar(value="06:30")
        self.sleep_quality = tk.IntVar(value=3)
        labeled_entry(form, "Woke up on", self.sleep_day, width=12, row=0, col=0)
        labeled_entry(form, "Bed (HH:MM)", self.sleep_bed, width=8, row=0, col=2)
        labeled_entry(form, "Wake (HH:MM)", self.sleep_wake, width=8, row=1, col=0)
        ttk.Label(form, text="Quality 1-5", foreground=MUTED).grid(row=1, column=2, padx=6)
        ttk.Spinbox(form, from_=1, to=5, textvariable=self.sleep_quality, width=4).grid(row=1, column=3, sticky="w", padx=6)
        FancyButton(form, "Save", self.save_sleep, color=AMBER, width=90, height=34).grid(row=1, column=4, padx=10)
        self.sleep_avg = tk.StringVar()
        ttk.Label(frame, textvariable=self.sleep_avg, style="Accent.TLabel").pack(pady=(6, 0))
        self.sleep_chart = BarChart(
            frame, color=AMBER, goal=SLEEP_GOAL, goal_text=f"goal {SLEEP_GOAL:g} h", fmt=lambda v: f"{v:.1f}"
        )
        self.sleep_chart.pack(fill="x", padx=18, pady=(8, 0))
        self.sleep_tree = make_tree(frame, ("day", "bed", "wake", "hours", "quality"), (170, 120, 120, 120, 120), height=5)

    def save_sleep(self):
        bed = parse_time(self.sleep_bed.get())
        wake = parse_time(self.sleep_wake.get())
        try:
            day = dt.date.fromisoformat(self.sleep_day.get().strip()).isoformat()
        except ValueError:
            day = None
        if not bed or not wake or not day:
            messagebox.showwarning("Sleep", "Use times like 23:00 and a date like 2026-10-08.")
            return
        b = int(bed[:2]) * 60 + int(bed[3:])
        w = int(wake[:2]) * 60 + int(wake[3:])
        hours = ((w - b) % 1440) / 60
        self.run(
            "insert or replace into sleep (day, bed, wake, hours, quality) values (?,?,?,?,?)",
            (day, bed, wake, hours, self.sleep_quality.get()),
        )
        self.refresh_all()

    def refresh_sleep(self):
        self.sleep_tree.delete(*self.sleep_tree.get_children())
        rows = self.db.execute(
            "select day, bed, wake, round(hours, 1), quality from sleep order by day desc limit 7"
        ).fetchall()
        for i, row in enumerate(rows):
            self.sleep_tree.insert("", "end", iid=row[0], values=row, tags=("odd",) if i % 2 else ())
        if rows:
            avg = sum(r[3] for r in rows) / len(rows)
            self.sleep_avg.set(f"Average of last {len(rows)} nights: {avg:.1f} h  (goal {SLEEP_GOAL:g} h)")
        else:
            self.sleep_avg.set("No sleep logged yet.")
        labels, values = self.week_series("select day, hours from sleep where day>=?")
        self.sleep_chart.set(labels, values)

    def build_fitness(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Fitness")
        form = ttk.Frame(frame)
        form.pack(pady=(16, 4))
        self.fit_activity = tk.StringVar(value="Walk")
        self.fit_minutes = tk.IntVar(value=30)
        self.fit_notes = tk.StringVar()
        ttk.Label(form, text="Activity", foreground=MUTED).grid(row=0, column=0, padx=6)
        ttk.Combobox(
            form,
            textvariable=self.fit_activity,
            values=["Walk", "Run", "Gym", "Cycling", "Yoga", "Swimming", "Sports", "Other"],
            width=12,
            state="readonly",
        ).grid(row=0, column=1, padx=6)
        ttk.Label(form, text="Minutes", foreground=MUTED).grid(row=0, column=2, padx=6)
        ttk.Spinbox(form, from_=5, to=300, increment=5, textvariable=self.fit_minutes, width=6).grid(row=0, column=3)
        labeled_entry(form, "Notes", self.fit_notes, width=34, row=1, col=0).grid(columnspan=3, sticky="w")
        FancyButton(form, "Log", self.add_fitness, color=GREEN, width=90, height=34).grid(row=1, column=4, padx=10)
        self.fit_week = tk.StringVar()
        ttk.Label(frame, textvariable=self.fit_week, style="Accent.TLabel").pack(pady=(6, 0))
        self.fit_chart = BarChart(
            frame, color=GREEN, goal=FIT_GOAL, goal_text=f"goal {FIT_GOAL} min", fmt=lambda v: f"{int(v)}"
        )
        self.fit_chart.pack(fill="x", padx=18, pady=(8, 0))
        self.fit_tree = make_tree(frame, ("day", "activity", "minutes", "notes"), (130, 150, 100, 360), height=5)

    def add_fitness(self):
        try:
            minutes = int(self.fit_minutes.get())
        except (tk.TclError, ValueError):
            return
        self.run(
            "insert into fitness (day, activity, minutes, notes) values (?,?,?,?)",
            (self.today, self.fit_activity.get(), minutes, self.fit_notes.get().strip()),
        )
        self.fit_notes.set("")
        self.refresh_all()

    def refresh_fitness(self):
        self.fill(self.fit_tree, "select id, day, activity, minutes, notes from fitness order by id desc limit 15")
        start = (dt.date.today() - dt.timedelta(days=6)).isoformat()
        total = self.one("select sum(minutes) from fitness where day>=?", (start,))
        self.fit_week.set(f"Active minutes in the last 7 days: {total}")
        labels, values = self.week_series("select day, sum(minutes) from fitness where day>=? group by day")
        self.fit_chart.set(labels, values)

    def on_tab(self, event=None):
        name = self.tabs.tab(self.tabs.select(), "text")
        self.refresh_all(replay=(name == "Dashboard"))

    def refresh_all(self, replay=False):
        self.refresh_dashboard(replay)
        self.refresh_focus()
        self.refresh_planner()
        self.refresh_water()
        self.refresh_study()
        self.refresh_sleep()
        self.refresh_fitness()

    def tick(self):
        now = dt.datetime.now()
        self.check_water(now)
        self.check_tasks(now)
        self.check_bedtime(now)
        self.root.after(CHECK_EVERY_MS, self.tick)

    def check_water(self, now):
        glasses = self.one("select count(*) from water where day=?", (self.today,))
        if glasses >= WATER_GOAL or not (AWAKE_FROM <= now.hour < AWAKE_UNTIL):
            return
        last = self.db.execute("select max(logged_at) from water where day=?", (self.today,)).fetchone()[0]
        reference = dt.datetime.fromisoformat(last) if last else self.started_at
        overdue = now - reference >= WATER_EVERY
        cooled = self.last_water_ping is None or now - self.last_water_ping >= WATER_REPING
        if overdue and cooled:
            self.last_water_ping = now
            self.notify("Time to drink water 💧", f"{glasses} of {WATER_GOAL} glasses so far today.")

    def check_tasks(self, now):
        rows = self.db.execute(
            "select id, title from tasks where day=? and at=? and done=0",
            (self.today, now.strftime("%H:%M")),
        ).fetchall()
        for tid, title in rows:
            if tid not in self.notified_tasks:
                self.notified_tasks.add(tid)
                self.notify("Planner reminder", title)

    def check_bedtime(self, now):
        if now.strftime("%H:%M") == BEDTIME_REMINDER and self.bed_pinged_on != self.today:
            self.bed_pinged_on = self.today
            self.notify("Wind down", f"Aim for {SLEEP_GOAL:g} hours of sleep tonight.")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
