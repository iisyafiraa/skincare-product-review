DROP TABLE IF EXISTS gold.dim_product;
 
CREATE TABLE gold.dim_product AS 
SELECT
    id,
    product_name,
    brand_name,
    price,
    product_url 
FROM silver.product_transformed;