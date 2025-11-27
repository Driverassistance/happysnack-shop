import React, { useState, useEffect } from 'react';
import { clientAPI } from '../api';
import './OrderHistory.css';

function OrderHistory() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedOrder, setSelectedOrder] = useState(null);

    useEffect(() => {
        loadOrders();
    }, []);

    const loadOrders = async () => {
        try {
            const response = await clientAPI.getOrders();
            setOrders(response.data);
            setLoading(false);
        } catch (error) {
            console.error('Error loading orders:', error);
            setLoading(false);
        }
    };

    const getStatusBadge = (status) => {
        const badges = {
            new: { text: 'Новый', color: '#0088cc', icon: '🆕' },
            confirmed: { text: 'Подтвержден', color: '#ffc107', icon: '✅' },
            processing: { text: 'Обрабатывается', color: '#17a2b8', icon: '⏳' },
            shipped: { text: 'Доставляется', color: '#6f42c1', icon: '🚚' },
            delivered: { text: 'Доставлен', color: '#28a745', icon: '✔️' },
            cancelled: { text: 'Отменен', color: '#dc3545', icon: '❌' },
        };
        return badges[status] || badges.new;
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner">🔄</div>
                <p>Загрузка заказов...</p>
            </div>
        );
    }

    if (orders.length === 0) {
        return (
            <div className="empty-orders">
                <div className="empty-icon">📋</div>
                <h2>Нет заказов</h2>
                <p>Оформите первый заказ из каталога</p>
            </div>
        );
    }

    return (
        <div className="order-history">
            <h2>📋 Мои заказы</h2>

            <div className="orders-list">
                {orders.map(order => {
                    const badge = getStatusBadge(order.status);
                    
                    return (
                        <div 
                            key={order.id} 
                            className="order-card"
                            onClick={() => setSelectedOrder(selectedOrder?.id === order.id ? null : order)}
                        >
                            <div className="order-header">
                                <div className="order-number">
                                    <strong>№ {order.order_number}</strong>
                                    <span className="order-date">{formatDate(order.created_at)}</span>
                                </div>
                                <div 
                                    className="status-badge"
                                    style={{ background: badge.color }}
                                >
                                    {badge.icon} {badge.text}
                                </div>
                            </div>

                            <div className="order-info">
                                <p className="order-total">
                                    <strong>{order.final_total.toLocaleString()}₸</strong>
                                </p>
                                <p className="order-items-count">
                                    {order.items?.length || 0} {order.items?.length === 1 ? 'товар' : 'товаров'}
                                </p>
                            </div>

                            {selectedOrder?.id === order.id && (
                                <div className="order-details">
                                    <hr />
                                    
                                    <h4>Состав заказа:</h4>
                                    <div className="order-items">
                                        {order.items.map((item, index) => (
                                            <div key={index} className="order-item">
                                                <span className="item-name">{item.product_name}</span>
                                                <span className="item-quantity">× {item.quantity}</span>
                                                <span className="item-price">{item.total.toLocaleString()}₸</span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="order-summary">
                                        <div className="summary-line">
                                            <span>Товары:</span>
                                            <span>{order.total.toLocaleString()}₸</span>
                                        </div>
                                        {order.discount > 0 && (
                                            <div className="summary-line discount">
                                                <span>Скидка:</span>
                                                <span>-{order.discount.toLocaleString()}₸</span>
                                            </div>
                                        )}
                                        {order.bonus_used > 0 && (
                                            <div className="summary-line bonus">
                                                <span>Использовано бонусов:</span>
                                                <span>-{order.bonus_used.toLocaleString()}₸</span>
                                            </div>
                                        )}
                                        <div className="summary-line total">
                                            <span>Итого:</span>
                                            <span>{order.final_total.toLocaleString()}₸</span>
                                        </div>
                                    </div>

                                    {order.delivery_address && (
                                        <div className="delivery-info">
                                            <strong>📍 Адрес доставки:</strong>
                                            <p>{order.delivery_address}</p>
                                        </div>
                                    )}

                                    {order.comment && (
                                        <div className="order-comment">
                                            <strong>💬 Комментарий:</strong>
                                            <p>{order.comment}</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default OrderHistory;