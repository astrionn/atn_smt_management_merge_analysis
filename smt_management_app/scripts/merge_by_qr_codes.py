# Save as: smt_management_app/scripts/merge_by_qr_codes.py

from smt_management_app.models import StorageSlot, merge_storage_slots, Storage
from smt_management_app.collecting import find_slot_by_qr_code
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher
from django.db import transaction
from threading import Thread
import time


def light_up_slots(slots, color="yellow"):
    """
    Light up a list of slots with the specified color.

    Args:
        slots: List of StorageSlot objects to light up
        color: Color to use (default: yellow)
    """
    # Group slots by storage to create dispatchers
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        # Set LED state and start lighting thread
        slot.led_state = 1
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_on,
            kwargs={"lamp": slot.name, "color": color},
        ).start()


def turn_off_slots(slots):
    """
    Turn off LEDs for a list of slots.

    Args:
        slots: List of StorageSlot objects to turn off
    """
    # Group slots by storage to create dispatchers
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        # Set LED state and turn off
        slot.led_state = 0
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_off, kwargs={"lamp": slot.name}
        ).start()


def run():
    """
    Aggressively merge two slots by their QR codes in a continuous loop,
    always using the first entered slot as the primary/master slot.
    Now with LED visualization!
    """

    print("=== Aggressive Slot Merge by QR Codes (Looping) with LED Support ===\n")
    print("This script allows you to merge multiple pairs of slots.")
    print("LEDs will light up to show which slots are being merged!")
    print("Enter 'quit' or 'exit' for any QR code to stop.\n")

    while True:
        print("-" * 50)
        print("Starting new merge operation...")

        # Prompt user for QR codes
        qr1 = input("Enter first QR code (will be the master): ").strip()

        # Check for exit conditions
        if qr1.lower() in ["quit", "exit", "q"]:
            print("Exiting merge script. Goodbye!")
            break

        qr2 = input("Enter second QR code to merge into first: ").strip()

        # Check for exit conditions
        if qr2.lower() in ["quit", "exit", "q"]:
            print("Exiting merge script. Goodbye!")
            break

        # Validate inputs
        if qr1 == qr2:
            print("Error: Both QR codes are the same. Please try again.\n")
            continue

        if not qr1 or not qr2:
            print("Error: Empty QR code entered. Please try again.\n")
            continue

        # Find the slots by QR
        slot1 = find_slot_by_qr_code(qr1)
        slot2 = find_slot_by_qr_code(qr2)

        if not slot1:
            print(
                f"Error: QR code '{qr1}' could not be resolved to a slot. Please try again.\n"
            )
            continue

        if not slot2:
            print(
                f"Error: QR code '{qr2}' could not be resolved to a slot. Please try again.\n"
            )
            continue

        print(f"\nFound Slot 1: {slot1.name} (Master)")
        print(f"Found Slot 2: {slot2.name} (To be merged)")

        # Determine full slot list from any existing combined structure
        slots1 = slot1.get_combined_slots() if slot1.is_combined_slot() else [slot1]
        slots2 = slot2.get_combined_slots() if slot2.is_combined_slot() else [slot2]

        # Flatten and remove duplicates while keeping order
        all_slots = [s for s in slots1 + slots2 if s.id != slot1.id]
        all_slots = list({s.id: s for s in all_slots}.values())

        # Get all slots involved in the merge (including the master)
        all_merge_slots = [slot1] + all_slots

        print("\n🔍 Lighting up slots to be merged...")
        print(f"  Primary: {slot1.name}")
        print(f"  Others: {[s.name for s in all_slots]}")

        try:
            # Light up all slots involved in yellow
            light_up_slots(all_merge_slots, "yellow")

            # Give user time to see the LEDs
            print("\n💡 All slots involved in the merge are now lit in YELLOW.")
            input("Press Enter to continue with the merge, or Ctrl+C to cancel...")

            with transaction.atomic():
                print("\nMerging slots:")
                print(f"  Primary: {slot1.name}")
                print(f"  Others: {[s.name for s in all_slots]}")

                # Perform the merge
                merged_slot = merge_storage_slots(slot1, *all_slots)

            # Turn off the individual slots that were merged
            print("\n🔄 Turning off individual slot LEDs...")
            turn_off_slots(all_merge_slots)

            # Wait a moment then light up the merged slot in green
            time.sleep(0.5)
            print("✅ Lighting up merged slot in GREEN...")
            light_up_slots([merged_slot], "green")

            print("\n✓ Merge successful!")
            print(f"  - New combined slot: {merged_slot.name}")
            print(f"  - QR codes: {merged_slot.get_all_qr_codes()}")
            print(f"  - Slot names: {merged_slot.get_all_slot_names()}")
            print(f"  - Combined: {merged_slot.is_combined_slot()}")

            # Keep the success LED on for a few seconds
            time.sleep(3)
            print("🔄 Turning off success LED...")
            turn_off_slots([merged_slot])

        except KeyboardInterrupt:
            print("\n\n⚠️ Merge cancelled by user!")
            print("🔄 Turning off all LEDs...")
            turn_off_slots(all_merge_slots)

        except Exception as e:
            print(f"✗ Merge failed: {e}")
            print("Please check the error and try again.")

            # Turn off LEDs and light them red briefly to indicate error
            print("🔄 Indicating error with RED LEDs...")
            turn_off_slots(all_merge_slots)
            time.sleep(0.5)
            light_up_slots(all_merge_slots, "red")
            time.sleep(2)
            turn_off_slots(all_merge_slots)

        print()  # Add some spacing for the next iteration

    print("\n=== Done ===")
