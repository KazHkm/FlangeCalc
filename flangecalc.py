import math
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.patches import Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pathlib import Path

from calculations import (
    calculate_torque, calculate_pressure, calculate_tensioning, assign_bolt_passes,
    generate_crisscross_order,
    BOLT_MATERIALS, BOLT_SIZES, COVERAGE_PASSES
)
from htw_data import (get_nut_size_mm, get_brands, get_drive_types, get_models, get_hex_sizes,
                      bar_to_psi, nm_to_lbft)
from htb_data import get_tensioner_brands, get_tensioner_tools, get_hydraulic_area

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

appWidth, appHeight = 1200, 880

# Colors shared across both pages, kept in one place so the two pages stay
# visually consistent.
ACCENT_GREEN = "#8CE99A"
ACCENT_GREEN_DARK = "#517343"
GRID_COLOR = "#444444"
SPINE_COLOR = "#666666"
FIG_BG = "#2b2b2b"

# Distinct colors per tensioning pass letter (A = first (highest) pressure
# pass through D = last/base pass), reused for both the bar chart and the
# bolt-pattern diagram so a pass always reads the same color everywhere.
PASS_COLORS = {
    "A": "#e6a23c",  # amber
    "B": "#5c9ecf",  # blue
    "C": "#9b7fd4",  # purple  <- was "#c9a24b", too close to A
    "D": "#cc6666",  # red
}


# ---------------------------------------------------------------------------
# Shared small helpers used by both pages
# ---------------------------------------------------------------------------
def style_axes(ax: Axes, xlabel: str, ylabel: str):
    ax.set_facecolor(FIG_BG)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.set_xlabel(xlabel, color="white")
    ax.set_ylabel(ylabel, color="white")
    ax.grid(True, color=GRID_COLOR, linewidth=0.6)


def placeholder_text(ax: Axes, text="Enter values and click Calculate"):
    ax.text(
        0.5, 0.5, text,
        transform=ax.transAxes, ha="center", va="center",
        color="#888888", fontsize=11
    )


def make_result_cell(parent, column, title, initial_value, value_color="white"):
    """Build one title/value cell in a results bar. Shared by both pages
    so neither has to reach into the other's internals to use it."""
    title_label = ctk.CTkLabel(parent, text=title, font=("Arial", 12), text_color="#aaaaaa")
    title_label.grid(row=0, column=column, sticky="ew", padx=10, pady=(10, 0))
    value_label = ctk.CTkLabel(parent, text=initial_value, font=("Arial", 16, "bold"), text_color=value_color)
    value_label.grid(row=1, column=column, sticky="ew", padx=10, pady=(0, 10))
    return value_label


