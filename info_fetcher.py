 # --- START OF COMPLETE SCRIPT (Scrape Details from Pre-collected Links - Updated Address Logic) ---

print("--- Starting Google Maps Detail Scraper from Links Script ---")

# --- Installation Steps ---
# Update apt-get and install Google Chrome and dependencies for virtual display
print("\n--- Step 1: Installing System Dependencies ---")
print("Updating apt-get and installing wget, xvfb, and attempting Google Chrome setup...")
try:
    # Update apt-get
    !apt-get update

    # Install wget and xvfb (for virtual display)
    !apt-get install -y wget xvfb
    print("System dependencies (wget, xvfb) installation/check complete.")

    # Check if Chrome is already installed and is the correct architecture
    chrome_version_check = !google-chrome --version 2>&1
    print(f"Google Chrome version check result: {chrome_version_check}")
    chrome_installed_correctly = False
    if chrome_version_check and "Google Chrome" in chrome_version_check[0]:
        print("Google Chrome seems to be installed.")
        chrome_installed_correctly = True
    else:
        print("Google Chrome not detected or not in expected path. Proceeding with download and install.")

    if not chrome_installed_correctly:
        # Download Google Chrome .deb package
        print("Downloading Google Chrome .deb package...")
        # Using -O to specify the output filename to avoid .1 suffix
        !wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O google-chrome-stable_current_amd64.deb
        print("Google Chrome package download complete.")

        # Install the downloaded package
        print("Installing Google Chrome...")
        !dpkg -i google-chrome-stable_current_amd64.deb
        print("dpkg installation command executed.")

        # Fix broken dependencies - crucial for Chrome installation to complete
        print("Fixing broken dependencies...")
        !apt-get install -f -y
        print("Dependency fix command executed.")
        print("Google Chrome installation attempted.")
    else:
         print("Skipping Google Chrome download/install as it appears to be present.")

    print("Step 1: System dependencies and Google Chrome setup complete.")

except Exception as e:
    print(f"--- ERROR during Step 1: System Dependency or Chrome Installation Failed ---")
    print(f"Error details: {e}")
    print("Please check the output above for specific installation errors.")
    # Continue to Python package installation


# Install Python packages
print("\n--- Step 2: Installing Python Packages ---")
print("Installing Python packages (selenium, beautifulsoup4, pandas, requests, webdriver-manager, pyvirtualdisplay)...")
try:
    !pip install selenium beautifulsoup4 pandas requests webdriver-manager pyvirtualdisplay
    print("Step 2: Python package installation complete.")
except Exception as e:
    print(f"--- ERROR during Step 2: Python Package Installation Failed ---")
    print(f"Error details: {e}")
    print("Please ensure you have network access and pip is working correctly.")
    # Installation failure here will likely cause import errors later.


# --- Import libraries ---
print("\n--- Step 3: Importing Libraries ---")
try:
    import time
    import re
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from google.colab import files # Import for Colab download
    import urllib.parse
    from pyvirtualdisplay import Display # Import Display
    print("Step 3: Libraries imported successfully.")
except Exception as e:
    print(f"--- ERROR during Step 3: Library Import Failed ---")
    print(f"Error details: {e}")
    print("Please ensure all necessary Python packages were installed correctly in Step 2.")
    # If imports fail, the script cannot proceed.
    # Consider adding a sys.exit() here in a non-notebook environment.


