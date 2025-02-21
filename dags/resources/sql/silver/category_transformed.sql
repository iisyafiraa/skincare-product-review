-- Hapus constraint dan tabel terkait jika ada
ALTER TABLE silver.product_transformed DROP CONSTRAINT IF EXISTS product_transformed_category_id_fkey;

-- Hapus tabel category_transformed
DROP TABLE IF EXISTS silver.category_transformed CASCADE;

-- Buat ulang tabel category_transformed
CREATE TABLE IF NOT EXISTS silver.category_transformed (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(255),
    category_url TEXT
);
