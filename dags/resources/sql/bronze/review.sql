CREATE TABLE IF NOT EXISTS bronze.review (
    id SERIAL PRIMARY KEY,
    product_id INT,
    reviewer_name VARCHAR(255),
    reviewer_age VARCHAR(50),
    reviewer_description TEXT,
    rating INTEGER,
    thumb VARCHAR(50),
    review_text TEXT,
    usage_period VARCHAR(100),
    purchase_point VARCHAR(100),
    review_date TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES bronze.product(id) ON DELETE CASCADE
);
