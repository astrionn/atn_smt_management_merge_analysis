models = [
    "Article",
    "Board",
    "BoardArticle",
    "Carrier",
    "Job",
    "Machine",
    "MachineSlot",
    "Manufacturer",
    "Provider",
    "Storage",
    "StorageSlot"
]
f = open("urls.txt",'a+')
for m in models:
    print(f"router.register(r\'{m.lower()}\', views.{m}ViewSet,\'{m.lower()}\')",sep="\n",file=f)
f.close()