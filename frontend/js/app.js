import { api } from "./api.js";
import { cart } from "./cart.js";

const tg = window.Telegram?.WebApp;

// App State
let currentView = "catalog"; // "catalog" | "cart" | "orders" | "checkout"
let categories = [];
let selectedCategoryId = null;
let products = [];
let activeProductModal = null;
let storeSettings = null;

// DOM Elements
const elBrandLogo = document.getElementById("brand-logo");
const elBrandName = document.getElementById("brand-name");
const elCategories = document.getElementById("categories-slider");
const elProductsGrid = document.getElementById("products-grid");
const elSearchInput = document.getElementById("search-input");
const elCartCountBadge = document.getElementById("cart-count-badge");
const elCartItemsList = document.getElementById("cart-items-list");
const elCartTotalPrice = document.getElementById("cart-total-price");
const elOrdersList = document.getElementById("orders-list");

// Modal Elements
const elProductModal = document.getElementById("product-modal");
const elModalImg = document.getElementById("modal-img");
const elModalTitle = document.getElementById("modal-title");
const elModalPrice = document.getElementById("modal-price");
const elModalDesc = document.getElementById("modal-desc");
const elModalAddBtn = document.getElementById("modal-add-btn");

// Navigation Elements
const navBtns = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");

// Helper: Image URL
function getImageUrl(fileId) {
  if (!fileId) {
    return 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><rect width="200" height="200" fill="%23e5e5ea"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%238e8e93" font-size="14" font-family="sans-serif">Rasm yo‘q</text></svg>';
  }
  return `/images/${fileId}`;
}

// 1. Initialize Store Settings (White-Label)
async function initStore() {
  try {
    storeSettings = await api.getStoreSettings();
    document.title = storeSettings.store_name;
    elBrandName.textContent = storeSettings.store_name;

    if (storeSettings.currency) {
      cart.setCurrency(storeSettings.currency);
    }

    if (storeSettings.logo_file_id) {
      elBrandLogo.innerHTML = `<img src="${getImageUrl(storeSettings.logo_file_id)}" class="brand-logo" alt="Logo">`;
    } else {
      elBrandLogo.textContent = (storeSettings.store_name || "M")[0].toUpperCase();
    }
  } catch (err) {
    console.error("Store settings fetch error:", err);
  }
}

// 2. Load Categories
async function loadCategories() {
  try {
    categories = await api.getCategories();
    renderCategories();
  } catch (err) {
    console.error("Categories load error:", err);
  }
}

function renderCategories() {
  elCategories.innerHTML = "";

  const allPill = document.createElement("button");
  allPill.className = `category-pill ${selectedCategoryId === null ? "active" : ""}`;
  allPill.textContent = "Barchasi";
  allPill.onclick = () => selectCategory(null);
  elCategories.appendChild(allPill);

  for (const cat of categories) {
    const pill = document.createElement("button");
    pill.className = `category-pill ${selectedCategoryId === cat.id ? "active" : ""}`;
    pill.textContent = cat.name;
    pill.onclick = () => selectCategory(cat.id);
    elCategories.appendChild(pill);
  }
}

function selectCategory(id) {
  selectedCategoryId = id;
  renderCategories();
  loadProducts();
}

// 3. Load Products
async function loadProducts() {
  try {
    const searchVal = elSearchInput.value.trim() || null;
    products = await api.getProducts(selectedCategoryId, searchVal);
    renderProducts();
  } catch (err) {
    console.error("Products load error:", err);
    elProductsGrid.innerHTML = `<div class="empty-state">Mahsulotlarni yuklashda xatolik</div>`;
  }
}