# ---------------------------------------------------------------------------
# Page 1: Torque Wrench calculator (original functionality)
# ---------------------------------------------------------------------------
class TorquePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.torque = 0
        self.one_third_torque = 0
        self.two_third_torque = 0
        self.pressure = 0
        self.torque_unit = "lb-ft"

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame for user input
        self.left_frame = ctk.CTkScrollableFrame(self, width=335)
        self.left_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        # Frame to display the graphs and results
        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=0)  # results bar
        self.right_frame.grid_rowconfigure(1, weight=1)  # tabview
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.left_frame,
                                        text="Bolted-Flange Torque Calculator",
                                        font=("Arial", 18, "bold"))
        self.title_label.pack(padx=(20, 30), pady=(15, 4), anchor="w")

        self.torque_equation = ctk.CTkLabel(self.left_frame,
                                            text="T = F · K · D",
                                            font=ctk.CTkFont(size=17),
                                            text_color=ACCENT_GREEN)
        self.torque_equation.pack(padx=20, pady=(0, 10), anchor="w")

        # Labels and comboboxes for input
        self.bolttype_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Material",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.bolttype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.bolttype_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=BOLT_MATERIALS,
                                                 width=200)
        self.bolttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.bolttype_combobox.set(BOLT_MATERIALS[0])

        self.utilfactor_label = ctk.CTkLabel(self.left_frame,
                                             text="Utilization Factor (P)",
                                             font=("Arial", 12, "bold"),
                                             anchor="w")
        self.utilfactor_label.pack(padx=20, pady=(6, 2), fill="x")

        self.utilfactor_entry = ctk.CTkEntry(self.left_frame,
                                             width=200,
                                             placeholder_text="e.g. 0.5")
        self.utilfactor_entry.insert(0, "0.5")
        self.utilfactor_entry.pack(padx=20, pady=(0, 4), fill="x")

        self.cof_label = ctk.CTkLabel(self.left_frame,
                                      text="Coefficient of Friction (K)",
                                      font=("Arial", 12, "bold"),
                                      anchor="w")
        self.cof_label.pack(padx=20, pady=(6, 2), fill="x")

        self.cof_entry = ctk.CTkEntry(self.left_frame,
                                      width=200,
                                      placeholder_text="e.g. 0.13")
        self.cof_entry.insert(0, "0.13")
        self.cof_entry.pack(padx=20, pady=(0, 4), fill="x")

        self.boltsize_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Size (inch)",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.boltsize_label.pack(padx=20, pady=(6, 2), fill="x")

        self.boltsize_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=BOLT_SIZES,
                                                 width=200,
                                                 command=self.update_htw_state)
        self.boltsize_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.boltsize_combobox.set(BOLT_SIZES[0])

        self.nutsize_label = ctk.CTkLabel(self.left_frame,
                                          text=f"Nut Size: {get_nut_size_mm(BOLT_SIZES[0])} mm",
                                          font=("Arial", 11),
                                          text_color=ACCENT_GREEN,
                                          anchor="w")
        self.nutsize_label.pack(padx=22, pady=(0, 0), anchor="w")

        self.numbolts_label = ctk.CTkLabel(self.left_frame,
                                           text="Number of Bolts (for diagram)",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.numbolts_label.pack(padx=20, pady=(6, 2), fill="x")

        self.numbolts_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=["4", "8", "12", "16", "20", "24", "28"],
                                                 width=200,
                                                 state="readonly",
                                                 command=self.on_numbolts_change)
        self.numbolts_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.numbolts_combobox.set("8")

        # Unit system selector
        self.unit_label = ctk.CTkLabel(self.left_frame,
                                       text="Unit system",
                                       font=("Arial", 12, "bold"),
                                       anchor="w")
        self.unit_label.pack(padx=20, pady=(4, 2), fill="x")

        self.unit_combobox = ctk.CTkComboBox(self.left_frame,
                                             values=["Metric (N·m, N)", "Imperial (lb-ft, lbf)"],
                                             width=200)
        self.unit_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.unit_combobox.set("Imperial (lb-ft, lbf)")

        # Hydraulic Torque Wrench selection (brand -> drive type -> model -> drive size)
        self.htw_section_label = ctk.CTkLabel(self.left_frame,
                                              text='Hydraulic Torque Wrench (Bolt Size > 1")',
                                              font=("Arial", 13, "bold"),
                                              text_color=ACCENT_GREEN,
                                              anchor="w")
        self.htw_section_label.pack(padx=20, pady=(4, 4), anchor="w")

        self.htwbrand_label = ctk.CTkLabel(self.left_frame,
                                           text="HTW Brand",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.htwbrand_label.pack(padx=20, pady=(4, 2), fill="x")

        self.htwbrand_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=get_brands(),
                                                 width=200,
                                                 command=self.on_brand_change)
        self.htwbrand_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.htwbrand_combobox.set(get_brands()[0])

        self.htwdrivetype_label = ctk.CTkLabel(self.left_frame,
                                               text="Drive Type",
                                               font=("Arial", 12, "bold"),
                                               anchor="w")
        self.htwdrivetype_label.pack(padx=20, pady=(6, 2), fill="x")

        initial_brand = get_brands()[0]
        initial_drive_types = get_drive_types(initial_brand)
        self.htwdrivetype_combobox = ctk.CTkComboBox(self.left_frame,
                                                     values=initial_drive_types,
                                                     width=200,
                                                     command=self.on_drivetype_change)
        self.htwdrivetype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.htwdrivetype_combobox.set(initial_drive_types[0])

        self.htwmodel_label = ctk.CTkLabel(self.left_frame,
                                           text="HTW Model",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.htwmodel_label.pack(padx=20, pady=(6, 2), fill="x")

        initial_models = get_models(initial_brand, initial_drive_types[0])
        self.htwmodel_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=initial_models,
                                                 width=200,
                                                 command=self.on_model_change)
        self.htwmodel_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.htwmodel_combobox.set(initial_models[0])

        self.htwhex_label = ctk.CTkLabel(self.left_frame,
                                         text="Drive Size",
                                         font=("Arial", 12, "bold"),
                                         anchor="w")
        self.htwhex_label.pack(padx=20, pady=(6, 2), fill="x")

        initial_hex_sizes = get_hex_sizes(initial_brand, initial_drive_types[0], initial_models[0])
        self.htwhex_combobox = ctk.CTkComboBox(self.left_frame,
                                               values=initial_hex_sizes,
                                               width=200)
        self.htwhex_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.htwhex_combobox.set(initial_hex_sizes[0])
        self.update_htw_state()

        # Frame to display the buttons
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(padx=20, pady=(4, 10), fill="x")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.calculateTorque_button = ctk.CTkButton(self.button_frame,
                                                    text='Calculate',
                                                    command=self.calculate_torque_value,
                                                    fg_color="#6E9451",
                                                    hover_color="#465936")
        self.calculateTorque_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.reset_button = ctk.CTkButton(self.button_frame,
                                          text="Reset",
                                          command=self.clear_calculation,
                                          fg_color="transparent",
                                          hover_color="#465936",
                                          border_width=1)
        self.reset_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Frame to display the results bar and graphs
        self.results_frame = ctk.CTkFrame(self.right_frame, corner_radius=12)
        self.results_frame.grid(row=0, column=0, padx=16, pady=(16, 0), sticky="ew")
        for col in range(5):
            self.results_frame.grid_columnconfigure(col, weight=1)

        self.result_value = make_result_cell(self.results_frame, 0, "Torque", "-- lb-ft", ACCENT_GREEN)
        self.load_value = make_result_cell(self.results_frame, 1, "Bolt Load", "-- lbf")
        self.nutfactor_value = make_result_cell(self.results_frame, 2, "Nut Factor (K)", "--")
        self.utilization_value = make_result_cell(self.results_frame, 3, "Utilization Factor (P)", "--")
        self.pressure_value = make_result_cell(self.results_frame, 4, "HTW Pressure", "-- bar", ACCENT_GREEN)

        # Tabview holding the two graphs
        self.tabview = ctk.CTkTabview(self.right_frame,
                                      segmented_button_selected_color="#576E51",
                                      segmented_button_selected_hover_color="#6F945F")
        self.tabview.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        self.tab_tightening = self.tabview.add("Tightening Sequence")
        self.tab_yield = self.tabview.add("   Yield Utilization   ")
        self.tab_pressure = self.tabview.add("Torque → Pressure (HTW)")

        self.tab_tightening.grid_rowconfigure(0, weight=1)
        self.tab_tightening.grid_columnconfigure(0, weight=1)
        self.tab_pressure.grid_rowconfigure(0, weight=1)
        self.tab_pressure.grid_columnconfigure(0, weight=1)
        self.tab_yield.grid_rowconfigure(0, weight=1)
        self.tab_yield.grid_columnconfigure(0, weight=1)

        # Graph 1: bolt tightening sequence diagram
        self.fig = Figure(figsize=(7.5, 6.5), dpi=100)
        self.fig.patch.set_facecolor(FIG_BG)
        self.ax: Axes = self.fig.add_subplot(111)
        self.ax.set_facecolor(FIG_BG)
        self.ax.set_aspect("equal")
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_tightening)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.draw_default_tightening_diagram(8)
        self.canvas.draw()

        # Graph 2: torque vs pressure interpolation curve (HTW)
        self.fig2 = Figure(figsize=(5, 4), dpi=100)
        self.fig2.patch.set_facecolor(FIG_BG)
        self.ax2: Axes = self.fig2.add_subplot(111)
        style_axes(self.ax2, "Pressure", "Torque")
        placeholder_text(self.ax2)

        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab_pressure)
        self.canvas2.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas2.draw()

        # Graph 3: bolt load vs. yield-strength utilization gauge
        self.fig3 = Figure(figsize=(6, 2.5), dpi=100)
        self.fig3.patch.set_facecolor(FIG_BG)
        self.ax3: Axes = self.fig3.add_subplot(111)
        self.draw_default_yield_gauge()

        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=self.tab_yield)
        self.canvas3.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas3.draw()

    # HTW combobox chaining
    def on_brand_change(self, brand):
        drive_types = get_drive_types(brand)
        self.htwdrivetype_combobox.configure(values=drive_types)
        self.htwdrivetype_combobox.set(drive_types[0])
        self.on_drivetype_change(drive_types[0])

    def on_drivetype_change(self, drive_type):
        brand = self.htwbrand_combobox.get()
        models = get_models(brand, drive_type)
        self.htwmodel_combobox.configure(values=models)
        self.htwmodel_combobox.set(models[0])
        self.on_model_change(models[0])

    def on_model_change(self, model):
        brand = self.htwbrand_combobox.get()
        drive_type = self.htwdrivetype_combobox.get()
        hex_sizes = get_hex_sizes(brand, drive_type, model)
        self.htwhex_combobox.configure(values=hex_sizes)
        self.htwhex_combobox.set(hex_sizes[0])

    def update_htw_state(self, *_):
        bolt_size = self.boltsize_combobox.get()

        nut_mm = get_nut_size_mm(bolt_size)
        self.nutsize_label.configure(text=f"Nut Size: {nut_mm} mm" if nut_mm else "Nut Size: --")

        large_bolts = ["1 1/8", "1 1/4", "1 3/8", "1 1/2", "1 5/8", "1 3/4", "1 7/8",
                       "2", "2 1/4", "2 1/2", "2 3/4", "3", "3 1/4", "3 1/2", "3 3/4", "4"]

        state = "normal" if self.boltsize_combobox.get() in large_bolts else "disabled"

        self.htwbrand_combobox.configure(state=state)
        self.htwdrivetype_combobox.configure(state=state)
        self.htwmodel_combobox.configure(state=state)
        self.htwhex_combobox.configure(state=state)

    def on_numbolts_change(self, *_):
        num_bolts = int(self.numbolts_combobox.get())
        if self.torque:
            self.draw_tightening_diagram(num_bolts)
        else:
            self.draw_default_tightening_diagram(num_bolts)
        self.canvas.draw()

    @staticmethod
    def _bolt_coords(num_bolts, flange_radius=1.0):
        coords = []
        for i in range(num_bolts):
            angle = math.pi / 2 - (2 * math.pi * i / num_bolts)
            coords.append((flange_radius * math.cos(angle), flange_radius * math.sin(angle)))
        return coords

    def _draw_flange_base(self, flange_radius=1.0):
        self.ax.add_patch(Circle((0, 0), flange_radius + 0.16, facecolor="#3a3a3a",
                                 edgecolor=SPINE_COLOR, linewidth=1.2, zorder=1))
        self.ax.add_patch(Circle((0, 0), 0.22, facecolor=FIG_BG,
                                 edgecolor=SPINE_COLOR, linewidth=1.0, zorder=2))

    def draw_default_tightening_diagram(self, num_bolts=8):
        self.ax.clear()
        for txt in self.fig.texts[:]:
            txt.remove()
        self.ax.set_facecolor(FIG_BG)
        self.ax.set_aspect("equal")
        self.ax.axis("off")

        flange_radius = 1.0
        coords = self._bolt_coords(num_bolts, flange_radius)

        self._draw_flange_base(flange_radius)

        for i, (x, y) in enumerate(coords):
            self.ax.add_patch(Circle((x, y), 0.11, facecolor=SPINE_COLOR,
                                     edgecolor="white", linewidth=1.0, zorder=3))
            self.ax.text(x, y, str(i + 1), ha="center", va="center",
                         color="white", fontsize=9, fontweight="bold", zorder=4)

        self.ax.text(0, -(flange_radius + 0.4), "Enter values and click Calculate",
                     ha="center", va="center", color="#888888", fontsize=10)

        margin = flange_radius + 0.35
        self.ax.set_xlim(-margin, margin)
        self.ax.set_ylim(-margin, margin)

    def draw_tightening_diagram(self, num_bolts):
        self.ax.clear()
        for txt in self.fig.texts[:]:
            txt.remove()
        self.ax.set_facecolor(FIG_BG)
        self.ax.set_aspect("equal")
        self.ax.axis("off")

        flange_radius = 1.0
        order = generate_crisscross_order(num_bolts)
        coords = self._bolt_coords(num_bolts, flange_radius)

        self._draw_flange_base(flange_radius)

        # The dashed line should trace bolts in ascending tightening order
        # (1st tightened, 2nd, 3rd...), which is the INVERSE of `order` —
        # order[i] tells us the label at position i, so we sort positions
        # by that label to get the actual visiting sequence.
        tightening_positions = sorted(range(num_bolts), key=lambda pos: order[pos])
        path_x = [coords[p][0] for p in tightening_positions]
        path_y = [coords[p][1] for p in tightening_positions]
        self.ax.plot(path_x, path_y, color=ACCENT_GREEN, linewidth=1.0,
                     alpha=0.5, zorder=2, linestyle="--")

        for i, (x, y) in enumerate(coords):
            self.ax.add_patch(Circle((x, y), 0.11, facecolor=ACCENT_GREEN,
                                     edgecolor="white", linewidth=1.0, zorder=3))
            self.ax.text(x, y, str(order[i] + 1), ha="center", va="center",
                         color="black", fontsize=9, fontweight="bold", zorder=4)

        top_x, top_y = coords[0]
        self.ax.annotate(
            "Bolt 1 = largest\nmeasured gap",
            xy=(top_x, top_y), xytext=(top_x, top_y + 0.38),
            ha="center", va="bottom", color="white", fontsize=8,
            arrowprops=dict(arrowstyle="->", color=SPINE_COLOR, lw=1.2),
            bbox=dict(boxstyle="round,pad=0.3", fc=FIG_BG, ec=SPINE_COLOR, alpha=0.9)
        )

        table_text = (
            "Target Torque\n"
            f" 30%    {self.one_third_torque:>8.1f} {self.torque_unit}\n"
            f" 60%    {self.two_third_torque:>8.1f} {self.torque_unit}\n"
            f"100%    {self.torque:>8.1f} {self.torque_unit}\n"
            "\n"
            "* Repeat sequence each pass"
        )
        self.fig.text(0.02, 0.98, table_text,
                      ha="left", va="top", color="white", fontsize=9,
                      fontfamily="monospace", linespacing=1.6,
                      bbox=dict(boxstyle="round,pad=0.3", fc=FIG_BG, ec=SPINE_COLOR, alpha=0.9))

        margin = flange_radius + 0.35
        self.ax.set_xlim(-margin, margin)
        self.ax.set_ylim(-margin, margin)

    def draw_default_yield_gauge(self):
        self.ax3.clear()
        self.ax3.set_facecolor(FIG_BG)
        self.ax3.axis("off")
        placeholder_text(self.ax3)

    def draw_yield_gauge(self, utilization_pct, bolt_load_lbf, max_load_lbf):
        self.ax3.clear()
        self.ax3.set_facecolor(FIG_BG)
        self.ax3.set_xlim(0, 110)
        self.ax3.set_ylim(0, 1)
        self.ax3.axis("off")

        # Background zones: green (<70%), amber (70-90%), red (>90%)
        self.ax3.axvspan(0, 70, color="#3a3a3a", zorder=0)
        self.ax3.axvspan(70, 90, color="#4a3f2a", zorder=0)
        self.ax3.axvspan(90, 110, color="#4a2a2a", zorder=0)

        if utilization_pct >= 90:
            bar_color = "#cc6666"
        elif utilization_pct >= 70:
            bar_color = "#e6a23c"
        else:
            bar_color = ACCENT_GREEN

        bar_value = min(utilization_pct, 110)
        self.ax3.barh(0.5, bar_value, height=0.5, color=bar_color, zorder=2)

        self.ax3.axvline(100, color="white", linewidth=1.5, linestyle="--", zorder=3)
        self.ax3.text(100, 0.85, "100% Yield", ha="center", va="bottom",
                      color="white", fontsize=8)

        label_x = min(bar_value + 2, 104)
        self.ax3.text(label_x, 0.5, f"{utilization_pct:.1f}%", ha="left", va="center",
                      color="white", fontsize=13, fontweight="bold", zorder=4)

        self.ax3.text(0, 0.05,
                      f"Bolt Load: {bolt_load_lbf:.0f} lbf   /   Load at Yield: {max_load_lbf:.0f} lbf",
                      ha="left", va="bottom", color="#aaaaaa", fontsize=9)

        self.canvas3.draw()

    # Convert a pressure/torque pair from bar/N·m into whichever unit system is currently selected
    @staticmethod
    def _convert_pt(pressure_bar, torque_nm, unit_system):
        if unit_system == "Imperial (lb-ft, lbf)":
            return bar_to_psi(pressure_bar), nm_to_lbft(torque_nm)
        return pressure_bar, torque_nm

    # Main calculation
    def calculate_torque_value(self):
        bolt_material = self.bolttype_combobox.get()
        bolt_size = self.boltsize_combobox.get()

        try:
            utilization_factor = float(self.utilfactor_entry.get())
        except ValueError:
            self.result_value.configure(text="Invalid utilization factor")
            return

        try:
            cof = float(self.cof_entry.get())
        except ValueError:
            self.result_value.configure(text="Invalid friction coefficient")
            return

        large_bolts = ["1 1/8", "1 1/4", "1 3/8", "1 1/2", "1 5/8", "1 3/4", "1 7/8",
                       "2", "2 1/4", "2 1/2", "2 3/4", "3", "3 1/4", "3 1/2", "3 3/4", "4"]
        use_htw = bolt_size in large_bolts

        unit_system = self.unit_combobox.get()

        htw_brand = self.htwbrand_combobox.get()
        htw_drive_type = self.htwdrivetype_combobox.get()
        htw_model = self.htwmodel_combobox.get()
        htw_hex = self.htwhex_combobox.get()

        result = calculate_torque(bolt_material, utilization_factor, cof, bolt_size, unit_system)

        self.torque = result["torque"]
        self.one_third_torque = result["30_percent"]
        self.two_third_torque = result["60_percent"]

        pressure_result = None
        pressure_30 = None
        pressure_60 = None

        if use_htw:
            pressure_result = calculate_pressure(result["torque_nm"], htw_brand, htw_drive_type, htw_model, htw_hex)
            self.pressure = pressure_result["pressure"]
            pressure_30 = calculate_pressure(result["torque_nm"] * 0.3, htw_brand, htw_drive_type, htw_model, htw_hex)
            pressure_60 = calculate_pressure(result["torque_nm"] * 0.6, htw_brand, htw_drive_type, htw_model, htw_hex)
        else:
            self.pressure = 0

        self.result_value.configure(text=f"{self.torque:.2f} {result['unit']}")
        self.load_value.configure(text=f"{result['bolt_load']:.2f} {result['bolt_load_unit']}")
        self.nutfactor_value.configure(text=f"{result['nut_factor']:.2f}")
        self.utilization_value.configure(text=f"{result['utilization_factor'] * 100:.1f}%")

        pressure_unit = "psi" if unit_system == "Imperial (lb-ft, lbf)" else "bar"

        if use_htw:
            display_pressure = bar_to_psi(self.pressure) if pressure_unit == "psi" else self.pressure
            pressure_text = f"{display_pressure:.1f} {pressure_unit}"
            if pressure_result["out_of_range"]:
                pressure_text += " (out of chart range)"
        else:
            pressure_text = f"-- {pressure_unit}"

        self.pressure_value.configure(text=pressure_text)

        # Update graph 1: bolt tightening sequence diagram
        self.torque_unit = result['unit']
        num_bolts = int(self.numbolts_combobox.get())
        self.draw_tightening_diagram(num_bolts)
        self.canvas.draw()

        # Update graph 2: HTW torque -> pressure interpolation
        self.ax2.clear()

        if use_htw:
            table = pressure_result["table"]
            imperial = unit_system == "Imperial (lb-ft, lbf)"
            pressure_unit = "psi" if imperial else "bar"
            torque_unit = "lb-ft" if imperial else "N·m"

            chart_pressures, chart_torques = zip(
                *[self._convert_pt(p, t, unit_system) for p, t in table]
            )

            style_axes(self.ax2, f"Pressure ({pressure_unit})", f"Torque ({torque_unit})")

            self.ax2.plot(
                chart_pressures, chart_torques, marker="o", linewidth=1.5,
                color=SPINE_COLOR, markersize=4, label=f"{htw_model} {htw_hex}"
            )

            stages = [
                (30, pressure_30, result["torque_nm"] * 0.3, 7, "#5c9ecf"),
                (60, pressure_60, result["torque_nm"] * 0.6, 8, "#c9a24b"),
                (100, pressure_result, result["torque_nm"], 10, ACCENT_GREEN),
            ]

            for pct, stage_result, stage_torque_nm, marker_size, base_color in stages:
                point_color = "#e6a23c" if stage_result["out_of_range"] else base_color
                stage_pressure, stage_torque = self._convert_pt(
                    stage_result["pressure"], stage_torque_nm, unit_system
                )

                self.ax2.plot([stage_pressure], [stage_torque], marker="o", markersize=marker_size,
                              color=point_color, markerfacecolor=point_color, linestyle="None")

                self.ax2.annotate(
                    f"{pct}%: {stage_pressure:.1f} {pressure_unit}",
                    (stage_pressure, stage_torque), textcoords="offset points",
                    xytext=(10, -10 if pct == 100 else 8), ha="left", color="white", fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.3", fc=FIG_BG, ec=SPINE_COLOR, alpha=0.7)
                )

                self.ax2.axhline(stage_torque, color=GRID_COLOR, linewidth=0.6, linestyle="--")
                self.ax2.axvline(stage_pressure, color=GRID_COLOR, linewidth=0.6, linestyle="--")

            self.ax2.set_xlim(left=0)
            self.ax2.set_ylim(bottom=0)
            self.ax2.legend(facecolor=FIG_BG, edgecolor=SPINE_COLOR, labelcolor="white", fontsize=9)
        else:
            style_axes(self.ax2, "Pressure", "Torque")
            placeholder_text(self.ax2)

        self.canvas2.draw()

        # Update graph 3: yield utilization gauge
        max_load_lbf = result["yield_strength"] * result["tensile_area"]
        utilization_pct = (100 * result["bolt_load_lbf"] / max_load_lbf) if max_load_lbf else 0
        self.draw_yield_gauge(utilization_pct, result["bolt_load_lbf"], max_load_lbf)

    def clear_calculation(self):
        self.torque = 0
        self.one_third_torque = 0
        self.two_third_torque = 0
        self.pressure = 0

        self.result_value.configure(text="-- lb-ft")
        self.load_value.configure(text="-- lbf")
        self.nutfactor_value.configure(text="--")
        self.utilization_value.configure(text="--")
        pressure_unit = "psi" if self.unit_combobox.get() == "Imperial (lb-ft, lbf)" else "bar"
        self.pressure_value.configure(text=f"-- {pressure_unit}")

        try:
            reset_bolts = int(self.numbolts_combobox.get())
        except ValueError:
            reset_bolts = 8
        self.draw_default_tightening_diagram(reset_bolts)
        self.canvas.draw()

        self.ax2.clear()
        style_axes(self.ax2, "Pressure", "Torque")
        placeholder_text(self.ax2)
        self.canvas2.draw()

        self.draw_default_yield_gauge()


