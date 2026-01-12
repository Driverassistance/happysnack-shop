/**
 * HappySnack Admin Dashboard
 * Версия с централизованной функцией apiFetch для всех запросов.
 */

// ============================================
// КОНФИГУРАЦИЯ И ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
// ============================================

const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://happysnack-app.onrender.com';

// ВАЖНО: Убедитесь, что этот ID правильный для администратора/менеджера
const ADMIN_TELEGRAM_ID = '473294026'; 

let currentView = 'table'; // 'table' или 'grid' для страницы товаров

// ============================================
// ЦЕНТРАЛИЗОВАННАЯ ФУНКЦИЯ ДЛЯ API ЗАПРОСОВ
// ============================================

/**
 * Выполняет запрос к API, автоматически добавляя заголовки и обрабатывая ошибки.
 * @param {string} endpoint - Путь к API (например, '/api/admin/stats/dashboard' )
 * @param {object} options - Стандартные опции для fetch (method, body, и т.д.)
 * @returns {Promise<any>} - Результат запроса в формате JSON или Blob для скачивания.
 */
async function apiFetch(endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;

    const defaultHeaders = {
        'Authorization': ADMIN_TELEGRAM_ID,
        'Content-Type': 'application/json'
    };

    const finalOptions = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        }
    };
    
    // Для FormData (загрузка файлов) браузер сам установит правильный Content-Type
    if (finalOptions.body instanceof FormData) {
        delete finalOptions.headers['Content-Type'];
    }

    try {
        const response = await fetch(url, finalOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Request failed with status ${response.status}`);
        }

        if (response.status === 204) { // No Content
            return null;
        }
        
        if (options.download) { // Для скачивания файлов
            return response.blob();
        }

        return response.json();

    } catch (error) {
        console.error(`API Fetch Error: ${error.message} (URL: ${url})`);
        throw error; // Пробрасываем ошибку для обработки в вызывающей функции
    }
}

// ============================================
// НАВИГАЦИЯ
// ============================================

function showPage(pageId) {
    document.querySelectorAll('.page-section').forEach(section => section.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    
    document.getElementById(pageId).classList.add('active');
    document.querySelector(`a[href="#${pageId}"]`).classList.add('active');
    
    loadPageData(pageId);
}

function loadPageData(pageId) {
    switch(pageId) {
        case 'dashboard':
            loadDashboardStats();
            break;
        case 'products':
            loadProducts();
            loadCategories();
            break;
        case 'categories':
            loadCategoriesTable();
            break;
        case 'clients':
            loadClients();
            break;
        case 'orders':
            loadOrders();
            break;
        case 'sales_reps':
            loadSalesReps();
            break;
        case 'ai':
            // // loadAIStats(); // TODO: Implement AI stats // TODO: Implement AI stats
            loadAIConversations();
            break;    
        case 'settings':
            loadSettings();
            break;
    }
}

// ============================================
// DASHBOARD - Статистика
// ============================================

async function loadDashboardStats() {
    try {
        const stats = await apiFetch('/api/admin/stats/dashboard');
        document.getElementById('todayOrders').textContent = stats.today_orders;
        document.getElementById('todayRevenue').textContent = formatMoney(stats.today_revenue);
        document.getElementById('weekOrders').textContent = stats.week_orders;
        document.getElementById('weekRevenue').textContent = formatMoney(stats.week_revenue);
        document.getElementById('pendingClients').textContent = stats.pending_clients;
        document.getElementById('lowStock').textContent = stats.low_stock_products;
    } catch (error) {
        alert(`Ошибка загрузки статистики: ${error.message}`);
    }
}

// ============================================
// PRODUCTS - Товары
// ============================================

async function loadProducts() {
    const search = document.getElementById('searchProduct')?.value || '';
    const category = document.getElementById('filterCategory')?.value || '';
    const active = document.getElementById('filterActive')?.value || '';
    
    try {
        let endpoint = '/api/admin/products?limit=100';
        if (search) endpoint += `&search=${encodeURIComponent(search)}`;
        if (category) endpoint += `&category_id=${category}`;
        if (active) endpoint += `&is_active=${active}`;
        
        const products = await apiFetch(endpoint);
        
        if (currentView === 'table') {
            renderProductsTable(products);
        } else {
            renderProductsGrid(products);
        }
    } catch (error) {
        alert(`Ошибка загрузки товаров: ${error.message}`);
    }
}

function renderProductsTable(products) {
    const tbody = document.getElementById('productsTable');
    if (!products || products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Товары не найдены</td></tr>';
        return;
    }
    tbody.innerHTML = products.map(p => `
        <tr>
            <td>${p.id}</td>
            <td><strong>${p.name}</strong></td>
            <td>${p.category?.name || 'N/A'}</td>
            <td>${formatMoney(p.price)} ₸</td>
            <td><span class="badge ${p.stock < 50 ? 'bg-danger' : 'bg-success'}">${p.stock} шт</span></td>
            <td><span class="badge ${p.is_active ? 'bg-success' : 'bg-secondary'}">${p.is_active ? 'Активен' : 'Неактивен'}</span></td>
            <td>
                <button class="btn btn-sm btn-info" onclick="uploadProductPhoto(${p.id})" title="Загрузить фото"><i class="bi bi-camera"></i></button>
                <button class="btn btn-sm btn-primary" onclick="editProduct(${p.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-${p.is_active ? 'warning' : 'success'}" onclick="toggleProduct(${p.id}, ${!p.is_active})"><i class="bi bi-${p.is_active ? 'eye-slash' : 'eye'}"></i></button>
            </td>
        </tr>
    `).join('');
}

function renderProductsGrid(products) {
    const grid = document.getElementById('productsGrid');
    if (!products || products.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center">Товары не найдены</div>';
        return;
    }
    grid.innerHTML = products.map(p => `
        <div class="col-md-3 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="badge ${p.is_active ? 'bg-success' : 'bg-secondary'}">${p.is_active ? 'Активен' : 'Неактивен'}</span>
                        <span class="badge ${p.stock < 50 ? 'bg-danger' : 'bg-success'}">${p.stock} шт</span>
                    </div>
                    <h6 class="card-title">${p.name}</h6>
                    <p class="text-muted small mb-1">${p.category?.name || 'N/A'}</p>
                    ${p.weight ? `<p class="small mb-1">⚖️ ${p.weight}</p>` : ''}
                    ${p.package_size ? `<p class="small mb-2">📦 ${p.package_size}</p>` : ''}
                    <h5 class="text-primary">${formatMoney(p.price)} ₸</h5>
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-sm btn-primary flex-fill" onclick="editProduct(${p.id})"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-${p.is_active ? 'warning' : 'success'} flex-fill" onclick="toggleProduct(${p.id}, ${!p.is_active})"><i class="bi bi-${p.is_active ? 'eye-slash' : 'eye'}"></i></button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

async function loadCategories() {
    try {
        const categories = await apiFetch('/api/admin/categories');
        const select = document.getElementById('filterCategory');
        select.innerHTML = '<option value="">Все категории</option>' + 
            categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading categories:', error.message);
    }
}

function showAddProductModal() {
    alert('Добавление товара: эта функция еще не реализована.');
}

async function editProduct(productId) {
    const newPrice = prompt('Введите новую цену:');
    if (!newPrice || isNaN(parseFloat(newPrice))) return;
    
    try {
        await apiFetch(`/api/admin/products/${productId}`, {
            method: 'PUT',
            body: JSON.stringify({ price: parseFloat(newPrice) })
        });
        alert('Цена обновлена!');
        loadProducts();
    } catch (error) {
        alert(`Ошибка обновления товара: ${error.message}`);
    }
}

async function toggleProduct(productId, isActive) {
    try {
        await apiFetch(`/api/admin/products/${productId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: isActive })
        });
        alert(`Товар ${isActive ? 'активирован' : 'деактивирован'}!`);
        loadProducts();
    } catch (error) {
        alert(`Ошибка изменения статуса: ${error.message}`);
    }
}

// ============================================
// CATEGORIES - Категории
// ============================================

async function loadCategoriesTable() {
    try {
        const categories = await apiFetch('/api/admin/categories');
        const tbody = document.getElementById('categoriesTable');
        tbody.innerHTML = categories.map(c => `
            <tr>
                <td>${c.id}</td>
                <td><strong>${c.name}</strong></td>
                <td>${c.sort_order}</td>
                <td><span class="badge ${c.is_active ? 'bg-success' : 'bg-secondary'}">${c.is_active ? 'Активна' : 'Неактивна'}</span></td>
                <td><button class="btn btn-sm btn-primary" onclick="editCategory(${c.id})"><i class="bi bi-pencil"></i></button></td>
            </tr>
        `).join('');
    } catch (error) {
        alert(`Ошибка загрузки категорий: ${error.message}`);
    }
}

async function showAddCategoryModal() {
    const name = prompt('Введите название категории:');
    if (!name) return;
    const sortOrder = prompt('Порядок сортировки:', '0');
    
    try {
        await apiFetch(`/api/admin/categories?name=${encodeURIComponent(name)}&sort_order=${sortOrder}`, {
            method: 'POST'
        });
        alert('Категория создана!');
        loadCategoriesTable();
    } catch (error) {
        alert(`Ошибка создания категории: ${error.message}`);
    }
}

function editCategory(categoryId) {
    alert('Редактирование категории: эта функция еще не реализована.');
}

// ============================================
// CLIENTS - Клиенты
// ============================================
// Показываем форму добавления клиента
function showAddClientForm() {
    const formHtml = `
        <div class="card mb-3">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">➕ Добавить нового клиента</h5>
            </div>
            <div class="card-body">
                <form id="addClientForm">
                    <div class="mb-3">
                        <label class="form-label">Название компании *</label>
                        <input type="text" class="form-control" id="companyName" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">БИН/ИИН *</label>
                        <input type="text" class="form-control" id="binIin" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Адрес *</label>
                        <input type="text" class="form-control" id="address" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Телефон *</label>
                        <input type="text" class="form-control" id="phone" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Telegram ID *</label>
                        <input type="number" class="form-control" id="telegramId" required>
                        <small class="text-muted">ID пользователя в Telegram (например: 123456789)</small>
                    </div>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Кредитный лимит (₸)</label>
                            <input type="number" class="form-control" id="creditLimit" value="500000">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Отсрочка (дней)</label>
                            <input type="number" class="form-control" id="paymentDelay" value="14">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Скидка (%)</label>
                            <input type="number" class="form-control" id="discount" value="0" min="0" max="100">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Статус *</label>
                        <select class="form-control" id="status">
                            <option value="pending">Ожидает одобрения</option>
                            <option value="active" selected>Активен</option>
                            <option value="blocked">Заблокирован</option>
                        </select>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-success">💾 Создать клиента</button>
                        <button type="button" class="btn btn-secondary" onclick="loadClients()">❌ Отмена</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.getElementById('clientsContent').innerHTML = formHtml;
    
    document.getElementById('addClientForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createClient();
    });
}

// Создаём клиента
async function createClient() {
    const data = {
        company_name: document.getElementById('companyName').value,
        bin_iin: document.getElementById('binIin').value,
        address: document.getElementById('address').value,
        phone: document.getElementById('phone').value,
        telegram_id: parseInt(document.getElementById('telegramId').value),
        credit_limit: parseFloat(document.getElementById('creditLimit').value),
        payment_delay_days: parseInt(document.getElementById('paymentDelay').value),
        discount_percent: parseFloat(document.getElementById('discount').value),
        status: document.getElementById('status').value
    };
    
    try {
        const response = await fetch(`${API_URL}/api/admin/clients/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Telegram-ID': ADMIN_TELEGRAM_ID
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showNotification('✅ Клиент успешно создан!', 'success');
            loadClients();
        } else {
            const error = await response.json();
            showNotification(`❌ Ошибка: ${error.detail}`, 'danger');
        }
    } catch (error) {
        console.error('Error creating client:', error);
        showNotification('❌ Ошибка создания клиента', 'danger');
    }
}
async function loadClients() {
    const search = document.getElementById('searchClient')?.value || '';
    const status = document.getElementById('filterStatus')?.value || '';
    
    try {
        let endpoint = '/api/admin/clients?limit=100';
        if (search) endpoint += `&search=${encodeURIComponent(search)}`;
        if (status) endpoint += `&status=${status}`;
        
        const clients = await apiFetch(endpoint);
        
        // Рендерим всю секцию клиентов с кнопкой
        const clientsHtml = `
            <div class="stat-card">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <input type="text" class="form-control" id="searchClient" 
                               placeholder="Поиск клиента..." onkeyup="loadClients()" value="${search}">
                    </div>
                    <div class="col-md-3">
                        <select class="form-select" id="filterStatus" onchange="loadClients()">
                            <option value="" ${status === '' ? 'selected' : ''}>Все статусы</option>
                            <option value="pending" ${status === 'pending' ? 'selected' : ''}>На модерации</option>
                            <option value="active" ${status === 'active' ? 'selected' : ''}>Активные</option>
                            <option value="blocked" ${status === 'blocked' ? 'selected' : ''}>Заблокированные</option>
                        </select>
                    </div>
                </div>
                
                <table class="table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Компания</th>
                            <th>БИН</th>
                            <th>Бонусы</th>
                            <th>Долг</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${clients.length === 0 
                            ? '<tr><td colspan="7" class="text-center">Клиенты не найдены</td></tr>'
                            : clients.map(c => `
                                <tr>
                                    <td>${c.id}</td>
                                    <td><strong>${c.company_name}</strong></td>
                                    <td>${c.bin_iin || '-'}</td>
                                    <td>${formatMoney(c.bonus_balance)} ₸</td>
                                    <td>${formatMoney(c.debt)} ₸</td>
                                    <td><span class="badge ${getStatusBadge(c.status)}">${getStatusText(c.status)}</span></td>
                                    <td>
                                        ${c.status === 'pending' ? `<button class="btn btn-sm btn-success" onclick="approveClient(${c.id})"><i class="bi bi-check"></i> Одобрить</button>` : ''}
                                        <button class="btn btn-sm btn-primary" onclick="editClient(${c.id})"><i class="bi bi-pencil"></i></button>
                                    </td>
                                </tr>
                            `).join('')
                        }
                    </tbody>
                </table>
            </div>
        `;
        
        document.getElementById('clientsContent').innerHTML = clientsHtml;
    } catch (error) {
        alert(`Ошибка загрузки клиентов: ${error.message}`);
    }
}

async function approveClient(clientId) {
    if (!confirm('Одобрить регистрацию клиента?')) return;
    try {
        await apiFetch(`/api/admin/clients/${clientId}/approve`, { method: 'POST' });
        alert('Клиент одобрен!');
        loadClients();
    } catch (error) {
        alert(`Ошибка одобрения клиента: ${error.message}`);
    }
}

function editClient(clientId) {
    alert(`Редактирование клиента ${clientId}: эта функция еще не реализована.`);
}

// ============================================
// ORDERS - Заказы
// ============================================

async function loadOrders() {
    const status = document.getElementById('filterOrderStatus')?.value || '';
    try {
        let endpoint = '/api/admin/orders?limit=50';
        if (status) endpoint += `&status=${status}`;
        
        const orders = await apiFetch(endpoint);
        const tbody = document.getElementById('ordersTable');
        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">Заказы не найдены</td></tr>';
            return;
        }
        tbody.innerHTML = orders.map(o => `
            <tr>
                <td><strong>${o.order_number}</strong></td>
                <td>${o.client_id}</td>
                <td>${formatMoney(o.final_total)} ₸</td>
                <td><span class="badge ${getOrderStatusBadge(o.status)}">${getOrderStatusText(o.status)}</span></td>
                <td>${formatDate(o.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewOrder(${o.id})"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-sm btn-primary" onclick="changeOrderStatus(${o.id}, '${o.status}')"><i class="bi bi-arrow-repeat"></i></button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        alert(`Ошибка загрузки заказов: ${error.message}`);
    }
}

function viewOrder(orderId) {
    alert(``Просмотр заказа ${orderId}: эта функция еще не реализована.``);
}

async function changeOrderStatus(orderId, currentStatus) {
    const statuses = { 'new': 'confirmed', 'confirmed': 'preparing', 'preparing': 'delivering', 'delivering': 'delivered' };
    const nextStatus = statuses[currentStatus];
    if (!nextStatus) {
        alert('Для этого статуса нет следующего шага.');
        return;
    }
    if (!confirm(`Изменить статус на "${getOrderStatusText(nextStatus)}"?`)) return;
    
    try {
        await apiFetch(`/api/admin/orders/${orderId}/status?new_status=${nextStatus}`, { method: 'PUT' });
        alert('Статус обновлен!');
        loadOrders();
    } catch (error) {
        alert(`Ошибка изменения статуса: ${error.message}`);
    }
}

// ============================================
// SETTINGS - Настройки
// ============================================

async function loadSettings() {
    try {
        const settingsObj = await apiFetch('/api/settings');
        // Конвертируем объект в массив
        const settings = Object.entries(settingsObj).map(([key, value]) => ({
            key: key,
            value: value,
            type: typeof value === 'number' ? 'int' : 'string',
            description: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        }));
        
        const groups = {
            bonusSettings: s => s.key.startsWith('bonus_'),
            financeSettings: s => ['min_order_amount'].includes(s.key),
            deliverySettings: s => s.key.includes('tier'),
            discountSettings: s => s.key.startsWith('discount_')
        };
        Object.keys(groups).forEach(id => renderSettings(id, settings.filter(groups[id])));
    } catch (error) {
        alert(`Ошибка загрузки настроек: ${error.message}`);
    }
}

function renderSettings(containerId, settings) {
    const container = document.getElementById(containerId);
    container.innerHTML = settings.map(s => `
        <div class="row mb-3 align-items-center">
            <div class="col-md-6"><label class="form-label">${s.description || s.key}</label></div>
            <div class="col-md-4"><input type="text" class="form-control" id="setting_${s.key}" value="${s.value}" onchange="updateSetting('${s.key}', this.value)"></div>
            <div class="col-md-2"><small class="text-muted">${s.type}</small></div>
        </div>
    `).join('');
}

async function updateSetting(key, value) {
    try {
        await apiFetch('/api/settings', { 
            method: 'POST',
            body: JSON.stringify({ key, value })
        });
        alert('Настройка обновлена!');
    } catch (error) {
        alert(`Ошибка обновления настройки: ${error.message}`);
    }
}

// ============================================
// IMPORT / EXPORT - Импорт / Экспорт
// ============================================

async function downloadTemplate() {
    try {
        const blob = await apiFetch('/api/admin/products/template', { download: true });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'products_template.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert('Шаблон скачан!');
    } catch (error) {
        alert(`Ошибка скачивания шаблона: ${error.message}`);
    }
}

async function importProducts(file) {
    if (!file) return;
    if (!confirm(`Импортировать товары из файла "${file.name}"?\nСуществующие товары будут обновлены.`)) {
        document.getElementById('importFile').value = '';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const result = await apiFetch('/api/admin/products/import', {
            method: 'POST',
            body: formData
        });
        
        let message = `✅ Импорт завершен!\n\nСоздано: ${result.created}\nОбновлено: ${result.updated}\nВсего: ${result.total}\n`;
        if (result.errors && result.errors.length > 0) {
            message += `\n⚠️ Ошибки (${result.errors.length}):\n${result.errors.slice(0, 5).join('\n')}`;
            if (result.errors.length > 5) message += `\n... и еще ${result.errors.length - 5}`;
        }
        alert(message);
        loadProducts();
    } catch (error) {
        alert(`Ошибка импорта: ${error.message}`);
    } finally {
        document.getElementById('importFile').value = '';
    }
}

// ============================================
// AI AGENT DASHBOARD
// ============================================