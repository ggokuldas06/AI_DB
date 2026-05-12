DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS regions CASCADE;

CREATE TABLE regions (
    region_id   SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    code        VARCHAR(10)  UNIQUE NOT NULL,
    continent   VARCHAR(50)  NOT NULL,
    timezone    VARCHAR(60)
);

CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    first_name  VARCHAR(80)  NOT NULL,
    last_name   VARCHAR(80)  NOT NULL,
    email       VARCHAR(200) UNIQUE NOT NULL,
    phone       VARCHAR(30),
    hire_date   DATE         NOT NULL,
    job_title   VARCHAR(100) NOT NULL,
    department  VARCHAR(80),
    salary      NUMERIC(12,2) NOT NULL CHECK (salary > 0),
    commission_pct NUMERIC(5,2) DEFAULT 0 CHECK (commission_pct BETWEEN 0 AND 100),
    manager_id  INT REFERENCES employees(employee_id),
    region_id   INT REFERENCES regions(region_id),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE categories (
    category_id        SERIAL PRIMARY KEY,
    name               VARCHAR(120) NOT NULL,
    description        TEXT,
    parent_category_id INT REFERENCES categories(category_id),
    display_order      INT DEFAULT 0,
    is_active          BOOLEAN DEFAULT TRUE
);

CREATE TABLE suppliers (
    supplier_id    SERIAL PRIMARY KEY,
    company_name   VARCHAR(200) NOT NULL,
    contact_name   VARCHAR(160),
    contact_email  VARCHAR(200),
    contact_phone  VARCHAR(30),
    website        VARCHAR(200),
    address        TEXT,
    city           VARCHAR(100),
    country        VARCHAR(100) NOT NULL,
    payment_terms  VARCHAR(80),
    lead_time_days INT CHECK (lead_time_days >= 0),
    rating         NUMERIC(3,2) CHECK (rating BETWEEN 1.0 AND 5.0),
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE customers (
    customer_id    SERIAL PRIMARY KEY,
    first_name     VARCHAR(80) NOT NULL,
    last_name      VARCHAR(80) NOT NULL,
    email          VARCHAR(200) UNIQUE NOT NULL,
    phone          VARCHAR(30),
    company_name   VARCHAR(200),
    industry       VARCHAR(100),
    customer_since DATE NOT NULL,
    credit_limit   NUMERIC(12,2) DEFAULT 5000,
    total_spent    NUMERIC(14,2) DEFAULT 0,
    status         VARCHAR(20) NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active','inactive','vip','suspended','prospect')),
    assigned_rep   INT REFERENCES employees(employee_id),
    notes          TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE addresses (
    address_id    SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    address_type  VARCHAR(20) NOT NULL DEFAULT 'shipping'
                  CHECK (address_type IN ('billing','shipping','both')),
    street_line1  VARCHAR(200) NOT NULL,
    street_line2  VARCHAR(200),
    city          VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    postal_code   VARCHAR(20),
    country       VARCHAR(100) NOT NULL DEFAULT 'USA',
    is_default    BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    sku             VARCHAR(60) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category_id     INT REFERENCES categories(category_id),
    supplier_id     INT REFERENCES suppliers(supplier_id),
    unit_price      NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    cost_price      NUMERIC(12,2) CHECK (cost_price >= 0),
    stock_quantity  INT NOT NULL DEFAULT 0,
    reorder_level   INT DEFAULT 10,
    weight_kg       NUMERIC(8,3),
    dimensions_cm   VARCHAR(60),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE orders (
    order_id            SERIAL PRIMARY KEY,
    customer_id         INT NOT NULL REFERENCES customers(customer_id),
    employee_id         INT REFERENCES employees(employee_id),
    order_date          TIMESTAMP NOT NULL DEFAULT NOW(),
    required_date       DATE,
    shipped_date        DATE,
    status              VARCHAR(30) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','confirmed','processing',
                                          'shipped','delivered','cancelled','refunded')),
    shipping_address_id INT REFERENCES addresses(address_id),
    billing_address_id  INT REFERENCES addresses(address_id),
    subtotal            NUMERIC(14,2) DEFAULT 0,
    discount_amount     NUMERIC(12,2) DEFAULT 0,
    tax_amount          NUMERIC(12,2) DEFAULT 0,
    shipping_cost       NUMERIC(10,2) DEFAULT 0,
    total_amount        NUMERIC(14,2) DEFAULT 0,
    currency            VARCHAR(5) DEFAULT 'USD',
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id     INT NOT NULL REFERENCES products(product_id),
    quantity       INT NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(12,2) NOT NULL,
    discount_pct   NUMERIC(5,2) DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    line_total     NUMERIC(14,2) GENERATED ALWAYS AS
                     (quantity * unit_price * (1 - discount_pct / 100)) STORED
);

CREATE TABLE payments (
    payment_id      SERIAL PRIMARY KEY,
    order_id        INT NOT NULL REFERENCES orders(order_id),
    payment_date    TIMESTAMP NOT NULL DEFAULT NOW(),
    amount          NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_method  VARCHAR(50) NOT NULL
                    CHECK (payment_method IN ('credit_card','debit_card',
                                              'bank_transfer','paypal','check','cash','crypto')),
    transaction_ref VARCHAR(120),
    gateway         VARCHAR(80),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','completed','failed','refunded','disputed')),
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_employees_region    ON employees(region_id);
CREATE INDEX idx_employees_manager   ON employees(manager_id);
CREATE INDEX idx_customers_status    ON customers(status);
CREATE INDEX idx_customers_rep       ON customers(assigned_rep);
CREATE INDEX idx_addresses_customer  ON addresses(customer_id);
CREATE INDEX idx_products_category   ON products(category_id);
CREATE INDEX idx_products_supplier   ON products(supplier_id);
CREATE INDEX idx_products_sku        ON products(sku);
CREATE INDEX idx_orders_customer     ON orders(customer_id);
CREATE INDEX idx_orders_employee     ON orders(employee_id);
CREATE INDEX idx_orders_date         ON orders(order_date);
CREATE INDEX idx_orders_status       ON orders(status);
CREATE INDEX idx_order_items_order   ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_payments_order      ON payments(order_id);
CREATE INDEX idx_payments_status     ON payments(status);
