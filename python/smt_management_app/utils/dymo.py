from os import path
from tkinter.constants import E
from win32com.client import Dispatch

class DymoHandler:
    def __init__(self,label_name='Siemens.label') -> None:
        import pythoncom

        pythoncom.CoInitialize()

        self.label = path.join('matmanagment', 'media',label_name)
        if not path.isfile(self.label):
            print('PyDymoLabel','Template file siemens.label does not exist')
            return

        else:
            try:
                self.labelCom = Dispatch('Dymo.DymoAddIn')
                self.labelText = Dispatch('Dymo.DymoLabels')
            except Exception as e:
                print('PyDymoLabel','Dymo Add-in not installed', e)
                return

    def print_label(self,message_a='', message_b='',message_c='',message_d='',message_e='', feeder = False):
        try:
            selectPrinter = 'DYMO LabelWriter 450'
            self.labelCom.SelectPrinter(selectPrinter)
            is_open = self.labelCom.Open(self.label)
            if not feeder:
                self.labelText.SetField('BARCODE', message_a)
                self.labelText.SetField('C_UID_VAL', message_a)
                self.labelText.SetField('A_UID_VAL', message_b)
                self.labelText.SetField('A_DESC_VAL', message_c)
                self.labelText.SetField('WIDTH_VAL', message_d)
                self.labelText.SetField('M_QTY_VAL', message_e)
            else:
                self.labelText.SetField('BARCODE', message_a)
                self.labelText.SetField('BARCODE_1', message_a)
                self.labelText.SetField('TEXT__1', message_a)
                self.labelText.SetField('TEXT_2', message_a)
                self.labelText.SetField('TEXT_1', "Feeder")
                self.labelText.SetField('TEXT', "Feeder")

            self.labelCom.StartPrintJob()
            self.labelCom.Print(1, False)
            self.labelCom.EndPrintJob()
            return True
        except Exception as e:
            print('PyDymoLabel','Error printing label', e)
            return False