# ---------------------------------------------------------------------------
# Page 2: Hydraulic Bolt Tensioning calculator
# ---------------------------------------------------------------------------
class TensioningPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.passes_psi = {}
        self.passes_bar = {}

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkScrollableFrame(self, width=335)
        self.left_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=0)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.left_frame,
                                        text="Hydraulic Bolt Tensioning\nCalculator",
                                        font=("Arial", 18, "bold"),
                                        justify="left")
        self.title_label.pack(padx=(20, 30), pady=(15, 4), anchor="w")

        self.tensioning_equation = ctk.CTkLabel(self.left_frame,
                                                text="T = (F / A) · TLLF",
                                                font=ctk.CTkFont(size=17),
                                                text_color=ACCENT_GREEN)
        self.tensioning_equation.pack(padx=20, pady=(0, 10), anchor="w")

        self.bolttype_label = ctk.CTkLabel(self.left_frame, text="Bolt Material",
                                           font=("Arial", 12, "bold"), anchor="w")
        self.bolttype_label.pack(padx=20, pady=(6, 2), fill="x")
        self.bolttype_combobox = ctk.CTkComboBox(self.left_frame, values=BOLT_MATERIALS, width=200)
        self.bolttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.bolttype_combobox.set(BOLT_MATERIALS[0])

        self.utilfactor_label = ctk.CTkLabel(self.left_frame, text="Utilization Factor (P)",
                                             font=("Arial", 12, "bold"), anchor="w")
        self.utilfactor_label.pack(padx=20, pady=(6, 2), fill="x")
        self.utilfactor_entry = ctk.CTkEntry(self.left_frame, width=200, placeholder_text="e.g. 0.5")
        self.utilfactor_entry.insert(0, "0.5")
        self.utilfactor_entry.pack(padx=20, pady=(0, 4), fill="x")

        self.boltsize_label = ctk.CTkLabel(self.left_frame, text="Bolt Size (inch)",
                                           font=("Arial", 12, "bold"), anchor="w")
        self.boltsize_label.pack(padx=20, pady=(6, 2), fill="x")
        self.boltsize_combobox = ctk.CTkComboBox(self.left_frame, values=BOLT_SIZES, width=200)
        self.boltsize_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.boltsize_combobox.set(BOLT_SIZES[0])

        self.griplength_label = ctk.CTkLabel(self.left_frame, text="Grip Length (mm)",
                                             font=("Arial", 12, "bold"), anchor="w")
        self.griplength_label.pack(padx=20, pady=(6, 2), fill="x")
        self.griplength_entry = ctk.CTkEntry(self.left_frame, width=200, placeholder_text="e.g. 100")
        self.griplength_entry.insert(0, "100")
        self.griplength_entry.pack(padx=20, pady=(0, 4), fill="x")

        self.numbolts_label = ctk.CTkLabel(self.left_frame, text="Number of Bolts (for diagram)",
                                           font=("Arial", 12, "bold"), anchor="w")
        self.numbolts_label.pack(padx=20, pady=(6, 2), fill="x")
        self.numbolts_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=["4", "8", "12", "16", "20", "24", "28"],
                                                 width=200,
                                                 state="readonly")
        self.numbolts_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.numbolts_combobox.set("8")

        # Unit system selector
        self.unit_label = ctk.CTkLabel(self.left_frame, text="Unit system",
                                       font=("Arial", 12, "bold"), anchor="w")
        self.unit_label.pack(padx=20, pady=(4, 2), fill="x")
        self.unit_combobox = ctk.CTkComboBox(self.left_frame,
                                             values=["Metric (bar, N)", "Imperial (psi, lbf)"],
                                             width=200)
        self.unit_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.unit_combobox.set("Imperial (psi, lbf)")

        # Tensioner tool selection
        self.tool_section_label = ctk.CTkLabel(self.left_frame, text="Hydraulic Tensioner Tool",
                                               font=("Arial", 13, "bold"), text_color=ACCENT_GREEN, anchor="w")
        self.tool_section_label.pack(padx=20, pady=(4, 4), anchor="w")

        self.toolbrand_label = ctk.CTkLabel(self.left_frame, text="Tool Brand",
                                            font=("Arial", 12, "bold"), anchor="w")
        self.toolbrand_label.pack(padx=20, pady=(4, 2), fill="x")
        self.toolbrand_combobox = ctk.CTkComboBox(self.left_frame, values=get_tensioner_brands(),
                                                  width=200, command=self.on_tool_brand_change)
        self.toolbrand_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.toolbrand_combobox.set(get_tensioner_brands()[0])

        self.tool_label = ctk.CTkLabel(self.left_frame, text="Tool",
                                       font=("Arial", 12, "bold"), anchor="w")
        self.tool_label.pack(padx=20, pady=(6, 2), fill="x")
        initial_tools = get_tensioner_tools(get_tensioner_brands()[0])
        self.tool_combobox = ctk.CTkComboBox(self.left_frame, values=initial_tools, width=200)
        self.tool_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.tool_combobox.set(initial_tools[0])

        self.area_label = ctk.CTkLabel(self.left_frame,
                                       text=f"Hydraulic Area: {get_hydraulic_area(get_tensioner_brands()[0], 
                                                                                  initial_tools[0])} in²",
                                       font=("Arial", 11), text_color=ACCENT_GREEN, anchor="w")
        self.area_label.pack(padx=22, pady=(0, 10), anchor="w")
        self.tool_combobox.configure(command=self.on_tool_change)

        self.coverage_label = ctk.CTkLabel(self.left_frame, text="Coverage Pattern",
                                           font=("Arial", 12, "bold"), anchor="w")
        self.coverage_label.pack(padx=20, pady=(6, 2), fill="x")
        self.coverage_combobox = ctk.CTkComboBox(self.left_frame, values=list(COVERAGE_PASSES.keys()), width=200)
        self.coverage_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.coverage_combobox.set("50% Coverage")

        # Buttons
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(padx=20, pady=(4, 10), fill="x")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.calculate_button = ctk.CTkButton(self.button_frame, text="Calculate",
                                              command=self.calculate_tensioning_value,
                                              fg_color="#6E9451", hover_color="#465936")
        self.calculate_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.reset_button = ctk.CTkButton(self.button_frame, text="Reset",
                                          command=self.clear_calculation,
                                          fg_color="transparent", hover_color="#465936", border_width=1)
        self.reset_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Results bar
        self.results_frame = ctk.CTkFrame(self.right_frame, corner_radius=12)
        self.results_frame.grid(row=0, column=0, padx=16, pady=(16, 0), sticky="ew")
        for col in range(5):
            self.results_frame.grid_columnconfigure(col, weight=1)

        self.load_value = make_result_cell(self.results_frame, 0, "Bolt Load", "-- lbf")
        self.tllf_value = make_result_cell(self.results_frame, 1, "TLLF", "--")
        self.area_value = make_result_cell(self.results_frame, 2, "Hydraulic Area", "-- in²")
        self.target_value = make_result_cell(self.results_frame, 3, "Target Pressure", "-- psi", ACCENT_GREEN)
        self.passa_value = make_result_cell(self.results_frame, 4, "Pass A Pressure", "-- psi", PASS_COLORS["A"])

        # Tabview holding the bar chart + bolt pattern diagram
        self.tabview = ctk.CTkTabview(self.right_frame,
                                      segmented_button_selected_color="#576E51",
                                      segmented_button_selected_hover_color="#6F945F")
        self.tabview.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        self.tab_passes = self.tabview.add("Pass Pressures")
        self.tab_pattern = self.tabview.add("Bolt Pattern")

        self.tab_passes.grid_rowconfigure(0, weight=1)
        self.tab_passes.grid_columnconfigure(0, weight=1)
        self.tab_pattern.grid_rowconfigure(0, weight=1)
        self.tab_pattern.grid_columnconfigure(0, weight=1)

        # Graph 1: bar chart of pass pressures
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor(FIG_BG)
        self.ax: Axes = self.fig.add_subplot(111)
        style_axes(self.ax, "Pass", "Pressure")
        placeholder_text(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_passes)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas.draw()

        # Graph 2: bolt pattern diagram around the flange
        self.fig2 = Figure(figsize=(5, 4), dpi=100)
        self.fig2.patch.set_facecolor(FIG_BG)
        self.ax2: Axes = self.fig2.add_subplot(111)
        self.ax2.set_facecolor(FIG_BG)
        self.ax2.set_aspect("equal")
        self.ax2.axis("off")

        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab_pattern)
        self.canvas2.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.draw_default_bolt_pattern(8)
        self.canvas2.draw()

    def on_tool_brand_change(self, brand):
        tools = get_tensioner_tools(brand)
        self.tool_combobox.configure(values=tools)
        self.tool_combobox.set(tools[0])
        self.on_tool_change(tools[0])

    def on_tool_change(self, tool):
        brand = self.toolbrand_combobox.get()
        area = get_hydraulic_area(brand, tool)
        self.area_label.configure(text=f"Hydraulic Area: {area} in²" if area else "Hydraulic Area: --")

    def calculate_tensioning_value(self):
        bolt_material = self.bolttype_combobox.get()
        bolt_size = self.boltsize_combobox.get()
        brand = self.toolbrand_combobox.get()
        tool = self.tool_combobox.get()
        coverage = self.coverage_combobox.get()
        unit_system = self.unit_combobox.get()

        try:
            utilization_factor = float(self.utilfactor_entry.get())
        except ValueError:
            self.target_value.configure(text="Invalid utilization factor")
            return

        try:
            grip_length_mm = float(self.griplength_entry.get())
        except ValueError:
            grip_length_mm = 0
        grip_length = grip_length_mm / 25.4

        try:
            num_bolts = int(self.numbolts_combobox.get())
        except ValueError:
            num_bolts = 8

        if grip_length <= 0:
            self.target_value.configure(text="Invalid grip length")
            return
        if num_bolts <= 0:
            self.target_value.configure(text="Invalid bolt count")
            return

        result = calculate_tensioning(bolt_material, utilization_factor, bolt_size, grip_length,
                                      brand, tool, coverage, unit_system)

        self.passes_psi = result["passes_psi"]
        self.passes_bar = result["passes_bar"]
        unit = result["unit"]

        self.load_value.configure(text=f"{result['bolt_load']:.1f} {result['bolt_load_unit']}")
        self.tllf_value.configure(text=f"{result['tllf']:.3f}")
        self.area_value.configure(text=f"{result['area_in2']:.2f} in²")

        passes = result["passes"]
        # Target pressure is the last-lettered pass tensioned (the calculated base value)
        base_letter = COVERAGE_PASSES[coverage][-1]
        self.target_value.configure(text=f"{passes[base_letter]:.1f} {unit} (Pass {base_letter})")
        self.passa_value.configure(text=f"{passes['A']:.1f} {unit}")

        # --- Bar chart of pass pressures ---
        self.ax.clear()
        style_axes(self.ax, "Tensioning Pass", f"Pressure ({unit})")

        pass_letters = COVERAGE_PASSES[coverage]
        pass_values = [passes[letter] for letter in pass_letters]
        bar_colors = [PASS_COLORS[letter] for letter in pass_letters]
        order_labels = [f"Pass {letter}\n({i + 1} of {len(pass_letters)})" for i, letter in enumerate(pass_letters)]

        bars = self.ax.bar(order_labels, pass_values, color=bar_colors, edgecolor=FIG_BG)
        for bar, value in zip(bars, pass_values):
            self.ax.annotate(
                f"{value:.1f} {unit}",
                (bar.get_x() + bar.get_width() / 2, value),
                textcoords="offset points", xytext=(0, 6), ha="center",
                color="white", fontsize=10
            )
        self.ax.set_ylim(bottom=0)
        self.canvas.draw()

        # --- Bolt pattern diagram ---
        bolt_pass_assignment = assign_bolt_passes(num_bolts, coverage)

        self.ax2.clear()
        self.ax2.set_facecolor(FIG_BG)
        self.ax2.set_aspect("equal")
        self.ax2.axis("off")

        flange_radius = 1.0
        bolt_marker_radius = 0.09

        # Flange body (outer plate + bolt circle) purely for visual context
        self.ax2.add_patch(Circle((0, 0), flange_radius + 0.16, facecolor="#3a3a3a",
                                  edgecolor=SPINE_COLOR, linewidth=1.2, zorder=1))
        self.ax2.add_patch(Circle((0, 0), 0.22, facecolor=FIG_BG,
                                  edgecolor=SPINE_COLOR, linewidth=1.0, zorder=2))

        for i in range(num_bolts):
            angle = math.pi / 2 - (2 * math.pi * i / num_bolts)  # start at top, go clockwise
            x = flange_radius * math.cos(angle)
            y = flange_radius * math.sin(angle)

            letter = bolt_pass_assignment[i]
            color = PASS_COLORS[letter]
            pressure_val = passes[letter]

            self.ax2.add_patch(Circle((x, y), bolt_marker_radius, facecolor=color,
                                      edgecolor="white", linewidth=1.0, zorder=3))
            self.ax2.text(x, y, letter, ha="center", va="center", color="black",
                          fontsize=9, fontweight="bold", zorder=4)

            label_x = (flange_radius + 0.32) * math.cos(angle)
            label_y = (flange_radius + 0.32) * math.sin(angle)
            self.ax2.text(label_x, label_y, f"#{i + 1}\n{pressure_val:.0f} {unit}",
                          ha="center", va="center", color="white", fontsize=7.5, zorder=4)

        legend_handles = [
            Circle((0, 0), 1, facecolor=PASS_COLORS[letter],
                   edgecolor="white", label=f"Pass {letter}: {passes[letter]:.1f} {unit}")
            for letter in pass_letters
        ]
        self.ax2.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                        ncol=len(pass_letters), facecolor=FIG_BG, edgecolor=SPINE_COLOR,
                        labelcolor="white", fontsize=8, handlelength=1, handleheight=1)

        margin = flange_radius + 0.55
        self.ax2.set_xlim(-margin, margin)
        self.ax2.set_ylim(-margin, margin)

        self.canvas2.draw()

    def draw_default_bolt_pattern(self, num_bolts=8):
        """Neutral bolt-circle preview shown before any calculation has run,
        so the tab isn't just empty text."""
        self.ax2.clear()
        self.ax2.set_facecolor(FIG_BG)
        self.ax2.set_aspect("equal")
        self.ax2.axis("off")

        flange_radius = 1.0
        bolt_marker_radius = 0.09

        self.ax2.add_patch(Circle((0, 0), flange_radius + 0.16, facecolor="#3a3a3a",
                                  edgecolor=SPINE_COLOR, linewidth=1.2, zorder=1))
        self.ax2.add_patch(Circle((0, 0), 0.22, facecolor=FIG_BG,
                                  edgecolor=SPINE_COLOR, linewidth=1.0, zorder=2))

        for i in range(num_bolts):
            angle = math.pi / 2 - (2 * math.pi * i / num_bolts)
            x = flange_radius * math.cos(angle)
            y = flange_radius * math.sin(angle)

            self.ax2.add_patch(Circle((x, y), bolt_marker_radius, facecolor=SPINE_COLOR,
                                      edgecolor="white", linewidth=1.0, zorder=3))
            self.ax2.text(x, y, str(i + 1), ha="center", va="center", color="white",
                          fontsize=8, fontweight="bold", zorder=4)

        self.ax2.text(0, -(flange_radius + 0.4), "Enter values and click Calculate",
                      ha="center", va="center", color="#888888", fontsize=10)

        margin = flange_radius + 0.55
        self.ax2.set_xlim(-margin, margin)
        self.ax2.set_ylim(-margin, margin)

    def clear_calculation(self):
        self.passes_psi = {}
        self.passes_bar = {}

        self.load_value.configure(text="-- lbf")
        self.tllf_value.configure(text="--")
        self.area_value.configure(text="-- in²")
        self.target_value.configure(text="-- psi")
        self.passa_value.configure(text="-- psi")

        self.ax.clear()
        style_axes(self.ax, "Pass", "Pressure")
        placeholder_text(self.ax)
        self.canvas.draw()

        try:
            reset_bolts = int(self.numbolts_combobox.get())
        except ValueError:
            reset_bolts = 8
        self.draw_default_bolt_pattern(reset_bolts)
        self.canvas2.draw()


# ---------------------------------------------------------------------------
# App shell: nav bar + page switching
# ---------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FlangeCalc")
        self.geometry(f"{appWidth}x{appHeight}")
        self.iconbitmap(ASSETS_DIR / "icon.ico")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # Navigation bar to switch between calculator pages
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.grid(row=0, column=0, padx=20, pady=(16, 0), sticky="w")

        self.nav_selector = ctk.CTkSegmentedButton(
            self.nav_frame,
            values=["Torque Wrench", "Bolt Tensioning"],
            command=self.show_page,
            selected_color="#6E9451",
            selected_hover_color="#465936",
        )
        self.nav_selector.pack()
        self.nav_selector.set("Torque Wrench")

        # Container that both pages share the same grid cell in
        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

        self.torque_page = TorquePage(self.page_container)
        self.tensioning_page = TensioningPage(self.page_container)

        self.torque_page.grid(row=0, column=0, sticky="nsew")
        self.tensioning_page.grid(row=0, column=0, sticky="nsew")

        self.show_page("Torque Wrench")

    def show_page(self, selection):
        if selection == "Torque Wrench":
            self.torque_page.tkraise()
        else:
            self.tensioning_page.tkraise()


app = App()
app.mainloop()
