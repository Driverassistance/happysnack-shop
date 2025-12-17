// Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const userId = tg.initDataUnsafe.user?.id;
const API_BASE = '';

// Скрыть прелоадер
function hideLoader() {
    document.getElementById('loader').classList.add('hidden');
}

// API запросы
async function apiRequest(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error('API Error');
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        tg.showAlert('Ошибка загрузки данных');
        return null;
    }
}

// Загрузка профиля
async function loadProfile() {
    const profile = await apiRequest(`/api/client/profile?user_id=${userId}`);
    if (!profile) return;
    
    document.getElementById('companyName').textContent = profile.company_name;
    document.getElementById('userStatus').textContent = `⭐ ${profile.status_name}`;
    document.getElementById('bonusBalance').textContent = `${profile.bonus_balance.toLocaleString()}₸`;
    document.getElementById('ordersCount').textContent = profile.orders_count;
    document.getElementById('totalSpent').textContent = `${profile.total_spent.toLocaleString()}₸`;
    document.getElementById('totalSaved').textContent = `${profile.total_saved.toLocaleString()}₸`;
}

// Загрузка заказов
async function loadOrders(status = 'all') {
    const endpoint = status === 'all' 
        ? `/api/client/orders?user_id=${userId}`
        : `/api/client/orders?user_id=${userId}&status=${status}`;
    
    const orders = await apiRequest(endpoint);
    const container = document.getElementById('ordersList');
    
    if (!orders || orders.length === 0) {
        container.innerHTML = '<div class="empty-state">Заказов пока нет</div>';
        return;
    }
    
    container.innerHTML = orders.map(order => `
        <div class="order-card">
            <div class="order-header">
                <span class="order-number">Заказ #${order.id}</span>
                <span class="order-status status-${order.status}">
                    ${order.status === 'delivered' ? '✅ Доставлен' : '🚚 В работе'}
                </span>
            </div>
            <div class="order-amount">${order.total_amount.toLocaleString()}₸</div>
            <div class="order-items">${order.items_count} товаров</div>
            <div class="order-actions">
                <button class="order-btn" onclick="repeatOrder(${order.id})">🔄 Повторить</button>
                <button class="order-btn" onclick="viewOrder(${order.id})">👁 Детали</button>
            </div>
        </div>
    `).join('');
}

// Повторить заказ
async function repeatOrder(orderId) {
    const data = await apiRequest(`/api/client/orders/${orderId}/repeat`);
    if (!data) return;
    
    // Открываем каталог с товарами в корзине
    tg.showAlert('Товары добавлены в корзину! Переходим в каталог...');
    
    setTimeout(() => {
        tg.close();
    }, 1500);
}

// Посмотреть заказ
function viewOrder(orderId) {
    tg.showAlert(`Детали заказа #${orderId} (TODO: сделать модальное окно)`);
}

// Загрузка избранного
async function loadFavorites() {
    const favorites = await apiRequest(`/api/client/favorites?user_id=${userId}`);
    const container = document.getElementById('favoritesList');
    
    if (!favorites || favorites.length === 0) {
        container.innerHTML = '<div class="empty-state">Избранных товаров пока нет</div>';
        return;
    }
    
    container.innerHTML = favorites.map(item => `
        <div class="favorite-card">
            <div class="favorite-info">
                <h4>${item.name}</h4>
                <div class="favorite-price">${item.price.toLocaleString()}₸</div>
            </div>
            <button class="add-to-cart-btn" onclick="addToCart(${item.product_id})">
                + В корзину
            </button>
        </div>
    `).join('');
}

// Добавить в корзину
function addToCart(productId) {
    tg.showAlert('Товар добавлен! Переходим в каталог...');
    setTimeout(() => tg.close(), 1000);
}

// Отправить отзыв
async function submitFeedback(type, text) {
    try {
        const response = await fetch('/api/client/feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                type: type,
                text: text
            })
        });
        
        const result = await response.json();
        if (result.success) {
            tg.showAlert(result.message);
            loadProfile(); // Обновляем бонусы
        }
    } catch (error) {
        tg.showAlert('Ошибка отправки');
    }
}

// Навигация
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Переключаем активную вкладку
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Показываем контент
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById(`tab-${tabName}`).classList.add('active');
        
        // Загружаем данные если нужно
        if (tabName === 'orders') loadOrders();
        if (tabName === 'favorites') loadFavorites();
    });
});

// Фильтр заказов
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadOrders(btn.dataset.status);
    });
});

// Кнопки действий
document.getElementById('repeatLastOrder').addEventListener('click', async () => {
    const orders = await apiRequest(`/api/client/orders?user_id=${userId}&limit=1`);
    if (orders && orders.length > 0) {
        repeatOrder(orders[0].id);
    } else {
        tg.showAlert('У вас пока нет заказов');
    }
});

document.getElementById('gotoCatalog').addEventListener('click', () => {
    tg.close();
});

// Отзывы
document.getElementById('submitQuickFeedback').addEventListener('click', () => {
    const text = document.getElementById('quickFeedback').value;
    if (!text.trim()) {
        tg.showAlert('Напишите отзыв');
        return;
    }
    submitFeedback('feedback', text);
    document.getElementById('quickFeedback').value = '';
});

document.getElementById('submitIdea').addEventListener('click', () => {
    const text = document.getElementById('ideaText').value;
    if (!text.trim()) {
        tg.showAlert('Опишите вашу идею');
        return;
    }
    submitFeedback('idea', text);
    document.getElementById('ideaText').value = '';
});

// Загрузка при старте
loadProfile();
hideLoader();