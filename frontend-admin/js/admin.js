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

// State
let currentTab = "orders";
let currentOrderStatusFilter = null;
let categoriesList = [];
let uploadedImagesList = [];
let selectedImageFileIds = new Set();
let editingProductId = null;
let storeSettings = null;

// Helpers
function getImageUrl(fileId) {
  if (!fileId) return "";
  return `/images/${fileId}`;
}

function formatPrice(amount) {
  const curr = storeSettings?.currency || "so'm";
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(amount) + " " + curr;
}

// 1. Tab Switching
const tabs = document.querySelectorAll(".nav-tab");
const sections = document.querySelectorAll(".admin-section");

function switchTab(tabName) {
  currentTab = tabName;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  sections.forEach((s) => s.classList.toggle("active", s.id === `tab-${tabName}`));

  if (tabName === "orders") loadOrders();
  else if (tabName === "products") loadProducts();
  else if (tabName === "images") loadImagesGallery();
  else if (tabName === "categories") loadCategories();
  else if (tabName === "settings") loadSettings();
}

tabs.forEach((t) => {
  t.onclick = () => switchTab(t.dataset.tab);
});

// 2. Orders Tab with Skeletons
const elOrdersContainer = document.getElementById("admin-orders-list");
const statusFilterBtns = document.querySelectorAll(".filter-btn");

statusFilterBtns.forEach((btn) => {
  btn.onclick = () => {
    statusFilterBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentOrderStatusFilter = btn.dataset.status || null;
    loadOrders();
  };
});