function renderProducts() {
  if (!products.length) {
    elProductsGrid.innerHTML = `
      <div class="empty-state" style="grid-column: span 2;">
        <div class="empty-icon">🔍</div>
        <div>Hozircha mahsulotlar topilmadi</div>
      </div>
    `;
    return;
  }

  elProductsGrid.innerHTML = "";
  for (const p of products) {
    const card = document.createElement("div");
    card.className = "product-card";

    const firstImage = p.images && p.images.length > 0 ? p.images[0].file_id : null;
    const imgUrl = getImageUrl(firstImage);

    const qtyInCart = cart.getItemQuantity(p.id);
    const cartItemId = cart.getCartItemId(p.id);

    let actionBtnHtml = "";
    if (qtyInCart > 0) {
      actionBtnHtml = `
        <div class="qty-counter" onclick="event.stopPropagation()">
          <button class="qty-btn btn-dec" data-itemid="${cartItemId}" data-qty="${qtyInCart - 1}">−</button>
          <span class="qty-val">${qtyInCart}</span>
          <button class="qty-btn btn-inc" data-itemid="${cartItemId}" data-qty="${qtyInCart + 1}">+</button>
        </div>
      `;
    } else {
      actionBtnHtml = `
        <button class="btn-add-cart btn-add" data-prodid="${p.id}" onclick="event.stopPropagation()">
          🛒 Savatga
        </button>
      `;
    }

    card.innerHTML = `
      <div class="product-thumb-wrapper">
        <img src="${imgUrl}" class="product-thumb" alt="${p.name}" loading="lazy" />
      </div>
      <div class="product-details">
        <div class="product-title">${p.name}</div>
        <div class="product-price">${cart.formatPrice(p.price)}</div>
        ${actionBtnHtml}
      </div>
    `;

    card.onclick = () => openProductModal(p);
    elProductsGrid.appendChild(card);
  }

  // Attach card button handlers
  elProductsGrid.querySelectorAll(".btn-add").forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const prodId = parseInt(btn.dataset.prodid);
      await cart.add(prodId, 1);
      renderProducts();
    };
  });

  elProductsGrid.querySelectorAll(".btn-dec").forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const itemId = parseInt(btn.dataset.itemid);
      const newQty = parseInt(btn.dataset.qty);
      await cart.updateQuantity(itemId, newQty);
      renderProducts();
    };
  });

  elProductsGrid.querySelectorAll(".btn-inc").forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const itemId = parseInt(btn.dataset.itemid);
      const newQty = parseInt(btn.dataset.qty);
      await cart.updateQuantity(itemId, newQty);
      renderProducts();
    };
  });
}

// 4. Product Modal
function openProductModal(prod) {
  activeProductModal = prod;
  const firstImage = prod.images && prod.images.length > 0 ? prod.images[0].file_id : null;
  elModalImg.src = getImageUrl(firstImage);
  elModalTitle.textContent = prod.name;
  elModalPrice.textContent = cart.formatPrice(prod.price);
  elModalDesc.textContent = prod.description || "Tavsif berilmagan.";

  elProductModal.classList.add("active");
  if (tg) tg.BackButton.show();
}

function closeProductModal() {
  elProductModal.classList.remove("active");
  activeProductModal = null;
  if (tg && currentView === "catalog") {
    tg.BackButton.hide();
  }
}

elProductModal.onclick = (e) => {
  if (e.target === elProductModal) closeProductModal();
};

elModalAddBtn.onclick = async () => {
  if (activeProductModal) {
    await cart.add(activeProductModal.id, 1);
    closeProductModal();
    renderProducts();
  }
};

// 5. Cart Rendering
function renderCart() {
  if (!cart.items.length) {
    elCartItemsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🛒</div>
        <div>Savatingiz bo'sh</div>
        <button class="btn-primary" style="margin-top: 16px;" id="btn-back-to-catalog">
          Xarid qilish
        </button>
      </div>
    `;
    const btn = document.getElementById("btn-back-to-catalog");
    if (btn) btn.onclick = () => switchView("catalog");
    elCartTotalPrice.textContent = cart.formatPrice(0);
    document.getElementById("cart-summary-box").style.display = "none";
    if (tg) tg.MainButton.hide();
    return;
  }

  document.getElementById("cart-summary-box").style.display = "block";
  elCartItemsList.innerHTML = "";

  for (const item of cart.items) {
    const prod = item.product;
    if (!prod) continue;
    const firstImg = prod.images && prod.images.length > 0 ? prod.images[0].file_id : null;

    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `
      <img src="${getImageUrl(firstImg)}" class="cart-item-img" alt="${prod.name}">
      <div class="cart-item-info">
        <div class="cart-item-title">${prod.name}</div>
        <div class="cart-item-price">${cart.formatPrice(prod.price)}</div>
      </div>
      <div class="qty-counter">
        <button class="qty-btn cart-dec" data-id="${item.id}" data-qty="${item.quantity - 1}">−</button>
        <span class="qty-val">${item.quantity}</span>
        <button class="qty-btn cart-inc" data-id="${item.id}" data-qty="${item.quantity + 1}">+</button>
      </div>
    `;
    elCartItemsList.appendChild(row);
  }

  elCartTotalPrice.textContent = cart.formatPrice(cart.getTotalPrice());

  elCartItemsList.querySelectorAll(".cart-dec").forEach((btn) => {
    btn.onclick = async () => {
      await cart.updateQuantity(parseInt(btn.dataset.id), parseInt(btn.dataset.qty));
      renderCart();
      renderProducts();
    };
  });

  elCartItemsList.querySelectorAll(".cart-inc").forEach((btn) => {
    btn.onclick = async () => {
      await cart.updateQuantity(parseInt(btn.dataset.id), parseInt(btn.dataset.qty));
      renderCart();
      renderProducts();
    };
  });
}

// 6. Navigation / Views Switch
function switchView(viewName) {
  currentView = viewName;
  views.forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${viewName}`).classList.add("active");

  navBtns.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });

  if (viewName === "cart") {
    renderCart();
  } else if (viewName === "orders") {
    loadOrders();
  } else if (viewName === "catalog") {
    renderProducts();
  }

  // Telegram BackButton management
  if (tg) {
    if (viewName === "checkout" || viewName === "cart" || viewName === "orders") {
      tg.BackButton.show();
    } else {
      tg.BackButton.hide();
    }
  }
}

