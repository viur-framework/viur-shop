import {getSkey, request} from './HttpClient.js';

/**
 * ViUR Shop Client (WIP)
 *
 * Order of functions should always be RCUD (this is NOT a typo of CRUD!)
 *
 */
export class ViURShopClient {

    api_url = '/shop/api';

    constructor() {
        const self = this;
    }


    // --- Article ------------------------------------------------------------

    article_view({
                     article_key,
                     parent_cart_key,
                 } = {}) {
        return request(`${this.api_url}/article_view`, {
            params: {
                'article_key': article_key,
                'parent_cart_key': parent_cart_key,
            },
        })
            .then(req => req.json())
    }


    article_add({
                    article_key,
                    parent_cart_key,
                    quantity = 1,
                    quantity_mode = 'increase',
                } = {}) {
        return request(`${this.api_url}/article_add`, {
            method: 'POST',
            params: {
                article_key,
                parent_cart_key,
                quantity,
                quantity_mode,
            },
        })
            .then(req => req.json())
    }

    article_update({
                       article_key,
                       parent_cart_key,
                       quantity = 1,
                       quantity_mode = 'increase',
                   } = {}) {
        return request(`${this.api_url}/article_update`, {
            method: 'POST',
            params: {
                article_key,
                parent_cart_key,
                quantity,
                quantity_mode,
            },
        })
            .then(req => req.json())
    }


    //TODO
    article_remove({} = {}) {
        throw Error('Not implemented');
    }


    // --- Cart ---------------------------------------------------------------

    cart_list({cart_key = null} = {}) {
        const self = this;
        return request(`${this.api_url}/cart_list`, {
            params: cart_key === null ? {} : {cart_key},
        })
            .then(req => req.json())
    }

    cart_add({
                 parent_cart_key,
                 name,
                 cart_type, // TODO
                 customer_comment,
                 shipping_address_key,
                 shipping_key,
                 discount_key,
             } = {}) {
        return request(`${this.api_url}/cart_add`, {
            method: 'POST',
            params: this.removeUndefinedValues({
                parent_cart_key,
                name,
                cart_type, // TODO
                customer_comment,
                shipping_address_key,
                shipping_key,
                discount_key,
            }),
        })
            .then(req => req.json())
    }

    //TODO
    cart_update({
                    cart_key,
                    parent_cart_key,
                    cart_type, // TODO
                    name,
                    customer_comment,
                    shipping_address_key,
                    shipping_key,
                    discount_key,
                } = {}) {
        return request(`${this.api_url}/cart_update`, {
            method: 'POST',
            params: this.removeUndefinedValues({
                cart_key,
                parent_cart_key,
                cart_type, // TODO
                name,
                customer_comment,
                shipping_address_key,
                shipping_key,
                discount_key,
            }),
        })
            .then(req => req.json())
    }

    cart_remove({cart_key} = {}) {
        return request(`${this.api_url}/cart_remove`, {
            method: 'POST',
            params: {
                cart_key,
            },
        })
            .then(req => req.json())
    }

    // --- Address ------------------------------------------------------------

    address_list({} = {}) {
        const self = this;
        return request(`/json/shop/address/list`, {
            params: {
                limit: 100,
            },
        })
            .then(req => req.json())
            .then(response => response.skellist)
    }

    address_add({
                    customer_type,
                    salutation,
                    company_name,
                    firstname,
                    lastname,
                    street_name,
                    street_number,
                    address_addition,
                    zip_code,
                    city,
                    country,
                    customer_key,
                    is_default,
                    address_type,
                } = {}) {
        return getSkey()
            .then(skey => {
                return request(`/json/shop/address/add`, {
                    method: 'POST',
                    params: this.removeUndefinedValues({
                        skey,
                        customer_type,
                        salutation,
                        company_name,
                        firstname,
                        lastname,
                        street_name,
                        street_number,
                        address_addition,
                        zip_code,
                        city,
                        country,
                        customer: customer_key,
                        is_default,
                        address_type,
                    }),
                })
                    .then(req => req.json())
                    .then(response => response.values)

            });
    }

    // --- Order --------------------------------------------------------------

    payment_providers_list({} = {}) {
        return request(`${this.api_url}/../order/payment_providers_list`)
            .then(req => req.json())
    }

    order_add({
                  cart_key,
                  payment_provider,
                  billing_address_key,
                  email,
                  customer_key,
                  state_ordered,
                  state_paid,
                  state_rts,
              } = {}) {
        return request(`${this.api_url}/order_add`, {
            method: 'POST',
            params: this.removeUndefinedValues({
                cart_key,
                payment_provider,
                billing_address_key,
                email,
                customer_key,
                state_ordered,
                state_paid,
                state_rts,
            }),
        })
            .then(req => req.json())
    }

    order_update({
                     order_key,
                     payment_provider,
                     billing_address_key,
                     email,
                     customer_key,
                     state_ordered,
                     state_paid,
                     state_rts,
                 } = {}) {
        return request(`${this.api_url}/order_update`, {
            method: 'POST',
            params: this.removeUndefinedValues({
                order_key,
                payment_provider,
                billing_address_key,
                email,
                customer_key,
                state_ordered,
                state_paid,
                state_rts,
            }),
        })
            .then(req => req.json())
    }

    order_checkout_start({
                             order_key,
                         } = {}) {
        return request(`${this.api_url}/../order/checkout_start`, {
            method: 'POST',
            params: {order_key},
        })
            .then(req => req.json())
    }

    order_checkout_order({
                             order_key,
                         } = {}) {
        return request(`${this.api_url}/../order/checkout_order`, {
            method: 'POST',
            params: {order_key},
        })
            .then(req => req.json())
    }

    order_pp_get_settings({
                              order_key,
                          } = {}) {
        return request(`${this.api_url}/../order/checkout_order`, {
            method: 'POST',
            params: {order_key},
        })
            .then(req => req.json())
    }


    // --- User ---------------------------------------------------------------

    user_view({
                  user_key = 'self',
              } = {}) {
        return request(`/vi/user/view/${user_key}`)
            .then(req => req.json())
            .then(response => response.values);
    }


    // --- Discount -----------------------------------------------------------

    discount_add({
                     code,
                     discount_key,
                 } = {}) {
        return request(`${this.api_url}/discount_add`, {
            method: 'POST',
            params: this.removeUndefinedValues({
                code,
                discount_key,
            }),
        })
            .then(req => req.json())
    }


    // --- Utils -------------------------------------------------------------

    removeUndefinedValues(obj) {
        return Object.fromEntries(
            Object.entries(obj)
                .filter(([key, value]) => value !== undefined),
        );
    }
}
