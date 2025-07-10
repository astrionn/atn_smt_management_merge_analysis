#!/usr/bin/env python
"""
Django script to scan QR codes and turn on corresponding LEDs
Place this file in your smt_management_app/scripts/ directory
Run with: python manage.py runscript qr_led_control
"""

from smt_management_app.models import StorageSlot
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher


def run():
    """
    Simple loop that scans QR codes and turns on LEDs
    """
    print("QR Code LED Control")
    print("Press Ctrl+C to exit")
    print()

    try:
        while True:
            qr_value = input("Scan QR code: ").strip()

            if not qr_value:
                continue

            try:
                slot = StorageSlot.objects.get(qr_value=qr_value)
                led_dispatcher = LED_shelf_dispatcher(slot.storage)
                led_dispatcher.led_on(int(slot.name), "blue")
                slot.led_state = 1
                slot.save()
                print(f"✅ LED ON: slot {slot.name}")

            except StorageSlot.DoesNotExist:
                print(f"❌ No slot found: {qr_value}")
            except Exception as e:
                print(f"❌ Error: {e}")

    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    run()
