// Admin API client
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
    console.error(`Admin API Error on ${url}:`, err);
    throw err;
  }
}

export const adminApi = {
  // Store Settings
  async getStoreSettings() {
    return await request(`${API_BASE}/api/store-settings`);
  },

  async updateStoreSettings(data) {
    return await request(`${API_BASE}/api/admin/store-settings`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  // Categories
  async getCategories() {
    return await request(`${API_BASE}/api/admin/categories`);
  },

  async createCategory(data) {
    return await request(`${API_BASE}/api/admin/categories`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateCategory(id, data) {
    return await request(`${API_BASE}/api/admin/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteCategory(id) {
    return await request(`${API_BASE}/api/admin/categories/${id}`, {
      method: "DELETE",
    });
  },

  // Products
  async getProducts() {
    return await request(`${API_BASE}/api/admin/products`);
  },

  async createProduct(data) {
    return await request(`${API_BASE}/api/admin/products`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateProduct(id, data) {
    return await request(`${API_BASE}/api/admin/products/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteProduct(id) {
    return await request(`${API_BASE}/api/admin/products/${id}`, {
      method: "DELETE",
    });
  },

  async announceProduct(id) {
    return await request(`${API_BASE}/api/admin/products/${id}/announce`, {
      method: "POST",
    });
  },

  // Uploaded Images
  async getUploadedImages(isUsed = null) {
    const url = isUsed !== null
      ? `${API_BASE}/api/admin/uploaded-images?is_used=${isUsed}`
      : `${API_BASE}/api/admin/uploaded-images`;
    return await request(url);
  },

  async deleteUploadedImage(id) {
    return await request(`${API_BASE}/api/admin/uploaded-images/${id}`, {
      method: "DELETE",
    });
  },

  // Orders
  async getOrders(status = null) {
    const url = status
      ? `${API_BASE}/api/admin/orders?status=${status}`
      : `${API_BASE}/api/admin/orders`;
    return await request(url);
  },

  async updateOrderStatus(id, status) {
    return await request(`${API_BASE}/api/admin/orders/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },
};