navBtns.forEach((btn) => {
  btn.onclick = () => switchView(btn.dataset.view);
});

// Checkout Button in Cart
document.getElementById("btn-go-to-checkout").onclick = () => {
  if (!cart.items.length) return;
  switchView("checkout");
};

// 7. Checkout Form Submission
const checkoutForm = document.getElementById("checkout-form");
checkoutForm.onsubmit = async (e) => {
  e.preventDefault();
  const address = document.getElementById("input-address").value.trim();
  const phone = document.getElementById("input-phone").value.trim();
  const paymentType = document.getElementById("input-payment-type").value;
  const notes = document.getElementById("input-notes").value.trim();

  if (!address || !phone) {
    alert("Iltimos, manzil va telefon raqamingizni kiriting!");
    return;
  }

  const submitBtn = document.getElementById("btn-submit-order");
  submitBtn.disabled = true;
  submitBtn.textContent = "Buyurtma berilmoqda...";

  try {
    await api.createOrder({
      address,
      phone,
      payment_type: paymentType,
      notes: notes || null,
    });

    await cart.load();
    alert("Buyurtmangiz muvaffaqiyatli qabul qilindi!");
    checkoutForm.reset();
    switchView("orders");
  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Buyurtmani tasdiqlash";
  }
};

// 8. Orders History
async function loadOrders() {
  try {
    elOrdersList.innerHTML = `<div class="empty-state">Yuklanmoqda...</div>`;
    const orders = await api.getMyOrders();

    if (!orders.length) {
      elOrdersList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📦</div>
          <div>Buyurtmalar tarixi bo'sh</div>
        </div>
      `;
      return;
    }

    elOrdersList.innerHTML = "";
    for (const ord of orders) {
      const card = document.createElement("div");
      card.className = "order-card";

      const badgeClass = `badge-${ord.status}`;
      const statusLabelMap = {
        pending: "⏳ Kutilmoqda",
        confirmed: "✅ Tasdiqlandi",
        preparing: "👨‍🍳 Tayyorlanmoqda",
        delivering: "🛵 Yetkazilmoqda",
        completed: "🎉 Yakunlandi",
        cancelled: "❌ Bekor qilindi",
      };
      const statusText = statusLabelMap[ord.status] || ord.status;

      let itemsHtml = "";
      for (const itm of ord.items) {
        itemsHtml += `<div class="order-item-line">• ${itm.product_name} (${itm.quantity} dona)</div>`;
      }

      const dateStr = new Date(ord.created_at).toLocaleDateString("uz-UZ", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });

      card.innerHTML = `
        <div class="order-header">
          <span class="order-id">Buyurtma #${ord.id}</span>
          <span class="order-badge ${badgeClass}">${statusText}</span>
        </div>
        <div style="font-size: 12px; color: var(--hint-color);">${dateStr}</div>
        <div style="margin: 6px 0;">${itemsHtml}</div>
        <div class="order-total-line">
          <span>Jami:</span>
          <span>${cart.formatPrice(ord.total_price)}</span>
        </div>
      `;
      elOrdersList.appendChild(card);
    }
  } catch (err) {
    console.error("Orders load error:", err);
    elOrdersList.innerHTML = `<div class="empty-state">Buyurtmalarni yuklab bo'lmadi</div>`;
  }
}

// 9. Search Debounce
let searchTimeout = null;
elSearchInput.oninput = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadProducts();
  }, 350);
};

// 10. Cart Badge Listener
cart.subscribe((items, totalCount, totalPrice) => {
  if (totalCount > 0) {
    elCartCountBadge.textContent = totalCount;
    elCartCountBadge.style.display = "flex";
  } else {
    elCartCountBadge.style.display = "none";
  }
});

// Telegram BackButton Handler
if (tg) {
  tg.BackButton.onClick(() => {
    if (activeProductModal) {
      closeProductModal();
    } else if (currentView === "checkout") {
      switchView("cart");
    } else {
      switchView("catalog");
    }
  });
}

// Initial Boot
async function startApp() {
  // Check if current user is admin — redirect to admin panel if so
  if (tg && tg.initData) {
    try {
      const me = await api.getMe();
      if (me && me.is_admin === true) {
        // Admin — yo'naltirish
        window.location.replace("/admin/");
        return;
      }
    } catch (err) {
      // Admin emas yoki autentifikatsiya yo'q — odatdagi do'kon sifatida davom et
      console.log("Oddiy foydalanuvchi:", err.message);
    }
  }

  await initStore();
  await loadCategories();
  await cart.load();
  await loadProducts();
}

startApp();
