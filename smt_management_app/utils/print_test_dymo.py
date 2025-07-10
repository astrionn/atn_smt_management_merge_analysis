import pythoncom
from win32com.client import Dispatch

pythoncom.CoInitialize()
addin = Dispatch('Dymo.DymoAddIn')
labels = Dispatch('Dymo.DymoLabels')
print('DYMO COM objects initialized successfully')
