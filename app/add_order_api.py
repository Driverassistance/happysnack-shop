# Читаем api_server.py
with open('app/api_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем новый endpoint перед create_app()
new_endpoint = '''
# ============================================
# ORDERS API - DIRECT FROM WEBAPP
# ============================================

async def create_order_from_webapp(request):
    """Создать заказ напрямую из WebApp (без sendData)"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        cart = data.get('cart', {})  # {product_id: quantity}
        payment_method = data.get('payment_method', 'cash')
        notes = data.get('notes', '')
        
        db = SessionLocal()
        
        # Находим пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        client = user.client
        
        # Проверяем статус клиента
        if client.status != 'active':
            db.close()
            return web.json_response({'error': 'Client not active'}, status=403)
        
        # Рассчитываем сумму и применяем скидки
        total_amount = 0
        discount_amount = 0
        items_data = []
        
        for product_id, quantity in cart.items():
            product = db.query(Product).filter(Product.id == int(product_id)).first()
            if not product or not product.is_active:
                continue
            
            # Получаем цену для клиента
            price = product.price
            custom_price = db.query(CustomPrice).filter(
                CustomPrice.client_id == client.id,
                CustomPrice.product_id == product.id
            ).first()
            
            if custom_price:
                price = custom_price.custom_price
            
            item_total = price * quantity
            
            # Применяем скидку первого заказа
            if client.orders_count == 0:
                item_discount = item_total * (client.first_order_discount / 100)
                discount_amount += item_discount
            
            total_amount += item_total
            
            items_data.append({
                'product': product,
                'quantity': quantity,
                'price': price
            })
        
        final_amount = total_amount - discount_amount
        
        # Начисляем бонусы (5%)
        bonus_earned = final_amount * 0.05
        
        # Создаём заказ
        order = Order(
            client_id=client.id,
            status='pending',
            total_amount=final_amount,
            discount_amount=discount_amount,
            payment_method=payment_method,
            notes=notes
        )
        db.add(order)
        db.flush()
        
        # Добавляем товары
        for item in items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['price']
            )
            db.add(order_item)
        
        # Обновляем клиента
        client.orders_count += 1
        client.bonus_balance += bonus_earned
        
        db.commit()
        db.refresh(order)
        
        logger.info(f"✅ Order #{order.id} created from WebApp! Client: {client.company_name}")
        
        # Отправляем уведомление клиенту
        try:
            from bot import bot
            
            await bot.send_message(
                user_id,
                f"✅ <b>Заказ #{order.id} принят!</b>\\n\\n"
                f"💰 Сумма: {final_amount:,.0f}₸\\n"
                f"🎁 Бонусов начислено: {bonus_earned:,.0f}₸\\n"
                f"💎 Ваш баланс: {client.bonus_balance:,.0f}₸\\n\\n"
                f"🚚 Доставим в течение дня!\\n"
                f"Спасибо за заказ! 🙏",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
        
        # Уведомляем админов
        try:
            admin_message = (
                f"🔔 <b>Новый заказ #{order.id}</b>\\n\\n"
                f"👤 Клиент: {client.company_name}\\n"
                f"📱 Телефон: {client.contact_phone}\\n"
                f"💰 Сумма: {final_amount:,.0f}₸\\n"
                f"📦 Товаров: {len(items_data)}\\n"
                f"💳 Оплата: {payment_method}"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                except:
                    pass
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
        
        db.close()
        
        return web.json_response({
            'success': True,
            'order_id': order.id,
            'total': float(final_amount),
            'bonus_earned': float(bonus_earned),
            'new_balance': float(client.bonus_balance)
        })
        
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({'error': str(e)}, status=500)

'''

# Вставляем перед create_app
content = content.replace(
    'def create_app():',
    new_endpoint + '\ndef create_app():'
)

# Добавляем роут
old_routes = '    # Products API'
new_routes = '''    # Orders from WebApp
    app.router.add_post('/api/orders/create', create_order_from_webapp)
    
    # Products API'''

content = content.replace(old_routes, new_routes)

with open('app/api_server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ API endpoint создан!")
print("✅ POST /api/orders/create")

