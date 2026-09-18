import { adminApi } from "./admin-api.js";

// Telegram Theme Sync
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.colorScheme) {
    document.documentElement.setAttribute("data-theme", tg.colorScheme);
  }
}

// ─── State ───────────────────────────────────────────────────────────────────
let currentTab = "orders";
let currentOrderStatusFilter = null;
let categoriesList = [];
let uploadedImagesList = [];
let selectedImageFileIds = new Set();
let editingProductId = null;
let storeSettings = null;

// ─── Client-side Cache ───────────────────────────────────────────────────────
let _allAdminOrders = null;     // null = not loaded yet; array of all orders
let _productsCache = null;      // null = not loaded yet
let _categoriesCache = null;    // null = not loaded yet
let _imagesCache = null;        // null = not loaded yet
let _settingsCache = null;      // null = not loaded yet
// Which tabs have been shown at least once (to skip animation on revisit)
const _tabShown = new Set();

// ─── Helpers ─────────────────────────────────────────────────────────────────
function getImageUrl(fileId) {
  if (!fileId) return "";
  return `/images/${fileId}`;
}

function formatPrice(amount) {
  const curr = storeSettings?.currency || "so'm";
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(amount || 0) + " " + curr;
}

// ─── 1. Tab Switching ────────────────────────────────────────────────────────
const tabs = document.querySelectorAll(".nav-tab");
const sections = document.querySelectorAll(".admin-section");

function switchTab(tabName) {
  currentTab = tabName;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));

  sections.forEach((s) => {
    const isTarget = s.id === `tab-${tabName}`;
    s.classList.toggle("active", isTarget);
    // Animation only on first visit — remove class if already seen
    if (isTarget) {
      if (_tabShown.has(tabName)) {
        s.style.animation = "none";
      } else {
        s.style.animation = "";
        _tabShown.add(tabName);
      }
    }
  });

  if (tabName === "orders") loadOrders();
  else if (tabName === "products") loadProducts();
  else if (tabName === "images") loadImagesGallery();
  else if (tabName === "categories") loadCategories();
  else if (tabName === "settings") loadSettings();
}

tabs.forEach((t) => {
  t.onclick = () => switchTab(t.dataset.tab);
});

// ─── 2. Orders Tab ───────────────────────────────────────────────────────────
const elOrdersContainer = document.getElementById("admin-orders-list");
const statusFilterBtns = document.querySelectorAll(".filter-btn");

function filterAndRenderOrders() {
  if (!_allAdminOrders) return;
  let list = _allAdminOrders;
  if (currentOrderStatusFilter) {
    list = _allAdminOrders.filter((o) => o.status === currentOrderStatusFilter);
  }
  renderOrdersFromData(list);
}

statusFilterBtns.forEach((btn) => {
  if (btn.id === "btn-refresh-orders") return;
  btn.onclick = () => {
    statusFilterBtns.forEach((b) => {
      if (b.id !== "btn-refresh-orders") b.classList.remove("active");
    });
    btn.classList.add("active");
    currentOrderStatusFilter = btn.dataset.status || null;
    // 0ms instant filter directly in memory — NO skeleton, NO server call!
    filterAndRenderOrders();
  };
});

const btnRefreshOrders = document.getElementById("btn-refresh-orders");
if (btnRefreshOrders) {
  btnRefreshOrders.onclick = () => {
    loadOrders(true);
  };
}

function renderAdminOrdersSkeleton() {
  if (!elOrdersContainer) return;
  elOrdersContainer.innerHTML = `
    <div class="admin-card" style="padding: 16px;">
      <div class="skeleton" style="width: 40%; height: 18px; margin-bottom: 8px;"></div>
      <div class="skeleton" style="width: 65%; height: 14px; margin-bottom: 12px;"></div>
      <div class="skeleton" style="width: 100%; height: 50px; border-radius: 8px; margin-bottom: 12px;"></div>
      <div class="skeleton" style="width: 30%; height: 20px;"></div>
    </div>
    <div class="admin-card" style="padding: 16px;">
      <div class="skeleton" style="width: 40%; height: 18px; margin-bottom: 8px;"></div>
      <div class="skeleton" style="width: 60%; height: 14px; margin-bottom: 12px;"></div>
      <div class="skeleton" style="width: 100%; height: 40px; border-radius: 8px;"></div>
    </div>
  `;
}

