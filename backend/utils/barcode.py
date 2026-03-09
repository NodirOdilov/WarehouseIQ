"""Barcode and QR code generation utilities for WarehouseIQ."""

import io
import logging
from typing import Optional

import barcode
from barcode.writer import ImageWriter
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def generate_barcode_image(
    code: str,
    barcode_type: str = "code128",
    writer_options: Optional[dict] = None,
) -> ContentFile:
    """
    Generate a barcode image and return it as a Django ContentFile.

    Args:
        code: The data to encode in the barcode.
        barcode_type: Type of barcode (code128, ean13, upc, etc.).
        writer_options: Optional dict of ImageWriter configuration.

    Returns:
        A ContentFile containing the barcode image (PNG).
    """
    default_options = {
        "module_width": 0.3,
        "module_height": 15.0,
        "font_size": 10,
        "text_distance": 5.0,
        "quiet_zone": 6.5,
    }
    if writer_options:
        default_options.update(writer_options)

    barcode_class = barcode.get_barcode_class(barcode_type)
    barcode_instance = barcode_class(code, writer=ImageWriter())

    buffer = io.BytesIO()
    barcode_instance.write(buffer, options=default_options)
    buffer.seek(0)

    filename = f"barcode_{code}.png"
    return ContentFile(buffer.read(), name=filename)


def generate_qr_code_image(
    data: str,
    box_size: int = 10,
    border: int = 4,
) -> ContentFile:
    """
    Generate a QR code image and return it as a Django ContentFile.

    Args:
        data: The data to encode in the QR code.
        box_size: Size of each QR module in pixels.
        border: Border width in modules.

    Returns:
        A ContentFile containing the QR code image (PNG).
    """
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"qr_{data[:30].replace('/', '_')}.png"
        return ContentFile(buffer.read(), name=filename)
    except ImportError:
        logger.error("qrcode library not installed. Cannot generate QR codes.")
        raise


def generate_location_barcode(
    warehouse_code: str,
    zone_code: str,
    aisle: str,
    rack: str,
    shelf: str,
    position: str = "",
) -> str:
    """
    Generate a deterministic barcode string for a warehouse location.

    Format: WH-{warehouse_code}-{zone_code}-{aisle}-{rack}-{shelf}[-{position}]
    """
    parts = [warehouse_code, zone_code, aisle, rack, shelf]
    if position:
        parts.append(position)
    return "LOC-" + "-".join(parts).upper()


def generate_bin_barcode(location_barcode: str, bin_code: str) -> str:
    """Generate a barcode string for a bin within a location."""
    return f"BIN-{location_barcode.replace('LOC-', '')}-{bin_code}".upper()