# Function to set up the Chrome driver with Virtual Display
def setup_driver():
    print("\n--- Step 4: Setting up Selenium Driver and Virtual Display ---")
    display = None
    driver = None
    try:
        print("Starting virtual display...")
        display = Display(visible=0, size=(1280, 720)) # Use a common screen size
        display.start()
        print("Virtual display started.")

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Use a common user agent string to appear more like a real browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Helps avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Helps avoid detection
        chrome_options.add_experimental_option('useAutomationExtension', False) # Helps avoid detection
        chrome_options.add_argument("--disable-extensions") # Disable extensions
        # Point binary location to the installed chrome executable
        chrome_options.binary_location = "/usr/bin/google-chrome"
         # Add argument to allow remote origin - sometimes necessary in Colab/headless
        chrome_options.add_argument("--remote-allow-origins=*")
         # Add argument to ignore certificate errors if needed (use with caution)
        # chrome_options.add_argument('--ignore-certificate-errors')
        # Added arguments for stability in headless mode - attempt to fix crash
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-zygote")


        print("Installing/locating chrome driver executable and initializing Selenium...")
        # Use ChromeDriverManager to automatically get the correct driver version
        # This also downloads the driver if not cached
        try:
             service = Service(ChromeDriverManager().install())
             driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as driver_e:
             print(f"--- ERROR: Chrome Driver Manager failed to install/locate driver ---")
             print(f"Error details: {driver_e}")
             print("Attempting to use a static path if available (less reliable)...")
             # Fallback attempt - might not work depending on environment
             try:
                 service = Service("/usr/local/bin/chromedriver") # Common path
                 driver = webdriver.Chrome(service=service, options=chrome_options)
             except Exception as fallback_e:
                 print(f"--- ERROR: Fallback driver path also failed ---")
                 print(f"Error details: {fallback_e}")
                 driver = None # Ensure driver is None if both fail


        if driver:
            print("Step 4: Driver setup successful.")
            # Optional: Set implicit wait (can be combined with explicit waits)
            driver.implicit_wait = 5 # Wait up to 5 seconds for elements if not found immediately
        else:
            print("Step 4: Driver setup failed.")


        return driver, display

    except Exception as e:
        print(f"--- ERROR during Step 4: Driver or Virtual Display Setup Failed ---")
        print(f"Error details: {e}")
        print("This could be due to Chrome installation issues, incompatible driver versions, or environment problems.")
        if display:
            try:
                display.stop()
            except:
                pass
        return None, None


