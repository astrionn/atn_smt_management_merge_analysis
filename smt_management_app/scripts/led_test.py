#!/usr/bin/env python3
"""
Django script to test LED functionality across all storage systems.
Usage: python manage.py runscript led_tests

This script will:
1. Find all storage systems
2. Light up each slot one by one
3. Cycle through colors: red, green, blue, yellow
4. Include delays between each slot
5. KEEP LEDs ON after script completion
"""

import time
import sys
from django.core.exceptions import ObjectDoesNotExist
from smt_management_app.models import Storage, StorageSlot
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher


def run():
    """Main function called by django-extensions runscript command"""
    print("Starting LED test script...")
    print("=" * 50)

    # Configuration
    colors = ["red", "green", "blue", "yellow"]
    delay_between_slots = 0.2  # seconds
    delay_between_storages = 2.0  # seconds
    keep_leds_on = True  # Set to False if you want to turn off LEDs at the end

    try:
        # Get all storage systems
        storages = Storage.objects.all()

        if not storages.exists():
            print("No storage systems found in database.")
            return

        print(f"Found {storages.count()} storage system(s)")

        for storage_idx, storage in enumerate(storages, 1):
            print(
                f"\n[{storage_idx}/{storages.count()}] Testing storage: {storage.name}"
            )
            print(f"Device type: {storage.device}")

            # Get all slots for this storage
            slots = StorageSlot.objects.filter(storage=storage).order_by("name")

            if not slots.exists():
                print(f"  No slots found for storage {storage.name}")
                continue

            print(f"  Found {slots.count()} slot(s)")

            try:
                # Create LED dispatcher for this storage
                print(f"  Initializing LED dispatcher...")
                dispatcher = LED_shelf_dispatcher(storage)

                # Reset LEDs before starting
                print(f"  Resetting LEDs...")
                dispatcher.reset_leds()

                # Test each slot
                color_idx = 0
                for slot_idx, slot in enumerate(slots, 1):
                    current_color = colors[color_idx % len(colors)]

                    print(
                        f"    [{slot_idx:3d}/{slots.count():3d}] Slot {slot.name:3d} -> {current_color}"
                    )

                    try:
                        # Turn on LED with current color
                        dispatcher.led_on(lamp=slot.name, color=current_color)

                        # Wait
                        time.sleep(delay_between_slots)

                        # REMOVED: dispatcher.led_off(lamp=slot.name) - Keep LEDs on!

                        # Move to next color
                        color_idx += 1

                    except Exception as slot_error:
                        print(f"      ERROR controlling slot {slot.name}: {slot_error}")
                        continue

                # REMOVED: Final reset - Keep LEDs on!
                if not keep_leds_on:
                    print(f"  Final LED reset...")
                    dispatcher.reset_leds()
                else:
                    print(f"  Keeping LEDs on for storage {storage.name}")

                print(f"  ✓ Completed testing storage {storage.name}")

            except Exception as storage_error:
                print(f"  ERROR initializing storage {storage.name}: {storage_error}")
                continue

            # Delay between storages (except for the last one)
            if storage_idx < storages.count():
                print(f"  Waiting {delay_between_storages}s before next storage...")
                time.sleep(delay_between_storages)

    except KeyboardInterrupt:
        print("\n\nScript interrupted by user (Ctrl+C)")

        # Ask user if they want to reset LEDs on interrupt
        try:
            response = input("Reset all LEDs? (y/N): ").strip().lower()
            if response in ["y", "yes"]:
                print("Resetting all LEDs...")
                for storage in Storage.objects.all():
                    try:
                        dispatcher = LED_shelf_dispatcher(storage)
                        dispatcher.reset_leds()
                        print(f"  Reset LEDs for {storage.name}")
                    except:
                        pass
            else:
                print("Keeping LEDs on...")
        except:
            print("Keeping LEDs on...")

        sys.exit(1)

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("LED test script completed successfully!")
    print("\nSummary:")
    print(f"  - Tested {storages.count()} storage system(s)")
    print(f"  - Used colors: {', '.join(colors)}")
    print(f"  - Delay between slots: {delay_between_slots}s")
    if keep_leds_on:
        print("  - LEDs remain ON after script completion")
    else:
        print("  - LEDs turned OFF after script completion")


