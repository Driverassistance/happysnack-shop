import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Получаем Telegram user ID из Mini App
const getTelegramUserId = () => {
    if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
        return window.Telegram.WebApp.initDataUnsafe.user.id;
    }
    return null;
};

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Добавляем Telegram ID в каждый запрос
api.interceptors.request.use((config) => {
    const userId = getTelegramUserId();
    if (userId) {
        config.headers['Authorization'] = userId;
    }
    return config;
});

export const clientAPI = {
    // Товары
    getProducts: () => api.get('/api/products'),
    getCategories: () => api.get('/api/products/categories'),
    
    // Корзина
    getCart: () => api.get('/api/cart'),
    addToCart: (productId, quantity) => api.post('/api/cart/add', { product_id: productId, quantity }),
    updateCart: (productId, quantity) => api.put('/api/cart/update', { product_id: productId, quantity }),
    removeFromCart: (productId) => api.delete(`/api/cart/remove/${productId}`),
    clearCart: () => api.delete('/api/cart/clear'),
    
    // Заказы
    createOrder: (data) => api.post('/api/orders', data),
    getOrders: () => api.get('/api/orders'),
    getOrder: (orderId) => api.get(`/api/orders/${orderId}`),
    
    // Клиент
    getProfile: () => api.get('/api/client/profile'),
};

export default api;