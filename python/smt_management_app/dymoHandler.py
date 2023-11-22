from os import path
from tkinter.constants import E
from win32com.client import Dispatch


# label printer
class DymoHandler:
    def __init__(self) -> None:
        import pythoncom

        pythoncom.CoInitialize()

        self.label = path.join("Siemens.label")
        if not path.isfile(self.label):
            print("PyDymoLabel", "Template file siemens.label does not exist")
            return

        else:
            try:
                self.labelCom = Dispatch("Dymo.DymoAddIn")
                self.labelText = Dispatch("Dymo.DymoLabels")
            except Exception as e:
                print("PyDymoLabel", "Dymo Add-in not installed", e)
                return

    def print_label(self, message_a, message_b, feeder=False):
        print(f"printing {message_a,message_b}")
        try:
            selectPrinter = "DYMO LabelWriter 450 (Kopie 1)"
            self.labelCom.SelectPrinter(selectPrinter)
            is_open = self.labelCom.Open(self.label)
            if not feeder:
                self.labelText.SetField("BARCODE", message_b)
                self.labelText.SetField("TEXT_2", message_a)
                self.labelText.SetField("BARCODE_1", message_a)
                self.labelText.SetField("TEXT__1", message_b)
            else:
                self.labelText.SetField("BARCODE", message_a)
                self.labelText.SetField("BARCODE_1", message_a)
                self.labelText.SetField("TEXT__1", message_a)
                self.labelText.SetField("TEXT_2", message_a)
                self.labelText.SetField("TEXT_1", "Feeder")
                self.labelText.SetField("TEXT", "Feeder")

            self.labelCom.StartPrintJob()
            self.labelCom.Print(1, False)
            self.labelCom.EndPrintJob()
            return True
        except Exception as e:
            print("PyDymoLabel", "Error printing label", e)
            return False