# --- FUNCTION TO SCRAPE DATA FROM A SINGLE BUSINESS DETAIL PAGE ---
# This function navigates to a given URL and scrapes specific information from the resulting detail page/panel.
def scrape_detail_page_from_link(driver, detail_url):
    print(f"--> Navigating to business detail URL: {detail_url}")
    data_item = {
        'Google Maps Link': detail_url, # Store the URL we navigated to
        'Name': 'N/A',
        'Address': 'N/A', # Full address from detail page
        'Category': 'N/A', # Subcategory
        'Phone': 'N/A',
        'Website': 'N/A',
        'Scrape Status': 'Success' # Track if scraping for this URL was successful
    }

    try:
        driver.get(detail_url)
        print("Waiting for detail page/panel to load...")

        # --- Wait for a reliable element on the detail page/panel ---
        # A good indicator is the main place name.
        # Selector based on provided HTML: <h1 class="DUwDvf lfPIob">...</h1>
        name_locator = (By.CSS_SELECTOR, "h1.DUwDvf.lfPIob") # Verified from provided HTML snippet - VERIFY!

        # Wait for the Name element to appear, as it's a primary indicator the page loaded
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(name_locator)
        )
        print("Detail page loaded and key element (Name) found.")
        time.sleep(3) # Small buffer for dynamic content

        # --- Scrape data from the DETAIL PANEL using the provided HTML snippets ---
        # !!! IMPORTANT: These selectors are based on the HTML snippets you provided.
        # They MUST be verified by inspecting the HTML of the detail page using
        # browser Developer Tools (F12). Google's HTML can vary.
        # Each scraping attempt is in a try/except to prevent one failure from stopping the rest.

        # --- Scrape Name ---
        try:
            # Selector based on provided HTML: h1.DUwDvf.lfPIob
            name_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(name_locator)) # Using the locator defined above
            data_item['Name'] = name_element.text.strip()
            # print(f"Scraped Name: {data_item['Name']}")
        except Exception as e:
            data_item['Scrape Status'] = f"Name Failed: {e}"
            print(f"Warning: Could not scrape Name for {detail_url}: {e}") # Log specific failure
            pass # Silently fail

        # --- Scrape Category / Subcategory ---
        try:
            # Selector based on provided HTML: <button class="DkEaL " jsaction="pane.wfvdle17.category">Spanish restaurant</button>
            # >>> VERIFY THIS SELECTOR <<<
            category_locator = (By.CSS_SELECTOR, "button.DkEaL[jsaction*='category']") # Verified from provided HTML snippet - VERIFY!
            category_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(category_locator))
            data_item['Category'] = category_element.text.strip()
            # Handle multiple categories separated by '·' if necessary
            # You might need to adjust the selector or use find_elements if there are multiple category buttons/spans
            # print(f"Scraped Category: {data_item['Category']}")
        except Exception as e:
             # data_item['Scrape Status'] += f"; Category Failed: {e}" # Optionally log failure
             print(f"Warning: Could not scrape Category for {detail_url}: {e}") # Log specific failure
             pass # Silently fail


        # --- Scrape Address ---
        try:
            # Using the more robust selector based on the data-item-id="address" button
            # provided in the latest HTML snippet.
            address_container_locator = (By.CSS_SELECTOR, "button[data-item-id='address']") # VERIFIED from provided HTML - USE THIS!
            address_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(address_container_locator)) # Increased wait

            address_text = "N/A" # Default

            # Try getting the address from the aria-label of the button first
            aria_label = address_element.get_attribute('aria-label')
            if aria_label and "Address:" in aria_label:
                 # Example aria-label: "Address: 6 E 36th St, New York, NY 10016 "
                 address_text = aria_label.replace("Address:", "", 1).strip()
                 # print(f"Scraped Address (from aria-label): {address_text}")

            # If aria-label didn't contain the address or wasn't found, try finding the nested div text
            if address_text == "N/A":
                 # Selector for the text div *inside* the address button structure
                 # Based on provided HTML: button[data-item-id='address'] ... div.Io6YTe.kR99db.fdkmkc
                 # Use a slightly less specific but potentially more stable selector inside the button
                 address_text_div_locator = (By.CSS_SELECTOR, "div.Io6YTe") # Check for Io6YTe inside the button - VERIFY!
                 try:
                      # Search *within* the found address_element (the button)
                      nested_address_element = address_element.find_element(*address_text_div_locator)
                      nested_address_text = nested_address_element.text.strip()
                      if nested_address_text:
                           address_text = nested_address_text
                           # print(f"Scraped Address (from nested div): {address_text}")
                 except Exception as nested_e:
                      # print(f"Warning: Could not find nested address div for {detail_url}: {nested_e}")
                      pass # Silently fail finding nested div


            data_item['Address'] = address_text # Store the result (N/A or scraped text)


        except Exception as e:
            # Log the specific failure if the button container wasn't found at all
            print(f"Warning: Could not scrape Address container for {detail_url}: {e}")
            # data_item['Scrape Status'] += f"; Address Failed: {e}" # Optionally add to status string
            pass # Silently fail in terms of data_item, but log error


        # --- Scrape Website ---
        try:
            # Selector based on provided HTML: <a class="CsEnBe" data-item-id="authority" href="...">...</a>
            # Look for link with Open website tooltip or similar. >>> VERIFY THIS SELECTOR <<<
            website_locator = (By.CSS_SELECTOR, "a.CsEnBe[data-item-id='authority']") # Verified from provided HTML snippet - VERIFY!
            website_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(website_locator))
            data_item['Website'] = website_element.get_attribute('href')
            # print(f"Scraped Website: {data_item['Website']}")
        except Exception as e:
            # data_item['Scrape Status'] += f"; Website Failed: {e}" # Optionally log failure
            print(f"Warning: Could not scrape Website for {detail_url}: {e}") # Log specific failure
            pass # Silently fail


        # --- Scrape Phone ---
        try:
            # Selector based on provided HTML: <button class="CsEnBe" data-item-id^="phone:">...<div class="AeaXub">...<div class="Io6YTe ...">Phone Text</div>...</div></button>
            # Look for element with Copy phone number tooltip or similar. >>> VERIFY THIS SELECTOR <<<
            # Using the data-item-id^='phone:' on the button container
            phone_container_locator = (By.CSS_SELECTOR, "button.CsEnBe[data-item-id^='phone:']") # VERIFIED from provided HTML - USE THIS!
            phone_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(phone_container_locator)) # Increased wait

            phone_text = "N/A" # Default

            # Try getting the phone from the aria-label of the button first
            aria_label = phone_element.get_attribute('aria-label')
            if aria_label and "Phone:" in aria_label:
                 # Example aria-label: "Phone: (212) 696-5036 "
                 phone_text = aria_label.replace("Phone:", "", 1).strip()
                 # print(f"Scraped Phone (from aria-label): {phone_text}")

            # If aria-label didn't work or wasn't found, try finding the nested div text
            if phone_text == "N/A":
                 # Selector for the text div *inside* the phone button structure
                 # Based on provided HTML: button[data-item-id^='phone:'] ... div.Io6YTe.kR99db.fdkmkc
                 # Use a slightly less specific but potentially more stable selector inside the button
                 phone_text_div_locator = (By.CSS_SELECTOR, "div.Io6YTe") # Check for Io6YTe inside the button - VERIFY!
                 try:
                      # Search *within* the found phone_element (the button)
                      nested_phone_element = phone_element.find_element(*phone_text_div_locator)
                      nested_phone_text = nested_phone_element.text.strip()
                      if nested_phone_text:
                           phone_text = nested_phone_text
                           # print(f"Scraped Phone (from nested div): {phone_text}")
                 except Exception as nested_e:
                      # print(f"Warning: Could not find nested phone div for {detail_url}: {nested_e}")
                      pass # Silently fail finding nested div

            data_item['Phone'] = phone_text # Store the result (N/A or scraped text)


        except Exception as e:
             # Log the specific failure if the button container wasn't found at all
             print(f"Warning: Could not scrape Phone container for {detail_url}: {e}")
             # data_item['Scrape Status'] += f"; Phone Failed: {e}" # Optionally add to status string
             pass # Silently fail


        # --- Add other fields here if needed (Rating, Review Count, Hours, etc.) ---
        # Remember to define locators and add try/except blocks for them


        # If primary data (like Name) wasn't scraped, mark as a scrape failure for this item
        # (This catch is already in the Name try/except, but good as a final check)
        if data_item['Name'] == 'N/A' and data_item['Scrape Status'] == 'Success':
             data_item['Scrape Status'] = f"Major Failure: Name Not Found"


        # print("--> Finished scraping detail page.")
        return data_item

    except Exception as e:
        # Catching errors during navigation or the initial wait for the Name element
        data_item['Scrape Status'] = f"Navigation/Load Failed: {e}"
        print(f"--> ERROR navigating or loading page {detail_url}: {e}")
        # Optionally print page source on error for debugging
        # try: print("Page source on error:", driver.page_source[:500])
        # except: pass
        return data_item # Return data_item with failure status


