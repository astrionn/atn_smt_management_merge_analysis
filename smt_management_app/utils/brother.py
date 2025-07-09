import win32print
import win32ui
from PIL import Image, ImageWin, ImageDraw, ImageFont
import qrcode
import os
from datetime import datetime


class BrotherQLHandler:
    def __init__(self, printer_name=None):
        """
        Initialize Windows printer handler

        Args:
            printer_name: Name of the printer as shown in Windows
        """
        if printer_name is None:
            # Try to find Brother QL printer automatically
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            brother_printers = [
                p for p in printers if "QL" in p.upper() and "BROTHER" in p.upper()
            ]
            if brother_printers:
                self.printer_name = brother_printers[0]
                print(f"Found Brother printer: {self.printer_name}")
            else:
                print("No Brother QL printer found in Windows.")
                print("Available printers:", printers)
                self.printer_name = None
        else:
            self.printer_name = printer_name

    def test_connection(self):
        """Test if printer is reachable and responding"""
        if not self.printer_name:
            return False

        try:
            # Try to get printer info to test connection
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            if self.printer_name in printers:
                # Additional test: try to open the printer
                handle = win32print.OpenPrinter(self.printer_name)
                win32print.ClosePrinter(handle)
                return True
            return False
        except Exception as e:
            print(f"Printer connection test failed: {e}")
            return False

    def create_label_image(
        self,
        message_a="",
        message_b="",
        message_c="",
        carrier_uid="",
        # Label dimensions (29mm high x 62mm wide)
        label_width_mm=62,
        label_height_mm=29,
        # Margins (all in mm)
        margin_top=1,
        margin_left=2,
        margin_right=1,
        margin_bottom=1,
        margin_after_qr=4,  # Space between QR code and text
        margin_between_text=0.5,  # Space between text lines
        # QR code settings
        qr_size_mm=22,  # QR code size
        # Scaling
        total_scale=1,  # Scale entire image (0.95 = 95% of original size)
        # DPI
        dpi=300,
    ):
        """
        Create carrier label image with proper orientation (62mm wide x 29mm high)

        Layout: [QR Code] [Text Section with 3 lines]
        """
        # Calculate pixel dimensions
        width_px = int(label_width_mm * dpi / 25.4)
        height_px = int(label_height_mm * dpi / 25.4)

        # Create image with white background
        img = Image.new("RGB", (width_px, height_px), "white")
        draw = ImageDraw.Draw(img)

        # Convert margins to pixels
        margin_top_px = int(margin_top * dpi / 25.4)
        margin_left_px = int(margin_left * dpi / 25.4)
        margin_right_px = int(margin_right * dpi / 25.4)
        margin_bottom_px = int(margin_bottom * dpi / 25.4)
        margin_after_qr_px = int(margin_after_qr * dpi / 25.4)
        margin_between_text_px = int(margin_between_text * dpi / 25.4)
        qr_size_px = int(qr_size_mm * dpi / 25.4)

        # Load fonts
        try:
            font_large = ImageFont.truetype("arial.ttf", 40)
            font_medium = ImageFont.truetype("arial.ttf", 22)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Generate QR code if carrier_uid is provided
        qr_img = None
        if carrier_uid:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(carrier_uid)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((qr_size_px, qr_size_px), Image.Resampling.LANCZOS)

        # Calculate layout positions
        current_x = margin_left_px
        current_y = margin_top_px

        # Place QR code
        qr_x = current_x
        qr_y = (
            current_y + (height_px - margin_top_px - margin_bottom_px - qr_size_px) // 2
        )  # Center vertically

        if qr_img:
            img.paste(qr_img, (qr_x, qr_y))

        # Calculate text area
        text_start_x = current_x + qr_size_px + margin_after_qr_px
        text_width = width_px - text_start_x - margin_right_px
        text_area_height = height_px - margin_top_px - margin_bottom_px

        # Calculate text line heights
        line_height = (text_area_height - 2 * margin_between_text_px) // 3

        # Text line 1: Carrier name
        if message_a:
            y_pos = margin_top_px
            text = f"Carrier: {message_a}"

            # Truncate if too long
            while (
                draw.textbbox((0, 0), text, font=font_small)[2] > text_width
                and len(text) > 10
            ):
                message_a = message_a[:-1]
                text = f"Carrier: {message_a}..."

            draw.text((text_start_x, y_pos), text, fill="black", font=font_small)

        # Text line 2: Article
        if message_b:
            y_pos = margin_top_px + line_height + margin_between_text_px
            text = f"Article: {message_b}"

            # Truncate if too long
            while (
                draw.textbbox((0, 0), text, font=font_large)[2] > text_width
                and len(text) > 10
            ):
                message_b = message_b[:-1]
                text = f"Article: {message_b}..."

            draw.text((text_start_x, y_pos), text, fill="black", font=font_large)

        # Text line 3: Description
        if message_c:
            y_pos = margin_top_px + 2 * (line_height + margin_between_text_px)

            # Truncate description if too long
            max_chars = max(15, text_width // 10)
            description = (
                message_c[:max_chars] + "..."
                if len(message_c) > max_chars
                else message_c
            )

            draw.text(
                (text_start_x, y_pos), description, fill="black", font=font_medium
            )

        # Apply total scaling if not 1.0
        if total_scale != 1.0:
            new_width = int(width_px * total_scale)
            new_height = int(height_px * total_scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Fix orientation - rotate 180 degrees to get QR positioning squares in correct corners
        img = img.transpose(Image.ROTATE_90)

        return img

    def save_debug_image(self, img, carrier_uid="", message_a=""):
        """
        Save debug image with timestamp and return full path
        """
        # Create debug directory if it doesn't exist
        debug_dir = os.path.join(os.getcwd(), "label_debug")
        os.makedirs(debug_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create descriptive filename
        filename_parts = ["label", timestamp]
        if carrier_uid:
            clean_uid = "".join(c for c in carrier_uid if c.isalnum() or c in "._-")
            filename_parts.append(f"uid_{clean_uid}")
        if message_a:
            clean_carrier = "".join(c for c in message_a if c.isalnum() or c in "._-")
            filename_parts.append(f"carrier_{clean_carrier}")

        filename = "_".join(filename_parts) + ".png"
        full_path = os.path.join(debug_dir, filename)

        # Save the image
        img.save(full_path, "PNG")

        return full_path

    def print_label(
        self,
        text="",
        message_a="",
        message_b="",
        message_c="",
        carrier_uid="",
        debug=True,
        # You can override any layout parameters here
        **layout_params,
    ):
        """
        Print carrier label using Windows printer

        Args:
            text: Simple text (for backward compatibility)
            message_a: Carrier name/barcode content
            message_b: Article name
            message_c: Article description
            carrier_uid: Carrier unique identifier for QR code
            debug: If True, save label image as PNG file for debugging
            **layout_params: Any parameters to override in create_label_image()
        """
        if not self.printer_name:
            print("No printer configured")
            return False

        try:
            # Create label - use multi-field if provided, otherwise use simple text
            if message_a or message_b or message_c or carrier_uid:
                img = self.create_label_image(
                    message_a=message_a,
                    message_b=message_b,
                    message_c=message_c,
                    carrier_uid=carrier_uid,
                    **layout_params,
                )
            else:
                # Fallback to simple text label
                img = self.create_label_image(message_a=text, **layout_params)

            # Save debug image if requested
            if debug:
                debug_path = self.save_debug_image(img, carrier_uid, message_a or text)
                print(f"DEBUG: Label image saved to: {debug_path}")

            # Print using Windows
            printer_dc = win32ui.CreateDC()
            printer_dc.CreatePrinterDC(self.printer_name)
            printer_dc.StartDoc("Carrier Label Print")
            printer_dc.StartPage()

            # Convert PIL image for Windows printing
            dib = ImageWin.Dib(img)
            dib.draw(printer_dc.GetHandleOutput(), (0, 0, img.width, img.height))

            printer_dc.EndPage()
            printer_dc.EndDoc()
            printer_dc.DeleteDC()

            print(
                f"Label printed - UID: {carrier_uid}, Carrier: {message_a}, Article: {message_b}, Description: {message_c}"
            )
            return True

        except Exception as e:
            print(f"Windows printing failed: {e}")
            return False
