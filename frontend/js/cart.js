import { api } from "./api.js";

class CartStore {
  constructor() {
    this.items = [];
    this.currency = "so'm";
    this.listeners = [];
    // Debounce timers per product_id: productId -> timer
    this._syncTimers = new Map();
  }

  setCurrency(curr) {
    this.currency = curr || "so'm";
    this.notify();
  }

  subscribe(callback) {
    this.listeners.push(callback);
  }

  notify() {
    const totalCount = this.getTotalCount();
    const totalPrice = this.getTotalPrice();
    for (const cb of this.listeners) {
      try {
        cb(this.items, totalCount, totalPrice);
      } catch (e) {
        console.error("Cart listener error:", e);
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
    const pId = Number(productId);
    const found = this.items.find((i) => Number(i.product_id) === pId);
    return found ? found.quantity : 0;
  }

  getCartItemId(productId) {
    const pId = Number(productId);
    const found = this.items.find((i) => Number(i.product_id) === pId);
    return found ? found.id : null;
  }

  /**
   * Optimistic Add or Increment
   * - 0ms synchronous local state update + notify
   * - Debounced background sync by product_id (guaranteed reliable, no temp ID bugs)
   */
  add(productId, quantity = 1, productObj = null) {
    const pId = Number(productId);
    let item = this.items.find((i) => Number(i.product_id) === pId);

    if (item) {
      item.quantity += quantity;
    } else {
      item = {
        id: `local_${pId}`,
        product_id: pId,
        quantity: quantity,
        product: productObj || { id: pId, price: 0, name: "Mahsulot" },
      };
      this.items.push(item);
    }

    // Instant local UI notification
    this.notify();

    // Trigger debounced server sync
    this._scheduleSync(pId, item.quantity);
  }

  /**
   * Optimistic Direct Quantity Set
   * - 0ms synchronous local update + notify
   */
  setQuantity(productId, newQty) {
    const pId = Number(productId);
    const targetQty = Math.max(0, parseInt(newQty) || 0);
    const idx = this.items.findIndex((i) => Number(i.product_id) === pId);

    if (targetQty <= 0) {
      if (idx !== -1) {
        this.items.splice(idx, 1);
      }
    } else {
      if (idx !== -1) {
        this.items[idx].quantity = targetQty;
      }
    }

    // Instant local UI notification
    this.notify();

    // Trigger debounced server sync
    this._scheduleSync(pId, targetQty);
  }

  /**
   * Compatibility wrapper for updateQuantity(cartItemId, newQty)
   */
  updateQuantity(cartItemId, newQty) {
    const item = this.items.find(
      (i) => i.id === cartItemId || String(i.id) === String(cartItemId)
    );
    if (item) {
      this.setQuantity(item.product_id, newQty);
    }
  }

  /**
   * Remove item from cart completely
   */
  remove(cartItemId) {
    const item = this.items.find(
      (i) => i.id === cartItemId || String(i.id) === String(cartItemId)
    );
    if (item) {
      this.setQuantity(item.product_id, 0);
    }
  }

  /**
   * Debounced background sync:
   * Aggregates rapid taps into a single network call after 300ms of user inactivity.
   */
  _scheduleSync(productId, quantity) {
    if (this._syncTimers.has(productId)) {
      clearTimeout(this._syncTimers.get(productId));
    }

    const timer = setTimeout(async () => {
      this._syncTimers.delete(productId);
      try {
        const res = await api.setCartQuantityByProduct(productId, quantity);
        // Sync the real DB item ID if it was local
        if (res && res.id) {
          const item = this.items.find((i) => Number(i.product_id) === productId);
          if (item) item.id = res.id;
        }
      } catch (err) {
        console.error("Cart sync error:", err);
        // Rollback from server on hard failure
        await this.load();
      }
    }, 300);

    this._syncTimers.set(productId, timer);
  }

  formatPrice(amount) {
    return (
      new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(
        amount || 0
      ) +
      " " +
      this.currency
    );
  }
}

export const cart = new CartStore();