# --- Main Process: Scrape Details from Pre-collected Links ---
# This function orchestrates the process of scraping details from a provided list of URLs.
def run_scrape_from_links(business_urls, csv_filename="Maps_scraped_details_from_links.csv"):
    print("--- Step 0: Starting Detailed Scraper from Links Process ---")
    # Call the setup function
    driver, display = setup_driver()

    # Check if driver setup was successful
    if not driver:
        print("--- Process Aborted: Driver setup failed. ---")
        if display:
            try:
                display.stop()
            except: pass
        return pd.DataFrame() # Return empty DataFrame on failure

    # List to store dictionaries of extracted data
    scraped_data = []
    # DataFrame to store the final results
    df = pd.DataFrame()

    try: # Use a try block for the main process to ensure cleanup happens
        # --- Step 5: Iterate Through Provided URLs and Scrape ---
        print(f"\n--- Step 5: Starting Scraping from Provided URLs ({len(business_urls)} links) ---")

        if business_urls:
            for i, url in enumerate(business_urls):
                # Skip invalid or empty URLs
                if not url or url == 'N/A':
                    print(f"Skipping invalid URL at index {i}: {url}")
                    scraped_data.append({'Google Maps Link': url, 'Scrape Status': 'Skipped (Invalid URL)'})
                    continue

                print(f"\nProcessing URL {i+1}/{len(business_urls)}")
                # Call the function to scrape data from the detail page
                business_detail_data = scrape_detail_page_from_link(driver, url)
                scraped_data.append(business_detail_data)

                # Add a small pause between scraping pages to be less aggressive
                time.sleep(2) # Adjust as needed

        else:
            print("No URLs provided in the input list. Skipping scraping.")


        # --- Step 6: Creating Final DataFrame ---
        print(f"\n--- Step 6: Creating Final DataFrame ---")
        if scraped_data:
            # Define the columns in the desired order
            expected_columns = ['Google Maps Link', 'Name', 'Address', 'Category', 'Phone', 'Website', 'Scrape Status']
            df = pd.DataFrame(scraped_data, columns=expected_columns)
            print(f"DataFrame created with {len(df)} rows and {len(df.columns)} columns.")
        else:
            print("No data was scraped, creating empty DataFrame.")
            # Create DataFrame with expected columns even if empty
            expected_columns = ['Google Maps Link', 'Name', 'Address', 'Category', 'Phone', 'Website', 'Scrape Status']
            df = pd.DataFrame(columns=expected_columns)


        # --- Step 7: Exporting Data to CSV ---
        print(f"\n--- Step 7: Exporting Data to CSV ---")
        if not df.empty:
            try:
                csv_filename = csv_filename # Use the filename passed to the function
                df.to_csv(csv_filename, index=False)
                print(f"Data successfully saved to '{csv_filename}'")
                # If running in Google Colab, you can download the file:
                # try:
                #      # Make sure google.colab.files is imported at the top
                #      files.download(csv_filename)
                #      print(f"Attempting to download '{csv_filename}'...")
                # except NameError:
                #      print("Running outside Colab, skipping auto-download.")
                # except Exception as download_e:
                #      print(f"Could not initiate download in Colab: {download_e}")

            except Exception as e:
                print(f"--- ERROR during Step 7: Failed to save data to CSV ---")
                print(f"Error details: {e}")
        else:
            print("No data to export. CSV file not created.")


        # --- Step 8: Reporting and Displaying Final Extracted Data ---
        print(f"\n--- Step 8: Reporting and Displaying Final Extracted Data ---")
        print(f"Total records extracted and included in Final DataFrame: {len(df)}")
        if not df.empty:
             print("\nFinal Extracted Data (All rows):")

             # Ensure pandas options allow full display for this final print
             pd.set_option('display.max_rows', None)
             pd.set_option('display.max_columns', None)
             # pd.set_option('display.width', None) # Optional

             # Display the entire DataFrame
             try:
                  # Use to_markdown for cleaner text output in environments that support it
                  print(df.to_markdown(index=False))
                  # If markdown doesn't look right, use display(df)
                  # display(df)
             except ImportError:
                   print(df) # Fallback print

             # Report on scrape statuses
             print("\nScrape Status Summary:")
             print(df['Scrape Status'].value_counts())


        else:
            print("No data to display.")


    except Exception as e:
        # Catching unexpected exceptions during the process
        print(f"\n--- UNEXPECTED ERROR during full scraping process ---")
        print(f"Error details: {e}")
        print("Attempting cleanup and returning any DataFrame created before the error.")
        # Ensure df exists even on error
        if 'df' not in locals():
             df = pd.DataFrame() # Create empty DataFrame if it was not created
        # Try creating final df from scraped_data if an error occurred before final df creation
        elif scraped_data and df.empty:
             try:
                 expected_cols = ['Google Maps Link', 'Name', 'Address', 'Category', 'Phone', 'Website', 'Scrape Status']
                 df = pd.DataFrame(scraped_data, columns=expected_cols)
                 print("DataFrame created from scraped_data after unexpected error.")
             except:
                 df = pd.DataFrame(columns=expected_cols) # Still fail if cannot create


    finally: # This block always runs whether there was an error or not
        print("\n--- Step 9: Cleaning up Selenium Driver and Virtual Display ---")
        if driver:
            try:
                driver.quit()
                print("Selenium driver closed.")
            except Exception as e:
                print(f"--- ERROR during Step 9: Error closing driver ---")
                print(f"Error details: {e}")

        if display:
            try:
                display.stop()
                print("Virtual display stopped.")
            except Exception as e:
                print(f"--- ERROR during Step 9: Error stopping virtual display ---")
                print(f"Error details: {e}")

    # Return the DataFrame containing the extracted data (might be empty or partial)
    return df

