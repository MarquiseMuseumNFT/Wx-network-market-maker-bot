import time
import random
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Auto-install ChromeDriver
chromedriver_autoinstaller.install()

WX_URL = "https://wx.network/trading/spot/9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

USER_EMAIL = "your_email_here"
USER_PASSWORD = "your_password_here"

TRADE_AMOUNT = 100
SPREAD = 0.01

# ===== Selenium headless setup =====
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

def login():
    driver.get(WX_URL)
    time.sleep(5)

    # Example login flow — must adjust selectors after testing
    login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
    login_btn.click()
    time.sleep(2)

    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys(USER_EMAIL)

    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(USER_PASSWORD)
    password_input.send_keys(Keys.RETURN)

    print("Logged in successfully")
    time.sleep(10)

def place_order(order_type, price, amount):
    try:
        price_box = driver.find_element(By.XPATH, "//input[@name='price']")
        amount_box = driver.find_element(By.XPATH, "//input[@name='amount']")
        
        price_box.clear()
        price_box.send_keys(str(price))
        amount_box.clear()
        amount_box.send_keys(str(amount))

        if order_type == "buy":
            btn = driver.find_element(By.XPATH, "//button[contains(text(),'Buy')]")
        else:
            btn = driver.find_element(By.XPATH, "//button[contains(text(),'Sell')]")

        btn.click()
        print(f"Placed {order_type} order: {amount} @ {price}")
    except Exception as e:
        print(f"Error placing order: {e}")

def market_make():
    while True:
        try:
            price_element = driver.find_element(By.XPATH, "//div[@class='price']")
            current_price = float(price_element.text)
        except:
            current_price = 1.0
            print("Could not fetch price, using fallback")

        buy_price = round(current_price * (1 - SPREAD), 6)
        sell_price = round(current_price * (1 + SPREAD), 6)

        place_order("buy", buy_price, TRADE_AMOUNT)
        time.sleep(2)
        place_order("sell", sell_price, TRADE_AMOUNT)

        time.sleep(60)

if __name__ == "__main__":
    login()
    market_make()