function renderOrdersFromData(orders) {
  if (!elOrdersContainer) return;

  if (!orders || !orders.length) {
    elOrdersContainer.innerHTML = `
      <div style="text-align:center; padding:40px 16px; color:var(--text-secondary);">
        <div style="font-size:46px; margin-bottom:8px;">📦</div>
        <div style="font-weight:700; font-size:15px;">Hozircha buyurtmalar yo'q</div>
        <div style="font-size:13px; margin-top:4px;">Yangi buyurtmalar tushishi bilan shu yerda ko'rinadi</div>
      </div>
    `;
    return;
  }

  elOrdersContainer.innerHTML = "";
  for (const ord of orders) {
    const card = document.createElement("div");
    card.className = "admin-card";

    let itemsHtml = "";
    for (const i of ord.items || []) {
      itemsHtml += `<div style="margin-bottom:3px;">• <b>${i.product_name}</b> — ${i.quantity} dona x ${formatPrice(i.price_at_order_time)}</div>`;
    }

    const dateStr = new Date(ord.created_at).toLocaleString("uz-UZ", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    let actionBtns = "";
    if (ord.status === "pending") {
      actionBtns = `
        <button class="btn btn-success btn-sm" onclick="updateStatus(${ord.id}, 'confirmed')">✅ Tasdiqlash</button>
        <button class="btn btn-danger btn-sm" onclick="updateStatus(${ord.id}, 'cancelled')">❌ Rad etish</button>
      `;
    } else if (ord.status === "confirmed") {
      actionBtns = `
        <button class="btn btn-primary btn-sm" onclick="updateStatus(${ord.id}, 'preparing')">👨‍🍳 Tayyorlash</button>
        <button class="btn btn-danger btn-sm" onclick="updateStatus(${ord.id}, 'cancelled')">Bekor qilish</button>
      `;
    } else if (ord.status === "preparing") {
      actionBtns = `
        <button class="btn btn-primary btn-sm" onclick="updateStatus(${ord.id}, 'delivering')">🛵 Yetkazishga berish</button>
      `;
    } else if (ord.status === "delivering") {
      actionBtns = `
        <button class="btn btn-success btn-sm" onclick="updateStatus(${ord.id}, 'completed')">🎉 Topshirildi (Yakunlandi)</button>
      `;
    }

    const badgeClass = `badge-${ord.status}`;
    const statusLabelMap = {
      pending: "⏳ Kutilmoqda",
      confirmed: "✅ Tasdiqlandi",
      preparing: "👨‍🍳 Tayyorlanmoqda",
      delivering: "🛵 Yetkazilmoqda",
      completed: "🎉 Yakunlandi",
      cancelled: "❌ Bekor qilindi",
    };

    card.innerHTML = `
      <div class="admin-card-header">
        <span style="font-weight:800; font-size:16px; color:var(--text-primary);">Buyurtma #${ord.id}</span>
        <span class="order-badge ${badgeClass}">${statusLabelMap[ord.status] || ord.status}</span>
      </div>
      <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">${dateStr}</div>
      <div style="font-size:13.5px; color:var(--text-primary); line-height:1.55; margin-bottom:10px;">
        <div>👤 <b>Mijoz:</b> ${ord.user ? ord.user.full_name : "Noma'lum"}</div>
        <div>📞 <b>Tel:</b> <a href="tel:${ord.phone}" style="color:var(--button-color); text-decoration:none; font-weight:700;">${ord.phone}</a></div>
        <div>📍 <b>Manzil:</b> ${ord.address}</div>
        <div>💳 <b>To'lov:</b> ${ord.payment_type === "cash" ? "Naqd pul" : "Karta"}</div>
        ${ord.notes ? `<div>📝 <b>Izoh:</b> ${ord.notes}</div>` : ""}
      </div>
      <div style="background:var(--secondary-bg); border:1px solid var(--border-subtle); padding:10px; border-radius:8px; font-size:13px; color:var(--text-primary); margin-bottom:8px;">
        <div style="font-weight:700; margin-bottom:4px;">Mahsulotlar:</div>
        ${itemsHtml || "<div>Mahsulot ma'lumoti yo'q</div>"}
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px dashed var(--border-subtle); padding-top:8px; margin-bottom:8px;">
        <span style="font-weight:600; color:var(--text-secondary);">Jami summa:</span>
        <span style="font-weight:800; font-size:16px; color:var(--button-color);">${formatPrice(ord.total_price)}</span>
      </div>
      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        ${actionBtns}
      </div>
    `;
    elOrdersContainer.appendChild(card);
  }
}

/**
 * Load orders with smart caching.
 * Fetches all orders once, then allows instant 0ms filtering by status.
 * @param {boolean} forceRefresh - if true, bypass cache and fetch from server
 */
async function loadOrders(forceRefresh = false) {
  if (!elOrdersContainer) return;

  // Serve from memory cache immediately (no skeleton, no server call)
  if (!forceRefresh && _allAdminOrders !== null) {
    filterAndRenderOrders();
    return;
  }

  // First time or forced — show skeleton and fetch from server
  try {
    renderAdminOrdersSkeleton();
    const orders = await adminApi.getOrders();
    _allAdminOrders = orders || [];
    filterAndRenderOrders();
  } catch (err) {
    console.error("Load orders error:", err);
    elOrdersContainer.innerHTML = `<div style="color:var(--danger-color); text-align:center; padding:20px;">Xatolik: ${err.message}</div>`;
  }
}

window.updateStatus = async (orderId, newStatus) => {
  if (!confirm(`Buyurtma statusini o'zgartirishni tasdiqlaysizmi: ${newStatus}?`)) return;
  try {
    // 1. Optimistic UI update: update local item immediately!
    if (_allAdminOrders) {
      const target = _allAdminOrders.find((o) => o.id === orderId);
      if (target) {
        target.status = newStatus;
        filterAndRenderOrders(); // Instant UI update (0ms)!
      }
    }

    // 2. Sync to server
    await adminApi.updateOrderStatus(orderId, newStatus);
  } catch (err) {
    alert("Xatolik: " + err.message);
    loadOrders(true); // Rollback on error
  }
};

// ─── 3. Products Tab ─────────────────────────────────────────────────────────
const elProductsContainer = document.getElementById("admin-products-list");
const elProductModal = document.getElementById("product-modal");
const elProductForm = document.getElementById("product-form");
const elImagePicker = document.getElementById("product-image-picker");
const elCategorySelect = document.getElementById("product-category-select");

function renderAdminProductsSkeleton() {
  if (!elProductsContainer) return;
  elProductsContainer.innerHTML = `
    <div class="admin-card" style="display:flex; gap:12px; align-items:center; padding:12px;">
      <div class="skeleton" style="width:56px; height:56px; border-radius:8px; flex-shrink:0;"></div>
      <div style="flex-grow:1;">
        <div class="skeleton" style="width:60%; height:16px; margin-bottom:8px;"></div>
        <div class="skeleton" style="width:40%; height:14px;"></div>
      </div>
    </div>
    <div class="admin-card" style="display:flex; gap:12px; align-items:center; padding:12px;">
      <div class="skeleton" style="width:56px; height:56px; border-radius:8px; flex-shrink:0;"></div>
      <div style="flex-grow:1;">
        <div class="skeleton" style="width:50%; height:16px; margin-bottom:8px;"></div>
        <div class="skeleton" style="width:35%; height:14px;"></div>
      </div>
    </div>
  `;
}

function renderProductsFromData(products) {
  if (!elProductsContainer) return;

  if (!products || !products.length) {
    elProductsContainer.innerHTML = `
      <div style="text-align:center; padding:40px 16px; color:var(--text-secondary);">
        <div style="font-size:46px; margin-bottom:8px;">🏷</div>
        <div style="font-weight:700; font-size:15px;">Hozircha mahsulotlar yo'q</div>
        <div style="font-size:13px; margin-top:4px;">Yuqoridagi tugma orqali yangi mahsulot qo'shing</div>
      </div>
    `;
    return;
  }

  elProductsContainer.innerHTML = "";
  for (const p of products) {
    const card = document.createElement("div");
    card.className = "admin-product-item";

    const firstImg = p.images && p.images.length > 0 ? p.images[0].file_id : null;
    const imgUrl = getImageUrl(firstImg);

    card.innerHTML = `
      <img src="${imgUrl || 'data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'60\' height=\'60\'><rect width=\'60\' height=\'60\' fill=\'%23eee\'/></svg>'}" class="admin-prod-img" alt="${p.name}">
      <div class="admin-prod-info">
        <div class="admin-prod-name">${p.name}</div>
        <div class="admin-prod-price">${formatPrice(p.price)}</div>
        <div style="font-size:11.5px; font-weight:700; color:${p.is_active ? 'var(--success-color)' : 'var(--danger-color)'};">
          ${p.is_active ? '● Faol' : '● Nofaol'}
        </div>
      </div>
      <div style="display:flex; gap:6px; flex-shrink:0;">
        <button class="btn btn-secondary btn-sm" onclick="openEditProduct(${p.id})">✏️</button>
        <button class="btn btn-primary btn-sm" onclick="announceToGroup(${p.id})" title="Guruhga e'lon qilish">📢</button>
        <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id})">🗑</button>
      </div>
    `;
    elProductsContainer.appendChild(card);
  }
}

/**
 * Load products with smart caching.
 * @param {boolean} forceRefresh - if true, bypass cache
 */
async function loadProducts(forceRefresh = false) {
  if (!elProductsContainer) return;

  if (!forceRefresh && _productsCache !== null) {
    renderProductsFromData(_productsCache);
    return;
  }

  try {
    renderAdminProductsSkeleton();
    const products = await adminApi.getProducts();
    _productsCache = products;
    renderProductsFromData(products);
  } catch (err) {
    console.error("Load products error:", err);
    elProductsContainer.innerHTML = `<div style="color:var(--danger-color); text-align:center; padding:20px;">Xatolik: ${err.message}</div>`;
  }
}

window.announceToGroup = async (productId) => {
  if (!confirm("Ushbu mahsulotni guruhga e'lon qilinsinmi?")) return;
  try {
    await adminApi.announceProduct(productId);
    alert("🎉 Mahsulot muvaffaqiyatli guruhga e'lon qilindi!");
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

window.deleteProduct = async (productId) => {
  if (!confirm("Haqiqatan ham ushbu mahsulotni o'chirmoqchimisiz?")) return;
  try {
    await adminApi.deleteProduct(productId);
    _productsCache = null; // Invalidate cache
    loadProducts(true);
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// Add / Edit Product Modal
document.getElementById("btn-add-product").onclick = () => {
  editingProductId = null;
  document.getElementById("product-modal-title").textContent = "Yangi mahsulot qo'shish";
  elProductForm.reset();
  selectedImageFileIds.clear();
  renderImagePicker();
  populateCategorySelect();
  elProductModal.classList.add("active");
};

const closeProductModal = () => {
  elProductModal.classList.remove("active");
};
document.getElementById("btn-close-product-modal").onclick = closeProductModal;
elProductModal.onclick = (e) => {
  if (e.target === elProductModal) closeProductModal();
};

async function populateCategorySelect(selectedId = null) {
  try {
    // Use categories cache if available
    if (_categoriesCache !== null) {
      categoriesList = _categoriesCache;
    } else {
      categoriesList = await adminApi.getCategories();
      _categoriesCache = categoriesList;
    }
    elCategorySelect.innerHTML = `<option value="">-- Kategoriyasiz --</option>`;
    for (const cat of categoriesList) {
      const opt = document.createElement("option");
      opt.value = cat.id;
      opt.textContent = cat.name;
      if (selectedId && cat.id === selectedId) opt.selected = true;
      elCategorySelect.appendChild(opt);
    }
  } catch (e) {
    console.error("Category select error:", e);
  }
}

async function renderImagePicker(forceRefresh = false) {
  elImagePicker.innerHTML = `<div style="grid-column:span 3; font-size:12px; color:var(--text-secondary); text-align:center; padding:10px;">Rasmlar yuklanmoqda...</div>`;
  try {
    if (forceRefresh || _imagesCache === null) {
      uploadedImagesList = await adminApi.getUploadedImages(false);
      _imagesCache = uploadedImagesList;
    } else {
      uploadedImagesList = _imagesCache;
    }

    if (!uploadedImagesList.length && selectedImageFileIds.size === 0) {
      elImagePicker.innerHTML = `
        <div style="grid-column:span 3; font-size:12px; color:var(--text-secondary); text-align:center; padding:12px; line-height:1.4;">
          📸 Galereyada bo'sh rasmlar yo'q.<br/>Telegram botingizga rasm yuboring, u shu yerda paydo bo'ladi!
        </div>
      `;
      return;
    }

    elImagePicker.innerHTML = "";

    // Show selected images first
    for (const fileId of selectedImageFileIds) {
      const item = document.createElement("div");
      item.className = "picker-item selected";
      item.innerHTML = `
        <img src="${getImageUrl(fileId)}" alt="Selected">
        <span class="picker-check">✓</span>
      `;
      item.onclick = () => toggleImageSelection(fileId, item);
      elImagePicker.appendChild(item);
    }

    // Show unselected uploaded images
    for (const img of uploadedImagesList) {
      if (selectedImageFileIds.has(img.file_id)) continue;
      const item = document.createElement("div");
      item.className = "picker-item";
      item.innerHTML = `
        <img src="${getImageUrl(img.file_id)}" alt="Photo">
        <span class="picker-check">✓</span>
      `;
      item.onclick = () => toggleImageSelection(img.file_id, item);
      elImagePicker.appendChild(item);
    }
  } catch (err) {
    console.error("Image picker error:", err);
  }
}

function toggleImageSelection(fileId, itemEl) {
  if (selectedImageFileIds.has(fileId)) {
    selectedImageFileIds.delete(fileId);
    itemEl.classList.remove("selected");
  } else {
    selectedImageFileIds.add(fileId);
    itemEl.classList.add("selected");
  }
}

window.openEditProduct = async (productId) => {
  editingProductId = productId;
  document.getElementById("product-modal-title").textContent = "Mahsulotni tahrirlash";
  elProductModal.classList.add("active");

  try {
    // Check in-memory cache first for 0ms instant display, or fetch from API
    let p = _productsCache?.find((x) => x.id === productId);
    if (!p) {
      p = await adminApi.getProduct(productId);
    }

    document.getElementById("prod-name").value = p.name;
    document.getElementById("prod-price").value = p.price;
    document.getElementById("prod-desc").value = p.description || "";
    document.getElementById("prod-active").checked = p.is_active;

    await populateCategorySelect(p.category_id);

    selectedImageFileIds.clear();
    if (p.images) {
      for (const img of p.images) {
        selectedImageFileIds.add(img.file_id);
      }
    }
    renderImagePicker();
  } catch (err) {
    alert("Mahsulotni yuklab bo'lmadi: " + err.message);
  }
};

elProductForm.onsubmit = async (e) => {
  e.preventDefault();
  const name = document.getElementById("prod-name").value.trim();
  const price = parseFloat(document.getElementById("prod-price").value);
  const description = document.getElementById("prod-desc").value.trim();
  const categoryIdVal = elCategorySelect.value;
  const category_id = categoryIdVal ? parseInt(categoryIdVal) : null;
  const is_active = document.getElementById("prod-active").checked;
  const image_file_ids = Array.from(selectedImageFileIds);

  const saveBtn = e.target.querySelector('button[type="submit"]');
  const origText = saveBtn.textContent;
  saveBtn.disabled = true;
  saveBtn.innerHTML = `<span class="spinner"></span> Saqlanmoqda...`;

  try {
    if (editingProductId) {
      await adminApi.updateProduct(editingProductId, {
        name,
        price,
        description: description || null,
        category_id,
        is_active,
        image_file_ids,
      });
    } else {
      await adminApi.createProduct({
        name,
        price,
        description: description || null,
        category_id,
        is_active,
        image_file_ids,
      });
    }

    _productsCache = null; // Invalidate on save
    closeProductModal();
    loadProducts(true);
  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = origText;
  }
};

// ─── 4. Images Gallery Tab ───────────────────────────────────────────────────
const elGalleryContainer = document.getElementById("admin-gallery-list");

function renderGalleryFromData(images) {
  if (!elGalleryContainer) return;

  if (!images || !images.length) {
    elGalleryContainer.innerHTML = `
      <div style="grid-column:span 3; text-align:center; padding:40px 16px; color:var(--text-secondary);">
        <div style="font-size:46px; margin-bottom:8px;">📸</div>
        <div style="font-weight:700; font-size:15px;">Galereyada rasmlar yo'q</div>
        <div style="font-size:13px; margin-top:4px;">Telegram botingizga rasm yuboring, u darhol shu yerda paydo bo'ladi!</div>
      </div>
    `;
    return;
  }

  elGalleryContainer.innerHTML = "";
  for (const img of images) {
    const item = document.createElement("div");
    item.className = "gallery-item";
    item.innerHTML = `
      <img src="${getImageUrl(img.file_id)}" class="gallery-img" alt="Uploaded Image">
      <div style="position:absolute; bottom:4px; right:4px; font-size:10px; font-weight:700; background:rgba(0,0,0,0.65); color:#ffffff; padding:2px 6px; border-radius:4px;">
        ${img.is_used ? "Band" : "Bo'sh"}
      </div>
    `;
    elGalleryContainer.appendChild(item);
  }
}

async function loadImagesGallery(forceRefresh = false) {
  if (!elGalleryContainer) return;

  if (!forceRefresh && _imagesCache !== null) {
    renderGalleryFromData(_imagesCache);
    return;
  }

  try {
    elGalleryContainer.innerHTML = `<div style="grid-column:span 3; text-align:center; padding:30px; color:var(--text-secondary);">Yuklanmoqda...</div>`;
    const images = await adminApi.getUploadedImages();
    _imagesCache = images;
    renderGalleryFromData(images);
  } catch (err) {
    console.error("Load images error:", err);
  }
}

// ─── 5. Categories Tab ───────────────────────────────────────────────────────
const elCategoriesContainer = document.getElementById("admin-categories-list");
const elCategoryForm = document.getElementById("category-form");

function renderCategoriesFromData(cats) {
  if (!elCategoriesContainer) return;

  if (!cats || !cats.length) {
    elCategoriesContainer.innerHTML = `
      <div style="text-align:center; padding:24px 16px; color:var(--text-secondary);">
        <div style="font-size:36px; margin-bottom:6px;">📂</div>
        <div style="font-weight:700; font-size:14px;">Hozircha kategoriyalar yo'q</div>
        <div style="font-size:12px; margin-top:2px;">Yuqoridagi forma orqali yangi kategoriya qo'shing</div>
      </div>
    `;
    return;
  }

  elCategoriesContainer.innerHTML = "";
  for (const cat of cats) {
    const row = document.createElement("div");
    row.className = "admin-card";
    row.style.flexDirection = "row";
    row.style.justifyContent = "space-between";
    row.style.alignItems = "center";
    row.style.padding = "12px 14px";
    row.style.marginBottom = "8px";
    row.innerHTML = `
      <div>
        <span style="font-weight:700; color:var(--text-primary); font-size:14.5px;">${cat.name}</span>
        <span style="font-size:12px; color:var(--text-secondary); margin-left:6px;">(tartib: ${cat.sort_order})</span>
      </div>
      <button class="btn btn-danger btn-sm" onclick="deleteCategory(${cat.id})">🗑 O'chirish</button>
    `;
    elCategoriesContainer.appendChild(row);
  }
}

async function loadCategories(forceRefresh = false) {
  if (!elCategoriesContainer) return;

  if (!forceRefresh && _categoriesCache !== null) {
    categoriesList = _categoriesCache;
    renderCategoriesFromData(_categoriesCache);
    return;
  }

  try {
    elCategoriesContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-secondary);">Yuklanmoqda...</div>`;
    categoriesList = await adminApi.getCategories();
    _categoriesCache = categoriesList;
    renderCategoriesFromData(categoriesList);
  } catch (err) {
    console.error("Load categories error:", err);
  }
}

if (elCategoryForm) {
  elCategoryForm.onsubmit = async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById("cat-name");
    const orderInput = document.getElementById("cat-order");
    const name = nameInput.value.trim();
    const sort_order = parseInt(orderInput.value) || 0;

    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Qo'shilmoqda...`;

    try {
      await adminApi.createCategory({ name, sort_order });
      elCategoryForm.reset();
      _categoriesCache = null; // Invalidate
      loadCategories(true);
    } catch (err) {
      alert("Xatolik: " + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Qo'shish";
    }
  };
}

window.deleteCategory = async (catId) => {
  if (!confirm("Haqiqatan ham ushbu kategoriyani o'chirmoqchimisiz?")) return;
  try {
    await adminApi.deleteCategory(catId);
    _categoriesCache = null; // Invalidate
    loadCategories(true);
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// ─── 6. Settings Tab ─────────────────────────────────────────────────────────
const elSettingsForm = document.getElementById("settings-form");

async function loadSettings(forceRefresh = false) {
  try {
    if (!forceRefresh && _settingsCache !== null) {
      storeSettings = _settingsCache;
    } else {
      storeSettings = await adminApi.getStoreSettings();
      _settingsCache = storeSettings;
    }

    const nameEl = document.getElementById("setting-store-name");
    const descEl = document.getElementById("setting-store-desc");
    const phoneEl = document.getElementById("setting-contact-phone");
    const currEl = document.getElementById("setting-currency");
    const logoEl = document.getElementById("setting-logo-id");

    if (nameEl) nameEl.value = storeSettings.store_name || "";
    if (descEl) descEl.value = storeSettings.store_description || "";
    if (phoneEl) phoneEl.value = storeSettings.contact_phone || "";
    if (currEl) currEl.value = storeSettings.currency || "so'm";
    if (logoEl) logoEl.value = storeSettings.logo_file_id || "";
  } catch (err) {
    console.error("Load settings error:", err);
  }
}

if (elSettingsForm) {
  elSettingsForm.onsubmit = async (e) => {
    e.preventDefault();
    const store_name = document.getElementById("setting-store-name").value.trim();
    const store_description = document.getElementById("setting-store-desc").value.trim();
    const contact_phone = document.getElementById("setting-contact-phone").value.trim();
    const currency = document.getElementById("setting-currency").value.trim();
    const logo_file_id = document.getElementById("setting-logo-id").value.trim();

    const saveBtn = e.target.querySelector('button[type="submit"]');
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="spinner"></span> Saqlanmoqda...`;

    try {
      await adminApi.updateStoreSettings({
        store_name,
        store_description: store_description || null,
        contact_phone: contact_phone || null,
        currency: currency || "so'm",
        logo_file_id: logo_file_id || null,
      });
      _settingsCache = null; // Invalidate
      alert("🎉 Do'kon sozlamalari muvaffaqiyatli saqlandi!");
      loadSettings(true);
    } catch (err) {
      alert("Xatolik: " + err.message);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "💾 Sozlamalarni saqlash";
    }
  };
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function bootAdmin() {
  // 1. Immediately switch to orders tab — starts loading with skeleton (first time)
  switchTab("orders");

  // 2. Preload settings in background (used by formatPrice)
  loadSettings();

  // 3. Auth check in background (non-blocking)
  if (tg && tg.initData) {
    try {
      const meResp = await fetch("/api/store-settings/me", {
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Init-Data": tg.initData,
        },
      });
      if (meResp.ok) {
        const me = await meResp.json();
        if (!me.is_admin) {
          window.location.replace("/");
          return;
        }
      }
    } catch (err) {
      console.warn("Admin check warning:", err.message);
    }
  }
}

bootAdmin();
