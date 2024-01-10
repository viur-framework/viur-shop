CREATE TABLE AddressSkel (
 key VARCHAR(64) NOT NULL,
 customer_type VARCHAR(255),
 salutation VARCHAR(255),
 company_name VARCHAR(255),
 firstname VARCHAR(255),
 lastname VARCHAR(255),
 street_name VARCHAR(255),
 street_number VARCHAR(10),
 address_addition VARCHAR(255),
 zip_code VARCHAR(10),
 city VARCHAR(255),
 country VARCHAR(2),
 customer VARCHAR(64) NOT NULL,
 is_default BIT(1),
 address_type VARCHAR(255)
);

ALTER TABLE AddressSkel ADD CONSTRAINT PK_AddressSkel PRIMARY KEY (key);


CREATE TABLE CartNodeSkel (
 key VARCHAR(64) NOT NULL,
 total FLOAT(10),
 vat_value FLOAT(10),
 vat_rate VARCHAR(64) NOT NULL,
 shipping_address VARCHAR(64) NOT NULL,
 customer_comment TEXT,
 name VARCHAR(255),
 parententry VARCHAR(64) NOT NULL,
 cart_type VARCHAR(255),
 shipping VARCHAR(64) NOT NULL,
 discount VARCHAR(64) NOT NULL
);

ALTER TABLE CartNodeSkel ADD CONSTRAINT PK_CartNodeSkel PRIMARY KEY (key);


CREATE TABLE File (
 key VARCHAR(255) NOT NULL
);

ALTER TABLE File ADD CONSTRAINT PK_File PRIMARY KEY (key);


CREATE TABLE ShippingConfigSkel (
 key VARCHAR(64) NOT NULL,
 name VARCHAR(255),
 shipping_skel VARCHAR(64) NOT NULL
);

ALTER TABLE ShippingConfigSkel ADD CONSTRAINT PK_ShippingConfigSkel PRIMARY KEY (key);


CREATE TABLE ShippingPreConditionRelSkel (
 minimum_order_value FLOAT(10),
 country VARCHAR(2),
 zip_code VARCHAR(10)
);


CREATE TABLE ShippingSkel (
 key VARCHAR(64) NOT NULL,
 name VARCHAR(10) NOT NULL,
 description TEXT,
 shipping_cost FLOAT(10),
 supplier VARCHAR(255) NOT NULL,
 delivery_time_min INT NOT NULL,
 delivery_time_max INT NOT NULL
);

ALTER TABLE ShippingSkel ADD CONSTRAINT PK_ShippingSkel PRIMARY KEY (key);


CREATE TABLE UserSkel (
 key VARCHAR(64) NOT NULL,
 wishlist VARCHAR(64) NOT NULL
);

ALTER TABLE UserSkel ADD CONSTRAINT PK_UserSkel PRIMARY KEY (key);


CREATE TABLE VatSkel (
 key VARCHAR(64) NOT NULL,
 rate FLOAT(10)
);

ALTER TABLE VatSkel ADD CONSTRAINT PK_VatSkel PRIMARY KEY (key);


CREATE TABLE AbstractArticleSkel (
 key VARCHAR(64) NOT NULL,
 shop_name VARCHAR(255),
 shop_description TEXT,
 shop_price_retail FLOAT(10),
 shop_price_recommended FLOAT(10),
 shop_availability VARCHAR(255),
 shop_listed BIT(1),
 shop_image VARCHAR(255),
 shop_art_no_or_gtin VARCHAR(10),
 shop_vat VARCHAR(64) NOT NULL,
 shop_shipping VARCHAR(64),
 shop_is_weee BIT(1),
 shop_is_low_price BIT(1) NOT NULL
);

ALTER TABLE AbstractArticleSkel ADD CONSTRAINT PK_AbstractArticleSkel PRIMARY KEY (key);


CREATE TABLE CartItemSkel (
 key VARCHAR(64) NOT NULL,
 parententry VARCHAR(64) NOT NULL,
 article VARCHAR(64) NOT NULL,
 **article_data_skey VARCHAR(255),
 project_data JSON NOT NULL,
 quantity INT
);

ALTER TABLE CartItemSkel ADD CONSTRAINT PK_CartItemSkel PRIMARY KEY (key);


