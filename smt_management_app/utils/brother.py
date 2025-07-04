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
        message_d="",
        carrier_uid="",
        width_mm=62,
        height_mm=29,
    ):
        """
        Create carrier label image with QR code, carrier info, article, and description
        Fixed positioning to ensure QR code is on the left and text doesn't get cut off
        MAXIMUM FONT SIZES for all fields

        Args:
            message_a: Carrier name/barcode content
            message_b: Article name
            message_c: Article description
            message_d: Storage location
            carrier_uid: Carrier unique identifier for QR code
            width_mm: Label width in millimeters
            height_mm: Label height in millimeters
        """
        dpi = 300
        width_px = int(width_mm * dpi / 25.4)
        height_px = int(height_mm * dpi / 25.4)

        img = Image.new("RGB", (width_px, height_px), "white")
        draw = ImageDraw.Draw(img)

        # MAXIMUM font sizes for all fields
        try:
            font_carrier = ImageFont.truetype("arial.ttf", 45)  # Maximum for carrier
            font_article = ImageFont.truetype("arial.ttf", 38)  # Maximum for article
            font_desc = ImageFont.truetype("arial.ttf", 32)  # Maximum for description
            font_location = ImageFont.truetype("arial.ttf", 28)  # Maximum for location
        except:
            # Fallback to default font if Arial not available
            font_carrier = ImageFont.load_default()
            font_article = ImageFont.load_default()
            font_desc = ImageFont.load_default()
            font_location = ImageFont.load_default()

        margin = 6  # Reduced margin for more space

        # Make QR code smaller to leave more room for text
        qr_size = min(height_px - (2 * margin), int(height_px * 0.8))

        # Generate QR code if carrier_uid is provided
        qr_img = None
        if carrier_uid:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=2,  # Reduced box size for smaller QR code
                border=1,
            )
            qr.add_data(carrier_uid)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

        # Calculate positions - ensure QR is on LEFT and text has enough space
        if qr_img:
            # QR code on the left side
            qr_x = margin
            qr_y = margin

            # Text area starts after QR code with small gap
            text_start_x = qr_x + qr_size + margin
            text_width = width_px - text_start_x - margin
        else:
            text_start_x = margin
            text_width = width_px - (2 * margin)

        # Place QR code on the LEFT side
        if qr_img:
            img.paste(qr_img, (qr_x, qr_y))

        # Calculate text layout in remaining space with larger fonts
        # Divide available height into sections for different text elements
        available_height = height_px - (2 * margin)

        # Estimate line heights based on actual font sizes
        carrier_height = int(available_height * 0.3)  # 30% for carrier (largest)
        article_height = int(available_height * 0.25)  # 25% for article
        desc_height = int(available_height * 0.25)  # 25% for description
        location_height = int(available_height * 0.2)  # 20% for location

        current_y = margin

        # Section 1: Carrier name (top) - MAXIMUM FONT
        if message_a:
            text = f"Carrier: {message_a}"
            # Truncate if too long for available width
            while (
                draw.textbbox((0, 0), text, font=font_carrier)[2] > text_width
                and len(text) > 10
            ):
                message_a = message_a[:-1]
                text = f"Carrier: {message_a}..."

            draw.text((text_start_x, current_y), text, fill="black", font=font_carrier)
            current_y += carrier_height

        # Section 2: Article - MAXIMUM FONT
        if message_b:
            text = f"Art: {message_b}"  # Shortened label to save space
            # Truncate if too long for available width
            while (
                draw.textbbox((0, 0), text, font=font_article)[2] > text_width
                and len(text) > 8
            ):
                message_b = message_b[:-1]
                text = f"Art: {message_b}..."

            draw.text((text_start_x, current_y), text, fill="black", font=font_article)
            current_y += article_height

        # Section 3: Description - MAXIMUM FONT
        if message_c:
            # Calculate max characters that fit in available width with larger font
            test_text = "A" * 30  # Test string
            test_width = draw.textbbox((0, 0), test_text, font=font_desc)[2]
            chars_per_pixel = len(test_text) / test_width
            max_chars = int(text_width * chars_per_pixel * 0.85)  # 85% safety margin

            description = (
                message_c[:max_chars] + "..."
                if len(message_c) > max_chars
                else message_c
            )

            draw.text(
                (text_start_x, current_y), description, fill="black", font=font_desc
            )
            current_y += desc_height

        # Section 4: Storage location - MAXIMUM FONT
        if message_d:
            text = f"Loc: {message_d}"  # Shortened label
            # Calculate max characters that fit with larger font
            test_text = "A" * 20
            test_width = draw.textbbox((0, 0), test_text, font=font_location)[2]
            chars_per_pixel = len(test_text) / test_width
            max_chars = int(text_width * chars_per_pixel * 0.85)

            if len(text) > max_chars:
                # Truncate message_d to fit
                available_for_location = max_chars - 5  # Account for "Loc: "
                location_text = (
                    message_d[:available_for_location] + "..."
                    if len(message_d) > available_for_location
                    else message_d
                )
                text = f"Loc: {location_text}"

            draw.text((text_start_x, current_y), text, fill="black", font=font_location)

        # Add border for better visibility
        draw.rectangle([0, 0, width_px - 1, height_px - 1], outline="black", width=2)

        # Apply positioning offset: 0.5mm right, 1mm up
        offset_right_mm = 1.5
        offset_up_mm = 1.0
        offset_right_px = int(offset_right_mm * dpi / 25.4)  # ~6 pixels
        offset_up_px = int(offset_up_mm * dpi / 25.4)  # ~12 pixels

        # Create a new image and paste the content with offset
        offset_img = Image.new("RGB", (width_px, height_px), "white")
        # Paste the original image content offset by the specified amount
        # Moving right = positive x offset, moving up = negative y offset
        offset_img.paste(img, (offset_right_px, -offset_up_px))
        img = offset_img

        # Rotate the entire image 90 degrees clockwise
        img = img.transpose(Image.Transpose.ROTATE_90)

        # Save the image to a file (optional, for debugging)
        img.save("carrier_label.png")
        return img

    def print_label(
        self,
        text="",
        message_a="",
        message_b="",
        message_c="",
        message_d="",
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
            message_d: Storage location
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
                    message_d=message_d,
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
            message_d="A1-B2",
            carrier_uid="12345-ABCDE-67890",
        )
    else:
        print("Please install Brother QL Windows driver first")
