/**
 * HappySnack Admin Dashboard
 */

const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://happysnack-app.onrender.com';
const ADMIN_TELEGRAM_ID = '473294026'; // ← ЗАМЕНИ НА СВОЙ!

// Навигация между страницами
function showPage(pageId) {
    // Скрываем все страницы
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Убираем active с навигации
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Показываем нужную страницу
    document.getElementById(pageId).classList.add('active');
    
    // Активируем нужную ссылку
    document.querySelector(`a[href="#${pageId}"]`).classList.add('active');
    
    // Загружаем данные для страницы
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
		case 'ai':  // ← ДОБАВЬ ЭТО
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
        const response = await fetch(`${API_URL}/admin/stats/dashboard`, {
            headers: {
                'Authorization': ADMIN_TELEGRAM_ID
            }
        });
        
        if (!response.ok) throw new Error('Failed to load stats');
        
        const stats = await response.json();
        
        document.getElementById('todayOrders').textContent = stats.today_orders;
        document.getElementById('todayRevenue').textContent = formatMoney(stats.today_revenue);
        document.getElementById('weekOrders').textContent = stats.week_orders;
        document.getElementById('weekRevenue').textContent = formatMoney(stats.week_revenue);
        document.getElementById('pendingClients').textContent = stats.pending_clients;
        document.getElementById('lowStock').textContent = stats.low_stock_products;
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Ошибка загрузки статистики');
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
        let url = `${API_URL}/admin/products?limit=100`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (category) url += `&category_id=${category}`;
        if (active) url += `&is_active=${active}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load products');
        
        const products = await response.json();
        
        if (currentView === 'table') {
            renderProductsTable(products);
        } else {
            renderProductsGrid(products);
        }
        
    } catch (error) {
        console.error('Error loading products:', error);
        showError('Ошибка загрузки товаров');
    }
}

function renderProductsTable(products) {
    const tbody = document.getElementById('productsTable');
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Товары не найдены</td></tr>';
        return;
    }
    
    tbody.innerHTML = products.map(p => `
        <tr>
            <td>${p.id}</td>
            <td><strong>${p.name}</strong></td>
            <td>${p.category.name}</td>
            <td>${formatMoney(p.price)} ₸</td>
            <td>
                <span class="badge ${p.stock < 50 ? 'bg-danger' : 'bg-success'}">
                    ${p.stock} шт
                </span>
            </td>
            <td>
                <span class="badge ${p.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${p.is_active ? 'Активен' : 'Неактивен'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editProduct(${p.id})">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-${p.is_active ? 'warning' : 'success'}" 
                        onclick="toggleProduct(${p.id}, ${!p.is_active})">
                    <i class="bi bi-${p.is_active ? 'eye-slash' : 'eye'}"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function renderProductsGrid(products) {
    const grid = document.getElementById('productsGrid');
    
    if (products.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center">Товары не найдены</div>';
        return;
    }
    
    grid.innerHTML = products.map(p => `
        <div class="col-md-3 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="badge ${p.is_active ? 'bg-success' : 'bg-secondary'}">
                            ${p.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                        <span class="badge ${p.stock < 50 ? 'bg-danger' : 'bg-success'}">
                            ${p.stock} шт
                        </span>
                    </div>
                    
                    <h6 class="card-title">${p.name}</h6>
                    <p class="text-muted small mb-1">${p.category.name}</p>
                    
                    ${p.weight ? `<p class="small mb-1">⚖️ ${p.weight}</p>` : ''}
                    ${p.package_size ? `<p class="small mb-2">📦 ${p.package_size}</p>` : ''}
                    
                    <h5 class="text-primary">${formatMoney(p.price)} ₸</h5>
                    
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-sm btn-primary flex-fill" onclick="editProduct(${p.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-${p.is_active ? 'warning' : 'success'} flex-fill" 
                                onclick="toggleProduct(${p.id}, ${!p.is_active})">
                            <i class="bi bi-${p.is_active ? 'eye-slash' : 'eye'}"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}
async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/products/categories`);
        const categories = await response.json();
        
        const select = document.getElementById('filterCategory');
        select.innerHTML = '<option value="">Все категории</option>' + 
            categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

function showAddProductModal() {
    // TODO: Implement modal for adding products
    alert('Добавление товара: создайте модальное окно или используйте отдельную форму');
}

async function editProduct(productId) {
    const newPrice = prompt('Введите новую цену:');
    if (!newPrice) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/products/${productId}`, {
            method: 'PUT',
            headers: {
                'Authorization': ADMIN_TELEGRAM_ID,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                price: parseFloat(newPrice)
            })
        });
        
        if (!response.ok) throw new Error('Failed to update product');
        
        showSuccess('Цена обновлена!');
        loadProducts();
        
    } catch (error) {
        console.error('Error updating product:', error);
        showError('Ошибка обновления товара');
    }
}

async function toggleProduct(productId, isActive) {
    try {
        const response = await fetch(`${API_URL}/admin/products/${productId}`, {
            method: 'PUT',
            headers: {
                'Authorization': ADMIN_TELEGRAM_ID,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_active: isActive
            })
        });
        
        if (!response.ok) throw new Error('Failed to toggle product');
        
        showSuccess(`Товар ${isActive ? 'активирован' : 'деактивирован'}!`);
        loadProducts();
        
    } catch (error) {
        console.error('Error toggling product:', error);
        showError('Ошибка изменения статуса');
    }
}

// ============================================
// CATEGORIES - Категории
// ============================================

async function loadCategoriesTable() {
    try {
        const response = await fetch(`${API_URL}/products/categories`);
        const categories = await response.json();
        
        const tbody = document.getElementById('categoriesTable');
        
        tbody.innerHTML = categories.map(c => `
            <tr>
                <td>${c.id}</td>
                <td><strong>${c.name}</strong></td>
                <td>${c.sort_order}</td>
                <td>
                    <span class="badge ${c.is_active ? 'bg-success' : 'bg-secondary'}">
                        ${c.is_active ? 'Активна' : 'Неактивна'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editCategory(${c.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading categories:', error);
        showError('Ошибка загрузки категорий');
    }
}

async function showAddCategoryModal() {
    const name = prompt('Введите название категории:');
    if (!name) return;
    
    const sortOrder = prompt('Порядок сортировки:', '0');
    
    try {
        const response = await fetch(`${API_URL}/admin/categories?name=${encodeURIComponent(name)}&sort_order=${sortOrder}`, {
            method: 'POST',
            headers: {
                'Authorization': ADMIN_TELEGRAM_ID
            }
        });
        
        if (!response.ok) throw new Error('Failed to create category');
        
        showSuccess('Категория создана!');
        loadCategoriesTable();
        
    } catch (error) {
        console.error('Error creating category:', error);
        showError('Ошибка создания категории');
    }
}

function editCategory(categoryId) {
    alert('Редактирование категории: реализуйте модальное окно');
}

// ============================================
// CLIENTS - Клиенты
// ============================================

async function loadClients() {
    const search = document.getElementById('searchClient')?.value || '';
    const status = document.getElementById('filterStatus')?.value || '';
    
    try {
        let url = `${API_URL}/admin/clients?limit=100`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status) url += `&status=${status}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load clients');
        
        const clients = await response.json();
        
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
                <td>
                    <span class="badge ${getStatusBadge(c.status)}">
                        ${getStatusText(c.status)}
                    </span>
                </td>
                <td>
                    ${c.status === 'pending' ? `
                        <button class="btn btn-sm btn-success" onclick="approveClient(${c.id})">
                            <i class="bi bi-check"></i> Одобрить
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-primary" onclick="editClient(${c.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading clients:', error);
        showError('Ошибка загрузки клиентов');
    }
}

async function approveClient(clientId) {
    if (!confirm('Одобрить регистрацию клиента?')) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/clients/${clientId}/approve`, {
            method: 'POST',
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to approve client');
        
        showSuccess('Клиент одобрен!');
        loadClients();
        
    } catch (error) {
        console.error('Error approving client:', error);
        showError('Ошибка одобрения клиента');
    }
}

function editClient(clientId) {
    alert(`Редактирование клиента ${clientId}: реализуйте модальное окно`);
}

// ============================================
// ORDERS - Заказы
// ============================================

async function loadOrders() {
    const status = document.getElementById('filterOrderStatus')?.value || '';
    
    try {
        let url = `${API_URL}/admin/orders?limit=50`;
        if (status) url += `&status=${status}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load orders');
        
        const orders = await response.json();
        
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
                <td>
                    <span class="badge ${getOrderStatusBadge(o.status)}">
                        ${getOrderStatusText(o.status)}
                    </span>
                </td>
                <td>${formatDate(o.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewOrder(${o.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="changeOrderStatus(${o.id}, '${o.status}')">
                        <i class="bi bi-arrow-repeat"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading orders:', error);
        showError('Ошибка загрузки заказов');
    }
}

function viewOrder(orderId) {
    alert(`Просмотр заказа ${orderId}: реализуйте модальное окно с деталями`);
}

async function changeOrderStatus(orderId, currentStatus) {
    const statuses = {
        'new': 'confirmed',
        'confirmed': 'preparing',
        'preparing': 'delivering',
        'delivering': 'delivered'
    };
    
    const nextStatus = statuses[currentStatus] || 'confirmed';
    
    if (!confirm(`Изменить статус на "${getOrderStatusText(nextStatus)}"?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/orders/${orderId}/status?new_status=${nextStatus}`, {
            method: 'PUT',
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to change status');
        
        showSuccess('Статус обновлен!');
        loadOrders();
        
    } catch (error) {
        console.error('Error changing status:', error);
        showError('Ошибка изменения статуса');
    }
}

// ============================================
// SETTINGS - Настройки
// ============================================

async function loadSettings() {
    try {
        const response = await fetch(`${API_URL}/admin/settings`, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load settings');
        
        const settings = await response.json();
        
        // Группируем настройки
        const bonusSettings = settings.filter(s => s.key.startsWith('bonus_'));
        const financeSettings = settings.filter(s => 
            ['credit_limit_default', 'payment_delay_default', 'min_order_amount'].includes(s.key)
        );
        const deliverySettings = settings.filter(s => 
            ['delivery_free_from', 'delivery_cost', 'working_hours_start', 'working_hours_end'].includes(s.key)
        );
        const discountSettings = settings.filter(s => s.key.startsWith('discount_') || s.key.includes('orders_for_'));
        
        // Отображаем
        renderSettings('bonusSettings', bonusSettings);
        renderSettings('financeSettings', financeSettings);
        renderSettings('deliverySettings', deliverySettings);
        renderSettings('discountSettings', discountSettings);
        
    } catch (error) {
        console.error('Error loading settings:', error);
        showError('Ошибка загрузки настроек');
    }
}

function renderSettings(containerId, settings) {
    const container = document.getElementById(containerId);
    
    container.innerHTML = settings.map(s => `
        <div class="row mb-3 align-items-center">
            <div class="col-md-6">
                <label class="form-label">${s.description || s.key}</label>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-control" id="setting_${s.key}" 
                       value="${s.value}" onchange="updateSetting('${s.key}', this.value)">
            </div>
            <div class="col-md-2">
                <small class="text-muted">${s.type}</small>
            </div>
        </div>
    `).join('');
}

async function updateSetting(key, value) {
    try {
        const response = await fetch(`${API_URL}/admin/settings/${key}?value=${encodeURIComponent(value)}`, {
            method: 'PUT',
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to update setting');
        
        showSuccess('Настройка обновлена!');
        
    } catch (error) {
        console.error('Error updating setting:', error);
        showError('Ошибка обновления настройки');
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatMoney(amount) {
    return new Intl.NumberFormat('ru-RU').format(Math.round(amount));
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getStatusBadge(status) {
    const badges = {
        'pending': 'bg-warning',
        'active': 'bg-success',
        'blocked': 'bg-danger'
    };
    return badges[status] || 'bg-secondary';
}

function getStatusText(status) {
    const texts = {
        'pending': 'На модерации',
        'active': 'Активен',
        'blocked': 'Заблокирован'
    };
    return texts[status] || status;
}

function getOrderStatusBadge(status) {
    const badges = {
        'new': 'bg-primary',
        'confirmed': 'bg-info',
        'preparing': 'bg-warning',
        'delivering': 'bg-warning',
        'delivered': 'bg-success',
        'cancelled': 'bg-danger'
    };
    return badges[status] || 'bg-secondary';
}

function getOrderStatusText(status) {
    const texts = {
        'new': 'Новый',
        'confirmed': 'Подтвержден',
        'preparing': 'Собирается',
        'delivering': 'В доставке',
        'delivered': 'Доставлен',
        'cancelled': 'Отменен'
    };
    return texts[status] || status;
}

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}
// ============================================
// ИМПОРТ ТОВАРОВ
// ============================================

async function downloadTemplate() {
    try {
        const response = await fetch(`${API_URL}/admin/products/template`, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to download template');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'products_template.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showSuccess('Шаблон скачан!');
        
    } catch (error) {
        console.error('Error downloading template:', error);
        showError('Ошибка скачивания шаблона');
    }
}

async function importProducts(file) {
    if (!file) return;
    
    if (!confirm(`Импортировать товары из файла "${file.name}"?\n\nСуществующие товары будут обновлены.`)) {
        document.getElementById('importFile').value = '';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/admin/products/import`, {
            method: 'POST',
            headers: {
                'Authorization': ADMIN_TELEGRAM_ID
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Import failed');
        }
        
        const result = await response.json();
        
        let message = `✅ Импорт завершен!\n\n`;
        message += `Создано: ${result.created}\n`;
        message += `Обновлено: ${result.updated}\n`;
        message += `Всего: ${result.total}\n`;
        
        if (result.errors && result.errors.length > 0) {
            message += `\n⚠️ Ошибки (${result.errors.length}):\n`;
            message += result.errors.slice(0, 5).join('\n');
            if (result.errors.length > 5) {
                message += `\n... и еще ${result.errors.length - 5}`;
            }
        }
        
        alert(message);
        loadProducts();
        
    } catch (error) {
        console.error('Error importing products:', error);
        showError(`Ошибка импорта: ${error.message}`);
    } finally {
        document.getElementById('importFile').value = '';
    }
}

// ============================================
// ПЕРЕКЛЮЧЕНИЕ ВИД: СПИСОК/ПЛИТКА
// ============================================

let currentView = 'table'; // 'table' или 'grid'

function toggleProductsView() {
    currentView = currentView === 'table' ? 'grid' : 'table';
    
    const tableView = document.getElementById('productsTableView');
    const gridView = document.getElementById('productsGridView');
    const btn = document.getElementById('viewToggleBtn');
    
    if (currentView === 'grid') {
        tableView.style.display = 'none';
        gridView.style.display = 'block';
        btn.innerHTML = '<i class="bi bi-list"></i> Список';
    } else {
        tableView.style.display = 'block';
        gridView.style.display = 'none';
        btn.innerHTML = '<i class="bi bi-grid-3x3"></i> Плитка';
    }
    
    loadProducts();
}
// ============================================
// AI AGENT DASHBOARD
// ============================================

async function loadAIStats() {
    try {
        const response = await fetch(`${API_URL}/ai/stats?days=7`, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load AI stats');
        
        const stats = await response.json();
        
        document.getElementById('aiTotalConversations').textContent = stats.conversations.total;
        document.getElementById('aiTotalProactive').textContent = stats.proactive_messages.total;
        document.getElementById('aiResponseRate').textContent = stats.proactive_messages.response_rate;
        document.getElementById('aiOrderRate').textContent = stats.proactive_messages.order_conversion_rate;
        
    } catch (error) {
        console.error('Error loading AI stats:', error);
    }
}

async function loadAIConversations() {
    try {
        const response = await fetch(`${API_URL}/ai/conversations?limit=20`, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load conversations');
        
        const conversations = await response.json();
        
        const container = document.getElementById('aiConversationsList');
        
        if (conversations.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Пока нет диалогов</div>';
            return;
        }
        
        container.innerHTML = conversations.map(conv => `
            <div class="conversation-item">
                <div class="mb-2">
                    <strong>${conv.client_name}</strong>
                    <small class="text-muted ms-2">${formatDate(conv.created_at)}</small>
                </div>
                <div class="user-message">
                    <small class="text-muted">Клиент:</small>
                    <div>${conv.user_message}</div>
                </div>
                <div class="ai-response">
                    <small class="text-muted">AI:</small>
                    <div>${conv.ai_response}</div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading conversations:', error);
        document.getElementById('aiConversationsList').innerHTML = 
            '<div class="text-center text-danger">Ошибка загрузки</div>';
    }
}

async function loadAIProactive() {
    try {
        const response = await fetch(`${API_URL}/ai/proactive?limit=20`, {
            headers: { 'Authorization': ADMIN_TELEGRAM_ID }
        });
        
        if (!response.ok) throw new Error('Failed to load proactive messages');
        
        const messages = await response.json();
        
        const container = document.getElementById('aiProactiveList');
        
        if (messages.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Пока нет проактивных сообщений</div>';
            return;
        }
        
        container.innerHTML = messages.map(msg => `
            <div class="conversation-item">
                <div class="mb-2">
                    <strong>${msg.client_name}</strong>
                    <span class="badge ${msg.resulted_in_order ? 'bg-success' : msg.client_responded ? 'bg-info' : 'bg-secondary'} ms-2">
                        ${msg.resulted_in_order ? '✅ Заказал' : msg.client_responded ? '💬 Ответил' : '📨 Отправлено'}
                    </span>
                    <small class="text-muted ms-2">${formatDate(msg.sent_at)}</small>
                </div>
                <div class="mb-2">
                    <span class="badge bg-warning">${msg.reason}</span>
                </div>
                <div class="ai-response">
                    ${msg.message_text}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading proactive messages:', error);
        document.getElementById('aiProactiveList').innerHTML = 
            '<div class="text-center text-danger">Ошибка загрузки</div>';
    }
}

// Event listener для вкладки проактивных сообщений
document.addEventListener('DOMContentLoaded', () => {
    const proactiveTab = document.querySelector('a[href="#aiProactive"]');
    if (proactiveTab) {
        proactiveTab.addEventListener('click', loadAIProactive);
    }
});
// ============================================
// INIT
// ============================================

// Загружаем дашборд при старте
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
});