CREATE TABLE DiscountConditionSkel (
 key VARCHAR(64) NOT NULL,
 code_type VARCHAR(255),
 application_domain VARCHAR(255),
 quantity_volume INT,
 quantity_used INT,
 individual_codes_amount INT,
 scope_code VARCHAR(10),
 individual_codes_prefix VARCHAR(10),
 scope_minimum_order_value FLOAT(10),
 scope_date_start TIMESTAMP WITH TIME ZONE(10),
 scope_date_end TIMESTAMP WITH TIME ZONE(10),
 scope_language VARCHAR(2),
 scope_country VARCHAR(2),
 scope_minimum_quantity INT,
 scope_customer_group VARCHAR(255),
 scope_combinable_other_discount BIT(1),
 scope_combinable_low_price BIT(1),
 scope_article VARCHAR(64),
 is_subcode BIT(1),
 parent_code VARCHAR(64) NOT NULL
);

ALTER TABLE DiscountConditionSkel ADD CONSTRAINT PK_DiscountConditionSkel PRIMARY KEY (key);


CREATE TABLE DiscountSkel (
 key VARCHAR(64) NOT NULL,
 name VARCHAR(255),
 description TEXT,
 discount_type VARCHAR(255),
 absolute FLOAT(10),
 percentage FLOAT(10),
 condition VARCHAR(64) NOT NULL,
 condition_operator VARCHAR(255)
);

ALTER TABLE DiscountSkel ADD CONSTRAINT PK_DiscountSkel PRIMARY KEY (key);


CREATE TABLE OrderSkel (
 key VARCHAR(64) NOT NULL,
 billing_address VARCHAR(64) NOT NULL,
 customer VARCHAR(64) NOT NULL,
 cart VARCHAR(64) NOT NULL,
 total FLOAT(10),
 order_uid VARCHAR(64) NOT NULL,
 payment_provider VARCHAR(255),
 is_ordered BIT(1),
 is_paid BIT(1),
 is_rts BIT(1),
 state VARCHAR(255),
 email VARCHAR(255),
 project_data JSON
);

ALTER TABLE OrderSkel ADD CONSTRAINT PK_OrderSkel PRIMARY KEY (key);


ALTER TABLE AddressSkel ADD CONSTRAINT FK_AddressSkel_0 FOREIGN KEY (customer) REFERENCES UserSkel (key);


ALTER TABLE CartNodeSkel ADD CONSTRAINT FK_CartNodeSkel_0 FOREIGN KEY (vat_rate) REFERENCES VatSkel (key);
ALTER TABLE CartNodeSkel ADD CONSTRAINT FK_CartNodeSkel_1 FOREIGN KEY (shipping_address) REFERENCES AddressSkel (key);
ALTER TABLE CartNodeSkel ADD CONSTRAINT FK_CartNodeSkel_2 FOREIGN KEY (parententry) REFERENCES CartNodeSkel (key);
ALTER TABLE CartNodeSkel ADD CONSTRAINT FK_CartNodeSkel_3 FOREIGN KEY (shipping) REFERENCES ShippingSkel (key);
ALTER TABLE CartNodeSkel ADD CONSTRAINT FK_CartNodeSkel_4 FOREIGN KEY (discount) REFERENCES DiscountSkel (key);


ALTER TABLE ShippingConfigSkel ADD CONSTRAINT FK_ShippingConfigSkel_0 FOREIGN KEY (shipping_skel) REFERENCES ShippingSkel (key);


ALTER TABLE UserSkel ADD CONSTRAINT FK_UserSkel_0 FOREIGN KEY (wishlist) REFERENCES CartNodeSkel (key);


ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_0 FOREIGN KEY (shop_image) REFERENCES File (key);
ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_1 FOREIGN KEY (shop_vat) REFERENCES VatSkel (key);
ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_2 FOREIGN KEY (shop_shipping) REFERENCES ShippingConfigSkel (key);


ALTER TABLE CartItemSkel ADD CONSTRAINT FK_CartItemSkel_0 FOREIGN KEY (parententry) REFERENCES CartNodeSkel (key);
ALTER TABLE CartItemSkel ADD CONSTRAINT FK_CartItemSkel_1 FOREIGN KEY (article) REFERENCES AbstractArticleSkel (key);


ALTER TABLE DiscountConditionSkel ADD CONSTRAINT FK_DiscountConditionSkel_0 FOREIGN KEY (scope_article) REFERENCES AbstractArticleSkel (key);
ALTER TABLE DiscountConditionSkel ADD CONSTRAINT FK_DiscountConditionSkel_1 FOREIGN KEY (parent_code) REFERENCES DiscountConditionSkel (key);


