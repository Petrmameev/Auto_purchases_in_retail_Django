API Сервис заказа товаров для розничных сетей

## Описание

Приложение предназначено для автоматизации закупок в розничной сети через REST API. Сервис подразумевает множество покупателей и продавцов(магазинов).

**Настройки проекта:**

     - settings.py
     - .env (содержит переменные из settings.py и )
     - Dockerfile
     - docker-compose.yml
     - /nginx/orders.conf

**Команды для запуска сервера**

     1) cd Diplom_developer_Python 
     2) sudo docker-compose up -d --build

**Команда для очистки БД**

     - sudo docker-compose exec backend python3 manage.py flush --no-input

**Команда для запуска Celery**

     - celery -A netology_pd_diplom worker

**Команда для остановки сервера**

     - sudo docker-compose down

## Доступные функции в приложении:

 - создание пользователя (на почту, указанную при регистрации отправляется уведомление)
 - авторизация (принимает логин и пароль, возвращает токен для авторизации)
 - создание и редактирование контакта (требуется авторизация пользователя)
 - изменения типа пользователя на тип "Магазин"
 - загрузка прайса (через ссылку или из файла, требуется авторизация пользователя - только для пользователя - магазина)
 - просмотр товаров, магазинов, категорий (не требуется авторизации пользователя)
 - формирование и редактирование корзины (требуется авторизация пользователя)
 - подтверждение заказа с указанием адреса (требуется авторизация пользователя, на почту приходит уведомление о заказе для покупателя и для админа)
 - просмотр заказов покупателем (требуется авторизация пользователя)
 - просмотр заказов продавцом (требует авторизации магазина)

   ![Screenshot_1](https://github.com/Petrmameev/Diplom_developer_Python/assets/103646573/17e7c53a-364c-4be3-9164-5bcd4b6873d5)

