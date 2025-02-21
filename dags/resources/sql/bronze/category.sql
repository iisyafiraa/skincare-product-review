ALTER TABLE bronze.product DROP CONSTRAINT IF EXISTS product_category_id_fkey;

DROP TABLE IF EXISTS bronze.category;

CREATE TABLE IF NOT EXISTS bronze.category (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(255),
    category_url TEXT UNIQUE,
    created_at TIMESTAMP
);
