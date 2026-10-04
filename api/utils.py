from typing import Optional


def get_safe_image_id(order_item) -> Optional[str]:
    """
    Safely extract the first product image file_id from an OrderItem's product relation.
    Returns None on any error (deleted product, empty images, detached instance, etc.).
    """
    try:
        product = getattr(order_item, "product", None)
        if not product:
            return None
        images = getattr(product, "images", None)
        if not images:
            return None
        first = images[0] if len(images) > 0 else None
        return getattr(first, "file_id", None) if first else None
    except Exception:
        return None