def run_single_storage(storage_name, keep_on=True):
    """Test LEDs for a single storage system"""
    print(f"Testing single storage: {storage_name}")

    try:
        storage = Storage.objects.get(name=storage_name)
    except ObjectDoesNotExist:
        print(f"Storage '{storage_name}' not found")
        return

    colors = ["red", "green", "blue", "yellow"]
    delay = 0.5

    slots = StorageSlot.objects.filter(storage=storage).order_by("name")
    print(f"Found {slots.count()} slots")

    dispatcher = LED_shelf_dispatcher(storage)
    dispatcher.reset_leds()

    color_idx = 0
    for slot in slots:
        current_color = colors[color_idx % len(colors)]
        print(f"  Slot {slot.name} -> {current_color}")

        dispatcher.led_on(lamp=slot.name, color=current_color)
        time.sleep(delay)
        # REMOVED: dispatcher.led_off(lamp=slot.name) - Keep LEDs on!

        color_idx += 1

    if not keep_on:
        dispatcher.reset_leds()
        print("Single storage test completed - LEDs turned off!")
    else:
        print("Single storage test completed - LEDs remain on!")


def run_color_wave(keep_on=True):
    """Create a wave effect with colors across all storages"""
    print("Starting color wave effect...")

    colors = ["red", "green", "blue", "yellow"]
    wave_delay = 0.1

    # Get all slots from all storages, ordered by storage and slot name
    all_slots = []
    storage_dispatchers = {}

    for storage in Storage.objects.all():
        try:
            dispatcher = LED_shelf_dispatcher(storage)
            storage_dispatchers[storage.name] = dispatcher
            dispatcher.reset_leds()

            slots = StorageSlot.objects.filter(storage=storage).order_by("name")
            for slot in slots:
                all_slots.append((storage, slot))
        except Exception as e:
            print(f"Error with storage {storage.name}: {e}")

    print(f"Total slots across all storages: {len(all_slots)}")

    # Create wave effect
    for wave in range(3):  # 3 waves
        print(f"Wave {wave + 1}/3")

        for i, (storage, slot) in enumerate(all_slots):
            color = colors[i % len(colors)]

            try:
                dispatcher = storage_dispatchers[storage.name]
                dispatcher.led_on(lamp=slot.name, color=color)

                # Turn off previous LED(s) in wave (but keep recent ones)
                if i >= 5:  # Keep 5 LEDs on at once
                    prev_storage, prev_slot = all_slots[i - 5]
                    prev_dispatcher = storage_dispatchers[prev_storage.name]
                    prev_dispatcher.led_off(lamp=prev_slot.name)

                time.sleep(wave_delay)

            except Exception as e:
                print(f"Error with slot {slot.name}: {e}")

    # Keep the last 5 LEDs on instead of turning all off
    if not keep_on:
        for storage_name, dispatcher in storage_dispatchers.items():
            dispatcher.reset_leds()
        print("Color wave effect completed - all LEDs turned off!")
    else:
        print("Color wave effect completed - final LEDs remain on!")


def reset_all_leds():
    """Utility function to reset all LEDs across all storages"""
    print("Resetting all LEDs across all storage systems...")

    try:
        storages = Storage.objects.all()
        for storage in storages:
            try:
                dispatcher = LED_shelf_dispatcher(storage)
                dispatcher.reset_leds()
                print(f"  Reset LEDs for {storage.name}")
            except Exception as e:
                print(f"  Error resetting {storage.name}: {e}")
        print("All LEDs reset complete!")
    except Exception as e:
        print(f"Error during LED reset: {e}")


if __name__ == "__main__":
    # Allow script to be run directly for testing
    import os
    import django

    # Setup Django environment
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "your_project.settings"
    )  # Update this
    django.setup()

    # Check command line arguments for different test modes
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "single" and len(sys.argv) > 2:
            storage_name = sys.argv[2]
            keep_on = "--keep-on" in sys.argv or "--keep" in sys.argv
            run_single_storage(storage_name, keep_on=keep_on)
        elif command == "wave":
            keep_on = "--keep-on" in sys.argv or "--keep" in sys.argv
            run_color_wave(keep_on=keep_on)
        elif command == "reset":
            reset_all_leds()
        else:
            print("Usage:")
            print(
                "  python led_tests.py                       # Test all storages (keep LEDs on)"
            )
            print("  python led_tests.py single <name>         # Test single storage")
            print(
                "  python led_tests.py single <name> --keep  # Test single storage, keep LEDs on"
            )
            print("  python led_tests.py wave                  # Color wave effect")
            print(
                "  python led_tests.py wave --keep           # Color wave effect, keep LEDs on"
            )
            print("  python led_tests.py reset                 # Reset all LEDs to off")
    else:
        run()
