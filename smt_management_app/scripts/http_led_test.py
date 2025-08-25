#!/usr/bin/env python3
"""
Pure requests script to control NeoLight LEDs sequentially
Turns on LEDs one by one, cycling through colors: red, green, blue, yellow
"""

import requests
import time
from urllib.parse import urljoin

# Configuration
NEOLIGHT_IP = "192.168.10.100"
NEOLIGHT_PORT = 5000
BASE_URL = f"http://{NEOLIGHT_IP}:{NEOLIGHT_PORT}/"
DELAY = 0.15  # seconds between each LED

# Colors to cycle through
COLORS = ["red", "green", "blue", "yellow"]

# LED range - starting from 0 as requested
# Max LEDs is typically 1400, but you can adjust this range as needed
START_LED = 0
END_LED = 1399  # Adjust this to your desired range (max 1400)


def turn_on_led(led_number, color):
    """Turn on a specific LED with the given color"""
    # Build the params string (format: "lamp_id=color")
    params_string = f"{led_number}={color}"

    # Prepare the request data
    request_data = {"params": params_string}

    # Send the POST request
    url = urljoin(BASE_URL, "/api/open")

    try:
        response = requests.post(url, json=request_data, timeout=5)
        response.raise_for_status()
        print(f"✓ LED {led_number}: {color}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to control LED {led_number}: {e}")
        return False


def turn_off_led(led_number):
    """Turn off a specific LED"""
    # For turning off, we just send the LED number in params
    params_string = str(led_number)
    request_data = {"params": params_string}

    url = urljoin(BASE_URL, "/api/close")

    try:
        response = requests.post(url, json=request_data, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to turn off LED {led_number}: {e}")
        return False


def reset_all_leds():
    """Turn off all LEDs"""
    # Turn off all LEDs by sending empty params to close endpoint
    request_data = {"params": ""}
    url = urljoin(BASE_URL, "/resetled")

    try:
        response = requests.post(url, json=request_data, timeout=10)
        response.raise_for_status()
        print("✓ All LEDs reset")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to reset LEDs: {e}")
        return False


def main():
    print(f"NeoLight Sequential LED Controller")
    print(f"Target: {BASE_URL}")
    print(f"LED range: {START_LED} to {END_LED}")
    print(f"Colors: {', '.join(COLORS)} (starting with red)")
    print(f"Delay: {DELAY} seconds")
    print("-" * 50)

    # Reset all LEDs first
    print("Resetting all LEDs...")
    reset_all_leds()
    time.sleep(1)

    try:
        # Main loop - cycle through LEDs and colors
        for led_num in range(START_LED, END_LED + 1):
            # Determine color by cycling through the colors list
            color_index = led_num % len(COLORS)
            color = COLORS[color_index]

            # Turn on the LED
            success = turn_on_led(led_num, color)

            if success:
                # Wait for the specified delay
                time.sleep(DELAY)
            else:
                # If request failed, still wait a bit before trying next LED
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        # Clean up - turn off all LEDs
        print("\nCleaning up...")
        reset_all_leds()


if __name__ == "__main__":
    main()
