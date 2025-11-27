import React from 'react';
import './Profile.css';

function Profile({ profile }) {
    if (!profile) {
        return (
            <div className="loading">
                <div className="spinner">🔄</div>
                <p>Загрузка профиля...</p>
            </div>
        );
    }

    const getStatusBadge = (status) => {
        const badges = {
            pending: { text: 'На модерации', color: '#ffc107', icon: '⏳' },
            active: { text: 'Активен', color: '#28a745', icon: '✅' },
            blocked: { text: 'Заблокирован', color: '#dc3545', icon: '❌' },
        };
        return badges[status] || badges.pending;
    };

    const badge = getStatusBadge(profile.status);

    return (
        <div className="profile">
            <h2>👤 Профиль</h2>

            <div className="profile-card">
                <div className="profile-header">
                    <h3>{profile.company_name}</h3>
                    <div 
                        className="status-badge"
                        style={{ background: badge.color }}
                    >
                        {badge.icon} {badge.text}
                    </div>
                </div>

                <div className="profile-section">
                    <h4>📋 Основная информация</h4>
                    <div className="info-grid">
                        <div className="info-item">
                            <span className="label">БИН:</span>
                            <span className="value">{profile.bin || 'Не указан'}</span>
                        </div>
                        <div className="info-item">
                            <span className="label">📍 Адрес:</span>
                            <span className="value">{profile.address || 'Не указан'}</span>
                        </div>
                        <div className="info-item">
                            <span className="label">📞 Телефон:</span>
                            <span className="value">{profile.phone || 'Не указан'}</span>
                        </div>
                        <div className="info-item">
                            <span className="label">👤 Контактное лицо:</span>
                            <span className="value">{profile.contact_person || 'Не указано'}</span>
                        </div>
                    </div>
                </div>

                <div className="profile-section">
                    <h4>💰 Финансы</h4>
                    <div className="finance-cards">
                        <div className="finance-card bonus">
                            <div className="card-icon">💎</div>
                            <div className="card-info">
                                <span className="card-label">Бонусы</span>
                                <span className="card-value">{profile.bonus_balance.toLocaleString()}₸</span>
                            </div>
                        </div>

                        <div className="finance-card credit">
                            <div className="card-icon">💳</div>
                            <div className="card-info">
                                <span className="card-label">Кредит</span>
                                <span className="card-value">
                                    {(profile.credit_limit - profile.debt).toLocaleString()}₸
                                </span>
                                <span className="card-sublabel">
                                    из {profile.credit_limit.toLocaleString()}₸
                                </span>
                            </div>
                        </div>

                        <div className="finance-card discount">
                            <div className="card-icon">🎁</div>
                            <div className="card-info">
                                <span className="card-label">Скидка</span>
                                <span className="card-value">{profile.discount_percent}%</span>
                            </div>
                        </div>

                        <div className="finance-card delay">
                            <div className="card-icon">⏰</div>
                            <div className="card-info">
                                <span className="card-label">Отсрочка</span>
                                <span className="card-value">{profile.payment_delay_days} дней</span>
                            </div>
                        </div>
                    </div>
                </div>

                {profile.debt > 0 && (
                    <div className="profile-section debt-warning">
                        <h4>⚠️ Задолженность</h4>
                        <p className="debt-amount">{profile.debt.toLocaleString()}₸</p>
                        <p className="debt-text">Пожалуйста, погасите задолженность для продолжения работы</p>
                    </div>
                )}

                <div className="profile-section">
                    <h4>ℹ️ Дополнительно</h4>
                    <div className="info-grid">
                        <div className="info-item">
                            <span className="label">📅 Дата регистрации:</span>
                            <span className="value">
                                {new Date(profile.created_at).toLocaleDateString('ru-RU')}
                            </span>
                        </div>
                        {profile.approved_at && (
                            <div className="info-item">
                                <span className="label">✅ Дата одобрения:</span>
                                <span className="value">
                                    {new Date(profile.approved_at).toLocaleDateString('ru-RU')}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Profile;