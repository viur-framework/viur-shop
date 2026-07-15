import collections
import typing as t

import unzer
from unzer.model import Basket, BasketItem, PaymentType
from viur.core.skeleton import SkeletonInstance

from viur import toolkit
from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER
from ..skeletons.cart import CartNodeSkel
from ..types import ApplicationDomain, Price, VatRateCategory

logger = SHOP_LOGGER.getChild(__name__)


class UnzerKlarna(UnzerAbstract):
    """
    Unzer Klarna payment method integration for the ViUR Shop.

    Enables customers to pay using Klarna through the Unzer payment gateway.
    """

    name: t.Final[str] = "unzer-klarna"

    currency_code: str = "EUR"
    """Currency the basket amounts are reported in."""

    # Unzer basket item types (serialized as ``type``).
    BASKET_ITEM_GOODS: t.Final[str] = "goods"
    BASKET_ITEM_SHIPMENT: t.Final[str] = "shipment"
    BASKET_ITEM_VOUCHER: t.Final[str] = "voucher"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Klarna(key=type_id)

    def get_basket_id(
        self,
        order_skel: SkeletonInstance,
    ) -> str:
        """Build a basket from the order's cart and create it at Unzer.

        Klarna requires a basket whose line items reconcile to the order
        total. The basket is built from the entire cart tree and created via
        the Unzer API; the returned basket id is passed to the charge request.

        :param order_skel: The order to derive the basket from.
        :return: The id of the created Unzer basket.
        """
        basket = Basket(
            amountTotalGross=order_skel["total"],
            currencyCode=self.currency_code,
            orderId=order_skel["key"].id_or_name,
            basketItems=self.build_basket_items(order_skel),
        )
        return self.client.createBasket(basket).key

    def build_basket_items(
        self,
        order_skel: SkeletonInstance,
    ) -> list[BasketItem]:
        """Collect the whole cart tree as Unzer basket items.

        The cart is a tree in which every node may apply its own shipping and
        (basket-domain) discount on top of the accumulated subtree total
        ("decorator" principle). This walks the entire tree and emits, per
        node, one item per article leaf plus — if present — a shipping item
        and a discount (voucher) item. The item grosses therefore reconcile
        exactly to ``order_skel["total"]`` (== root ``total_discount_price``).

        :param order_skel: The order whose cart is converted.
        :return: The basket items for the complete cart.
        """
        # The order's cart ref lacks the ``discount`` bone we need for
        # node-level discounts, so read the root node skeleton fully.
        root_skel = self.shop.cart.viewSkel("node")
        if not root_skel.read(order_skel["cart"]["dest"]["key"]):
            raise ValueError(f'Cannot read root cart node for order {order_skel["key"]!r}')

        basket_items: list[BasketItem] = []
        node_queue = collections.deque([root_skel])
        while node_queue:
            node_skel = node_queue.pop()
            # Sum of the subtree total as seen by the ``total_discount_price``
            # computation, i.e. the value the node's discount is applied to.
            node_base = 0.0
            for child in self.shop.cart.get_children(node_skel["key"]):
                if issubclass(child.skeletonCls, CartNodeSkel):
                    node_queue.append(child)
                    node_base += child["total_discount_price"] or 0.0
                else:
                    basket_items.append(self.build_article_item(child))
                    node_base += (child.price_.current or 0.0) * child["quantity"]

            if item := self.build_discount_item(node_skel, node_base):
                basket_items.append(item)
            if item := self.build_shipping_item(node_skel):
                basket_items.append(item)

        return basket_items

    def build_article_item(
        self,
        leaf_skel: SkeletonInstance,
    ) -> BasketItem:
        """Convert a single cart leaf (article) into an Unzer basket item.

        Article-level discounts are already contained in ``price_.current``;
        basket-level discounts are emitted separately, see
        :meth:`build_discount_item`.

        :param leaf_skel: The cart item (leaf) to convert.
        :return: The corresponding Unzer basket item.
        """
        price = leaf_skel.price_
        quantity = int(leaf_skel["quantity"])
        return BasketItem(
            basketItemReferenceId=leaf_skel["key"].id_or_name,
            title=leaf_skel["shop_name"] or leaf_skel["key"].id_or_name,
            quantity=quantity,
            unit="pc",
            kind=self.BASKET_ITEM_GOODS,
            vat=round(price.vat_rate_percentage * 100),
            amountPerUnit=price.current_net,
            amountNet=toolkit.round_decimal(price.current_net * quantity, 2),
            amountVat=toolkit.round_decimal(price.vat_included * quantity, 2),
            amountGross=toolkit.round_decimal(price.current * quantity, 2),
        )

    def build_shipping_item(
        self,
        node_skel: SkeletonInstance,
    ) -> BasketItem | None:
        """Build the shipping basket item for a cart node, if any.

        :param node_skel: The cart node whose shipping is converted.
        :return: The shipping basket item, or ``None`` if the node has no
            (chargeable) shipping.
        """
        if not (shipping := node_skel["shipping"]):
            return None
        gross = shipping["dest"]["shipping_cost"] or 0.0
        if not gross:
            return None
        # Shipping is taxed at the standard rate (see cart.get_vat_for_node).
        vat_percent = self.get_shipping_vat_percentage(node_skel)
        net = Price.gross_to_net(gross, vat_percent / 100.0)
        return BasketItem(
            basketItemReferenceId=f'shipping-{node_skel["key"].id_or_name}',
            title=shipping["dest"]["name"] or "Shipping",
            quantity=1,
            kind=self.BASKET_ITEM_SHIPMENT,
            vat=round(vat_percent),
            amountPerUnit=toolkit.round_decimal(net, 2),
            amountNet=toolkit.round_decimal(net, 2),
            amountVat=toolkit.round_decimal(gross - net, 2),
            amountGross=toolkit.round_decimal(gross, 2),
        )

    def build_discount_item(
        self,
        node_skel: SkeletonInstance,
        base: float,
    ) -> BasketItem | None:
        """Build the discount (voucher) basket item for a cart node, if any.

        Mirrors :func:`cart.add_discount`: only basket-domain discounts reduce
        the node total (article-domain discounts are already reflected in the
        article prices). The discount amount is ``base`` minus the discounted
        ``base``, matching the ``total_discount_price`` computation.

        :param node_skel: The cart node whose discount is converted.
        :param base: The subtree total the node's discount is applied to.
        :return: The voucher basket item, or ``None`` if the node has no
            applicable basket-domain discount.
        """
        if not (discount := node_skel["discount"]):
            return None
        if not any(
            condition["dest"]["application_domain"] == ApplicationDomain.BASKET
            for condition in discount["dest"]["condition"]
        ):
            return None
        amount = toolkit.round_decimal(base - Price.apply_discount(discount["dest"], base), 2)
        if not amount:
            return None
        # TODO: verify against the Unzer/Klarna sandbox:
        #       - the correct VAT for the voucher (basket discounts may span
        #         articles with mixed VAT rates; using 0 here so only the gross
        #         reconciles),
        #       - whether a negative-amount voucher line is accepted or the
        #         discount must be expressed via per-item ``amountDiscount``.
        return BasketItem(
            basketItemReferenceId=f'discount-{discount["dest"]["key"].id_or_name}',
            title=discount["dest"]["name"] or "Discount",
            quantity=1,
            kind=self.BASKET_ITEM_VOUCHER,
            vat=0,
            amountPerUnit=-amount,
            amountNet=-amount,
            amountVat=0.0,
            amountGross=-amount,
        )

    def get_shipping_vat_percentage(
        self,
        node_skel: SkeletonInstance,
    ) -> float:
        """Return the standard VAT percentage for a node's shipping.

        :param node_skel: The cart node providing the shipping country.
        :return: The standard VAT rate in percent (e.g. ``19.0``), or ``0.0``
            if none is configured.
        """
        try:
            country = node_skel["shipping_address"]["dest"]["country"]
        except (KeyError, TypeError):
            country = None
        try:
            return self.shop.vat_rate.get_vat_rate_for_country(
                country=country, category=VatRateCategory.STANDARD,
            )
        except Exception as exc:  # noqa: BLE001 -- fall back to 0 % on any config error
            logger.warning(f"No standard vat rate for shipping: {exc}")
            return 0.0
