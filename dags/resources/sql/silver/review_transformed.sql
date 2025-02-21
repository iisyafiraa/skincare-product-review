-- Hapus tabel review_transformed
DROP TABLE IF EXISTS silver.review_transformed CASCADE;

-- Buat ulang tabel review_transformed dengan foreign key ke product_transformed
CREATE TABLE IF NOT EXISTS silver.review_transformed (
    id SERIAL PRIMARY KEY,
    product_id INT,
    reviewer_name VARCHAR(255),
    reviewer_age VARCHAR(50),
    rating INTEGER,
    thumb VARCHAR(50),
    review_text TEXT,
    skin_type VARCHAR(50),
    skin_tone VARCHAR(50),
    undertone VARCHAR(50),
    usage_period VARCHAR(100),
    purchase_point VARCHAR(100),
    platform VARCHAR(50),
    review_date VARCHAR(100),
    FOREIGN KEY (product_id) REFERENCES silver.product_transformed(id) ON DELETE CASCADE
);
