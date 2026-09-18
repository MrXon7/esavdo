import { adminApi } from "./admin-api.js";

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

// 2. Orders Tab
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

async function loadOrders() {
  try {
    elOrdersContainer.innerHTML = `<div style="text-align:center; padding:20px; color:#888;">Yuklanmoqda...</div>`;
    const orders = await adminApi.getOrders(currentOrderStatusFilter);

    if (!orders.length) {
      elOrdersContainer.innerHTML = `<div style="text-align:center; padding:30px; color:#888;">Buyurtmalar yo'q</div>`;
      return;
    }

    elOrdersContainer.innerHTML = "";
    for (const ord of orders) {
      const card = document.createElement("div");
      card.className = "card";

      let itemsHtml = "";
      for (const i of ord.items) {
        itemsHtml += `<div>• ${i.product_name} — ${i.quantity} x ${formatPrice(i.price_at_order_time)}</div>`;
      }

      const dateStr = new Date(ord.created_at).toLocaleString("uz-UZ");

      // Status action buttons
      let actionBtns = "";
      if (ord.status === "pending") {
        actionBtns = `
          <button class="btn btn-success" onclick="updateStatus(${ord.id}, 'confirmed')">✅ Tasdiqlash</button>
          <button class="btn btn-danger" onclick="updateStatus(${ord.id}, 'cancelled')">❌ Rad etish</button>
        `;
      } else if (ord.status === "confirmed") {
        actionBtns = `
          <button class="btn btn-warning" onclick="updateStatus(${ord.id}, 'preparing')">👨‍🍳 Tayyorlash</button>
          <button class="btn btn-danger" onclick="updateStatus(${ord.id}, 'cancelled')">Bekor qilish</button>
        `;
      } else if (ord.status === "preparing") {
        actionBtns = `
          <button class="btn btn-primary" onclick="updateStatus(${ord.id}, 'delivering')">🛵 Yetkazishga berish</button>
        `;
      } else if (ord.status === "delivering") {
        actionBtns = `
          <button class="btn btn-success" onclick="updateStatus(${ord.id}, 'completed')">🎉 Yakunlandi (Topshirildi)</button>
        `;
      }

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <span style="font-weight:700; font-size:16px;">Buyurtma #${ord.id}</span>
          <span class="badge-admin" style="text-transform:uppercase;">${ord.status}</span>
        </div>
        <div style="font-size:12px; color:#888; margin-bottom:8px;">${dateStr}</div>
        <div style="margin-bottom:8px; font-size:13px;">
          <div>👤 <b>Mijoz:</b> ${ord.user ? ord.user.full_name : "Noma'lum"}</div>
          <div>📞 <b>Tel:</b> <a href="tel:${ord.phone}">${ord.phone}</a></div>
          <div>📍 <b>Manzil:</b> ${ord.address}</div>
          <div>💳 <b>To'lov:</b> ${ord.payment_type === "cash" ? "Naqd pul" : "Karta"}</div>
          ${ord.notes ? `<div>📝 <b>Izoh:</b> ${ord.notes}</div>` : ""}
        </div>
        <div style="background:#f9f9f9; padding:8px; border-radius:6px; font-size:13px; margin-bottom:8px;">
          <b>Mahsulotlar:</b><br/>${itemsHtml}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <span>Jami:</span>
          <span style="font-weight:700; font-size:16px; color:var(--button-color);">${formatPrice(ord.total_price)}</span>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          ${actionBtns}
        </div>
      `;
      elOrdersContainer.appendChild(card);
    }
  } catch (err) {
    console.error("Load orders error:", err);
    elOrdersContainer.innerHTML = `<div style="color:red; text-align:center;">Xatolik: ${err.message}</div>`;
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

// 3. Products Tab
const elProductsContainer = document.getElementById("admin-products-list");
const elProductModal = document.getElementById("product-modal");
const elProductForm = document.getElementById("product-form");
const elImagePicker = document.getElementById("product-image-picker");
const elCategorySelect = document.getElementById("product-category-select");

async function loadProducts() {
  try {
    elProductsContainer.innerHTML = `<div style="text-align:center; padding:20px; color:#888;">Yuklanmoqda...</div>`;
    const products = await adminApi.getProducts();

    if (!products.length) {
      elProductsContainer.innerHTML = `<div style="text-align:center; padding:30px; color:#888;">Mahsulotlar yo'q</div>`;
      return;
    }

    elProductsContainer.innerHTML = "";
    for (const p of products) {
      const card = document.createElement("div");
      card.className = "product-admin-card";

      const firstImg = p.images && p.images.length > 0 ? p.images[0].file_id : null;
      const imgUrl = getImageUrl(firstImg);

      card.innerHTML = `
        <img src="${imgUrl || 'data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'60\' height=\'60\'><rect width=\'60\' height=\'60\' fill=\'%23eee\'/></svg>'}" class="product-admin-img" alt="${p.name}">
        <div class="product-admin-info">
          <div class="product-admin-name">${p.name}</div>
          <div class="product-admin-price">${formatPrice(p.price)}</div>
          <div style="font-size:11px; color:${p.is_active ? 'green' : 'red'};">${p.is_active ? 'Faol' : 'Nofaol'}</div>
        </div>
        <div class="product-admin-actions">
          <button class="btn btn-secondary" onclick="openEditProduct(${p.id})">✏️</button>
          <button class="btn btn-primary" onclick="announceToGroup(${p.id})" title="Guruhga e'lon qilish">📢</button>
          <button class="btn btn-danger" onclick="deleteProduct(${p.id})">🗑</button>
        </div>
      `;
      elProductsContainer.appendChild(card);
    }
  } catch (err) {
    console.error("Load products error:", err);
    elProductsContainer.innerHTML = `<div style="color:red; text-align:center;">Xatolik: ${err.message}</div>`;
  }
}

