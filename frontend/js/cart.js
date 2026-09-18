import { api } from "./api.js";

class CartStore {
  constructor() {
    this.items = [];
    this.currency = "so'm";
    this.listeners = [];
  }

  setCurrency(curr) {
    this.currency = curr || "so'm";
    this.notify();
  }

  subscribe(callback) {
    this.listeners.push(callback);
  }

  notify() {
    for (const cb of this.listeners) {
      try {
        cb(this.items, this.getTotalCount(), this.getTotalPrice());
      } catch (e) {
        console.error("Listener error:", e);
      }
    }
  }

  async load() {
    try {
      this.items = await api.getCart();
      this.notify();
    } catch (e) {
      console.warn("Cart load error (guest or offline):", e);
    }
  }

  getTotalCount() {
    return this.items.reduce((sum, item) => sum + (item.quantity || 0), 0);
  }

  getTotalPrice() {
    return this.items.reduce((sum, item) => {
      const price = item.product ? Number(item.product.price) || 0 : 0;
      return sum + price * (item.quantity || 0);
    }, 0);
  }

  getItemQuantity(productId) {
    const found = this.items.find((i) => i.product_id === productId);
    return found ? found.quantity : 0;
  }

  getCartItemId(productId) {
    const found = this.items.find((i) => i.product_id === productId);
    return found ? found.id : null;
  }

  /**
   * Optimistic Add to Cart — Instant UI update (0ms), background API sync
   */
  async add(productId, quantity = 1, productObj = null) {
    const existing = this.items.find((i) => i.product_id === productId);
    if (existing) {
      existing.quantity += quantity;
    } else {
      this.items.push({
        id: `temp_${Date.now()}`,
        product_id: productId,
        quantity: quantity,
        product: productObj || { id: productId, price: 0, name: "Mahsulot" },
      });
    }
    // Instant UI feedback
    this.notify();

    // Background sync
    try {
      await api.addToCart(productId, quantity);
      await this.load();
    } catch (err) {
      console.error("Optimistic add error:", err);
      await this.load(); // Rollback on error
    }
  }

  /**
   * Optimistic Update Quantity — Instant UI update (0ms), background API sync
   */
  async updateQuantity(cartItemId, newQty) {
    const idx = this.items.findIndex((i) => i.id === cartItemId);
    if (idx !== -1) {
      if (newQty <= 0) {
        this.items.splice(idx, 1);
      } else {
        this.items[idx].quantity = newQty;
      }
      // Instant UI feedback
      this.notify();
    }

    // Background sync
    try {
      if (newQty <= 0) {
        await api.removeCartItem(cartItemId);
      } else {
        await api.updateCartItem(cartItemId, newQty);
      }
      await this.load();
    } catch (err) {
      console.error("Optimistic update error:", err);
      await this.load(); // Rollback on error
    }
  }

  /**
   * Optimistic Remove Item — Instant UI update (0ms)
   */
  async remove(cartItemId) {
    const idx = this.items.findIndex((i) => i.id === cartItemId);
    if (idx !== -1) {
      this.items.splice(idx, 1);
      this.notify();
    }

    try {
      await api.removeCartItem(cartItemId);
      await this.load();
    } catch (err) {
      console.error("Optimistic remove error:", err);
      await this.load();
    }
  }

  formatPrice(amount) {
    return (
      new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(amount || 0) +
      " " +
      this.currency
    );
  }
}

export const cart = new CartStore();
