-- Hapus tabel product_transformed
DROP TABLE IF EXISTS silver.product_transformed CASCADE;

-- Buat ulang tabel product_transformed dengan foreign key ke category_transformed
CREATE TABLE IF NOT EXISTS silver.product_transformed (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    brand_name VARCHAR(255),
    rating VARCHAR(50),
    reviews VARCHAR(50),
    price VARCHAR(50),
    product_url TEXT UNIQUE,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES silver.category_transformed(id) ON DELETE CASCADE
);
