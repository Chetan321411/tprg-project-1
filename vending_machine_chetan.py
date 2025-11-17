#!/usr/bin/env python3

# STUDENT version for Project 1 to be used on the Pi500.
# TPRG2131 Fall 202x
# Updated for Raspberry Pi 500 (NO pigpio support)
#
#Chetan 
#Student ID: 100969214

import FreeSimpleGUI as sg          # <-- FIXED (FreeSimpleGUI DOES NOT EXIST)
from time import sleep

# -------------------------------------------------------------
# HARDWARE DETECTION FOR RASPBERRY PI 500  (NO pigpio!)
# -------------------------------------------------------------
hardware_present = False

try:
    print("Checking native gpiozero support...")

    from gpiozero import Button, Servo

    key1 = Button(5)      # RETURN button
    servo = Servo(17)     # Servo PWM pin

    print("✔ Raspberry Pi 500 hardware detected.")
    hardware_present = True

except Exception as e:
    print("❌ Hardware error:", e)
    hardware_present = False


# -------------------------------------------------------------
# DEBUG LOGGING
# -------------------------------------------------------------
TESTING = True
def log(s):
    if TESTING:
        print(s)


# -------------------------------------------------------------
# VENDING MACHINE CLASS
# -------------------------------------------------------------
class VendingMachine(object):

    PRODUCTS = {
        "p0": ("KitKat", 125),
        "p1": ("Chips", 175),
        "p2": ("Coke", 150),
        "p3": ("Gum", 50),
        "p4": ("Candy", 100),
    }

    COINS = {
        "nickel": ("5c", 5),
        "dime": ("10c", 10),
        "quarter": ("25c", 25),
        "loonie": ("$1", 100),
        "toonie": ("$2", 200),
    }

    def __init__(self):
        self.state = None
        self.states = {}
        self.event = ""
        self.amount = 0
        self.change_due = 0

        self.coin_values = sorted([self.COINS[k][1] for k in self.COINS], reverse=True)
        log(f"Coin values (desc): {self.coin_values}")

        self.gui_log_callback = None

    def log(self, message):
        log(message)
        if self.gui_log_callback:
            prev = window["-LOG-"].get()
            window["-LOG-"].update(prev + message + "\n")


    def add_state(self, state):
        self.states[state.name] = state

    def go_to_state(self, state_name):
        if self.state:
            self.log(f"Exiting {self.state.name}")
            self.state.on_exit(self)
        self.state = self.states[state_name]
        self.log(f"Entering {self.state.name}")
        self.state.on_entry(self)

    def update(self):
        if self.state:
            self.state.update(self)

    def add_coin(self, key):
        value = self.COINS[key][1]
        self.amount += value
        self.log(f"Inserted {self.COINS[key][0]} ({value}c). Total: {self.amount}c.")

    def button_action(self):
        self.log("GPIO RETURN button pressed.")
        self.event = "RETURN"
        self.update()


# -------------------------------------------------------------
# ABSTRACT STATE
# -------------------------------------------------------------
class State(object):
    _NAME = ""
    @property
    def name(self): return self._NAME
    def on_entry(self, machine): pass
    def on_exit(self, machine): pass
    def update(self, machine): pass


# -------------------------------------------------------------
# WAITING STATE
# -------------------------------------------------------------
class WaitingState(State):
    _NAME = "waiting"
    def on_entry(self, machine):
        machine.log("Waiting for coins...")
    def update(self, machine):
        if machine.event in machine.COINS:
            machine.add_coin(machine.event)
            machine.go_to_state("add_coins")


# -------------------------------------------------------------
# ADD COINS STATE
# -------------------------------------------------------------
class AddCoinsState(State):
    _NAME = "add_coins"
    def update(self, machine):
        if machine.event == "RETURN":
            machine.change_due = machine.amount
            machine.amount = 0
            machine.go_to_state("count_change")

        elif machine.event in machine.COINS:
            machine.add_coin(machine.event)

        elif machine.event in machine.PRODUCTS:
            name, price = machine.PRODUCTS[machine.event]
            if machine.amount >= price:
                machine.go_to_state("deliver_product")
            else:
                need = price - machine.amount
                machine.log(f"Need {need} more cents.")

        machine.event = ""


