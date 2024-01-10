import subprocess
from os import path

class DymoHandler:
    def __init__(self) -> None:
        self.label = path.join("Siemens.label")
        if not path.isfile(self.label):
            print("PyDymoLabel", "Template file siemens.label does not exist")
            return

    def print_label(self, message_a, message_b, feeder=False):
        print(f"printing {message_a, message_b}")
        try:
            printer_name = "Your_Printer_Name"  # Replace with your printer's name
            label_file = "your_label_file.pdf"  # Replace with the path to your label file in PDF format

            label_text = f"BARCODE: {message_a}\nTEXT_2: {message_b}" if not feeder else f"BARCODE: {message_b}\nTEXT_2: {message_a}\nTEXT_1: Feeder"

            subprocess.run(["lp", "-d", printer_name, "-o", "fit-to-page", "-o", "media=Custom.36x89mm", "-o", "orientation-requested=4", "-o", f"Text_1={label_text}", label_file], check=True)

            print(f"Label printed: {message_a}, {message_b}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error printing label: {e}")
            return False

# Example usage
dymo_handler = DymoHandler()
dymo_handler.print_label("Hello", "12345")
