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
f = open("serializers.txt",'a+')
for m in models.keys():
    print(f"class {m}Serializer(serializers.ModelSerializer):",file=f)
    print(f"    class Meta:",file=f)
    print(f"        model = {m}",file=f)
    print(f"        fields = \"__all__\"",file=f)
f.close()