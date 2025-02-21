import time
import logging
import psycopg2
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_driver():
    """Initializes the Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def scrape_categories(driver):
    """Scrapes category names and links."""
    url = "https://femaledaily.com/category/skincare"
    driver.get(url)

    category_buttons = driver.find_elements(By.CLASS_NAME, "jsx-4277795821.category-landing-list")
    list_of_category = []
    list_of_href = []

    for category in category_buttons:
        category_columns = category.find_elements(By.CLASS_NAME, "jsx-4277795821.category-landing-column")
        for column in category_columns:
            category_links = column.find_elements(By.TAG_NAME, "a")
            for cat in category_links:
                list_of_category.append(cat.text)
                list_of_href.append(cat.get_attribute('href'))

    logging.info(f"Found {len(list_of_category)} categories.")
    return list_of_category, list_of_href

def scrape_products(driver, list_of_href):
    """Scrapes product details including price and review information."""
    list_of_product = []
    list_product_href = []

    for link in list_of_href:
        page = 1
        while page <= 1:
            driver.get(f"{link}?page={page}")
            time.sleep(3)

            product_cards = driver.find_elements(By.CLASS_NAME, "jsx-3793288165.product-card")

            for card in product_cards:
                product_url = card.get_attribute("href")
                brand_name = card.find_element(By.XPATH, './/p[contains(@class,"fd-body-md-bold")]').text
                product_name = card.find_element(By.XPATH, './/p[contains(@class,"fd-body-md-regular")]').text
                rating = card.find_element(By.XPATH, './/span[contains(@class,"fd-body-sm-regular")]').text
                reviews = card.find_element(By.XPATH, './/span[contains(@class,"fd-body-sm-regular grey")]').text

                category_url = link

                list_of_product.append({
                    "brand_name": brand_name,
                    "product_name": product_name,
                    "rating": rating,
                    "reviews": reviews,
                    "product_url": product_url,
                    "category_url": category_url
                })

            try:
                load_more_button = driver.find_element(By.CLASS_NAME, "btn-load-more")
                load_more_button.click()
                time.sleep(3)
            except:
                logging.warning(f"No 'Load More' button on page {page} for category {link}.")
                break

            page += 1

    # Fetch prices after scraping products
    for index, product in enumerate(list_of_product):
        driver.get(product["product_url"])
        time.sleep(3)
        prices = driver.find_elements(By.CLASS_NAME, "product-price")
        product_price = prices[0].text if prices else "Price not available"
        list_of_product[index]["price"] = product_price

    logging.info(f"Scraped {len(list_of_product)} products.")
    return list_of_product

def scrape_reviews(driver, list_product_href, max_page=1):
    """Scrapes reviews for each product."""
    list_of_review = []

    for link in list_product_href:
        page = 1
        while page <= max_page:
            product_url_with_page = f"{link['product_url']}?cat=&cat_id=0&age_range=&skin_type=&skin_tone=&skin_undertone=&hair_texture=&hair_type=&order=newest&page={page}"
            driver.get(product_url_with_page)
            time.sleep(3)

            try:
                reviews = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "review-card"))
                )

                if reviews:
                    for review in reviews:
                        reviewer_url = review.find_element(By.CLASS_NAME, "card-profile-wrapper").get_attribute("href")
                        reviewer_name = review.find_element(By.CLASS_NAME, "profile-username").text
                        reviewer_age = review.find_element(By.CLASS_NAME, "profile-age").text

                        try:
                            reviewer_description = review.find_element(By.CLASS_NAME, "profile-description").text
                        except:
                            reviewer_description = None

                        rating_elements = review.find_elements(By.CLASS_NAME, "icon-ic_big_star_full")
                        rating = len(rating_elements)

                        try:
                            thumb_element = review.find_element(By.CLASS_NAME, "recommend")
                            thumb = "thumb_up" if "recommends" in thumb_element.text else "thumb_down"
                        except:
                            thumb = None

                        review_text = review.find_element(By.CLASS_NAME, "text-content").text
                        usage_period = review.find_element(By.CSS_SELECTOR, ".information-wrapper p:nth-child(1) b").text
                        purchase_point = review.find_element(By.CSS_SELECTOR, ".information-wrapper p:nth-child(2) b").text
                        review_date = review.find_element(By.CLASS_NAME, "review-date").text

                        list_of_review.append({
                            "product_url": link['product_url'],
                            "reviewer_url": reviewer_url,
                            "reviewer_name": reviewer_name,
                            "reviewer_age": reviewer_age,
                            "reviewer_description": reviewer_description,
                            "rating": rating,
                            "thumb": thumb,
                            "review_text": review_text,
                            "usage_period": usage_period,
                            "purchase_point": purchase_point,
                            "review_date": review_date
                        })

            except Exception as e:
                logging.error(f"Error scraping reviews on page {page}: {e}")
                break

            page += 1
            if page > max_page:
                logging.info(f"Reached last page for product {link['product_url']}.")
                break

    logging.info(f"Scraped {len(list_of_review)} reviews.")
    return list_of_review

def connect_to_db():
    """Create connection to database PostgreSQL."""
    return psycopg2.connect(
        host="dibimbing-dataeng-postgres",
        dbname="postgres_db", 
        user="user", 
        password="password",
        port="5432"
    )

def insert_category_data(categories, connection):
    cursor = connection.cursor()
    insert_query = """
        INSERT INTO bronze.category (category_name, category_url, created_at)
        VALUES (%s, %s, %s) RETURNING id
    """

    current_time = datetime.now()

    for category_name, category_url in zip(categories[0], categories[1]):
        cursor.execute(insert_query, (category_name, category_url, current_time))
        category_id = cursor.fetchone()[0]
        connection.commit()
    cursor.close()

def insert_product_data(products, connection):
    cursor = connection.cursor()
    insert_query = """
        INSERT INTO bronze.product (product_name, brand_name, rating, reviews, price, product_url, category_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """

    current_time = datetime.now()

    print("Products data: ", products)

    for product in products:
        cursor.execute("SELECT id FROM bronze.product WHERE product_url = %s", (product['product_url'],))
        existing_product = cursor.fetchone()

        if existing_product:
            # Jika produk sudah ada, kita skip produk ini (tidak melakukan INSERT)
            print(f"Product with URL {product['product_url']} already exists, skipping.")
            continue  # Melewati produk yang sudah ada

        cursor.execute("SELECT id FROM bronze.category WHERE category_url = %s", (product['category_url'],))
        category_result = cursor.fetchone()[0]

        if category_result is None:
            # Jika category_url tidak ditemukan, lanjutkan ke produk berikutnya
            print(f"Category not found for product: {product['product_name']}")
            continue  # Lewati produk ini

        if isinstance(category_result, tuple):
            category_id = category_result[0]
        else:
            category_id = category_result

        cursor.execute(insert_query, (
            product['product_name'], 
            product['brand_name'], 
            product['rating'], 
            product['reviews'], 
            product['price'], 
            product['product_url'],
            category_id,
            current_time
        ))

        product_id = cursor.fetchone()[0]
        connection.commit()
    cursor.close()

def insert_review_data(reviews, connection):
    cursor = connection.cursor()
    insert_query = """
        INSERT INTO bronze.review (
            product_id, reviewer_name, reviewer_age, reviewer_description, 
            rating, thumb, review_text, usage_period, purchase_point, review_date, created_at
        ) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    current_time = datetime.now()

    for review in reviews:
        logging.info(f"Checking if product URL exists in database: {review['product_url']}")

        cursor.execute("SELECT id FROM bronze.product WHERE product_url = %s", (review['product_url'],))
        result = cursor.fetchone()

        if result is None:
            logging.warning(f"Product URL {review['product_url']} not found in the database.")
            continue  # Lewati review ini jika produk tidak ditemukan

        product_id = result[0]

        cursor.execute(insert_query, (
            product_id, 
            review['reviewer_name'], 
            review['reviewer_age'], 
            review['reviewer_description'],
            review['rating'], 
            review['thumb'], 
            review['review_text'], 
            review['usage_period'], 
            review['purchase_point'], 
            review['review_date'],
            current_time
        ))
        connection.commit()
        logging.info(f"Number of reviews to insert: {len(reviews)}")
    cursor.close()

def main():
    """Main function to run the scraping process."""
    driver = initialize_driver()

    try:
        list_of_category, list_of_href = scrape_categories(driver)
        list_of_product = scrape_products(driver, list_of_href)
        list_of_review = scrape_reviews(driver, list_of_product)

        connection = connect_to_db()

        insert_category_data((list_of_category, list_of_href), connection)
        insert_product_data(list_of_product, connection)
        insert_review_data(list_of_review, connection)

        connection.close()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
