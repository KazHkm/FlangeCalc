import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from calculations import calculate_torque, calculate_pressure
from htw_data import (get_brands, get_models, get_hex_sizes, bar_to_psi, nm_to_lbft)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

appWidth, appHeight = 1200, 800


# App Class
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.torque = 0
        self.one_third_torque = 0
        self.two_third_torque = 0
        self.pressure = 0

        self.title("FlangeCalc")
        self.geometry(f"{appWidth}x{appHeight}")

        # Grid layout (left = inputs, right = result, graph)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame for user input and text result
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.left_frame.grid_propagate(False)

        # Frame to display the graphs
        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=0)  # results bar
        self.right_frame.grid_rowconfigure(1, weight=1)  # tabview
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.left_frame,
                                        text="Bolted-Flange Torque Calculator",
                                        font=("Arial", 18, "bold"))
        self.title_label.pack(padx=(20, 30), pady=(24, 4), anchor="w")

        self.torque_equation = ctk.CTkLabel(self.left_frame,
                                            text="T = F · K · D",
                                            font=ctk.CTkFont(size=17),
                                            text_color="#8ce99a")
        self.torque_equation.pack(padx=20, pady=(0, 10), anchor="w")

        # Labels and comboboxes for input
        self.bolttype_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Material",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.bolttype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.bolttype_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=["ASTM A193 - B7",
                                                         "ASTM A193 - B7M",
                                                         "ASTM A193 - B16",
                                                         "ASTM A193 - L7",
                                                         "ASTM A193 - L7M",
                                                         "ISO 3506-1 - A2-70 (304SS)",
                                                         "ISO 3506-1 - A4-70 (304SS)",
                                                         "ASTM A193 - B8 Class 1",
                                                         "ASTM A193 - B8M Class 1"],
                                                 width=200)
        self.bolttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.bolttype_combobox.set("ASTM A193 - B7")

        self.gaskettype_label = ctk.CTkLabel(self.left_frame,
                                             text="Gasket Type",
                                             font=("Arial", 12, "bold"),
                                             anchor="w")
        self.gaskettype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.gaskettype_combobox = ctk.CTkComboBox(self.left_frame,
                                                   values=["Spiral Wound", "CNAF", "Rubber", "RTJ", "Teflon"],
                                                   width=200)
        self.gaskettype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.gaskettype_combobox.set("Spiral Wound")

        self.lubricanttype_label = ctk.CTkLabel(self.left_frame,
                                                text="Lubricant",
                                                font=("Arial", 12, "bold"),
                                                anchor="w")
        self.lubricanttype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.lubricanttype_combobox = ctk.CTkComboBox(self.left_frame,
                                                      values=["Molykote 1000",
                                                              "Molykote P37",
                                                              "Copa Slip",
                                                              "PTFE Coated",
                                                              "No Lubricant"],
                                                      width=200)
        self.lubricanttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.lubricanttype_combobox.set("Molykote 1000")

        self.boltsize_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Size (inch)",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.boltsize_label.pack(padx=20, pady=(6, 2), fill="x")

        self.boltsize_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=["1/2",
                                                         "5/8",
                                                         "3/4",
                                                         "7/8",
                                                         "1",
                                                         "1 1/8",
                                                         "1 1/4",
                                                         "1 3/8",
                                                         "1 1/2"],
                                                 width=200,
                                                 command=self.update_htw_state)
        self.boltsize_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.boltsize_combobox.set("1/2")

        # Unit system selector
        self.unit_label = ctk.CTkLabel(self.left_frame,
                                       text="Unit system",
                                       font=("Arial", 12, "bold"),
                                       anchor="w")
        self.unit_label.pack(padx=20, pady=(6, 2), fill="x")

        self.unit_combobox = ctk.CTkComboBox(self.left_frame,
                                             values=["Metric (N·m, N)", "Imperial (lb-ft, lbf)"],
                                             width=200)
        self.unit_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.unit_combobox.set("Imperial (lb-ft, lbf)")

        # Hydraulic Torque Wrench selection (brand -> model -> hex size)
        self.htw_section_label = ctk.CTkLabel(self.left_frame,
                                              text='Hydraulic Torque Wrench (Bolt Size > 1")',
                                              font=("Arial", 13, "bold"),
                                              text_color="#8ce99a",
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

        self.htwmodel_label = ctk.CTkLabel(self.left_frame,
                                           text="HTW Model",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.htwmodel_label.pack(padx=20, pady=(6, 2), fill="x")

        self.htwmodel_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=get_models(get_brands()[0]),
                                                 width=200,
                                                 command=self.on_model_change)
        self.htwmodel_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.htwmodel_combobox.set(get_models(get_brands()[0])[0])

        self.htwhex_label = ctk.CTkLabel(self.left_frame,
                                         text="Hex Drive Size",
                                         font=("Arial", 12, "bold"),
                                         anchor="w")
        self.htwhex_label.pack(padx=20, pady=(6, 2), fill="x")

        initial_hex_sizes = get_hex_sizes(get_brands()[0], get_models(get_brands()[0])[0])
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

        def _make_result_cell(parent, column, title, initial_value, value_color="white"):
            title_label = ctk.CTkLabel(parent, text=title, font=("Arial", 12), text_color="#aaaaaa")
            title_label.grid(row=0, column=column, sticky="ew", padx=10, pady=(10, 0))
            value_label = ctk.CTkLabel(parent, text=initial_value, font=("Arial", 16, "bold"), text_color=value_color)
            value_label.grid(row=1, column=column, sticky="ew", padx=10, pady=(0, 10))
            return value_label

        self.result_value = _make_result_cell(self.results_frame, 0, "Torque", "-- lb-ft", "#8CE99A")
        self.load_value = _make_result_cell(self.results_frame, 1, "Bolt Load", "-- lbf")
        self.nutfactor_value = _make_result_cell(self.results_frame, 2, "Nut Factor (K)", "--")
        self.utilization_value = _make_result_cell(self.results_frame, 3, "Utilization Factor (P)", "--")
        self.pressure_value = _make_result_cell(self.results_frame, 4, "HTW Pressure", "-- bar", "#8CE99A")

        # Tabview holding the two graphs
        self.tabview = ctk.CTkTabview(self.right_frame,
                                      segmented_button_selected_color="#576E51",
                                      segmented_button_selected_hover_color="#6F945F")
        self.tabview.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        self.tab_tightening = self.tabview.add("Torque → Tightening Progress")
        self.tab_pressure = self.tabview.add("Torque → Pressure (HTW)")

        self.tab_tightening.grid_rowconfigure(0, weight=1)
        self.tab_tightening.grid_columnconfigure(0, weight=1)
        self.tab_pressure.grid_rowconfigure(0, weight=1)
        self.tab_pressure.grid_columnconfigure(0, weight=1)

        # Graph 1: torque vs tightening progress
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor("#2b2b2b")
        self.ax: Axes = self.fig.add_subplot(111)
        self._style_axes(self.ax, "Tightening Progress (%)", "Torque")
        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(0, 100)
        self._placeholder_text(self.ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_tightening)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas.draw()

        # Graph 2: torque vs pressure interpolation curve (HTW)
        self.fig2 = Figure(figsize=(5, 4), dpi=100)
        self.fig2.patch.set_facecolor("#2b2b2b")
        self.ax2: Axes = self.fig2.add_subplot(111)
        self._style_axes(self.ax2, "Pressure", "Torque")
        self._placeholder_text(self.ax2)

        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab_pressure)
        self.canvas2.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas2.draw()

        # HTW combobox chaining

    def on_brand_change(self, brand):
        models = get_models(brand)
        self.htwmodel_combobox.configure(values=models)
        self.htwmodel_combobox.set(models[0])
        self.on_model_change(models[0])

    def on_model_change(self, model):
        brand = self.htwbrand_combobox.get()
        hex_sizes = get_hex_sizes(brand, model)
        self.htwhex_combobox.configure(values=hex_sizes)
        self.htwhex_combobox.set(hex_sizes[0])

    def update_htw_state(self, *_):
        large_bolts = ["1 1/8", "1 1/4", "1 3/8", "1 1/2"]

        state = "normal" if self.boltsize_combobox.get() in large_bolts else "disabled"

        self.htwbrand_combobox.configure(state=state)
        self.htwmodel_combobox.configure(state=state)
        self.htwhex_combobox.configure(state=state)

        # Shared axis styling helpers

    @staticmethod
    def _style_axes(ax: Axes, xlabel: str, ylabel: str):
        ax.set_facecolor("#2b2b2b")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#666666")
        ax.set_xlabel(xlabel, color="white")
        ax.set_ylabel(ylabel, color="white")
        ax.grid(True, color="#444444", linewidth=0.6)

    @staticmethod
    def _placeholder_text(ax: Axes):
        ax.text(
            0.5, 0.5, "Enter values and click Calculate",
            transform=ax.transAxes, ha="center", va="center",
            color="#888888", fontsize=11
        )

    # Convert a pressure/torque pair from bar/N·m into whichever unit system is currently selected
    # Keep every downstream use of a pressure/torque pair going through this so nothing ends up mixing converted
    # and unconverted values
    @staticmethod
    def _convert_pt(pressure_bar, torque_nm, unit_system):

        if unit_system == "Imperial (lb-ft, in, lbf)":
            return bar_to_psi(pressure_bar), nm_to_lbft(torque_nm)

        return pressure_bar, torque_nm

    # Main calculation
    def calculate_torque_value(self):
        bolt_material = self.bolttype_combobox.get()
        gasket_type = self.gaskettype_combobox.get()
        lubricant = self.lubricanttype_combobox.get()
        bolt_size = self.boltsize_combobox.get()

        large_bolts = ["1 1/8", "1 1/4", "1 3/8", "1 1/2"]
        use_htw = bolt_size in large_bolts

        unit_system = self.unit_combobox.get()

        htw_brand = self.htwbrand_combobox.get()
        htw_model = self.htwmodel_combobox.get()
        htw_hex = self.htwhex_combobox.get()

        # Call calculations.py
        result = calculate_torque(
            bolt_material,
            gasket_type,
            lubricant,
            bolt_size,
            unit_system
        )

        self.torque = result["torque"]
        self.one_third_torque = result["30_percent"]
        self.two_third_torque = result["60_percent"]

        # Default values (for smaller bolts without HTW)
        pressure_result = None
        pressure_30 = None
        pressure_60 = None

        if use_htw:
            pressure_result = calculate_pressure(
                result["torque_nm"],
                htw_brand,
                htw_model,
                htw_hex
            )

            self.pressure = pressure_result["pressure"]

            pressure_30 = calculate_pressure(
                result["torque_nm"] * 0.3,
                htw_brand,
                htw_model,
                htw_hex
            )

            pressure_60 = calculate_pressure(
                result["torque_nm"] * 0.6,
                htw_brand,
                htw_model,
                htw_hex
            )

        else:
            self.pressure = 0

        # Display the results
        self.result_value.configure(text=f"{self.torque:.2f} {result['unit']}")
        self.load_value.configure(text=f"{result['bolt_load']:.2f} {result['bolt_load_unit']}")
        self.nutfactor_value.configure(text=f"{result['nut_factor']:.2f}")
        self.utilization_value.configure(text=f"{result['utilization_factor']:.2f}")

        pressure_unit = "psi" if unit_system == "Imperial (lb-ft, lbf)" else "bar"

        if use_htw:
            display_pressure = bar_to_psi(self.pressure) if pressure_unit == "psi" else self.pressure
            pressure_text = f"{display_pressure:.1f} {pressure_unit}"

            if pressure_result["out_of_range"]:
                pressure_text += " (out of chart range)"
        else:
            pressure_text = f"-- {pressure_unit}"

        self.pressure_value.configure(text=pressure_text)

        # Update graph 1: tightening progress
        self.ax.clear()
        self._style_axes(self.ax, "Tightening Progress (%)", f"Torque ({result['unit']})")

        x_values = [0, 30, 60, 100]
        y_values = [0, self.one_third_torque, self.two_third_torque, self.torque]

        self.ax.plot(x_values, y_values, marker="o", linewidth=2,
                     color="#8CE99A", markersize=8, markerfacecolor="#517343")

        for x, y in zip(x_values[1:], y_values[1:]):
            self.ax.annotate(
                f"{x}%: {y:.2f} {result['unit']}",
                (x, y), textcoords="offset points", xytext=(0, 10),
                ha="center", color="white", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", fc="#2b2b2b", ec="#666666", alpha=0.7)
            )

        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(bottom=0)
        self.canvas.draw()

        # Update graph 2: HTW torque -> pressure interpolation
        self.ax2.clear()

        if use_htw:
            table = pressure_result["table"]
            imperial = unit_system == "Imperial (lb-ft, lbf)"
            pressure_unit = "psi" if imperial else "bar"
            torque_unit = "lb-ft" if imperial else "N·m"

            # Vendor curve, converted in one pass so pressure/torque (always stay paired correctly)
            chart_pressures, chart_torques = zip(
                *[self._convert_pt(p, t, unit_system) for p, t in table]
            )

            self._style_axes(self.ax2, f"Pressure ({pressure_unit})", f"Torque ({torque_unit})")

            self.ax2.plot(
                chart_pressures,
                chart_torques,
                marker="o",
                linewidth=1.5,
                color="#666666",
                markersize=4,
                label=f"{htw_model} {htw_hex}"
            )

            stages = [
                (30, pressure_30, result["torque_nm"] * 0.3, 7, "#5c9ecf"),
                (60, pressure_60, result["torque_nm"] * 0.6, 8, "#c9a24b"),
                (100, pressure_result, result["torque_nm"], 10, "#8CE99A"),
            ]

            for pct, stage_result, stage_torque_nm, marker_size, base_color in stages:
                point_color = "#e6a23c" if stage_result["out_of_range"] else base_color
                stage_pressure, stage_torque = self._convert_pt(
                    stage_result["pressure"], stage_torque_nm, unit_system
                )

                self.ax2.plot(
                    [stage_pressure],
                    [stage_torque],
                    marker="o",
                    markersize=marker_size,
                    color=point_color,
                    markerfacecolor=point_color,
                    linestyle="None"
                )

                self.ax2.annotate(
                    f"{pct}%: {stage_pressure:.1f} {pressure_unit}",
                    (stage_pressure, stage_torque),
                    textcoords="offset points",
                    xytext=(10, -10 if pct == 100 else 8),
                    ha="left",
                    color="white",
                    fontsize=9,
                    bbox=dict(
                        boxstyle="round,pad=0.3",
                        fc="#2b2b2b",
                        ec="#666666",
                        alpha=0.7
                    )
                )

                self.ax2.axhline(stage_torque,
                                 color="#444444",
                                 linewidth=0.6,
                                 linestyle="--")

                self.ax2.axvline(stage_pressure,
                                 color="#444444",
                                 linewidth=0.6,
                                 linestyle="--")

            self.ax2.set_xlim(left=0)
            self.ax2.set_ylim(bottom=0)

            self.ax2.legend(
                facecolor="#2b2b2b",
                edgecolor="#666666",
                labelcolor="white",
                fontsize=9
            )

        else:
            self._style_axes(self.ax2, "Pressure", "Torque")
            self._placeholder_text(self.ax2)

        self.canvas2.draw()

    def clear_calculation(self):

        # Reset stored values
        self.torque = 0
        self.one_third_torque = 0
        self.two_third_torque = 0
        self.pressure = 0

        # Reset displayed results
        self.result_value.configure(text="-- lb-ft")
        self.load_value.configure(text="-- lbf")
        self.nutfactor_value.configure(text="--")
        self.utilization_value.configure(text="--")
        pressure_unit = "psi" if self.unit_combobox.get() == "Imperial (lb-ft, lbf)" else "bar"
        self.pressure_value.configure(text=f"-- {pressure_unit}")

        # Clear graph 1
        self.ax.clear()
        self._style_axes(self.ax, "Tightening Progress (%)", "Torque")
        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(0, 100)
        self._placeholder_text(self.ax)
        self.canvas.draw()

        # Clear graph 2
        self.ax2.clear()
        self._style_axes(self.ax2, "Pressure", "Torque")
        self._placeholder_text(self.ax2)
        self.canvas2.draw()


app = App()
app.mainloop()