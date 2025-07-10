from os import path
from win32com.client import Dispatch


class DymoHandler:
    def __init__(self, label_name='atn_demo.label') -> None:
        import pythoncom

        pythoncom.CoInitialize()

        self.label = path.join('atn_smt_management', label_name)
        if not path.isfile(self.label):
            print('PyDymoLabel', f'Template file {label_name} does not exist')
            return

        else:
            try:
                self.labelCom = Dispatch('Dymo.DymoAddIn')
                self.labelText = Dispatch('Dymo.DymoLabels')
            except Exception as e:
                print('PyDymoLabel', 'Dymo Add-in not installed', e)
                return

    def print_label(self, message_a='', message_b='', message_c=''):
        try:
            selectPrinter = 'DYMO LabelWriter 450'
            self.labelCom.SelectPrinter(selectPrinter)
            isOpen = self.labelCom.Open(self.label)
            print(isOpen)
            self.labelText.SetField('BARCODE', message_a)
            self.labelText.SetField('CARRIER', self.split_text(message_a))
            self.labelText.SetField('ARTICLE', self.split_text(message_b,10))
            self.labelText.SetField('DESCRIPTION', self.split_text(message_c,45))
            #raise Exception()

            self.labelCom.StartPrintJob()
            self.labelCom.Print(1, False)
            self.labelCom.EndPrintJob()
            return True
        except Exception as e:
            print('PyDymoLabel', 'Error printing label', e)
            return False

    def split_text(self,text,line_length=27,lines_limit=4):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) > line_length:
                lines.append(current_line.strip())
                current_line = ""
            current_line += word
            current_line += " "
        else:
            lines.append(current_line.strip())
        s = '\n'.join(lines[:lines_limit])
        if len(lines)>lines_limit:
            s+=' ...'
        return s