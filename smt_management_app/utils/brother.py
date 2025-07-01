import win32print
import win32ui
from PIL import Image, ImageWin, ImageDraw, ImageFont
import qrcode


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
        width_mm=62,
        height_mm=25,
    ):
        """
        Create carrier label image with QR code, carrier info, article, and description

        Args:
            message_a: Carrier name/barcode content
            message_b: Article name
            message_c: Article description
            carrier_uid: Carrier unique identifier for QR code
            width_mm: Label width in millimeters
            height_mm: Label height in millimeters
        """
        dpi = 300
        width_px = int(width_mm * dpi / 25.4)
        height_px = int(height_mm * dpi / 25.4)

        img = Image.new("RGB", (width_px, height_px), "white")
        draw = ImageDraw.Draw(img)

        # Font sizes for different sections
        try:
            font_large = ImageFont.truetype("arial.ttf", 28)  # For carrier/barcode
            font_medium = ImageFont.truetype("arial.ttf", 20)  # For article
            font_small = ImageFont.truetype("arial.ttf", 16)  # For description
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        margin = 8
        qr_size = height_px - (2 * margin)  # QR code size based on label height

        # Generate QR code if carrier_uid is provided
        qr_img = None
        if carrier_uid:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(carrier_uid)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

        # Calculate text area (space remaining after QR code)
        if qr_img:
            text_start_x = qr_size + margin * 2
            text_width = width_px - text_start_x - margin
        else:
            text_start_x = margin
            text_width = width_px - (2 * margin)

        # Place QR code on the left side
        if qr_img:
            img.paste(qr_img, (margin, margin))

        # Calculate text layout in remaining space
        text_section_height = (height_px - 2 * margin) // 3

        # Section 1: Carrier name (top right)
        if message_a:
            y_pos = margin
            text = f"Carrier: {message_a}"
            # Truncate if too long for available width
            while (
                draw.textbbox((0, 0), text, font=font_large)[2] > text_width
                and len(text) > 10
            ):
                message_a = message_a[:-1]
                text = f"Carrier: {message_a}..."

            draw.text((text_start_x, y_pos), text, fill="black", font=font_large)

        # Section 2: Article (middle right)
        if message_b:
            y_pos = margin + text_section_height
            text = f"Article: {message_b}"
            # Truncate if too long for available width
            while (
                draw.textbbox((0, 0), text, font=font_medium)[2] > text_width
                and len(text) > 10
            ):
                message_b = message_b[:-1]
                text = f"Article: {message_b}..."

            draw.text((text_start_x, y_pos), text, fill="black", font=font_medium)

        # Section 3: Description (bottom right)
        if message_c:
            y_pos = margin + 2 * text_section_height
            # Truncate description if too long
            max_chars = max(15, text_width // 8)  # Estimate based on available width
            description = (
                message_c[:max_chars] + "..."
                if len(message_c) > max_chars
                else message_c
            )

            draw.text((text_start_x, y_pos), description, fill="black", font=font_small)

        # Add UID below QR code if present
        if carrier_uid and qr_img:
            uid_y = qr_size + margin + 5
            if uid_y < height_px - 20:  # Only if there's space
                uid_text = f"UID: {carrier_uid}"
                draw.text((margin, uid_y), uid_text, fill="black", font=font_small)

        # Add border for better visibility
        draw.rectangle([0, 0, width_px - 1, height_px - 1], outline="black", width=2)

        return img

    def print_label(
        self,
        text="",
        message_a="",
        message_b="",
        message_c="",
        carrier_uid="",
        label_height_mm=25,
    ):
        """
        Print carrier label using Windows printer

        Args:
            text: Simple text (for backward compatibility)
            message_a: Carrier name/barcode content
            message_b: Article name
            message_c: Article description
            carrier_uid: Carrier unique identifier for QR code
            label_height_mm: Label height in millimeters
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
                    height_mm=label_height_mm,
                )
            else:
                # Fallback to simple text label
                img = self.create_label_image(message_a=text, height_mm=label_height_mm)

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
                f"Carrier label printed - UID: {carrier_uid}, Barcode: {message_a}, Article: {message_b}, Description: {message_c}"
            )
            return True

        except Exception as e:
            print(f"Windows printing failed: {e}")
            return False


# Usage
if __name__ == "__main__":
    printer = BrotherQLHandler()
    if printer.printer_name:
        # Test with carrier data including QR code
        printer.print_label(
            message_a="CARR-001",
            message_b="Sample Article",
            message_c="This is a sample description for testing",
            carrier_uid="12345-ABCDE-67890",
        )
    else:
        print("Please install Brother QL Windows driver first")
