<div align="center">
    <img src="https://github.com/viur-framework/viur-artwork/raw/main/icons/icon-shop.svg" height="196" alt="A hexagonal logo of Shop" title="Shop logo"/>
    <h1>viur-shop</h1>
    <a href="https://pypi.org/project/viur-shop/">
        <img alt="Badge showing current PyPI version" title="PyPI" src="https://img.shields.io/pypi/v/viur-shop">
    </a>
    <a href='https://viur-shop.readthedocs.io/en/latest/?badge=latest'>
        <img src='https://readthedocs.org/projects/viur-shop/badge/?version=latest' alt='Documentation Status' />
    </a>
    <a href="LICENSE">
        <img src="https://img.shields.io/github/license/viur-framework/viur-shop" alt="Badge displaying the license" title="License badge">
    </a>
    <br>
    A modular e-commerce extension for the <a href="https://www.viur.dev">ViUR framework</a>.
</div>

## 📦 Features

- Fully integrated **Shop logic** via the central `shop.Shop` class: cart handling, order management, API routing, bootstrapping with custom `article_skel`, and payment/shipping modules.  
- Extensible **Modules**: Address, Api, Cart, Discount, Shipping, VatRate, Order, etc. — all provided as abstract base implementations.  
- **Payment Providers**: Amazon Pay, PayPal Plus, Prepayment, Invoice, and Unzer integrations (Credit Card, PayPal, SOFORT, Bancontact, iDEAL). Can be extended with custom implementations. 
- **Event & Hook System**: Customize checkout and order flow with hooks for events like `ORDER_PAID`, `CART_CHANGED`, and `CHECKOUT_STARTED`.  
- **Pricing & Discounts**: Automated calculation of unit and bulk prices, gross/net handling, VAT rates, savings, and discount combinations via the `Price` class.

---

## 🚀 Requirements

- [ViUR Framework (viur-core)](https://www.viur.dev/) installed and configured  
- Python **3.11+**  

---

## 🧩 Installation & Integration

```bash
pipenv install viur-shop
```

Integrate into your ViUR application:
```py
# deploy/modules/shop.py
from viur.shop import Shop
from skeletons.article import ArticleSkel  # your custom article skeleton

shop = Shop(
    name="myshop",
    article_skel=ArticleSkel,
    payment_providers=[
        # e.g. PayPalPlus(), Invoice(), ... ,
    ],
    suppliers=[
        # optional Shop.types.Supplier(...),
    ],
)
```

## 🔍 Additional Resources

- Full API Reference: [viur-shop.readthedocs.io](https://viur-shop.readthedocs.io/en/latest/viur/shop/index.html)
- [Frontend Components for Vue.js](https://github.com/viur-framework/shop-components)
