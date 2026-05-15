-- Pre-computed aggregates for fast analytical queries.
-- Run once after schema + seed. Refresh with REFRESH MATERIALIZED VIEW <name>;

-- Sales summary per region
CREATE MATERIALIZED VIEW mv_region_sales AS
SELECT
    r.region_id,
    r.name            AS region_name,
    r.country,
    r.continent,
    COUNT(DISTINCT o.order_id)    AS num_orders,
    COUNT(DISTINCT o.customer_id) AS num_customers,
    SUM(o.total_amount)           AS total_sales,
    AVG(o.total_amount)           AS avg_order_value,
    SUM(o.discount_amount)        AS total_discounts
FROM regions r
LEFT JOIN employees e  ON e.region_id   = r.region_id
LEFT JOIN orders o     ON o.employee_id = e.employee_id
GROUP BY r.region_id, r.name, r.country, r.continent;

-- Sales summary per product category
CREATE MATERIALIZED VIEW mv_category_sales AS
SELECT
    c.category_id,
    c.name              AS category_name,
    COUNT(DISTINCT oi.order_id) AS num_orders,
    SUM(oi.quantity)            AS total_units_sold,
    SUM(oi.line_total)          AS total_revenue,
    AVG(oi.unit_price)          AS avg_unit_price
FROM categories c
LEFT JOIN products   p  ON p.category_id  = c.category_id
LEFT JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY c.category_id, c.name;

-- Monthly sales trend
CREATE MATERIALIZED VIEW mv_monthly_sales AS
SELECT
    DATE_TRUNC('month', o.order_date)::date AS month,
    COUNT(DISTINCT o.order_id)              AS num_orders,
    COUNT(DISTINCT o.customer_id)           AS num_customers,
    SUM(o.total_amount)                     AS total_sales,
    AVG(o.total_amount)                     AS avg_order_value
FROM orders o
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month;

-- Sales per region per month (combined dimension)
CREATE MATERIALIZED VIEW mv_region_monthly_sales AS
SELECT
    r.region_id,
    r.name                                  AS region_name,
    DATE_TRUNC('month', o.order_date)::date AS month,
    COUNT(DISTINCT o.order_id)              AS num_orders,
    SUM(o.total_amount)                     AS total_sales,
    AVG(o.total_amount)                     AS avg_order_value
FROM regions r
LEFT JOIN employees e ON e.region_id   = r.region_id
LEFT JOIN orders o    ON o.employee_id = e.employee_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY r.region_id, r.name, DATE_TRUNC('month', o.order_date)
ORDER BY r.name, month;

-- Sales by payment method
CREATE MATERIALIZED VIEW mv_payment_method_sales AS
SELECT
    p.payment_method,
    COUNT(p.payment_id) AS num_payments,
    SUM(p.amount)       AS total_amount,
    AVG(p.amount)       AS avg_amount
FROM payments p
WHERE p.status = 'completed'
GROUP BY p.payment_method;
