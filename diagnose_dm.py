"""Diagnostic: check what the headless browser sees on Instagram/Facebook DM pages."""
import sys, os, time, json
sys.path.insert(0, r"d:\NEXUS")

from config import NEXUS_CONFIG, DATA_DIR

def diagnose():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
    except ImportError:
        print("ERROR: selenium not installed")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)

    driver.implicitly_wait(5)
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"})
    except:
        pass

    cfg = NEXUS_CONFIG.social_media

    print("\n" + "="*60)
    print("INSTAGRAM DM DIAGNOSIS")
    print("="*60)
    print(f"Instagram username: {cfg.instagram_username}")
    print(f"Instagram password set: {'yes' if cfg.instagram_password else 'no'}")

    # Login
    print("Attempting login...")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(4)
    
    # Dismiss cookie dialogs
    for btn_text in ['Allow', 'Accept', 'Allow all cookies']:
        try:
            cookie_btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{btn_text}')]")
            cookie_btn.click()
            time.sleep(1)
            break
        except:
            pass
    
    logged_in = False
    try:
        user_input = driver.find_element(By.CSS_SELECTOR, 'input[name="username"]')
        user_input.send_keys(cfg.instagram_username)
        time.sleep(0.5)
        pass_input = driver.find_element(By.CSS_SELECTOR, 'input[name="password"]')
        pass_input.send_keys(cfg.instagram_password)
        time.sleep(0.5)
        pass_input.submit()
        time.sleep(6)
        
        # Dismiss popups
        for _ in range(3):
            try:
                nn = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                nn.click()
                time.sleep(1)
            except:
                pass
        
        url = driver.current_url.lower()
        print(f"After login, URL: {url}")
        if "login" not in url and "challenge" not in url:
            logged_in = True
            print("LOGIN SUCCESSFUL!")
        else:
            print(f"LOGIN FAILED. URL: {url}")
    except Exception as e:
        print(f"Login error: {e}")

    if logged_in:
        print("\nNavigating to Instagram DMs...")
        driver.get("https://www.instagram.com/direct/inbox/")
        time.sleep(6)

        # Dismiss popups
        for _ in range(2):
            try:
                nn = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                nn.click()
                time.sleep(1)
            except:
                pass

        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Take screenshot
        ss_path = os.path.join(str(DATA_DIR), "insta_dm_debug.png")
        driver.save_screenshot(ss_path)
        print(f"Screenshot saved: {ss_path}")

        # Try various selectors
        selectors_to_try = [
            ('role=listitem', '//div[@role="listitem"]'),
            ('href /direct/t/', '//a[contains(@href,"/direct/t/")]'),
            ('role=row', '//div[@role="row"]'),
            ('role=list children', '//div[@role="list"]//div'),
            ('role=button in main', '//main//div[@role="button"]'),
            ('any a with /direct/', '//a[contains(@href,"/direct/")]'),
            ('all links in page', '//a[@href]'),
            ('textbox or textarea', '//textarea | //div[@role="textbox"]'),
            ('all divs with role', '//div[@role]'),
        ]

        print("\n--- Trying selectors ---")
        for name, xpath in selectors_to_try:
            try:
                els = driver.find_elements(By.XPATH, xpath)
                texts = []
                for e in els[:5]:
                    t = e.text[:50] if e.text else ""
                    if t.strip():
                        texts.append(t.replace("\n", " | "))
                print(f"  {name}: {len(els)} found")
                if texts:
                    for t in texts:
                        print(f"    -> {t}")
            except Exception as e:
                print(f"  {name}: ERROR {e}")

        # Page source analysis
        src = driver.page_source
        print(f"\nPage source length: {len(src)}")
        for pattern in ["/direct/t/", "inbox", "message", "Message", "chat", "conversation"]:
            count = src.count(pattern)
            if count > 0:
                print(f"  '{pattern}' appears {count} times")
                if pattern == "/direct/t/":
                    idx = src.index(pattern)
                    print(f"    Context: ...{src[max(0,idx-80):idx+80]}...")

        # Dump ALL elements with text  
        print("\n--- All visible text elements ---")
        try:
            all_els = driver.find_elements(By.XPATH, '//*[string-length(normalize-space(text())) > 1]')
            for el in all_els[:30]:
                tag = el.tag_name
                text = el.text[:60].replace("\n", " | ") if el.text else ""
                role = el.get_attribute("role") or ""
                href = el.get_attribute("href") or ""
                if text.strip() and tag not in ('script', 'style', 'noscript'):
                    extra = ""
                    if role:
                        extra += f" role={role}"
                    if href:
                        extra += f" href={href[:40]}"
                    print(f"  <{tag}{extra}> {text}")
        except Exception as e:
            print(f"  Error dumping elements: {e}")

    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)
    driver.quit()

if __name__ == "__main__":
    diagnose()
