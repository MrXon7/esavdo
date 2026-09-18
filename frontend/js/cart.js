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
      cb(this.items, this.getTotalCount(), this.getTotalPrice());
    }
  }

  async load() {
    try {
      this.items = await api.getCart();
      this.notify();
    } catch (e) {
      console.warn("Cart load error (may be guest):", e);
    }
  }

  getTotalCount() {
    return this.items.reduce((sum, item) => sum + item.quantity, 0);
  }

  getTotalPrice() {
    return this.items.reduce((sum, item) => {
      const price = item.product ? item.product.price : 0;
      return sum + price * item.quantity;
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

  async add(productId, quantity = 1) {
    await api.addToCart(productId, quantity);
    await this.load();
  }

  async updateQuantity(cartItemId, newQty) {
    await api.updateCartItem(cartItemId, newQty);
    await this.load();
  }

  async remove(cartItemId) {
    await api.removeCartItem(cartItemId);
    await this.load();
  }

  formatPrice(amount) {
    return (
      new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(amount) +
      " " +
      this.currency
    );
  }
}

export const cart = new CartStore();
