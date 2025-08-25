# scripts/light_led_after_scan.py
"""
Simple QR LED Test Script

Setup:
1. pip install django-extensions
2. Add 'django_extensions' to INSTALLED_APPS
3. Create scripts/ directory in project root
4. Save this file as scripts/light_led_after_scan.py
5. Run: python manage.py runscript light_led_after_scan
"""

from smt_management_app.models import StorageSlot, Storage
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher
from django.db import transaction


def run():
    """Main script function"""
    print("QR LED Test - Scan QR codes to light LEDs")
    print("Type 'quit' to exit")

    color = input("LED Color [yellow]: ").strip() or "yellow"

    try:
        while True:
            qr_code = input("\nScan QR: ").strip()

            if qr_code.lower() in ["quit", "q"]:
                break

            if not qr_code:
                continue

            # Find slot
            slot = StorageSlot.objects.filter(qr_value=qr_code).first()
            if not slot:
                print(f"No slot found for: {qr_code}")
                continue

            # Turn on LED
            try:
                with transaction.atomic():
                    slot.led_state = 1
                    slot.save()
                rack = Storage.objects.get(name=slot.storage.name)
                print(f"Rack: {rack} | {rack.ip_address} | {rack.device}")
                dispenser = LED_shelf_dispatcher(storage=rack)
                print(f"Dispenser: {dispenser} | {dispenser.ip_address}")
                r = dispenser.led_on(slot.name, color)

                print(f"LED ON: {slot.storage.name} Slot {slot.name} | {r}")

            except Exception as e:
                print(f"Error: {e}")

    except KeyboardInterrupt:
        print("\nDone!")
