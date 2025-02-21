-- dim_category.sql
DROP TABLE IF EXISTS gold.dim_category;

CREATE TABLE gold.dim_category AS 
SELECT
    id,
    category_name,
    category_url 
FROM silver.category_transformed;