# -------------------------------------------------------------
# PRODUCT DELIVERY STATE
# -------------------------------------------------------------
class DeliverProductState(State):
    _NAME = "deliver_product"
    def on_entry(self, machine):
        key = machine.event
        name, price = machine.PRODUCTS[key]

        machine.log(f"Dispensing {name}...")
        
        if hardware_present and servo:
            try:
                for _ in range(2):
                    servo.max(); sleep(0.4)
                    servo.mid(); sleep(0.4)
                    servo.min(); sleep(0.4)
                machine.log("Servo movement OK.")
            except Exception as e:
                machine.log(f"Servo error: {e}")
        else:
            machine.log("(Simulated dispense)")

        machine.change_due = machine.amount - price
        machine.amount = 0

        if machine.change_due > 0:
            machine.go_to_state("count_change")
        else:
            machine.go_to_state("waiting")


# -------------------------------------------------------------
# CHANGE RETURN STATE
# -------------------------------------------------------------
class CountChangeState(State):
    _NAME = "count_change"
    def update(self, machine):
        for value in machine.coin_values:
            while machine.change_due >= value:
                machine.log(f"Returning {value}c")
                machine.change_due -= value
                sleep(0.2)
        machine.go_to_state("waiting")


# -------------------------------------------------------------
# GUI SETUP
# -------------------------------------------------------------
sg.theme("BluePurple")

coin_col = [[sg.Text("ENTER COINS", font=("Helvetica", 20))]]
for key, (label, val) in VendingMachine.COINS.items():
    coin_col.append([sg.Button(f"{label} ({val}c)", key=f"COIN_{key}", font=("Helvetica", 16))])

prod_col = [[sg.Text("SELECT ITEM", font=("Helvetica", 20))]]
for key, (name, price) in VendingMachine.PRODUCTS.items():
    prod_col.append([sg.Button(f"{name}\n${price/100:.2f}", key=f"SELECT_{key}", size=(14,2), font=("Helvetica", 14))])

layout = [
    [sg.Column(coin_col), sg.VSeparator(), sg.Column(prod_col)],
    [sg.Text("Amount:"), sg.Text("$0.00", key="-AMOUNT-")],
    [sg.Button("RETURN"), sg.Button("TEST SERVO")],
    [sg.Multiline("", size=(60,10), key="-LOG-", disabled=True)]
]

window = sg.Window("Vending Machine", layout, finalize=True)


# -------------------------------------------------------------
# CREATE MACHINE & STATES
# -------------------------------------------------------------
vending = VendingMachine()
vending.gui_log_callback = vending.log

vending.add_state(WaitingState())
vending.add_state(AddCoinsState())
vending.add_state(DeliverProductState())
vending.add_state(CountChangeState())

vending.go_to_state("waiting")

if hardware_present and key1:
    key1.when_pressed = vending.button_action

def refresh_amt():
    window["-AMOUNT-"].update(f"${vending.amount/100:.2f}")


# -------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------
while True:
    event, values = window.read(timeout=100)

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    if event.startswith("COIN_"):
        vending.event = event.split("_")[1]
        vending.update()

    elif event.startswith("SELECT_"):
        vending.event = event.split("_")[1]
        vending.update()

    elif event == "RETURN":
        vending.event = "RETURN"
        vending.update()

    elif event == "TEST SERVO":
        if hardware_present:
            servo.max(); sleep(0.4)
            servo.mid(); sleep(0.4)
            servo.min(); sleep(0.4)
            vending.log("TEST SERVO completed.")
        else:
            vending.log("Servo not available.")

    refresh_amt()

window.close()