ALTER TABLE DiscountSkel ADD CONSTRAINT FK_DiscountSkel_0 FOREIGN KEY (condition) REFERENCES DiscountConditionSkel (key);


ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_0 FOREIGN KEY (billing_address) REFERENCES AddressSkel (key);
ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_1 FOREIGN KEY (customer) REFERENCES UserSkel (key);
ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_2 FOREIGN KEY (cart) REFERENCES CartNodeSkel (key);


COMMENT ON TABLE AddressSkel IS 'AddressSkel';
COMMENT ON COLUMN AddressSkel.key IS '';
COMMENT ON COLUMN AddressSkel.customer_type IS '';
COMMENT ON COLUMN AddressSkel.salutation IS '';
COMMENT ON COLUMN AddressSkel.company_name IS '';
COMMENT ON COLUMN AddressSkel.firstname IS '';
COMMENT ON COLUMN AddressSkel.lastname IS '';
COMMENT ON COLUMN AddressSkel.street_name IS '';
COMMENT ON COLUMN AddressSkel.street_number IS '';
COMMENT ON COLUMN AddressSkel.address_addition IS '';
COMMENT ON COLUMN AddressSkel.zip_code IS '';
COMMENT ON COLUMN AddressSkel.city IS '';
COMMENT ON COLUMN AddressSkel.country IS '';
COMMENT ON COLUMN AddressSkel.customer IS '';
COMMENT ON COLUMN AddressSkel.is_default IS '';
COMMENT ON COLUMN AddressSkel.address_type IS '';
COMMENT ON TABLE CartNodeSkel IS 'CartNodeSkel';
COMMENT ON COLUMN CartNodeSkel.key IS '';
COMMENT ON COLUMN CartNodeSkel.total IS '';
COMMENT ON COLUMN CartNodeSkel.vat_value IS '';
COMMENT ON COLUMN CartNodeSkel.vat_rate IS '';
COMMENT ON COLUMN CartNodeSkel.shipping_address IS '';
COMMENT ON COLUMN CartNodeSkel.customer_comment IS '';
COMMENT ON COLUMN CartNodeSkel.name IS '';
COMMENT ON COLUMN CartNodeSkel.parententry IS '';
COMMENT ON COLUMN CartNodeSkel.cart_type IS '';
COMMENT ON COLUMN CartNodeSkel.shipping IS '';
COMMENT ON COLUMN CartNodeSkel.discount IS '';
COMMENT ON TABLE File IS '';
COMMENT ON COLUMN File.key IS '';
COMMENT ON TABLE ShippingConfigSkel IS 'ShippingConfigSkel';
COMMENT ON COLUMN ShippingConfigSkel.key IS '';
COMMENT ON COLUMN ShippingConfigSkel.name IS '';
COMMENT ON COLUMN ShippingConfigSkel.shipping_skel IS '';
COMMENT ON TABLE ShippingPreConditionRelSkel IS '';
COMMENT ON COLUMN ShippingPreConditionRelSkel.minimum_order_value IS '';
COMMENT ON COLUMN ShippingPreConditionRelSkel.country IS '';
COMMENT ON COLUMN ShippingPreConditionRelSkel.zip_code IS '';
COMMENT ON TABLE ShippingSkel IS 'ShippingSkel';
COMMENT ON COLUMN ShippingSkel.key IS '';
COMMENT ON COLUMN ShippingSkel.name IS '';
COMMENT ON COLUMN ShippingSkel.description IS 'Kundenkommentar';
COMMENT ON COLUMN ShippingSkel.shipping_cost IS '';
COMMENT ON COLUMN ShippingSkel.supplier IS '';
COMMENT ON COLUMN ShippingSkel.delivery_time_min IS '';
COMMENT ON COLUMN ShippingSkel.delivery_time_max IS '';
COMMENT ON TABLE UserSkel IS 'UserSkel';
COMMENT ON COLUMN UserSkel.key IS '';
COMMENT ON COLUMN UserSkel.wishlist IS '';
COMMENT ON TABLE VatSkel IS 'VatSkel';
COMMENT ON COLUMN VatSkel.key IS '';
COMMENT ON COLUMN VatSkel.rate IS '';
COMMENT ON TABLE AbstractArticleSkel IS 'AbstractArticleSkel';
COMMENT ON COLUMN AbstractArticleSkel.key IS '';
COMMENT ON COLUMN AbstractArticleSkel.shop_name IS 'shop_name';
COMMENT ON COLUMN AbstractArticleSkel.shop_description IS 'shop_description';
COMMENT ON COLUMN AbstractArticleSkel.shop_price_retail IS 'Verkaufspreis';
COMMENT ON COLUMN AbstractArticleSkel.shop_price_recommended IS 'UVP';
COMMENT ON COLUMN AbstractArticleSkel.shop_availability IS '';
COMMENT ON COLUMN AbstractArticleSkel.shop_listed IS 'shop_listed';
COMMENT ON COLUMN AbstractArticleSkel.shop_image IS 'Produktbild';
COMMENT ON COLUMN AbstractArticleSkel.shop_art_no_or_gtin IS 'Artikelnummer';
COMMENT ON COLUMN AbstractArticleSkel.shop_vat IS 'Steuersatz';
COMMENT ON COLUMN AbstractArticleSkel.shop_shipping IS 'Versandkosten';
COMMENT ON COLUMN AbstractArticleSkel.shop_is_weee IS 'Elektro G';
COMMENT ON COLUMN AbstractArticleSkel.shop_is_low_price IS '';
COMMENT ON TABLE CartItemSkel IS 'CartItemSkel';
COMMENT ON COLUMN CartItemSkel.key IS '';
COMMENT ON COLUMN CartItemSkel.parententry IS '';
COMMENT ON COLUMN CartItemSkel.article IS '';
COMMENT ON COLUMN CartItemSkel.**article_data_skey IS '';
COMMENT ON COLUMN CartItemSkel.project_data IS '';
COMMENT ON COLUMN CartItemSkel.quantity IS '';
COMMENT ON TABLE DiscountConditionSkel IS '';
COMMENT ON COLUMN DiscountConditionSkel.key IS '';
COMMENT ON COLUMN DiscountConditionSkel.code_type IS '';
COMMENT ON COLUMN DiscountConditionSkel.application_domain IS '';
COMMENT ON COLUMN DiscountConditionSkel.quantity_volume IS '';
COMMENT ON COLUMN DiscountConditionSkel.quantity_used IS '';
COMMENT ON COLUMN DiscountConditionSkel.individual_codes_amount IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_code IS '';
COMMENT ON COLUMN DiscountConditionSkel.individual_codes_prefix IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_minimum_order_value IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_date_start IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_date_end IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_language IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_country IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_minimum_quantity IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_customer_group IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_combinable_other_discount IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_combinable_low_price IS '';
COMMENT ON COLUMN DiscountConditionSkel.scope_article IS '';
COMMENT ON COLUMN DiscountConditionSkel.is_subcode IS '';
COMMENT ON COLUMN DiscountConditionSkel.parent_code IS '';
COMMENT ON TABLE DiscountSkel IS '';
COMMENT ON COLUMN DiscountSkel.key IS '';
COMMENT ON COLUMN DiscountSkel.name IS '';
COMMENT ON COLUMN DiscountSkel.description IS '';
COMMENT ON COLUMN DiscountSkel.discount_type IS '';
COMMENT ON COLUMN DiscountSkel.absolute IS '';
COMMENT ON COLUMN DiscountSkel.percentage IS '';
COMMENT ON COLUMN DiscountSkel.condition IS '';
COMMENT ON COLUMN DiscountSkel.condition_operator IS '';
COMMENT ON TABLE OrderSkel IS 'OrderSkel';
COMMENT ON COLUMN OrderSkel.key IS '';
COMMENT ON COLUMN OrderSkel.billing_address IS '';
COMMENT ON COLUMN OrderSkel.customer IS '';
COMMENT ON COLUMN OrderSkel.cart IS '';
COMMENT ON COLUMN OrderSkel.total IS '';
COMMENT ON COLUMN OrderSkel.order_uid IS '';
COMMENT ON COLUMN OrderSkel.payment_provider IS '';
COMMENT ON COLUMN OrderSkel.is_ordered IS '';
COMMENT ON COLUMN OrderSkel.is_paid IS '';
COMMENT ON COLUMN OrderSkel.is_rts IS '';
COMMENT ON COLUMN OrderSkel.state IS '';
COMMENT ON COLUMN OrderSkel.email IS '';
COMMENT ON COLUMN OrderSkel.project_data IS '';