# --- Run the Detailed Scraper from Links Process ---
# --- Step 0: Input Your List of Google Maps URLs Here ---
# Replace the empty list below with the list of URLs you collected from the previous script.
# Example: business_links_to_scrape = ['https://www.google.com/maps/place/Banter+NYC+-+Murray+Hill/data=!4m7!3m6!1s0x89c259090455a375:0x2f3660fb084c781f!8m2!3d40.7437965!4d-73.9791166!16s%2Fg%2F11y2nwj0t2!19sChIJdaNVBAlZwokRH3hMCPtgNi8?authuser=0&hl=en&rclk=1', 'https://www.google.com/maps/place/Toledo+Restaurant/data=!4m7!3m6!1s0x89c259a9e2206527:0x679b5f6a0dd4ed32!8m2!3d40.7492904!4d-73.9830756!16s%2Fg%2F1hlgdbctw!19sChIJJ2Ug4qlZwokRMu3UDWpfm2c?authuser=0&hl=en&rclk=1']



output_csv_filename = "10036.csv" # You can change the filename

print(f"\n--- Running the Detailed Scraper from Provided Links ---")
# Execute the main process function
final_extracted_data_df = run_scrape_from_links(business_links_to_scrape_10036, csv_filename=output_csv_filename)

print("\n--- Overall Scraping from Links Process Finished ---")
print(f"Final DataFrame contains {len(final_extracted_data_df)} records.")
if not final_extracted_data_df.empty:
     print(f"Data should be saved as '{output_csv_filename}' and potentially downloaded.")


# The 'final_extracted_data_df' DataFrame now holds the extracted data from all URLs.
# You can perform further analysis here if needed.
# print("\nFinal Collected DataFrame Head:")
# print(final_extracted_data_df.head())


# --- END OF COMPLETE SCRIPT (Scrape Details from Pre-collected Links - Updated Address Logic) ---
