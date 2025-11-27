import React, { useState } from 'react';
import './ProductCard.css';

function ProductCard({ product, onAddToCart }) {
    const [quantity, setQuantity] = useState(1);
    const [adding, setAdding] = useState(false);

    const handleAdd = async () => {
        setAdding(true);
        await onAddToCart(product.id, quantity);
        setAdding(false);
        setQuantity(1);
    };

    const incrementQuantity = () => {
        if (quantity < product.stock) {
            setQuantity(q => q + 1);
        }
    };

    const decrementQuantity = () => {
        if (quantity > 1) {
            setQuantity(q => q - 1);
        }
    };

    return (
        <div className="product-card">
            <div className="product-image-wrapper">
                {product.image_url ? (
                    <img src={product.image_url} alt={product.name} className="product-image" />
                ) : (
                    <div className="product-placeholder">📦</div>
                )}
                {product.stock < 10 && (
                    <div className="stock-badge">⚠️ Осталось {product.stock}</div>
                )}
            </div>

            <div className="product-info">
                <h3 className="product-name">{product.name}</h3>
                {product.weight && (
                    <p className="product-weight">{product.weight}</p>
                )}
                
                <div className="product-footer">
                    <div className="product-price">
                        {product.price.toLocaleString()}₸
                        {product.package_size && (
                            <small className="package-size">/{product.package_size}</small>
                        )}
                    </div>
                </div>

                <div className="product-actions">
                    <div className="quantity-selector">
                        <button onClick={decrementQuantity} disabled={quantity <= 1}>-</button>
                        <span>{quantity}</span>
                        <button onClick={incrementQuantity} disabled={quantity >= product.stock}>+</button>
                    </div>
                    <button 
                        className="btn-add-to-cart"
                        onClick={handleAdd}
                        disabled={adding || product.stock < 1}
                    >
                        {adding ? '⏳' : product.stock < 1 ? 'Нет в наличии' : '🛒 В корзину'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default ProductCard;