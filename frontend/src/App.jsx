import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Catalog from './components/Catalog';
import Cart from './components/Cart';
import OrderHistory from './components/OrderHistory';
import Profile from './components/Profile';
import './App.css';

function App() {
    const [cartCount, setCartCount] = useState(0);
    const [profile, setProfile] = useState(null);

    useEffect(() => {
        // Инициализируем Telegram Mini App
        if (window.Telegram?.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            
            // Настраиваем цвета под тему Telegram
            document.documentElement.style.setProperty('--tg-theme-bg-color', tg.backgroundColor);
            document.documentElement.style.setProperty('--tg-theme-text-color', tg.textColor);
            document.documentElement.style.setProperty('--tg-theme-button-color', tg.buttonColor);
        }
        
        // Загружаем данные корзины
        loadCartCount();
        loadProfile();
    }, []);

    const loadCartCount = async () => {
        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL}/api/cart`, {
                headers: {
                    'Authorization': window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '473294026'
                }
            });
            const data = await response.json();
            setCartCount(data.items?.length || 0);
        } catch (error) {
            console.error('Error loading cart:', error);
        }
    };

    const loadProfile = async () => {
        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL}/api/client/profile`, {
                headers: {
                    'Authorization': window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '473294026'
                }
            });
            const data = await response.json();
            setProfile(data);
        } catch (error) {
            console.error('Error loading profile:', error);
        }
    };

    return (
        <Router>
            <div className="app">
                {/* Header */}
                <header className="header">
                    <div className="container">
                        <h1>🍿 HappySnack</h1>
                        {profile && (
                            <div className="header-info">
                                <span className="bonus">💎 {profile.bonus_balance.toLocaleString()}₸</span>
                            </div>
                        )}
                    </div>
                </header>

                {/* Main Content */}
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Catalog onCartUpdate={loadCartCount} />} />
                        <Route path="/cart" element={<Cart onCartUpdate={loadCartCount} />} />
                        <Route path="/orders" element={<OrderHistory />} />
                        <Route path="/profile" element={<Profile profile={profile} />} />
                    </Routes>
                </main>

                {/* Bottom Navigation */}
                <nav className="bottom-nav">
                    <Link to="/" className="nav-item">
                        <i className="icon">📦</i>
                        <span>Каталог</span>
                    </Link>
                    <Link to="/cart" className="nav-item">
                        <i className="icon">🛒</i>
                        {cartCount > 0 && <span className="badge">{cartCount}</span>}
                        <span>Корзина</span>
                    </Link>
                    <Link to="/orders" className="nav-item">
                        <i className="icon">📋</i>
                        <span>Заказы</span>
                    </Link>
                    <Link to="/profile" className="nav-item">
                        <i className="icon">👤</i>
                        <span>Профиль</span>
                    </Link>
                </nav>
            </div>
        </Router>
    );
}

export default App;