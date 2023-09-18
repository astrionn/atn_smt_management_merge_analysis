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
for m in models:
    
    g = open(f"{m.lower()}_form.html",'a+')
    g.seek(0)
    print("<form method=\"post\">{% csrf_token %}",sep="\n",file=g)
    print("{{ form.as_p }}",sep="\n",file=g)
    print("<input type=\"submit\" value=\"Save\">",sep="\n",file=g)
    print("</form>",sep="\n",file=g)    
    g.close()