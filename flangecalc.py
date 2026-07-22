import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from calculations import calculate_torque

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

        self.title("FlangeCalc")
        self.geometry(f"{appWidth}x{appHeight}")

        # Grid layout: left = inputs & result, right = graph
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame for user input and text result
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.left_frame.grid_propagate(False)

        # Frame to display the graph
        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.left_frame,
                                        text="Bolted-Flange Torque Calculator",
                                        font=("Arial", 18, "bold"))
        self.title_label.pack(padx=20, pady=(24, 4), anchor="w")

        self.torque_equation = ctk.CTkLabel(self.left_frame,
                                            text="T = F · K · D",
                                            font=ctk.CTkFont(size=15),
                                            text_color="#8ce99a")
        self.torque_equation.pack(padx=20, pady=(0, 20), anchor="w")

        # Labels and comboboxes for input
        self.bolttype_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Material",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.bolttype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.bolttype_combobox = ctk.CTkComboBox(self.left_frame,
                                                 values=['ASTM A193 - B7', 'ASTM A193 - B8 C2'],
                                                 width=200)
        self.bolttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.bolttype_combobox.set("ASTM A193 - B7")

        self.gaskettype_label = ctk.CTkLabel(self.left_frame,
                                             text="Gasket Type",
                                             font=("Arial", 12, "bold"),
                                             anchor="w")
        self.gaskettype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.gaskettype_combobox = ctk.CTkComboBox(self.left_frame,
                                                   values=["Spiral Wound", "CNAF", "Rubber", "RTJ"],
                                                   width=200)
        self.gaskettype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.gaskettype_combobox.set("Spiral Wound")

        self.lubricanttype_label = ctk.CTkLabel(self.left_frame,
                                                text="Lubricant",
                                                font=("Arial", 12, "bold"),
                                                anchor="w")
        self.lubricanttype_label.pack(padx=20, pady=(6, 2), fill="x")

        self.lubricanttype_combobox = ctk.CTkComboBox(self.left_frame,
                                                      values=["Molykote 1000", "Molykote P37"],
                                                      width=200)
        self.lubricanttype_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.lubricanttype_combobox.set("Molykote 1000")

        self.boltsize_label = ctk.CTkLabel(self.left_frame,
                                           text="Bolt Size (inch)",
                                           font=("Arial", 12, "bold"),
                                           anchor="w")
        self.boltsize_label.pack(padx=20, pady=(6, 2), fill="x")

        self.boltsize_combobox = ctk.CTkComboBox(self.left_frame, values=["1/2", "5/8", "3/4"], width=200)
        self.boltsize_combobox.pack(padx=20, pady=(0, 4), fill="x")
        self.boltsize_combobox.set("1/2")

        # Unit system selector
        self.unit_label = ctk.CTkLabel(self.left_frame,
                                       text="Unit system",
                                       font=("Arial", 12, "bold"),
                                       anchor="w")
        self.unit_label.pack(padx=20, pady=(6, 2), fill="x")

        self.unit_combobox = ctk.CTkComboBox(self.left_frame,
                                             values=["Metric (N·m, mm, N)", "Imperial (lb-ft, in, lbf)"],
                                             width=200)
        self.unit_combobox.pack(padx=20, pady=(0, 20), fill="x")
        self.unit_combobox.set("Imperial (lb-ft, in, lbf)")

        # Frame to display the buttons ("Calculate" & "Reset")
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(padx=20, pady=(4, 10), fill="x")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.calculateTorque_button = ctk.CTkButton(self.button_frame,
                                                    text='Calculate',
                                                    command=self.calculate_torque_value,
                                                    fg_color="#6e9451",
                                                    hover_color="#465936")
        self.calculateTorque_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.reset_button = ctk.CTkButton(self.button_frame,
                                          text="Reset",
                                          command=self.clear_calculation,
                                          fg_color="transparent",
                                          hover_color="#465936",
                                          border_width=1)
        self.reset_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Frame to display the results (Torque, Bolt Load, Nut Factor & Utilization Factor)
        self.results_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.results_frame.pack(padx=20, pady=(20, 0), fill="x")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(1, weight=1)

        # Torque
        self.result_label = ctk.CTkLabel(self.results_frame,
                                         text="Torque:",
                                         font=("Arial", 16, "bold"),
                                         text_color="white",
                                         anchor="w")
        self.result_label.grid(row=0, column=0, sticky="w", pady=4)

        self.result_value = ctk.CTkLabel(self.results_frame,
                                         text="-- lb-ft",
                                         font=("Arial", 16, "bold"),
                                         text_color="#8CE99A",
                                         anchor="e")
        self.result_value.grid(row=0, column=1, sticky="e", pady=4)

        # Bolt Load
        self.load_label = ctk.CTkLabel(self.results_frame,
                                       text="Bolt Load:",
                                       font=("Arial", 16, "bold"),
                                       text_color="white",
                                       anchor="w")
        self.load_label.grid(row=1, column=0, sticky="w", pady=4)

        self.load_value = ctk.CTkLabel(self.results_frame,
                                       text="-- lbf",
                                       font=("Arial", 16, "bold"),
                                       text_color="white",
                                       anchor="e")
        self.load_value.grid(row=1, column=1, sticky="e", pady=4)

        # Nut Factor
        self.nutfactor_label = ctk.CTkLabel(self.results_frame,
                                            text="Nut Factor (K):",
                                            font=("Arial", 16, "bold"),
                                            text_color="white",
                                            anchor="w")
        self.nutfactor_label.grid(row=2, column=0, sticky="w", pady=4)

        self.nutfactor_value = ctk.CTkLabel(self.results_frame,
                                            text="--",
                                            font=("Arial", 16, "bold"),
                                            text_color="white",
                                            anchor="e")
        self.nutfactor_value.grid(row=2, column=1, sticky="e", pady=4)

        # Utilization Factor
        self.utilization_label = ctk.CTkLabel(self.results_frame,
                                              text="Utilization Factor (P):",
                                              font=("Arial", 16, "bold"),
                                              text_color="white",
                                              anchor="w")
        self.utilization_label.grid(row=3, column=0, sticky="w", pady=4)

        self.utilization_value = ctk.CTkLabel(self.results_frame,
                                              text="--",
                                              font=("Arial", 16, "bold"),
                                              text_color="white",
                                              anchor="e")
        self.utilization_value.grid(row=3, column=1, sticky="e", pady=4)

        # Build graph
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor("#2b2b2b")

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#2b2b2b")
        self.ax.tick_params(colors="white")

        for spine in self.ax.spines.values():
            spine.set_color("#666666")

        self.ax.set_xlabel("Tightening Progress (%)", color="white")
        self.ax.set_ylabel("Torque", color="white")
        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(0, 100)

        self.ax.grid(True, color="#444444", linewidth=0.6)

        self.ax.text(
            0.5, 0.5, "Enter values and click Calculate",
            transform=self.ax.transAxes, ha="center", va="center",
            color="#888888", fontsize=11
        )

        # Canvas for graph
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.canvas.draw()

    def calculate_torque_value(self):
        bolt_material = self.bolttype_combobox.get()
        gasket_type = self.gaskettype_combobox.get()
        lubricant = self.lubricanttype_combobox.get()
        bolt_size = self.boltsize_combobox.get()
        unit_system = self.unit_combobox.get()

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

        # Display the results
        self.result_value.configure(text=f"{self.torque:.2f} {result['unit']}")
        self.load_value.configure(text=f"{result['bolt_load']:.2f} {result['bolt_load_unit']}")
        self.nutfactor_value.configure(text=f"{result['nut_factor']:.2f}")
        self.utilization_value.configure(text=f"{result['utilization_factor']:.2f}")

        # Update the graph
        self.ax.clear()

        self.ax.set_facecolor("#2b2b2b")
        self.ax.tick_params(colors="white")

        for spine in self.ax.spines.values():
            spine.set_color("#666666")

        # Tightening percentage points (30%, 60% & 100%)
        x_values = [0, 30, 60, 100]

        # Corresponding torque values
        y_values = [
            0,
            self.one_third_torque,
            self.two_third_torque,
            self.torque
        ]

        # Plot the curve
        self.ax.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=2,
            color="#8CE99A",
            markersize=8,
            markerfacecolor="#517343"
        )

        # Add value labels on each point
        for x, y in zip(x_values[1:], y_values[1:]):
            self.ax.annotate(
                f"{x}%: {y:.2f} {result['unit']}",
                (x, y),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                color="white",
                fontsize=10,
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    fc="#2b2b2b",
                    ec="#666666",
                    alpha=0.7
                )
            )

        # Axis labels
        self.ax.set_xlabel("Tightening Progress (%)", color="white")
        self.ax.set_ylabel(f"Torque ({result['unit']})", color="white")
        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(bottom=0)

        self.ax.grid(True, color="#444444", linewidth=0.6)

        self.canvas.draw()

    def clear_calculation(self):

        # Reset stored values
        self.torque = 0
        self.one_third_torque = 0
        self.two_third_torque = 0

        # Reset displayed results
        self.result_value.configure(text="-- lb-ft")
        self.load_value.configure(text="-- lbf")
        self.nutfactor_value.configure(text="--")
        self.utilization_value.configure(text="--")

        # Clear the graph
        self.ax.clear()

        self.ax.set_facecolor("#2b2b2b")
        self.ax.tick_params(colors="white")

        for spine in self.ax.spines.values():
            spine.set_color("#666666")

        self.ax.set_xlabel("Tightening Progress (%)", color="white")
        self.ax.set_ylabel("Torque", color="white")
        self.ax.set_xlim(0, 100)
        self.ax.set_xticks(range(0, 101, 10))
        self.ax.set_ylim(0, 100)

        self.ax.grid(True, color="#444444", linewidth=0.6)

        self.ax.text(
            0.5, 0.5,
            "Enter values and click Calculate",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color="#888888",
            fontsize=11
        )

        self.canvas.draw()


app = App()
app.mainloop()