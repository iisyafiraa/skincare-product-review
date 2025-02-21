DROP TABLE IF EXISTS gold.fact_product_review;
 
CREATE TABLE gold.fact_product_review AS 
SELECT
    p.id AS product_id,
    r.id AS review_id,
    r.rating,
    r.thumb,
    r.review_date
FROM silver.product_transformed p
JOIN silver.review_transformed r ON p.id = r.product_id;