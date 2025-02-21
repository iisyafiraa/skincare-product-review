ALTER TABLE bronze.review DROP CONSTRAINT IF EXISTS review_product_id_fkey;

DROP TABLE IF EXISTS bronze.product;

CREATE TABLE IF NOT EXISTS bronze.product (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    brand_name VARCHAR(255),
    rating VARCHAR(50),
    reviews VARCHAR(50),
    price VARCHAR(50),
    product_url TEXT UNIQUE,
    category_id INT,
    created_at TIMESTAMP
    FOREIGN KEY (category_id) REFERENCES bronze.category(id) ON DELETE CASCADE
);