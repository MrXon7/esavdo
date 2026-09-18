// Telegram WebApp API Client
const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const API_BASE = "";

function getAuthHeaders() {
  const headers = {
    "Content-Type": "application/json",
  };
  if (tg && tg.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  }
  return headers;
}

async function request(url, options = {}) {
  const defaultHeaders = getAuthHeaders();
  options.headers = { ...defaultHeaders, ...options.headers };

  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      let errDetail = "Xatolik yuz berdi";
      try {
        const errJson = await response.json();
        errDetail = errJson.detail || errDetail;
      } catch (e) {}
      throw new Error(errDetail);
    }
    return await response.json();
  } catch (err) {
    console.error(`API Error on ${url}:`, err);
    throw err;
  }
}

export const api = {
  // Store Settings (White-Label)
  async getStoreSettings() {
    return await request(`${API_BASE}/api/store-settings`);
  },

  async getMe() {
    return await request(`${API_BASE}/api/store-settings/me`);
  },

  // Categories
  async getCategories() {
    return await request(`${API_BASE}/api/categories`);
  },

  // Products
  async getProducts(categoryId = null, search = null) {
    const params = new URLSearchParams();
    if (categoryId) params.append("category_id", categoryId);
    if (search) params.append("search", search);
    return await request(`${API_BASE}/api/products?${params.toString()}`);
  },

  async getProduct(id) {
    return await request(`${API_BASE}/api/products/${id}`);
  },

  // Cart
  async getCart() {
    return await request(`${API_BASE}/api/cart`);
  },

  async addToCart(productId, quantity = 1) {
    return await request(`${API_BASE}/api/cart`, {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    });
  },

  async updateCartItem(itemId, quantity) {
    return await request(`${API_BASE}/api/cart/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity }),
    });
  },

  async setCartQuantityByProduct(productId, quantity) {
    return await request(`${API_BASE}/api/cart/by-product/${productId}`, {
      method: "PUT",
      body: JSON.stringify({ quantity }),
    });
  },

  async removeCartItem(itemId) {
    return await request(`${API_BASE}/api/cart/${itemId}`, {
      method: "DELETE",
    });
  },

  // Orders
  async createOrder(orderData) {
    return await request(`${API_BASE}/api/orders`, {
      method: "POST",
      body: JSON.stringify(orderData),
    });
  },

  async getMyOrders() {
    return await request(`${API_BASE}/api/orders`);
  },

  async deleteOrder(orderId) {
    return await request(`${API_BASE}/api/orders/${orderId}`, {
      method: "DELETE",
    });
  },
};
