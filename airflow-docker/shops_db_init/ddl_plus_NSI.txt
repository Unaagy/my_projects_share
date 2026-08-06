CREATE SCHEMA bd_shops;

CREATE TABLE bd_shops.shops (
	id int8 NOT NULL,
	market_name varchar(50) NULL,
	square float4 NULL,
	city varchar(50) NULL,
	CONSTRAINT shops_pk PRIMARY KEY (id)
);


CREATE TABLE bd_shops.market_size (
	size_name varchar(50) NOT NULL,
	min_square int4 NULL,
	CONSTRAINT market_size_pk PRIMARY KEY (size_name)
);

INSERT INTO bd_shops.market_size (size_name,min_square) VALUES
	 ('Ларек',0),
	 ('Минимаркет',50),
	 ('Магазин у дома',250),
	 ('Супермаркет',1000),
	 ('Гипермаркет',3000);
	 

CREATE TABLE bd_shops.market_board (
	size_name varchar(50) NOT NULL,
	count_employers int4 NULL,
	base_cost money NULL,
	CONSTRAINT market_board_pk PRIMARY KEY (size_name)
);

INSERT INTO bd_shops.market_board (size_name,count_employers,base_cost) VALUES
	 ('Ларек',1,15000.0),
	 ('Минимаркет',5,20000.0),
	 ('Магазин у дома',10,22000.0),
	 ('Супермаркет',40,30000.0),
	 ('Гипермаркет',100,45000.0);
	 

CREATE TABLE bd_shops.visits (
	id int8 NOT NULL,
	product_id int8 NULL,
	visit_date date NULL,
	line_size float8 NULL,
	employer_id int8 NULL,
	shop_id int8 NULL,
	CONSTRAINT visits_pk PRIMARY KEY (id)
);


CREATE TABLE bd_shops.employers (
	id int8 NOT NULL,
	"Name" varchar(100) NOT NULL,
	shop_id int8 NULL,
	salary float8 NULL,
	years_exp int4 NULL,
	departament varchar(50) NULL,
	CONSTRAINT employers_pk PRIMARY KEY (id)
);


CREATE TABLE bd_shops.vendors (
	id int8 NOT NULL,
	"name" varchar(100) NULL,
	country varchar(50) NULL,
	employers_count int4 NULL,
	CONSTRAINT vendors_pk PRIMARY KEY (id)
);

CREATE TABLE bd_shops.product (
	id int8 NOT NULL,
	product_name varchar(50) NULL,
	shop_id int8 NULL,
	revizion_date date NULL,
	count int8 NULL,
	price_sale_out float8 NULL,
	base_size float4 NULL,
	CONSTRAINT product_pk PRIMARY KEY (id)
);

CREATE TABLE bd_shops.product_deliv (
	product_id int8 NOT NULL,
	vendor_id int8 NOT NULL,
	shop_id int8 NOT NULL,
	delivery_day date NOT NULL,
	price_sale_in float8 NULL,
	count int8 NULL,
	CONSTRAINT product_deliv_pk PRIMARY KEY (product_id, vendor_id, shop_id, delivery_day)
);



	 

