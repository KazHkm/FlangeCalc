# FlangeCalc

A Python-based engineering GUI application for calculating **bolted flange torque** and **hydraulic torque wrench pressure**.

FlangeCalc was developed as a personal engineering project to simplify common bolted-flange calculations and provide a quick visual reference for torque and hydraulic pressure requirements.

> **Project Status:** Initial public release / Work in Progress

---

## Features

* Bolted flange torque calculation
* Torque calculation based on bolt load, bolt diameter, and nut factor
* Hydraulic torque wrench (HTW) pressure calculation
* Support for different torque and pressure units
* Graphical visualization of torque and pressure relationships

---

## Screenshots

*Screenshots will be added soon.*

---

## Demo

*Demo GIF will be added soon.*

---

## Installation

### Clone the repository

```bash
git clone https://github.com/KazHkm/FlangeCalc.git
cd FlangeCalc
```

### Install the required packages

```bash
pip install customtkinter matplotlib numpy
```

### Run the application

```bash
python flangecalc.py
```

---

## Technologies Used

* Python
* CustomTkinter
* Matplotlib
* NumPy

---

## Project Structure

```text
FlangeCalc/
│
├── flangecalc.py       # Main GUI application
├── calculations.py     # Engineering calculations
├── htw_data.py         # Hydraulic torque wrench data and conversions
├── README.md
├── LICENSE
├── .gitignore
└── .gitattributes
```

---

## How to Use

1. Launch the application.
2. Enter the required bolt and gasket information.
3. Select the required units.
4. Calculate the required bolt torque.
5. For hydraulic torque wrench applications, select the required wrench and hex size.
6. View the corresponding hydraulic pressure.
7. Use the graphs to visualize the torque and pressure relationship.

---

## Purpose

FlangeCalc was created as a practical engineering tool based on experience with **flange management and bolted joint calculations**.

The project also serves as a personal exercise in combining engineering calculations with Python GUI development.

---

## Future Improvements

* Add hydraulic bolt tensioning calculation
* Add more hydraulic torque wrench models
* Expand bolt and gasket data
* Add additional unit conversions
* Improve calculation validation
* Add calculation export/report functionality
* Further improve the graphical interface

---

## License

This project is licensed under the MIT License.