function renderAdminOrdersSkeleton() {
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

async function loadOrders() {
  try {
    renderAdminOrdersSkeleton();
    const orders = await adminApi.getOrders(currentOrderStatusFilter);

    if (!orders.length) {
      elOrdersContainer.innerHTML = `
        <div style="text-align:center; padding:40px 16px; color:var(--text-secondary);">
          <div style="font-size:42px; margin-bottom:8px;">📦</div>
          <div style="font-weight:700; font-size:15px;">Hozircha buyurtmalar yo'q</div>
        </div>
      `;
      return;
    }

    elOrdersContainer.innerHTML = "";
    for (const ord of orders) {
      const card = document.createElement("div");
      card.className = "admin-card";

      let itemsHtml = "";
      for (const i of ord.items) {
        itemsHtml += `<div style="margin-bottom:2px;">• <b>${i.product_name}</b> — ${i.quantity} x ${formatPrice(i.price_at_order_time)}</div>`;
      }

      const dateStr = new Date(ord.created_at).toLocaleString("uz-UZ", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });

      // Status action buttons
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
          <button class="btn btn-success btn-sm" onclick="updateStatus(${ord.id}, 'completed')">🎉 Yakunlandi (Topshirildi)</button>
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
        <div style="font-size:12px; color:var(--text-secondary);">${dateStr}</div>
        <div style="font-size:13.5px; color:var(--text-primary); line-height:1.5;">
          <div>👤 <b>Mijoz:</b> ${ord.user ? ord.user.full_name : "Noma'lum"}</div>
          <div>📞 <b>Tel:</b> <a href="tel:${ord.phone}" style="color:var(--button-color); text-decoration:none; font-weight:700;">${ord.phone}</a></div>
          <div>📍 <b>Manzil:</b> ${ord.address}</div>
          <div>💳 <b>To'lov:</b> ${ord.payment_type === "cash" ? "Naqd pul" : "Karta"}</div>
          ${ord.notes ? `<div>📝 <b>Izoh:</b> ${ord.notes}</div>` : ""}
        </div>
        <div style="background:var(--secondary-bg); border:1px solid var(--border-subtle); padding:10px; border-radius:8px; font-size:13px; color:var(--text-primary);">
          <div style="font-weight:700; margin-bottom:4px;">Xarid qilingan mahsulotlar:</div>
          ${itemsHtml}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px dashed var(--border-subtle); padding-top:8px;">
          <span style="font-weight:600; color:var(--text-secondary);">Jami summa:</span>
          <span style="font-weight:800; font-size:16px; color:var(--button-color);">${formatPrice(ord.total_price)}</span>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:4px;">
          ${actionBtns}
        </div>
      `;
      elOrdersContainer.appendChild(card);
    }
  } catch (err) {
    console.error("Load orders error:", err);
    elOrdersContainer.innerHTML = `<div style="color:var(--danger-color); text-align:center; padding:20px;">Xatolik: ${err.message}</div>`;
  }
}

window.updateStatus = async (orderId, newStatus) => {
  if (!confirm(`Buyurtma statusini o'zgartirishni tasdiqlaysizmi: ${newStatus}?`)) return;
  try {
    await adminApi.updateOrderStatus(orderId, newStatus);
    loadOrders();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// 3. Products Tab with Skeletons
const elProductsContainer = document.getElementById("admin-products-list");
const elProductModal = document.getElementById("product-modal");
const elProductForm = document.getElementById("product-form");
const elImagePicker = document.getElementById("product-image-picker");
const elCategorySelect = document.getElementById("product-category-select");

function renderAdminProductsSkeleton() {
  elProductsContainer.innerHTML = `
    <div class="admin-card" style="display:flex; gap:12px; align-items:center; padding:12px;">
      <div class="skeleton" style="width:54px; height:54px; border-radius:8px; flex-shrink:0;"></div>
      <div style="flex-grow:1;">
        <div class="skeleton" style="width:60%; height:16px; margin-bottom:8px;"></div>
        <div class="skeleton" style="width:40%; height:14px;"></div>
      </div>
    </div>
    <div class="admin-card" style="display:flex; gap:12px; align-items:center; padding:12px;">
      <div class="skeleton" style="width:54px; height:54px; border-radius:8px; flex-shrink:0;"></div>
      <div style="flex-grow:1;">
        <div class="skeleton" style="width:50%; height:16px; margin-bottom:8px;"></div>
        <div class="skeleton" style="width:35%; height:14px;"></div>
      </div>
    </div>
  `;
}

async function loadProducts() {
  try {
    renderAdminProductsSkeleton();
    const products = await adminApi.getProducts();

    if (!products.length) {
      elProductsContainer.innerHTML = `
        <div style="text-align:center; padding:40px 16px; color:var(--text-secondary);">
          <div style="font-size:42px; margin-bottom:8px;">🏷</div>
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
        <div style="display:flex; gap:6px;">
          <button class="btn btn-secondary btn-sm" onclick="openEditProduct(${p.id})">✏️</button>
          <button class="btn btn-primary btn-sm" onclick="announceToGroup(${p.id})" title="Guruhga e'lon qilish">📢</button>
          <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id})">🗑</button>
        </div>
      `;
      elProductsContainer.appendChild(card);
    }
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
    loadProducts();
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

document.getElementById("btn-close-product-modal").onclick = () => {
  elProductModal.classList.remove("active");
};

async function populateCategorySelect(selectedId = null) {
  if (!categoriesList.length) {
    categoriesList = await adminApi.getCategories();
  }
  elCategorySelect.innerHTML = `<option value="">-- Kategoriyasiz --</option>`;
  for (const cat of categoriesList) {
    const opt = document.createElement("option");
    opt.value = cat.id;
    opt.textContent = cat.name;
    if (selectedId && cat.id === selectedId) opt.selected = true;
    elCategorySelect.appendChild(opt);
  }
}

async function renderImagePicker() {
  elImagePicker.innerHTML = `<div style="grid-column:span 3; font-size:12px; color:var(--text-secondary); text-align:center; padding:10px;">Rasmlar yuklanmoqda...</div>`;
  try {
    uploadedImagesList = await adminApi.getUploadedImages(false);
    if (!uploadedImagesList.length && selectedImageFileIds.size === 0) {
      elImagePicker.innerHTML = `
        <div style="grid-column:span 3; font-size:12.5px; color:var(--text-secondary); text-align:center; padding:12px; background:var(--secondary-bg); border-radius:8px;">
          Ishlatilmagan rasmlar yo'q.<br/>Yangi rasm qo'shish uchun botga rasm yuboring!
        </div>
      `;
      return;
    }

    elImagePicker.innerHTML = "";
    // If editing, also show currently selected images
    for (const fileId of selectedImageFileIds) {
      const item = document.createElement("div");
      item.className = "gallery-item selected";
      item.innerHTML = `<img src="${getImageUrl(fileId)}" class="gallery-img">`;
      item.onclick = () => toggleImageSelection(fileId, item);
      elImagePicker.appendChild(item);
    }

    for (const img of uploadedImagesList) {
      if (selectedImageFileIds.has(img.file_id)) continue;
      const item = document.createElement("div");
      item.className = "gallery-item";
      item.innerHTML = `<img src="${getImageUrl(img.file_id)}" class="gallery-img">`;
      item.onclick = () => toggleImageSelection(img.file_id, item);
      elImagePicker.appendChild(item);
    }
  } catch (err) {
    console.error("Image picker load error:", err);
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
    const p = await adminApi.getProduct(productId);
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
  const origBtnText = saveBtn.textContent;
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

    elProductModal.classList.remove("active");
    loadProducts();
  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = origBtnText;
  }
};

// 4. Uploaded Images Gallery Tab
const elGalleryContainer = document.getElementById("admin-gallery-list");

async function loadImagesGallery() {
  try {
    elGalleryContainer.innerHTML = `<div style="grid-column:span 3; text-align:center; padding:20px; color:var(--text-secondary);">Yuklanmoqda...</div>`;
    const images = await adminApi.getUploadedImages();

    if (!images.length) {
      elGalleryContainer.innerHTML = `
        <div style="grid-column:span 3; text-align:center; padding:40px 16px; color:var(--text-secondary);">
          <div style="font-size:42px; margin-bottom:8px;">📸</div>
          <div style="font-weight:700; font-size:15px;">Galereyada rasmlar yo'q</div>
          <div style="font-size:13px; margin-top:4px;">Telegram botingizga rasm yuboring, u avtomatik shu yerda paydo bo'ladi!</div>
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
        <div style="position:absolute; bottom:4px; right:4px; font-size:10px; background:rgba(0,0,0,0.6); color:white; padding:2px 6px; border-radius:4px;">
          ${img.is_used ? "Band" : "Bo'sh"}
        </div>
      `;
      elGalleryContainer.appendChild(item);
    }
  } catch (err) {
    console.error("Load images error:", err);
  }
}

// 5. Categories Tab
const elCategoriesContainer = document.getElementById("admin-categories-list");
const elCategoryForm = document.getElementById("category-form");

async function loadCategories() {
  try {
    elCategoriesContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-secondary);">Yuklanmoqda...</div>`;
    categoriesList = await adminApi.getCategories();

    if (!categoriesList.length) {
      elCategoriesContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-secondary);">Kategoriyalar yo'q</div>`;
      return;
    }

    elCategoriesContainer.innerHTML = "";
    for (const cat of categoriesList) {
      const row = document.createElement("div");
      row.className = "admin-card";
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.style.alignItems = "center";
      row.style.padding = "10px 14px";
      row.innerHTML = `
        <div>
          <span style="font-weight:700; color:var(--text-primary); font-size:15px;">${cat.name}</span>
          <span style="font-size:12px; color:var(--text-secondary); margin-left:8px;">(tartib: ${cat.sort_order})</span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteCategory(${cat.id})">🗑 O'chirish</button>
      `;
      elCategoriesContainer.appendChild(row);
    }
  } catch (err) {
    console.error("Load categories error:", err);
  }
}

elCategoryForm.onsubmit = async (e) => {
  e.preventDefault();
  const name = document.getElementById("cat-name").value.trim();
  const sort_order = parseInt(document.getElementById("cat-order").value) || 0;

  try {
    await adminApi.createCategory({ name, sort_order });
    elCategoryForm.reset();
    loadCategories();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

window.deleteCategory = async (catId) => {
  if (!confirm("Ushbu kategoriyani o'chirmoqchimisiz?")) return;
  try {
    await adminApi.deleteCategory(catId);
    loadCategories();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// 6. Settings Tab
const elSettingsForm = document.getElementById("settings-form");

async function loadSettings() {
  try {
    storeSettings = await adminApi.getStoreSettings();
    document.getElementById("setting-store-name").value = storeSettings.store_name || "";
    document.getElementById("setting-store-desc").value = storeSettings.store_description || "";
    document.getElementById("setting-contact-phone").value = storeSettings.contact_phone || "";
    document.getElementById("setting-currency").value = storeSettings.currency || "so'm";
    document.getElementById("setting-logo-id").value = storeSettings.logo_file_id || "";
  } catch (err) {
    console.error("Load settings error:", err);
  }
}

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
    alert("🎉 Do'kon sozlamalari muvaffaqiyatli saqlandi!");
    loadSettings();
  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Sozlamalarni saqlash";
  }
};

// Boot — Admin huquqini tekshirish
async function bootAdmin() {
  if (tg && tg.initData) {
    try {
      const meResp = await fetch("/api/store-settings/me", {
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Init-Data": tg.initData,
        },
      });
      if (!meResp.ok) throw new Error("403");
      const me = await meResp.json();
      if (!me.is_admin) {
        window.location.replace("/");
        return;
      }
    } catch (err) {
      console.warn("Admin tekshiruvi muvaffaqiyatsiz:", err.message);
    }
  }

  loadSettings();
  loadOrders();
}

bootAdmin();
