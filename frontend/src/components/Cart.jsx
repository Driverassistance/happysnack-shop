import React, { useState, useEffect } from 'react';
import { clientAPI } from '../api';
import { useNavigate } from 'react-router-dom';
import './Cart.css';

function Cart({ onCartUpdate }) {
    const [cart, setCart] = useState(null);
    const [loading, setLoading] = useState(true);
    const [ordering, setOrdering] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        loadCart();
    }, []);

    const loadCart = async () => {
        try {
            const response = await clientAPI.getCart();
            setCart(response.data);
            setLoading(false);
        } catch (error) {
            console.error('Error loading cart:', error);
            setLoading(false);
        }
    };

    const handleUpdateQuantity = async (productId, newQuantity) => {
        if (newQuantity < 1) return;
        
        try {
            await clientAPI.updateCart(productId, newQuantity);
            await loadCart();
            onCartUpdate();
        } catch (error) {
            console.error('Error updating cart:', error);
        }
    };

    const handleRemoveItem = async (productId) => {
        try {
            await clientAPI.removeFromCart(productId);
            await loadCart();
            onCartUpdate();
        } catch (error) {
            console.error('Error removing item:', error);
        }
    };

    const handleCheckout = async () => {
        if (!cart || cart.items.length === 0) return;

        setOrdering(true);
        
        try {
            const response = await clientAPI.createOrder({
                delivery_address: cart.client.address,
                comment: ''
            });
            
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showAlert('✅ Заказ оформлен успешно!', () => {
                    navigate('/orders');
                });
            } else {
                navigate('/orders');
            }
            
            onCartUpdate();
        } catch (error) {
            console.error('Error creating order:', error);
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showAlert('❌ Ошибка оформления заказа');
            }
        } finally {
            setOrdering(false);
        }
    };

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner">🔄</div>
                <p>Загрузка корзины...</p>
            </div>
        );
    }

    if (!cart || cart.items.length === 0) {
        return (
            <div className="empty-cart">
                <div className="empty-icon">🛒</div>
                <h2>Корзина пуста</h2>
                <p>Добавьте товары из каталога</p>
                <button className="btn btn-primary" onClick={() => navigate('/')}>
                    Перейти в каталог
                </button>
            </div>
        );
    }

    return (
        <div className="cart">
            <h2>🛒 Корзина</h2>

            <div className="cart-items">
                {cart.items.map(item => (
                    <div key={item.product_id} className="cart-item">
                        <div className="item-info">
                            <h3>{item.product_name}</h3>
                            <p className="item-price">{item.price.toLocaleString()}₸ × {item.quantity}</p>
                        </div>

                        <div className="item-controls">
                            <div className="quantity-control">
                                <button onClick={() => handleUpdateQuantity(item.product_id, item.quantity - 1)}>
                                    -
                                </button>
                                <span>{item.quantity}</span>
                                <button onClick={() => handleUpdateQuantity(item.product_id, item.quantity + 1)}>
                                    +
                                </button>
                            </div>
                            
                            <div className="item-total">
                                {item.total.toLocaleString()}₸
                            </div>

                            <button 
                                className="btn-remove"
                                onClick={() => handleRemoveItem(item.product_id)}
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="cart-summary">
                <div className="summary-row">
                    <span>Товары:</span>
                    <span>{cart.total.toLocaleString()}₸</span>
                </div>
                
                {cart.discount > 0 && (
                    <div className="summary-row discount">
                        <span>Скидка ({cart.client.discount_percent}%):</span>
                        <span>-{cart.discount.toLocaleString()}₸</span>
                    </div>
                )}

                <div className="summary-row total">
                    <span>Итого:</span>
                    <span>{cart.final_total.toLocaleString()}₸</span>
                </div>

                <div className="client-info">
                    <p><strong>💎 Бонусы:</strong> {cart.client.bonus_balance.toLocaleString()}₸</p>
                    <p><strong>💳 Кредит:</strong> {(cart.client.credit_limit - cart.client.debt).toLocaleString()}₸</strong>
                </div>

                <button 
                    className="btn btn-success btn-checkout"
                    onClick={handleCheckout}
                    disabled={ordering}
                >
                    {ordering ? '⏳ Оформление...' : '✅ Оформить заказ'}
                </button>
            </div>
        </div>
    );
}

export default Cart;