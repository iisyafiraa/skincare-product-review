DROP TABLE IF EXISTS gold.fact_product_review;
 
CREATE TABLE gold.fact_product_review AS 
SELECT
    p.id AS product_id,
    r.id AS review_id,
    c.id AS category_id,
    r.rating,
    r.thumb,
    r.review_date
FROM silver.review_transformed r
JOIN silver.product_transformed p ON p.id = r.product_id
JOIN silver.category_transformed c ON p.category_id = c.id;