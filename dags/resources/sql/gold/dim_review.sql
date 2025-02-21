DROP TABLE IF EXISTS gold.dim_review;
 
CREATE TABLE gold.dim_review AS 
SELECT
    id,
    review_text,
    rating,
    review_date
FROM silver.review_transformed;