window.announceToGroup = async (productId) => {
  if (!confirm("Ushbu mahsulotni guruhga e'lon qilinsinmi?")) return;
  try {
    await adminApi.announceProduct(productId);
    alert("Mahsulot muvaffaqiyatli e'lon qilindi!");
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
  elImagePicker.innerHTML = `<div style="grid-column:span 3; font-size:12px; color:#888; text-align:center; padding:10px;">Rasmlar yuklanmoqda...</div>`;
  try {
    // Fetch unused images
    uploadedImagesList = await adminApi.getUploadedImages(false);
    if (!uploadedImagesList.length && selectedImageFileIds.size === 0) {
      elImagePicker.innerHTML = `
        <div style="grid-column:span 3; font-size:12px; color:#888; text-align:center; padding:10px;">
          Ishlatilmagan rasm yo'q. Rasm yuklash uchun botga rasm yuboring!
        </div>
      `;
      return;
    }

    elImagePicker.innerHTML = "";
    // Display selected images first
    for (const fileId of selectedImageFileIds) {
      const item = document.createElement("div");
      item.className = "picker-item selected";
      item.innerHTML = `<img src="${getImageUrl(fileId)}" />`;
      item.onclick = () => {
        selectedImageFileIds.delete(fileId);
        item.classList.remove("selected");
      };
      elImagePicker.appendChild(item);
    }

    // Display unused uploaded images
    for (const img of uploadedImagesList) {
      if (selectedImageFileIds.has(img.file_id)) continue;
      const item = document.createElement("div");
      item.className = "picker-item";
      item.innerHTML = `<img src="${getImageUrl(img.file_id)}" />`;
      item.onclick = () => {
        if (selectedImageFileIds.has(img.file_id)) {
          selectedImageFileIds.delete(img.file_id);
          item.classList.remove("selected");
        } else {
          selectedImageFileIds.add(img.file_id);
          item.classList.add("selected");
        }
      };
      elImagePicker.appendChild(item);
    }
  } catch (err) {
    elImagePicker.innerHTML = `<div style="grid-column:span 3; color:red; font-size:12px;">Rasmlarni yuklashda xatolik</div>`;
  }
}

window.openEditProduct = async (productId) => {
  editingProductId = productId;
  document.getElementById("product-modal-title").textContent = "Mahsulotni tahrirlash";
  selectedImageFileIds.clear();

  const products = await adminApi.getProducts();
  const prod = products.find((p) => p.id === productId);
  if (!prod) return;

  document.getElementById("prod-name").value = prod.name;
  document.getElementById("prod-price").value = prod.price;
  document.getElementById("prod-desc").value = prod.description || "";
  document.getElementById("prod-active").checked = prod.is_active;

  if (prod.images) {
    prod.images.forEach((img) => selectedImageFileIds.add(img.file_id));
  }

  await populateCategorySelect(prod.category_id);
  await renderImagePicker();
  elProductModal.classList.add("active");
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

  const payload = {
    name,
    price,
    description: description || null,
    category_id,
    is_active,
    image_file_ids,
  };

  try {
    if (editingProductId) {
      await adminApi.updateProduct(editingProductId, payload);
    } else {
      await adminApi.createProduct(payload);
    }
    elProductModal.classList.remove("active");
    loadProducts();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// 4. Images Gallery Tab
const elImagesGallery = document.getElementById("admin-images-gallery");

async function loadImagesGallery() {
  try {
    elImagesGallery.innerHTML = `<div style="text-align:center; padding:20px; color:#888;">Yuklanmoqda...</div>`;
    const images = await adminApi.getUploadedImages();

    if (!images.length) {
      elImagesGallery.innerHTML = `
        <div style="text-align:center; padding:30px; color:#888;">
          Hozircha bot orqali rasmlar yuklanmagan.<br/>
          Telegram botingizga rasm yoki albom yuboring!
        </div>
      `;
      return;
    }

    elImagesGallery.innerHTML = "";
    for (const img of images) {
      const card = document.createElement("div");
      card.className = "card";
      card.style.display = "flex";
      card.style.gap = "12px";
      card.style.alignItems = "center";

      const dateStr = new Date(img.uploaded_at).toLocaleString("uz-UZ");

      card.innerHTML = `
        <img src="${getImageUrl(img.file_id)}" style="width:70px; height:70px; border-radius:8px; object-fit:cover; background:#eee;" />
        <div style="flex-grow:1; font-size:13px;">
          <div><b>Status:</b> ${img.is_used ? '✅ Mahsulotga biriktirilgan' : '⏳ Yangi (ishlatilmagan)'}</div>
          <div style="font-size:11px; color:#888;">Yuklangan vaqt: ${dateStr}</div>
        </div>
        <button class="btn btn-danger" onclick="deleteImageRecord(${img.id})">🗑</button>
      `;
      elImagesGallery.appendChild(card);
    }
  } catch (err) {
    elImagesGallery.innerHTML = `<div style="color:red; text-align:center;">Xatolik: ${err.message}</div>`;
  }
}

window.deleteImageRecord = async (imageId) => {
  if (!confirm("Ushbu rasmni o'chirmoqchimisiz?")) return;
  try {
    await adminApi.deleteUploadedImage(imageId);
    loadImagesGallery();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// 5. Categories Tab
const elCategoriesList = document.getElementById("admin-categories-list");
const elCategoryForm = document.getElementById("category-add-form");

async function loadCategories() {
  try {
    elCategoriesList.innerHTML = `<div style="text-align:center; padding:20px; color:#888;">Yuklanmoqda...</div>`;
    categoriesList = await adminApi.getCategories();

    if (!categoriesList.length) {
      elCategoriesList.innerHTML = `<div style="text-align:center; padding:20px; color:#888;">Kategoriyalar yo'q</div>`;
      return;
    }

    elCategoriesList.innerHTML = "";
    for (const cat of categoriesList) {
      const card = document.createElement("div");
      card.className = "card";
      card.style.display = "flex";
      card.style.justifyContent = "space-between";
      card.style.alignItems = "center";

      card.innerHTML = `
        <div>
          <b>${cat.name}</b>
          <span style="font-size:12px; color:#888; margin-left:8px;">Tartib: ${cat.sort_order}</span>
        </div>
        <button class="btn btn-danger" onclick="deleteCategoryRecord(${cat.id})">🗑</button>
      `;
      elCategoriesList.appendChild(card);
    }
  } catch (err) {
    elCategoriesList.innerHTML = `<div style="color:red; text-align:center;">Xatolik: ${err.message}</div>`;
  }
}

elCategoryForm.onsubmit = async (e) => {
  e.preventDefault();
  const name = document.getElementById("new-cat-name").value.trim();
  const sort_order = parseInt(document.getElementById("new-cat-sort").value) || 0;

  try {
    await adminApi.createCategory({ name, sort_order, is_active: true });
    elCategoryForm.reset();
    loadCategories();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

window.deleteCategoryRecord = async (catId) => {
  if (!confirm("Kategoriyani o'chirmoqchimisiz?")) return;
  try {
    await adminApi.deleteCategory(catId);
    loadCategories();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// 6. Settings Tab (White-Label)
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

  try {
    await adminApi.updateStoreSettings({
      store_name,
      store_description: store_description || null,
      contact_phone: contact_phone || null,
      currency: currency || "so'm",
      logo_file_id: logo_file_id || null,
    });
    alert("Do'kon sozlamalari muvaffaqiyatli saqlandi!");
    loadSettings();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
};

// Boot
loadSettings();
loadOrders();
