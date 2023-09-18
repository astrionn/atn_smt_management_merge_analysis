models = {
    "Article":["name","provider","provider_description","manufacturer","manufacturer_description","description","sap_number"],
    "Board":["name","articles"],
    "BoardArticle":["name","article","board","count","carrier"],
    "Carrier":["name","article","diameter","width","container_type","quantity_original","quantity_current","lot_number","reserved","delivered","collecting","storage_slot","machine_slot"],
    "Job":["name","board","machine","project","customer","count","start_at","finish_at","status"],
    "Machine":["name","machine_type","capacity","lcoation"],
    "MachineSlot":["name","machine"],
    "Manufacturer":["name"],
    "Provider":["name"],
    "Storage":["name","storage_type","capacity","location"],
    "StorageSlot":["name","storage","led_state"]
}
f = open("views.txt",'a+')
for m in models.keys():
    print(f"class {m}ViewSet(viewsets.ModelViewSet):",file=f)
    print(f"    queryset = {m}.objects.all()",file=f)
    print(f"    serializer_class = {m}Serializer",sep=None,file=f)
    print(f"",sep="\n",file=f)

f.close()