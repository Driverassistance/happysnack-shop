import React, { useState, useEffect } from 'react';
import { clientAPI } from '../api';
import ProductCard from './ProductCard';
import './Catalog.css';

function Catalog({ onCartUpdate }) {
    const [products, setProducts] = useState([]);
    const [categories, setCategories] = useState([]);
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [productsRes, categoriesRes] = await Promise.all([
                clientAPI.getProducts(),
                clientAPI.getCategories()
            ]);
            
            setProducts(productsRes.data);
            setCategories(categoriesRes.data);
            setLoading(false);
        } catch (error) {
            console.error('Error loading data:', error);
            setLoading(false);
        }
    };

    const filteredProducts = products.filter(product => {
        const matchesCategory = selectedCategory === 'all' || product.category_id === selectedCategory;
        const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch && product.is_active;
    });

    const handleAddToCart = async (productId, quantity) => {
        try {
            await clientAPI.addToCart(productId, quantity);
            onCartUpdate();
            
            // Показываем уведомление
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showAlert('✅ Добавлено в корзину!');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showAlert('❌ Ошибка добавления в корзину');
            }
        }
    };

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner">🔄</div>
                <p>Загрузка товаров...</p>
            </div>
        );
    }

    return (
        <div className="catalog">
            {/* Поиск */}
            <div className="search-bar">
                <input
                    type="text"
                    placeholder="🔍 Поиск товаров..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {/* Категории */}
            <div className="categories">
                <button
                    className={`category-chip ${selectedCategory === 'all' ? 'active' : ''}`}
                    onClick={() => setSelectedCategory('all')}
                >
                    Все товары
                </button>
                {categories.map(category => (
                    <button
                        key={category.id}
                        className={`category-chip ${selectedCategory === category.id ? 'active' : ''}`}
                        onClick={() => setSelectedCategory(category.id)}
                    >
                        {category.name}
                    </button>
                ))}
            </div>

            {/* Товары */}
            {filteredProducts.length === 0 ? (
                <div className="empty-state">
                    <p>😔 Товары не найдены</p>
                </div>
            ) : (
                <div className="product-grid">
                    {filteredProducts.map(product => (
                        <ProductCard
                            key={product.id}
                            product={product}
                            onAddToCart={handleAddToCart}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default Catalog;