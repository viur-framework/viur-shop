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
 zip VARCHAR(10)
);


CREATE TABLE ShippingSkel (
 key VARCHAR(64) NOT NULL,
 name VARCHAR(10) NOT NULL,
 Kundenkommentar TEXT,
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
 value FLOAT(10)
);

ALTER TABLE VatSkel ADD CONSTRAINT PK_VatSkel PRIMARY KEY (key);


CREATE TABLE AbstractArticleSkel (
 key VARCHAR(64) NOT NULL,
 shop_name VARCHAR(255),
 shop_description TEXT,
 Verkaufspreis FLOAT(10),
 UVP FLOAT(10),
 shop_availability VARCHAR(255),
 shop_listed BIT(1),
 Produktbild VARCHAR(255),
 Artikelnummer VARCHAR(10),
 Steuersatz VARCHAR(64) NOT NULL,
 Versandkosten VARCHAR(64),
 Elektro G BIT(1),
 shop_is_low_price BIT(1) NOT NULL
);

ALTER TABLE AbstractArticleSkel ADD CONSTRAINT PK_AbstractArticleSkel PRIMARY KEY (key);


CREATE TABLE CartItemSkel (
 key VARCHAR(64) NOT NULL,
 parententry VARCHAR(64) NOT NULL,
 article VARCHAR(64) NOT NULL,
 **article_data_skey VARCHAR(255),
 project_data JSON NOT NULL
);

ALTER TABLE CartItemSkel ADD CONSTRAINT PK_CartItemSkel PRIMARY KEY (key);


CREATE TABLE DiscountConditionSkel (
 key VARCHAR(64) NOT NULL,
 code_type VARCHAR(255),
 application_domain VARCHAR(255),
 quantity_volume INT,
 quantity_used INT,
 individual_codes_amount INT,
 code VARCHAR(10),
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
 type VARCHAR(255),
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
 Bestellnummer VARCHAR(64) NOT NULL,
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


ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_0 FOREIGN KEY (Produktbild) REFERENCES File (key);
ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_1 FOREIGN KEY (Steuersatz) REFERENCES VatSkel (key);
ALTER TABLE AbstractArticleSkel ADD CONSTRAINT FK_AbstractArticleSkel_2 FOREIGN KEY (Versandkosten) REFERENCES ShippingConfigSkel (key);


ALTER TABLE CartItemSkel ADD CONSTRAINT FK_CartItemSkel_0 FOREIGN KEY (parententry) REFERENCES CartNodeSkel (key);
ALTER TABLE CartItemSkel ADD CONSTRAINT FK_CartItemSkel_1 FOREIGN KEY (article) REFERENCES AbstractArticleSkel (key);


ALTER TABLE DiscountConditionSkel ADD CONSTRAINT FK_DiscountConditionSkel_0 FOREIGN KEY (scope_article) REFERENCES AbstractArticleSkel (key);
ALTER TABLE DiscountConditionSkel ADD CONSTRAINT FK_DiscountConditionSkel_1 FOREIGN KEY (parent_code) REFERENCES DiscountConditionSkel (key);


ALTER TABLE DiscountSkel ADD CONSTRAINT FK_DiscountSkel_0 FOREIGN KEY (condition) REFERENCES DiscountConditionSkel (key);


ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_0 FOREIGN KEY (billing_address) REFERENCES AddressSkel (key);
ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_1 FOREIGN KEY (customer) REFERENCES UserSkel (key);
ALTER TABLE OrderSkel ADD CONSTRAINT FK_OrderSkel_2 FOREIGN KEY (cart) REFERENCES CartNodeSkel (key);


