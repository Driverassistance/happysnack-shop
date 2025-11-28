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
        case 'ai':
            loadAIStats();
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
        showError(`Ошибка загрузки статистики: ${error.message}`);
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
        showError(`Ошибка загрузки товаров: ${error.message}`);
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
        const categories = await apiFetch('/api/products/categories');
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
        showSuccess('Цена обновлена!');
        loadProducts();
    } catch (error) {
        showError(`Ошибка обновления товара: ${error.message}`);
    }
}

async function toggleProduct(productId, isActive) {
    try {
        await apiFetch(`/api/admin/products/${productId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: isActive })
        });
        showSuccess(`Товар ${isActive ? 'активирован' : 'деактивирован'}!`);
        loadProducts();
    } catch (error) {
        showError(`Ошибка изменения статуса: ${error.message}`);
    }
}

// ============================================
// CATEGORIES - Категории
// ============================================

async function loadCategoriesTable() {
    try {
        const categories = await apiFetch('/api/products/categories');
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
        showError(`Ошибка загрузки категорий: ${error.message}`);
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
        showSuccess('Категория создана!');
        loadCategoriesTable();
    } catch (error) {
        showError(`Ошибка создания категории: ${error.message}`);
    }
}

function editCategory(categoryId) {
    alert('Редактирование категории: эта функция еще не реализована.');
}

// ============================================
// CLIENTS - Клиенты
// ============================================

async function loadClients() {
    const search = document.getElementById('searchClient')?.value || '';
    const status = document.getElementById('filterStatus')?.value || '';
    
    try {
        let endpoint = '/api/admin/clients?limit=100';
        if (search) endpoint += `&search=${encodeURIComponent(search)}`;
        if (status) endpoint += `&status=${status}`;
        
        const clients = await apiFetch(endpoint);
        const tbody = document.getElementById('clientsTable');
        if (clients.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">Клиенты не найдены</td></tr>';
            return;
        }
        tbody.innerHTML = clients.map(c => `
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
        `).join('');
    } catch (error) {
        showError(`Ошибка загрузки клиентов: ${error.message}`);
    }
}

async function approveClient(clientId) {
    if (!confirm('Одобрить регистрацию клиента?')) return;
    try {
        await apiFetch(`/api/admin/clients/${clientId}/approve`, { method: 'POST' });
        showSuccess('Клиент одобрен!');
        loadClients();
    } catch (error) {
        showError(`Ошибка одобрения клиента: ${error.message}`);
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
        showError(`Ошибка загрузки заказов: ${error.message}`);
    }
}

function viewOrder(orderId) {
    alert(`Просмотр заказа ${orderId}: эта функция еще не реализована.`);
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
        showSuccess('Статус обновлен!');
        loadOrders();
    } catch (error) {
        showError(`Ошибка изменения статуса: ${error.message}`);
    }
}

// ============================================
// SETTINGS - Настройки
// ============================================

async function loadSettings() {
    try {
        const settings = await apiFetch('/api/admin/settings');
        const groups = {
            bonusSettings: s => s.key.startsWith('bonus_'),
            financeSettings: s => ['credit_limit_default', 'payment_delay_default', 'min_order_amount'].includes(s.key),
            deliverySettings: s => ['delivery_free_from', 'delivery_cost', 'working_hours_start', 'working_hours_end'].includes(s.key),
            discountSettings: s => s.key.startsWith('discount_') || s.key.includes('orders_for_')
        };
        Object.keys(groups).forEach(id => renderSettings(id, settings.filter(groups[id])));
    } catch (error) {
        showError(`Ошибка загрузки настроек: ${error.message}`);
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
        await apiFetch(`/api/admin/settings/${key}?value=${encodeURIComponent(value)}`, { method: 'PUT' });
        showSuccess('Настройка обновлена!');
    } catch (error) {
        showError(`Ошибка обновления настройки: ${error.message}`);
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
        showSuccess('Шаблон скачан!');
    } catch (error) {
        showError(`Ошибка скачивания шаблона: ${error.message}`);
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
        showError(`Ошибка импорта: ${error.message}`);
    } finally {
        document.getElementById('importFile').value = '';
    }
}

// ============================================
// AI AGENT DASHBOARD
// ============================================

async function loadAIStats() {
    try {
        const stats = await apiFetch('/api/ai/stats?days=7');
        document.getElementById('aiTotalConversations').textContent = stats.conversations.total;
        document.getElementById('aiTotalProactive').textContent = stats.proactive_messages.total;
        document.getElementById('aiResponseRate').textContent = stats.proactive_messages.response_rate;
        document.getElementById('aiOrderRate').textContent = stats.proactive_messages.order_conversion_rate;
    } catch (error) {
        console.error('Error loading AI stats:', error.message);
    }
}

async function loadAIConversations() {
    try {
        const conversations = await apiFetch('/api/ai/conversations?limit=20');
        const container = document.getElementById('aiConversationsList');
        if (conversations.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Пока нет диалогов</div>';
            return;
        }
        container.innerHTML = conversations.map(conv => `
            <div class="conversation-item">
                <div class="mb-2"><strong>${conv.client_name}</strong><small class="text-muted ms-2">${formatDate(conv.created_at)}</small></div>
                <div class="user-message"><small class="text-muted">Клиент:</small><div>${conv.user_message}</div></div>
                <div class="ai-response"><small class="text-muted">AI:</small><div>${conv.ai_response}</div></div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('aiConversationsList').innerHTML = '<div class="text-center text-danger">Ошибка загрузки диалогов</div>';
    }
}

async function loadAIProactive() {
    try {
        const messages = await apiFetch('/api/ai/proactive?limit=20');
        const container = document.getElementById('aiProactiveList');
        if (messages.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Пока нет проактивных сообщений</div>';
            return;
        }
        container.innerHTML = messages.map(msg => `
            <div class="conversation-item">
                <div class="mb-2">
                    <strong>${msg.client_name}</strong>
                    <span class="badge ${msg.resulted_in_order ? 'bg-success' : msg.client_responded ? 'bg-info' : 'bg-secondary'} ms-2">${msg.resulted_in_order ? '✅ Заказал' : msg.client_responded ? '💬 Ответил' : '📨 Отправлено'}</span>
                    <small class="text-muted ms-2">${formatDate(msg.sent_at)}</small>
                </div>
                <div class="mb-2"><span class="badge bg-warning">${msg.reason}</span></div>
                <div class="ai-response">${msg.message_text}</div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('aiProactiveList').innerHTML = '<div class="text-center text-danger">Ошибка загрузки сообщений</div>';
    }
}

// ============================================
// UI HELPERS & FORMATTERS
// ============================================

function toggleProductsView() {
    currentView = currentView === 'table' ? 'grid' : 'table';
    const isGrid = currentView === 'grid';
    document.getElementById('productsTableView').style.display = isGrid ? 'none' : 'block';
    document.getElementById('productsGridView').style.display = isGrid ? 'block' : 'none';
    document.getElementById('viewToggleBtn').innerHTML = isGrid ? '<i class="bi bi-list"></i> Список' : '<i class="bi bi-grid-3x3"></i> Плитка';
    loadProducts();
}

function formatMoney(amount) {
    return new Intl.NumberFormat('ru-RU').format(Math.round(amount));
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' });
}

function getStatusBadge(status) {
    return { pending: 'bg-warning', active: 'bg-success', blocked: 'bg-danger' }[status] || 'bg-secondary';
}

function getStatusText(status) {
    return { pending: 'На модерации', active: 'Активен', blocked: 'Заблокирован' }[status] || status;
}

function getOrderStatusBadge(status) {
    return { new: 'bg-primary', confirmed: 'bg-info', preparing: 'bg-warning', delivering: 'bg-warning', delivered: 'bg-success', cancelled: 'bg-danger' }[status] || 'bg-secondary';
}

function getOrderStatusText(status) {
    return { new: 'Новый', confirmed: 'Подтвержден', preparing: 'Собирается', delivering: 'В доставке', delivered: 'Доставлен', cancelled: 'Отменен' }[status] || status;
}

function showSuccess(message) { alert('✅ ' + message); }
function showError(message) { alert('❌ ' + message); }

// ============================================
// INIT & EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Загружаем дашборд при старте
    showPage('dashboard');

    // Навешиваем обработчик на вкладку "Проактивные сообщения"
    const proactiveTab = document.querySelector('a[href="#aiProactive"]');
    if (proactiveTab) {
        proactiveTab.addEventListener('click', loadAIProactive);
    }
});
